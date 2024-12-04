from flask import Flask, request, jsonify
import tensorflow as tf
import pandas as pd
import numpy as np
import os
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from functools import wraps
import jwt
from datetime import datetime, timedelta
import bcrypt
from dotenv import load_dotenv
import secrets

# Load environment variables
load_dotenv()

# Initialize Flask application
app = Flask(__name__)

# Get secret key from environment or generate a secure one
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
if not app.config['SECRET_KEY']:
    # Generate a secure secret key if not in environment
    app.config['SECRET_KEY'] = secrets.token_hex(32)
    # Save it to .env file
    with open('.env', 'a') as f:
        f.write(f"\nSECRET_KEY={app.config['SECRET_KEY']}")

# Initialize Firebase based on environment
def initialize_firebase():
    """Initialize Firebase with appropriate credentials"""
    try:
        # For Cloud Run, this will use the default credentials
        firebase_admin.initialize_app(options={
            'projectId': 'bolatix-test'
        })
    except Exception as e:
        # Fallback to service account file for local development
        cred = credentials.Certificate('serviceAccountKey.json')
        firebase_admin.initialize_app(cred)
    print("Firebase initialized successfully")

# Initialize Firebase and get Firestore client
initialize_firebase()
db = firestore.client()

# Model and dataset paths
HISTORY_MODEL_PATH = "models/history.h5"
COLDSTART_MODEL_PATH = "models/cold_start.h5"
DATASET_PATH = "data/dataset.csv"

# Check availability of models and dataset
USE_DUMMY = not (os.path.exists(HISTORY_MODEL_PATH) and
                os.path.exists(COLDSTART_MODEL_PATH) and
                os.path.exists(DATASET_PATH))

if not USE_DUMMY:
    # Load models
    try:
        model_history = tf.keras.models.load_model(HISTORY_MODEL_PATH)
        model_coldstart = tf.keras.models.load_model(COLDSTART_MODEL_PATH)
        print("Models loaded successfully")
    except Exception as e:
        print(f"Error loading models: {e}")
        USE_DUMMY = True

    # Load match dataset
    dataset = pd.read_csv(DATASET_PATH)

def get_user_data(user_id):
    """Get user data from Firestore"""
    user_ref = db.collection('users').document(user_id)
    user = user_ref.get()
    if user.exists:
        return user.to_dict()
    return None

def user_has_history(user_id):
    """Check if user has ticket purchase history"""
    user_data = get_user_data(user_id)
    if user_data:
        return len(user_data.get('purchase_history', [])) > 0
    return False

def get_recommendations_history(user_id):
    """Generate recommendations based on user's purchase history using ML model"""
    user_data = get_user_data(user_id)
    if not user_data:
        return []

    purchase_history = user_data.get('purchase_history', [])
    if not purchase_history:
        return []

    # Find matches involving teams from purchase history
    relevant_teams = set()
    for purchase in purchase_history:
        home_team, away_team = purchase['match'].split(" vs ")
        relevant_teams.add(home_team)
        relevant_teams.add(away_team)

    # Use ML model for recommendations
    if USE_DUMMY:
        # Fallback to simple recommendation if model not available
        recommendations = []
        for _, match in dataset.iterrows():
            if match['Home'].strip() in relevant_teams or match['Away'].strip() in relevant_teams:
                recommendations.append({
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
                    "suggested_action": "Consider buying tickets"
                })
        return recommendations[:10]
    else:
        # Use ML model for recommendations
        # Implement your ML model prediction logic here
        return process_predictions(model_history.predict(user_data))

def get_recommendations_new_user(favorite_team):
    """Generate recommendations for new users based on their favorite team"""
    if USE_DUMMY:
        # Simple recommendation based on favorite team
        recommendations = []
        for _, match in dataset.iterrows():
            if favorite_team in [match['Home'].strip(), match['Away'].strip()]:
                recommendations.append({
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
                    "suggested_action": "New match for you!"
                })
        return recommendations[:10]
    else:
        # Use cold start model for recommendations
        return process_predictions(model_coldstart.predict([favorite_team]))

def generate_token(user_id):
    """Generate JWT token"""
    try:
        # Token never expires (no 'exp' claim)
        payload = {
            'iat': datetime.utcnow(),
            'sub': user_id,
            'type': 'persistent'  # Mark as persistent token
        }
        return jwt.encode(
            payload,
            app.config['SECRET_KEY'],
            algorithm='HS256'
        )
    except Exception as e:
        return None

def verify_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'error': 'Token is missing'}), 401
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
            
        try:
            # Decode without expiration verification
            payload = jwt.decode(
                token, 
                app.config['SECRET_KEY'],
                algorithms=['HS256'],
                options={"verify_exp": False}  # Don't verify expiration
            )
            request.user_id = payload['sub']
            
            # Check if token is marked as invalidated in Firestore
            user_ref = db.collection('users').document(payload['sub'])
            user_data = user_ref.get().to_dict()
            
            if user_data.get('token_invalidated_at'):
                # Token was invalidated (user logged out)
                return jsonify({'error': 'Token has been invalidated'}), 401
                
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
            
        return f(*args, **kwargs)
    return decorated_function

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.json
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password are required'}), 400
            
        # Check if user already exists
        users_ref = db.collection('users')
        existing_user = users_ref.where('email', '==', data['email']).get()
        
        if len(list(existing_user)) > 0:
            return jsonify({'error': 'Email already registered'}), 409
            
        # Hash password
        hashed = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())
        
        # Create user document with profile data
        user_data = {
            'email': data['email'],
            'password': hashed.decode('utf-8'),
            'created_at': firestore.SERVER_TIMESTAMP,
            'name': data.get('name', ''),
            'favorite_team': data.get('favorite_team', ''),
            'profile': data.get('profile', {}),
            'updated_at': firestore.SERVER_TIMESTAMP
        }
        
        # Add user to Firestore
        new_user_ref = users_ref.document()
        new_user_ref.set(user_data)
        
        # Generate token
        token = generate_token(new_user_ref.id)
        
        # Return response without sensitive data
        response_data = {
            'email': user_data['email'],
            'name': user_data['name'],
            'favorite_team': user_data['favorite_team'],
            'profile': user_data['profile']
        }
        
        return jsonify({
            'message': 'User registered successfully',
            'token': token,
            'user_id': new_user_ref.id,
            'user': response_data
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login user"""
    try:
        data = request.json
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password are required'}), 400
            
        # Find user
        users_ref = db.collection('users')
        user_docs = users_ref.where('email', '==', data['email']).get()
        
        if not user_docs:
            return jsonify({'error': 'Invalid credentials'}), 401
            
        user_doc = list(user_docs)[0]
        user_data = user_doc.to_dict()
        
        # Check password
        if not bcrypt.checkpw(data['password'].encode('utf-8'), user_data['password'].encode('utf-8')):
            return jsonify({'error': 'Invalid credentials'}), 401
            
        # Clear any previous token invalidation
        user_doc.reference.update({
            'token_invalidated_at': None
        })
        
        # Generate new persistent token
        token = generate_token(user_doc.id)
        
        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user_id': user_doc.id
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auth/logout', methods=['POST'])
@verify_token
def logout():
    """Logout user by invalidating their token"""
    try:
        user_id = request.user_id
        
        # Mark token as invalidated in Firestore
        user_ref = db.collection('users').document(user_id)
        user_ref.update({
            'token_invalidated_at': firestore.SERVER_TIMESTAMP
        })
        
        return jsonify({
            'message': 'Successfully logged out'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<user_id>', methods=['GET'])
@verify_token
def read_user(user_id):
    """Get user data by ID"""
    try:
        # Verify user can only access their own data
        if user_id != request.user_id:
            return jsonify({'error': 'Unauthorized access'}), 403
            
        user_data = get_user_data(user_id)
        if user_data:
            # Remove sensitive data
            if 'password' in user_data:
                del user_data['password']
            return jsonify({
                'status': 'success',
                'data': user_data
            }), 200
        return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<user_id>', methods=['PUT'])
@verify_token
def update_user(user_id):
    """Update user data"""
    try:
        if user_id != request.user_id:
            return jsonify({'error': 'Unauthorized access'}), 403
            
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        user_ref = db.collection('users').document(user_id)
        if not user_ref.get().exists:
            return jsonify({'error': 'User not found'}), 404
            
        # Don't allow password update through this endpoint
        if 'password' in data:
            del data['password']
        
        # Update user data with timestamp
        data['updated_at'] = firestore.SERVER_TIMESTAMP
        user_ref.update(data)
        
        # Get updated user data
        updated_data = user_ref.get().to_dict()
        if 'password' in updated_data:
            del updated_data['password']
            
        return jsonify({
            'message': 'User updated successfully',
            'data': updated_data
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<user_id>', methods=['DELETE'])
@verify_token
def delete_user(user_id):
    """Delete user"""
    try:
        if user_id != request.user_id:
            return jsonify({'error': 'Unauthorized access'}), 403
            
        user_ref = db.collection('users').document(user_id)
        if not user_ref.get().exists:
            return jsonify({'error': 'User not found'}), 404
            
        # Delete user
        user_ref.delete()
        return jsonify({
            'status': 'success',
            'message': 'User deleted successfully'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recommend', methods=['POST'])
@verify_token
def recommend():
    """Endpoint to get match recommendations"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        user_id = data.get('user_id')
        favorite_team = data.get('favorite_team')

        if not user_id or not favorite_team:
            return jsonify({"error": "user_id and favorite_team must be provided."}), 400

        if user_has_history(user_id):
            # User with purchase history
            recommendations = get_recommendations_history(user_id)
        else:
            # New user without purchase history
            recommendations = get_recommendations_new_user(favorite_team)

        return jsonify({
            "status": "success",
            "recommendations": recommendations
        })

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

def process_predictions(predictions):
    """Process ML model prediction results into readable recommendation format"""
    recommendations = []
    for idx, score in enumerate(predictions[0]):
        match = dataset.iloc[idx]
        recommendations.append({
            "id_match": match['ID Match'],
            "home_team": match['Home'].strip(),
            "away_team": match['Away'].strip(),
            "tanggal": match['Tanggal'].strip(),
            "jam": match['Jam'].rsplit(':', 1)[0],
            "stadion": match['Stadion'],
            "lokasi": match['Lokasi'],
            "tiket_terjual": match['Jumlah Tiket Terjual'],
            "score": float(score)
        })
    return sorted(recommendations, key=lambda x: x['score'], reverse=True)[:10]

if __name__ == '__main__':
    app.run(debug=True)