from flask import Flask, request, jsonify
import tensorflow as tf
import pandas as pd
import numpy as np
import os

app = Flask(__name__)

# Path ke model dan dataset
HISTORY_MODEL_PATH = "models/History.h5"
COLDSTART_MODEL_PATH = "models/ColdStart.h5"
DATASET_PATH = "DATASET - data liga 1.csv"

# Dummy data untuk pengembangan
DUMMY_USERS = {
    "user123": {
        "favorite_team": "Persib",
        "purchase_history": [
            {
                "ID Match": 1,
                "Match": "Persib vs PSBS Biak",
                "Lokasi": "Bandung",
                "Jam": "20:00:00",
                "purchase_date": "2024-08-01"
            },
            {
                "ID Match": 7,
                "Match": "Persebaya vs PSS Sleman",
                "Lokasi": "Surabaya",
                "Jam": "20:00:00",
                "purchase_date": "2024-08-05"
            }
        ]
    },
    "user456": {
        "favorite_team": "Persija",
        "purchase_history": []
    }
}

# Validasi keberadaan model dan dataset
USE_DUMMY = not (os.path.exists(HISTORY_MODEL_PATH) and
                 os.path.exists(COLDSTART_MODEL_PATH) and
                 os.path.exists(DATASET_PATH))

if not USE_DUMMY:
    # Load model History dan ColdStart
    model_history = tf.keras.models.load_model(
        HISTORY_MODEL_PATH,
        custom_objects={'mse': tf.keras.losses.MeanSquaredError()}
    )
    model_coldstart = tf.keras.models.load_model(
        COLDSTART_MODEL_PATH,
        custom_objects={'mse': tf.keras.losses.MeanSquaredError()}
    )

    # Load dataset
    dataset = pd.read_csv(DATASET_PATH)

@app.route('/recommend', methods=['POST'])
def recommend():
    #Endpoint untuk mendapatkan rekomendasi pertandingan
    if not request.is_json:
        return jsonify({"error": "Request harus berupa JSON."}), 400
    
    data = request.get_json()

    # Validasi apakah user_id dan favorite_team ada dalam request
    user_id = data.get('user_id')
    favorite_team = data.get('favorite_team')

    if not user_id or not favorite_team:
        return jsonify({"error": "user_id dan favorite_team harus disediakan."}), 400

    try:
        if USE_DUMMY:
            # Menggunakan data dummy jika model/dataset tidak ada
            if user_id in DUMMY_USERS:
                recommendations = get_dummy_recommendations(user_id)
            else:
                recommendations = get_dummy_recommendations_new_user(favorite_team)
        else:
            # Gunakan model untuk menghasilkan rekomendasi
            if user_has_history(user_id):
                recommendations = get_recommendations_history(user_id)
            else:
                recommendations = get_recommendations_new_user(favorite_team)

        return jsonify({
            "status": "success",
            "recommendations": recommendations
        })

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

def user_has_history(user_id):
    #Memeriksa apakah pengguna memiliki riwayat pembelian berdasarkan user_id
    if user_id in DUMMY_USERS:
        # Jika menggunakan data dummy, periksa apakah ada riwayat pembelian untuk user_id
        user_data = DUMMY_USERS[user_id]
        return len(user_data.get('purchase_history', [])) > 0
    else:
        # Jika menggunakan dataset yang nyata, periksa apakah ada riwayat pembelian untuk user_id
        user_data = dataset[dataset['user_id'] == user_id]
        return not user_data.empty

def get_recommendations_history(user_id):
    #Menghasilkan rekomendasi berdasarkan riwayat pengguna
    if user_id in DUMMY_USERS:
        # Jika menggunakan data dummy
        user_data = DUMMY_USERS[user_id]
        purchase_history = user_data.get('purchase_history', [])
        
        # Temukan pertandingan yang melibatkan tim Match berdasarkan history dummy
        relevant_teams = set()
        for purchase in purchase_history:
            Home_team, Away_team = purchase['Match'].split(" vs ")
            relevant_teams.add(Home_team)
            relevant_teams.add(Away_team)
        
        # Mencari pertandingan yang relevan dengan tim Match berdasarkan history dummy
        recommendations = []
        for _, Match in dataset.iterrows():
            if Match['Home'] in relevant_teams or Match['Away'] in relevant_teams:
                recommendations.append({
                    "Match": f"{Match['Home']} vs {Match['Away']}",
                    "Lokasi": Match['Lokasi'],
                    "Jam": Match['Jam'],
                    "Stadion": Match['Stadion'],
                    "suggested_action": "Consider buying tickets"
                })
        return recommendations[:10]
    else:
        # Jika menggunakan dataset yang sesungguhnya
        user_data = dataset[dataset['user_id'] == user_id]
        if user_data.empty:
            return {"error": "Data pengguna tidak ditemukan."}

        # Ambil fitur yang relevan dari dataset
        features = user_data[['ID Match', 'Home', 'Away', 'Stadion', 'Lokasi']].values

        # Prediksi menggunakan model History
        predictions = model_history.predict(features)

        # Proses hasil prediksi
        return process_predictions(predictions)

def get_recommendations_new_user(favorite_team):
    #Menghasilkan rekomendasi untuk pengguna baru berdasarkan tim favorit.
    # Filter data dari dataset untuk mencari pertandingan dengan tim favorit
    relevant_Matches = dataset[(dataset['Home'] == favorite_team) | (dataset['Away'] == favorite_team)]
    
    recommendations = []
    for _, Match in relevant_Matches.iterrows():
        recommendations.append({
            "ID Match": Match['ID Match'],
            "Home_team": Match['Home'],
            "Away_team": Match['Away'],
            "Tanggal": Match['Tanggal'],
            "Jam": Match['Jam'],
            "Stadion": Match['Stadion'],
            "Lokasi": Match['Lokasi'],
            "Jumlah Tiket Terjual": Match['Jumlah Tiket Terjual'],
            "score": 0 
        })
    
    return recommendations

def process_predictions(predictions):
    # Memproses hasil prediksi menjadi format rekomendasi
    recommendations = []
    for idx, score in enumerate(predictions[0]):
        Match = dataset.iloc[idx]
        recommendations.append({
            "ID Match": Match['ID Match'],
            "Home_team": Match['Home'],
            "Away_team": Match['Away'],
            "Tanggal": Match['Tanggal'],
            "Jam": Match['Jam'],
            "Stadion": Match['Stadion'],
            "Lokasi": Match['Lokasi'],
            "Jumlah Tiket Terjual": Match['Jumlah Tiket Terjual'],
            "score": float(score)
        })
    return sorted(recommendations, key=lambda x: x['score'], reverse=True)[:10]

def get_dummy_recommendations(user_id):
    #Menghasilkan rekomendasi dummy berdasarkan riwayat
    user_data = DUMMY_USERS.get(user_id, {})
    purchase_history = user_data.get('purchase_history', [])
    
    # Temukan pertandingan yang melibatkan tim Match berdasarkan riwayat 
    relevant_teams = set()
    for purchase in purchase_history:
        Home_team, Away_team = purchase['Match'].split(" vs ")
        relevant_teams.add(Home_team)
        relevant_teams.add(Away_team)
    
    recommendations = []
    for _, Match in dataset.iterrows():
        if Match['Home'] in relevant_teams or Match['Away'] in relevant_teams:
            recommendations.append({
                "Match": f"{Match['Home']} vs {Match['Away']}",
                "Lokasi": Match['Lokasi'],
                "Jam": Match['Jam'],
                "Stadion": Match['Stadion'],
                "suggested_action": "Buy ticket again"
            })
    return recommendations[:10]

def get_dummy_recommendations_new_user(favorite_team):
    #Menghasilkan rekomendasi dummy untuk pengguna baru
    recommendations = [
        {"Match": f"{favorite_team} vs Random FC", "Lokasi": "Stadion A", "Jam": "19:00:00"},
        {"Match": f"{favorite_team} vs Sample United", "Lokasi": "Stadion B", "Jam": "20:00:00"}
    ]
    return recommendations

if __name__ == '__main__':
    app.run(debug=True)
