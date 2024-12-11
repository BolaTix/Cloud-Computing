# ⚽ BolaTix API Documentation

## 📚 Table of Contents

- [Authentication](#authentication)
  - [Register](#register)
  - [Login](#login)
  - [Logout](#logout)
- [User Management](#user-management)
  - [Get User Profile](#get-user-profile)
  - [Update User Profile](#update-user-profile)
  - [Delete User](#delete-user)
- [Purchase History](#purchase-history)
  - [Add Purchase](#add-purchase)
  - [Get Purchase History](#get-purchase-history)
- [Recommendations](#recommendations)
  - [Recommend Based on Favorite Team](#recommend-based-on-favorite-team)
  - [Recommend Based on Purchase History](#recommend-based-on-purchase-history)
- [All Data](#all-data)
  - [Get All Data](#get-all-data)
  - [Get Standings](#get-standings)
- [Profile Picture Management](#profile-picture-management)
  - [Get Profile Picture](#get-profile-picture)
  - [Upload/Replace Profile Picture](#uploadreplace-profile-picture)
  - [Delete Profile Picture](#delete-profile-picture)

## 🔐 Authentication

### Register

-   **Endpoint**: `/api/auth/register`
-   **Method**: `POST`
-   **Request Body**:

    ```json
    {
        "email": "user@example.com",
        "password": "securepassword123",
        "name": "John Doe",
        "favorite_team": "Persebaya"
    }
    ```

-   **Response** (201 Created):

    ```json
    {
        "status": true,
        "message": "User registered successfully",
        "data": {
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "user_id": "user123",
            "user": {
                "email": "user@example.com",
                "name": "John Doe",
                "favorite_team": "Persebaya"
            }
        }
    }
    ```

### Login

-   **Endpoint**: `/api/auth/login`
-   **Method**: `POST`
-   **Request Body**:

    ```json
    {
        "email": "user@example.com",
        "password": "securepassword123"
    }
    ```

-   **Response** (200 OK):

    ```json
    {
        "status": true,
        "message": "Login successful",
        "data": {
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "user_id": "user123"
        }
    }
    ```

### Logout

-   **Endpoint**: `/api/auth/logout`
-   **Method**: `POST`
-   **Headers**:

    ```
    Authorization: Bearer <your-token-here>
    ```

-   **Response** (200 OK):

    ```json
    {
        "status": true,
        "message": "Logout successful"
    }
    ```

## 👤 User Management

### Get User Profile

-   **Endpoint**: `/api/users/{user_id}`
-   **Method**: `GET`
-   **Response** (200 OK):

    ```json
    {
        "status": true,
        "message": "User data retrieved successfully",
        "data": {
            "email": "user@example.com",
            "name": "John Doe",
            "favorite_team": "Persebaya",
            "created_at": "2024-03-15T10:30:00Z",
            "updated_at": "2024-03-15T10:30:00Z"
        }
    }
    ```

### Update User Profile

-   **Endpoint**: `/api/users/{user_id}`
-   **Method**: `PUT`
-   **Request Body**:

    ```json
    {
        "name": "Jane Doe",
        "birth_date": "1999-05-10"
    }
    ```

-   **Response** (200 OK):

    ```json
    {
        "status": true,
        "message": "User data updated successfully",
        "data": {
            "name": "Jane Doe",
            "birth_date": "1999-05-10"
        }
    }
    ```

### Delete User

-   **Endpoint**: `/api/users/{user_id}`
-   **Method**: `DELETE`
-   **Response** (200 OK):

    ```json
    {
        "status": true,
        "message": "User deleted successfully"
    }
    ```

## 🎟️ Purchase History

### Add Purchase

-   **Endpoint**: `/api/users/{user_id}/purchases`
-   **Method**: `POST`
-   **Request Body**:

    ```json
    {
        "match_id": "match13",
        "home_team": "Persebaya",
        "away_team": "Arema",
        "stadium": "Gelora Bung Tomo",
        "match_date": "2024-12-07",
        "purchase_date": "2024-11-20",
        "ticket_quantity": 1
    }
    ```

-   **Response** (201 Created):

    ```json
    {
        "status": true,
        "message": "Purchase added to history successfully",
        "data": {
            "match_id": "match13",
            "home_team": "Persebaya",
            "away_team": "Arema",
            "stadium": "Gelora Bung Tomo",
            "match_date": "2024-12-07",
            "purchase_date": "2024-11-20",
            "ticket_quantity": 1
        }
    }
    ```

### Get Purchase History

-   **Endpoint**: `/api/users/{user_id}/purchases`
-   **Method**: `GET`
-   **Response** (200 OK):

    ```json
    {
        "status": true,
        "message": "Purchase history retrieved successfully",
        "data": [
            {
                "match_id": "match13",
                "home_team": "Persebaya",
                "away_team": "Arema",
                "stadium": "Gelora Bung Tomo",
                "match_date": "2024-12-07",
                "purchase_date": "2024-11-20",
                "ticket_quantity": 1
            }
        ]
    }
    ```

## 🎯 Recommendations

### Recommend Based on Favorite Team

-   **Endpoint**: `/api/recommend-teamfavorite`
-   **Method**: `GET`
-   **Query Parameters**:
    -   `user_id`: The ID of the user.
-   **Response** (200 OK):

    ```json
    {
        "status": true,
        "message": "Recommendations retrieved successfully",
        "data": [
            {
                "away_team": "Borneo FC",
                "hari": "Weekday",
                "home_team": "Persebaya",
                "id_match": 137,
                "jam": "19:00",
                "lokasi": "Surabaya",
                "match": "Persebaya vs Borneo FC",
                "stadion": "Stadion Gelora Bung Tomo",
                "tanggal": "20/12/2024",
                "tiket_terjual": 12021,
                "waktu": "Malam"
            },
            {
                "away_team": "Persebaya",
                "hari": "Weekend",
                "home_team": "Bali United",
                "id_match": 150,
                "jam": "19:00",
                "lokasi": "Bali",
                "match": "Bali United vs Persebaya",
                "stadion": "Stadion Kapten I Wayan Dipta",
                "tanggal": "28/12/2024",
                "tiket_terjual": 4507,
                "waktu": "Malam"
            }
        ]
    }
    ```

### Recommend Based on Purchase History

-   **Endpoint**: `/api/recommend-history`
-   **Method**: `GET`
-   **Query Parameters**:
    -   `user_id`: The ID of the user.
-   **Response** (200 OK):

    ```json
    {
        "status": true,
        "message": "Recommendations retrieved successfully",
        "data": [
            {
                "away_team": "Persebaya",
                "hari": "Weekend",
                "home_team": "PSS Sleman",
                "id_match": 157,
                "jam": "15:30",
                "lokasi": "Padang",
                "match": "PSS Sleman vs Persebaya",
                "stadion": "Stadion Sultan Agung",
                "tanggal": "11/1/2025",
                "tiket_terjual": 13299,
                "waktu": "Sore"
            },
            {
                "away_team": "Persebaya",
                "hari": "Weekday",
                "home_team": "PERSIS",
                "id_match": 191,
                "jam": "19:00",
                "lokasi": "Solo",
                "match": "PERSIS vs Persebaya",
                "stadion": "Stadion Manahan",
                "tanggal": "7/2/2025",
                "tiket_terjual": 15558,
                "waktu": "Malam"
            }
        ]
    }
    ```

## 🌐 All Data

### Get All Data

-   **Endpoint**: `/api/alldata`
-   **Method**: `GET`
-   **Response** (200 OK):

    ```json
    {
        "status": true,
        "message": "All data retrieved successfully",
        "data": [
            {
                "away_score": 1,
                "away_team": "PSBS Biak",
                "hari": "Weekday",
                "home_score": 4,
                "home_team": "Persib",
                "id_match": 1,
                "jam": "20:00",
                "lokasi": "Bandung",
                "match": "Persib vs PSBS Biak",
                "stadion": "Stadion Si Jalak Harupat",
                "tanggal": "9/8/2024",
                "tiket_terjual": 10949,
                "waktu": "Malam"
            }
        ]
    }
    ```

### Get Standings

-   **Endpoint**: `/api/standings`
-   **Method**: `GET`
-   **Response** (200 OK):

    ```json
    {
        "status": true,
        "message": "Standings retrieved successfully",
        "data": [
            {
                "rank": 1,
                "team": "Persebaya",
                "points": 30,
                "wins": 9,
                "draws": 3,
                "losses": 1
            },
            {
                "rank": 2,
                "team": "Persib Bandung",
                "points": 26,
                "wins": 7,
                "draws": 5,
                "losses": 0
            }
        ]
    }
    ```

## 🖼️ Profile Picture Management

### Get Profile Picture

-   **Endpoint**: `/api/users/{user_id}/profile-picture`
-   **Method**: `GET`
-   **Response** (200 OK):

    ```json
    {
        "status": true,
        "data": {
            "profile_picture_url": "https://storage.googleapis.com/bolatix/profile_pictures/user123/uuid.jpg"
        }
    }
    ```

### Upload/Replace Profile Picture

-   **Endpoint**: `/api/users/{user_id}/profile-picture`
-   **Method**: `POST` or `PUT`
-   **Request Body**: `multipart/form-data`
    -   `profile_picture`: The image file.
-   **Response** (200 OK):

    ```json
    {
        "status": true,
        "message": "Profile picture updated successfully",
        "data": {
            "profile_picture_url": "https://storage.googleapis.com/bolatix/profile_pictures/user123/new_uuid.jpg"
        }
    }
    ```

### Delete Profile Picture

-   **Endpoint**: `/api/users/{user_id}/profile-picture`
-   **Method**: `DELETE`
-   **Response** (200 OK):

    ```json
    {
        "status": true,
        "message": "Profile picture removed successfully"
    }
    ```
