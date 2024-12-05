from flask import Flask, request, jsonify
import tensorflow as tf
import pandas as pd
import numpy as np
import os
import firebase_admin
from firebase_admin import credentials, firestore
from functools import wraps
import jwt
from datetime import datetime, timedelta
import bcrypt
from dotenv import load_dotenv
import secrets
from google.cloud import storage
import uuid
from werkzeug.utils import secure_filename

# Load environment variables and initialize app
load_dotenv()
app = Flask(__name__)

# Configure secret key
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY') or secrets.token_hex(32)
if not os.getenv('SECRET_KEY'):
    with open('.env', 'a') as f:
        f.write(f"\nSECRET_KEY={app.config['SECRET_KEY']}")

# Initialize Firebase
try:
    firebase_admin.initialize_app(options={'projectId': 'bolatix-test'})
except Exception:
    cred = credentials.Certificate('serviceAccountKey.json')
    firebase_admin.initialize_app(cred)
db = firestore.client()

# Initialize Google Cloud Storage client
storage_client = storage.Client(project='bolatix-test')
BUCKET_NAME = 'bolatix-user-profiles'
bucket = storage_client.bucket(BUCKET_NAME)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def upload_profile_picture(file, user_id):
    if not file or not allowed_file(file.filename):
        return None
        
    # Create a unique filename
    original_extension = file.filename.rsplit('.', 1)[1].lower()
    filename = f"profile_pictures/{user_id}/{str(uuid.uuid4())}.{original_extension}"
    
    # Upload to Google Cloud Storage
    blob = bucket.blob(filename)
    blob.upload_from_string(
        file.read(),
        content_type=file.content_type
    )
    
    # Make the blob publicly readable
    blob.make_public()
    
    return blob.public_url

# Model and dataset paths
HISTORY_MODEL_PATH = "models/history.h5"
COLDSTART_MODEL_PATH = "models/cold_start.h5"
DATASET_PATH = "data/dataset.csv"

# Check model and dataset availability
USE_DUMMY = not all(os.path.exists(path) for path in [HISTORY_MODEL_PATH, COLDSTART_MODEL_PATH, DATASET_PATH])

# Load dataset globally
try:
    dataset = pd.read_csv(DATASET_PATH)
except Exception as e:
    print(f"Error loading dataset: {e}")
    dataset = pd.DataFrame()

if not USE_DUMMY:
    try:
        model_history = tf.keras.models.load_model(HISTORY_MODEL_PATH)
        model_coldstart = tf.keras.models.load_model(COLDSTART_MODEL_PATH)
    except Exception as e:
        print(f"Error loading models: {e}")
        USE_DUMMY = True

def get_user_data(user_id):
    doc = db.collection('users').document(user_id).get()
    return doc.to_dict() if doc.exists else None

def generate_token(user_id):
    try:
        payload = {
            'iat': datetime.utcnow(),
            'sub': user_id,
            'type': 'persistent'
        }
        return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')
    except Exception:
        return None

def verify_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.split(" ")[1] if len(auth_header.split()) > 1 else None
        
        if not token:
            return jsonify({'status': False, 'message': 'Token is missing'}), 401
            
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], 
                               algorithms=['HS256'], options={"verify_exp": False})
            request.user_id = payload['sub']
            
            user_data = get_user_data(payload['sub'])
            if user_data and user_data.get('token_invalidated_at'):
                return jsonify({'status': False, 'message': 'Token has been invalidated'}), 401
                
        except jwt.InvalidTokenError:
            return jsonify({'status': False, 'message': 'Invalid token'}), 401
            
        return f(*args, **kwargs)
    return decorated

def format_match_recommendation(match, action="Consider buying tickets"):
    return {
        "match": match['Match'],
        "home_team": match['Home'].strip(),
        "away_team": match['Away'].strip(),
        "lokasi": match['Lokasi'],
        "jam": match['Jam'].rsplit(':', 1)[0],
        "waktu": match['Waktu'],
        "stadion": match['Stadion'],
        "hari": match['Hari'],
        "tanggal": match['Tanggal'],
        "tiket_terjual": int(match['Jumlah Tiket Terjual']),
        "suggested_action": action
    }

def get_recommendations_history(user_id):
    user_data = get_user_data(user_id)
    if not user_data or not user_data.get('purchase_history'):
        return []

    relevant_teams = {team.strip() for purchase in user_data['purchase_history']
                     for team in [purchase['home_team'], purchase['away_team']]}

    if USE_DUMMY:
        recommendations = [
            format_match_recommendation(match)
            for _, match in dataset.iterrows()
            if match['Home'].strip() in relevant_teams or match['Away'].strip() in relevant_teams
        ]
        return recommendations
    
    return process_predictions(model_history.predict(user_data))

def get_recommendations_new_user(favorite_team):
    if USE_DUMMY:
        recommendations = [
            format_match_recommendation(match, "New match for you!")
            for _, match in dataset.iterrows()
            if favorite_team in [match['Home'].strip(), match['Away'].strip()]
        ]
        return recommendations[:10]
    
    return process_predictions(model_coldstart.predict([favorite_team]))

def process_predictions(predictions):
    """Process ML model prediction results into readable recommendation format"""
    try:
        if dataset.empty:
            return []
            
        recommendations = []
        for idx, score in enumerate(predictions[0]):
            match = dataset.iloc[idx]
            recommendations.append({
                "id_match": str(match['ID Match']),
                "home_team": match['Home'].strip(),
                "away_team": match['Away'].strip(),
                "tanggal": match['Tanggal'].strip(),
                "jam": match['Jam'].rsplit(':', 1)[0],
                "stadion": match['Stadion'],
                "lokasi": match['Lokasi'],
                "tiket_terjual": int(match['Jumlah Tiket Terjual']),
                "score": float(score)
            })
        return sorted(recommendations, key=lambda x: x['score'], reverse=True)[:10]
    except Exception as e:
        print(f"Error processing predictions: {e}")
        return []

# API Endpoints
@app.route('/api/auth/register', methods=['POST'])
def register():
    try:
        data = request.json
        if not all(key in data for key in ['email', 'password']):
            return jsonify({
                'status': False,
                'message': 'Email and password are required'
            }), 400
            
        existing = db.collection('users').where('email', '==', data['email']).get()
        if len(list(existing)) > 0:
            return jsonify({
                'status': False,
                'message': 'Email already registered'
            }), 409
            
        user_data = {
            'email': data['email'],
            'password': bcrypt.hashpw(data['password'].encode('utf-8'), 
                                    bcrypt.gensalt()).decode('utf-8'),
            'name': data.get('name', ''),
            'favorite_team': data.get('favorite_team', ''),
            'birth_date': data.get('birth_date'),
            'profile_picture': data.get('profile_picture', ''),
            'purchase_history': []
        }
        
        new_user_ref = db.collection('users').document()
        
        user_data_with_timestamps = {
            **user_data,
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP
        }
        new_user_ref.set(user_data_with_timestamps)
        
        token = generate_token(new_user_ref.id)
        
        response_data = {k: v for k, v in user_data.items() 
                        if k not in ['password']}
        
        return jsonify({
            'status': True,
            'message': 'User registered successfully',
            'data': {
                'token': token,
                'user_id': new_user_ref.id,
                'user': response_data
            }
        }), 201
        
    except Exception as e:
        return jsonify({
            'status': False,
            'message': str(e)
        }), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.json
        if not all(key in data for key in ['email', 'password']):
            return jsonify({
                'status': False,
                'message': 'Email and password are required'
            }), 400
            
        users = list(db.collection('users').where('email', '==', data['email']).get())
        if not users:
            return jsonify({
                'status': False,
                'message': 'Invalid credentials'
            }), 401
            
        user = users[0]
        user_data = user.to_dict()
        
        if not bcrypt.checkpw(data['password'].encode('utf-8'), 
                            user_data['password'].encode('utf-8')):
            return jsonify({
                'status': False,
                'message': 'Invalid credentials'
            }), 401
            
        user.reference.update({'token_invalidated_at': None})
        token = generate_token(user.id)
        
        return jsonify({
            'status': True,
            'message': 'Login successful',
            'data': {
                'token': token,
                'user_id': user.id
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': False,
            'message': str(e)
        }), 500

@app.route('/api/auth/logout', methods=['POST'])
@verify_token
def logout():
    try:
        user_ref = db.collection('users').document(request.user_id)
        user_ref.update({'token_invalidated_at': firestore.SERVER_TIMESTAMP})
        return jsonify({
            'status': True,
            'message': 'Logout successful'
        }), 200
    except Exception as e:
        return jsonify({
            'status': False,
            'message': str(e)
        }), 500

@app.route('/api/users/<user_id>', methods=['GET'])
@verify_token
def read_user(user_id):
    try:
        if request.user_id != user_id:
            return jsonify({
                'status': False,
                'message': 'Unauthorized access'
            }), 403
            
        user_data = get_user_data(user_id)
        if not user_data:
            return jsonify({
                'status': False,
                'message': 'User not found'
            }), 404
            
        user_data.pop('password', None)
        return jsonify({
            'status': True,
            'message': 'User data retrieved successfully',
            'data': user_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': False,
            'message': str(e)
        }), 500

@app.route('/api/users/<user_id>', methods=['PUT'])
@verify_token
def update_user(user_id):
    try:
        if request.user_id != user_id:
            return jsonify({
                'status': False,
                'message': 'Unauthorized access'
            }), 403
            
        data = request.json
        if not data:
            return jsonify({
                'status': False,
                'message': 'No data provided for update'
            }), 400
            
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            return jsonify({
                'status': False,
                'message': 'User not found'
            }), 404
            
        update_data = {}
        allowed_fields = ['name', 'favorite_team', 'birth_date', 'profile_picture']
        for field in allowed_fields:
            if field in data:
                update_data[field] = data[field]
                
        update_data_with_timestamp = {
            **update_data,
            'updated_at': firestore.SERVER_TIMESTAMP
        }
        
        user_ref.update(update_data_with_timestamp)
        
        return jsonify({
            'status': True,
            'message': 'User updated successfully',
            'data': update_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': False,
            'message': str(e)
        }), 500

@app.route('/api/users/<user_id>', methods=['DELETE'])
@verify_token
def delete_user(user_id):
    try:
        if request.user_id != user_id:
            return jsonify({
                'status': False,
                'message': 'Unauthorized access'
            }), 403
            
        user_ref = db.collection('users').document(user_id)
        if not user_ref.get().exists:
            return jsonify({
                'status': False,
                'message': 'User not found'
            }), 404
            
        user_ref.delete()
        return jsonify({
            'status': True,
            'message': 'User deleted successfully'
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': False,
            'message': str(e)
        }), 500

@app.route('/api/users/<user_id>/purchases', methods=['POST'])
@verify_token
def add_purchase(user_id):
    try:
        if request.user_id != user_id:
            return jsonify({
                'status': False,
                'message': 'Unauthorized access'
            }), 403
            
        data = request.json
        required_fields = [
            'match_id', 'home_team', 'away_team', 'stadium', 
            'match_date', 'purchase_date', 'ticket_quantity'
        ]
        if not all(field in data for field in required_fields):
            return jsonify({
                'status': False,
                'message': f'Required fields: {", ".join(required_fields)}'
            }), 400
            
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            return jsonify({
                'status': False,
                'message': 'User not found'
            }), 404
            
        purchase = {
            'match_id': data['match_id'],
            'home_team': data['home_team'],
            'away_team': data['away_team'],
            'stadium': data['stadium'],
            'match_date': data['match_date'],
            'purchase_date': data['purchase_date'],
            'ticket_quantity': data['ticket_quantity']
        }
        
        user_ref.update({
            'purchase_history': firestore.ArrayUnion([purchase])
        })
        
        return jsonify({
            'status': True,
            'message': 'Purchase added to history successfully',
            'data': purchase
        }), 201
        
    except Exception as e:
        return jsonify({
            'status': False,
            'message': str(e)
        }), 500

@app.route('/api/users/<user_id>/purchases', methods=['GET'])
@verify_token
def get_purchase_history(user_id):
    try:
        if request.user_id != user_id:
            return jsonify({
                'status': False,
                'message': 'Unauthorized access'
            }), 403
            
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            return jsonify({
                'status': False,
                'message': 'User not found'
            }), 404
            
        user_data = user_doc.to_dict()
        purchase_history = user_data.get('purchase_history', [])
        
        return jsonify({
            'status': True,
            'message': 'Purchase history retrieved successfully',
            'data': purchase_history
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': False,
            'message': str(e)
        }), 500

@app.route('/api/recommend', methods=['GET'])
@verify_token
def recommend():
    try:
        user_data = get_user_data(request.user_id)
        if not user_data:
            return jsonify({
                'status': False,
                'message': 'User not found'
            }), 404
            
        if USE_DUMMY:
            favorite_team = user_data.get('favorite_team', '')
            recommendations = [
                format_match_recommendation(match)
                for _, match in dataset.iterrows()
                if favorite_team and (favorite_team in [match['Home'].strip(), match['Away'].strip()])
            ][:10]
        else:
            if user_data.get('purchase_history'):
                predictions = model_history.predict([request.user_id])
            else:
                favorite_team = user_data.get('favorite_team')
                if not favorite_team:
                    return jsonify({
                        'status': False,
                        'message': 'Favorite team is required for recommendations'
                    }), 400
                predictions = model_coldstart.predict([[favorite_team]])
                
            recommendations = process_predictions(predictions)
            
        return jsonify({
            'status': True,
            'message': 'Recommendations retrieved successfully',
            'data': recommendations
        }), 200
        
    except Exception as e:
        print(f"Recommendation error: {e}")
        return jsonify({
            'status': False,
            'message': str(e)
        }), 500

@app.route('/api/users/<user_id>/profile-picture', methods=['POST'])
@verify_token
def update_profile_picture(user_id):
    try:
        if request.user_id != user_id:
            return jsonify({
                'status': False,
                'message': 'Unauthorized access'
            }), 403
            
        if 'profile_picture' not in request.files:
            return jsonify({
                'status': False,
                'message': 'No file provided'
            }), 400
            
        file = request.files['profile_picture']
        if file.filename == '':
            return jsonify({
                'status': False,
                'message': 'No file selected'
            }), 400
            
        if not allowed_file(file.filename):
            return jsonify({
                'status': False,
                'message': f'File type not allowed. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
            
        # Get user document
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            return jsonify({
                'status': False,
                'message': 'User not found'
            }), 404
            
        # Delete old profile picture if exists
        user_data = user_doc.to_dict()
        old_picture_url = user_data.get('profile_picture')
        if old_picture_url:
            try:
                old_blob_name = old_picture_url.split('/')[-1]
                old_blob = bucket.blob(f"profile_pictures/{user_id}/{old_blob_name}")
                old_blob.delete()
            except Exception:
                pass
                
        # Upload new profile picture
        picture_url = upload_profile_picture(file, user_id)
        if not picture_url:
            return jsonify({
                'status': False,
                'message': 'Failed to upload profile picture'
            }), 500
            
        # Update user document with new profile picture URL
        user_ref.update({
            'profile_picture': picture_url,
            'updated_at': firestore.SERVER_TIMESTAMP
        })
        
        return jsonify({
            'status': True,
            'message': 'Profile picture updated successfully',
            'data': {
                'profile_picture_url': picture_url
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': False,
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True)