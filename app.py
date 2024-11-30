from flask import Flask, request, jsonify
import tensorflow as tf
import pandas as pd
import numpy as np
import os

# Initialize Flask application
app = Flask(__name__)

# Define paths for models and dataset that will be used
HISTORY_MODEL_PATH = "models/history.h5"
COLDSTART_MODEL_PATH = "models/cold_start.h5"
DATASET_PATH = "data/dataset.csv"

# Dummy data for development
DUMMY_USERS = {
    "user1": {
        "favorite_team": "Persib",
        "purchase_history": [
            {
                "id_match": 1,
                "match": "Persib vs PSBS Biak",
                "lokasi": "Bandung",
                "jam": "20:00",
                "tanggal_pembelian": "2024-08-01"
            },
            {
                "id_match": 7,
                "match": "Persebaya vs PSS Sleman",
                "lokasi": "Surabaya",
                "jam": "20:00",
                "tanggal_pembelian": "2024-08-05"
            }
        ]
    },
    "user2": {
        "favorite_team": "Persebaya",
        "purchase_history": []
    }
}

# Check availability of models and dataset. If any file is missing, use dummy mode
USE_DUMMY = not (os.path.exists(HISTORY_MODEL_PATH) and
                 os.path.exists(COLDSTART_MODEL_PATH) and
                 os.path.exists(DATASET_PATH))

if not USE_DUMMY:
    # Load models for users with history and new users
    model_history = tf.keras.models.load_model(
        HISTORY_MODEL_PATH,
        custom_objects={'mse': tf.keras.losses.MeanSquaredError()}
    )
    model_coldstart = tf.keras.models.load_model(
        COLDSTART_MODEL_PATH,
        custom_objects={'mse': tf.keras.losses.MeanSquaredError()}
    )

    # Load match dataset
    dataset = pd.read_csv(DATASET_PATH)

@app.route('/recommend', methods=['POST'])
def recommend():
    """Endpoint to get match recommendations"""
    if not request.is_json:
        return jsonify({"error": "Request must be in JSON format."}), 400
    
    data = request.get_json()

    # Validate if user_id and favorite_team exist in the request
    user_id = data.get('user_id')
    favorite_team = data.get('favorite_team')

    if not user_id or not favorite_team:
        return jsonify({"error": "user_id and favorite_team must be provided."}), 400

    try:
        if USE_DUMMY:
            # Dummy mode: use sample data if models are not available
            if user_id in DUMMY_USERS:
                recommendations = get_dummy_recommendations(user_id)
            else:
                recommendations = get_dummy_recommendations_new_user(favorite_team)
        else:
            # Production mode: use ML model for recommendations
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

def user_has_history(user_id):
    """Check if user has ticket purchase history"""
    if user_id in DUMMY_USERS:
        # If using dummy data, check if there's purchase history for user_id
        user_data = DUMMY_USERS[user_id]
        return len(user_data.get('purchase_history', [])) > 0
    else:
        # If using real dataset, check if there's purchase history for user_id
        user_data = dataset[dataset['user_id'] == user_id]
        return not user_data.empty

def get_recommendations_history(user_id):
    """Generate recommendations based on user's purchase history using ML model"""
    if user_id in DUMMY_USERS:
        # If using dummy data
        user_data = DUMMY_USERS[user_id]
        purchase_history = user_data.get('purchase_history', [])
        
        # Find matches involving teams from purchase history
        relevant_teams = set()
        for purchase in purchase_history:
            home_team, away_team = purchase['match'].split(" vs ")
            relevant_teams.add(home_team)
            relevant_teams.add(away_team)
        
        # Search for matches relevant to the teams
        recommendations = []
        for _, match in dataset.iterrows():
            if match['Home'].strip() in relevant_teams or match['Away'].strip() in relevant_teams:
                recommendations.append({
                    "match": match['Match'],
                    "lokasi": match['Lokasi'],
                    "jam": match['Jam'].rsplit(':', 1)[0],
                    "stadion": match['Stadion'],
                    "suggested_action": "Consider buying tickets"
                })
        return recommendations[:10]
    else:
        # If using real dataset
        user_data = dataset[dataset['user_id'] == user_id]
        if user_data.empty:
            return {"error": "User data not found."}

        # Get relevant features from dataset
        features = user_data[['ID Match', 'Home', 'Away', 'Stadion', 'Lokasi']].values

        # Predict using History model
        predictions = model_history.predict(features)

        # Process prediction results
        return process_predictions(predictions)

def get_recommendations_new_user(favorite_team):
    """Generate recommendations for new users based on their favorite team"""
    # Filter data from dataset to find matches with favorite team
    relevant_matches = dataset[(dataset['Home'].str.strip() == favorite_team) | (dataset['Away'].str.strip() == favorite_team)]
    
    recommendations = []
    for _, match in relevant_matches.iterrows():
        recommendations.append({
            "id_match": match['ID Match'],
            "home_team": match['Home'].strip(),
            "away_team": match['Away'].strip(),
            "tanggal": match['Tanggal'].strip(),
            "jam": match['Jam'].rsplit(':', 1)[0],
            "stadion": match['Stadion'],
            "lokasi": match['Lokasi'],
            "tiket_terjual": match['Jumlah Tiket Terjual'],
            "score": 0
        })
    
    return recommendations

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

def get_dummy_recommendations(user_id):
    """Generate dummy recommendations based on history"""
    user_data = DUMMY_USERS.get(user_id, {})
    purchase_history = user_data.get('purchase_history', [])
    
    # Find matches involving teams from purchase history
    relevant_teams = set()
    for purchase in purchase_history:
        home_team, away_team = purchase['match'].split(" vs ")
        relevant_teams.add(home_team)
        relevant_teams.add(away_team)
    
    recommendations = []
    for _, match in dataset.iterrows():
        if match['Home'].strip() in relevant_teams or match['Away'].strip() in relevant_teams:
            recommendations.append({
                "id_match": match['ID Match'],
                "match": match['Match'],
                "lokasi": match['Lokasi'],
                "jam": match['Jam'].rsplit(':', 1)[0],
                "stadion": match['Stadion'],
                "suggested_action": "Buy ticket again"
            })
    return recommendations[:10]

def get_dummy_recommendations_new_user(favorite_team):
    """Generate dummy recommendations for new users"""
    recommendations = [
        {"match": f"{favorite_team} vs Random FC", "location": "Stadium A", "time": "19:00"},
        {"match": f"{favorite_team} vs Sample United", "location": "Stadium B", "time": "20:00"}
    ]
    return recommendations

if __name__ == '__main__':
    app.run(debug=True)