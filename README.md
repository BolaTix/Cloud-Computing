# BolaTix API Documentation

## 📚 Table of Contents
- [Authentication](#authentication)
- [User Management](#user-management)

## 🔐 Authentication

### Register a New User
```http
POST /api/auth/register
```

**Request Body**
```json
{
    "email": "user@example.com",
    "password": "securepassword123",
    "name": "John Smith",
    "favorite_team": "Persebaya",
    "profile": {
        "age": 25,
        "location": "Surabaya"
    }
}
```

**Response** (201 Created)
```json
{
    "message": "User registered successfully",
    "token": "eyJhbG...",
    "user_id": "user123"
}
```

### Login
```http
POST /api/auth/login
```

**Request Body**
```json
{
    "email": "user@example.com",
    "password": "securepassword123"
}
```

**Response** (200 OK)
```json
{
    "message": "Login successful",
    "token": "eyJhbG...",
    "user_id": "user123"
}
```

### Logout
```http
POST /api/auth/logout
```

**Headers**
```
Authorization: Bearer your-token-here
```

**Response** (200 OK)
```json
{
    "message": "Successfully logged out"
}
```

## 👤 User Management

### Get User Profile
```http
GET /api/users/{user_id}
```

**Headers**
```
Authorization: Bearer your-token-here
```

**Response** (200 OK)
```json
{
    "user_id": "user123",
    "email": "user@example.com",
    "name": "John Smith",
    "favorite_team": "Persebaya",
    "profile": {
        "age": 25,
        "location": "Surabaya"
    },
    "created_at": "2024-03-15T10:30:00Z",
    "updated_at": "2024-03-15T10:30:00Z"
}
```

### Update User Profile
```http
PUT /api/users/{user_id}
```

**Headers**
```
Authorization: Bearer your-token-here
```

**Request Body**
```json
{
    "name": "John Smith",
    "favorite_team": "Persib",
    "profile": {
        "age": 26,
        "location": "Bandung"
    },
    "purchase_history": [
        {
            "harga": 150000,
            "jam": "20:00",
            "jumlah_tiket": 1,
            "lokasi": "Bandung",
            "match": "Persib vs PSBS Biak",
            "stadion": "Gelora Bandung Lautan Api"
        }
    ]
}
```

**Response** (200 OK)
```json
{
    "message": "User updated successfully",
    "user": {
        "user_id": "user123",
        "name": "John Smith",
        "favorite_team": "Persib",
        "profile": {
            "age": 26,
            "location": "Bandung"
        },
        "purchase_history": [
            {
                "harga": 150000,
                "jam": "20:00",
                "jumlah_tiket": 1,
                "lokasi": "Bandung",
                "match": "Persib vs PSBS Biak",
                "stadion": "Gelora Bandung Lautan Api"
            }
        ],
        "updated_at": "2024-03-15T11:30:00Z"
    }
}
```
