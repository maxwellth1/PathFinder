# API Endpoints Documentation

## Base URL
```
https://api.example.com/v1
```

## Authentication Endpoints

### Register User
```
POST /auth/register
Content-Type: application/json

Request Body:
{
  "username": "string",
  "email": "string",
  "password": "string",
  "fullName": "string"
}

Response (201 Created):
{
  "user": {
    "id": "uuid",
    "username": "string",
    "email": "string",
    "fullName": "string",
    "createdAt": "timestamp"
  },
  "token": "jwt_token",
  "refreshToken": "refresh_token"
}
```

### Login
```
POST /auth/login
Content-Type: application/json

Request Body:
{
  "username": "string", // or email
  "password": "string"
}

Response (200 OK):
{
  "user": {
    "id": "uuid",
    "username": "string",
    "email": "string",
    "fullName": "string"
  },
  "token": "jwt_token",
  "refreshToken": "refresh_token"
}
```

### Refresh Token
```
POST /auth/refresh
Content-Type: application/json

Request Body:
{
  "refreshToken": "string"
}

Response (200 OK):
{
  "token": "jwt_token",
  "refreshToken": "new_refresh_token"
}
```

### Logout
```
POST /auth/logout
Authorization: Bearer {token}

Response (200 OK):
{
  "message": "Successfully logged out"
}
```

## User Endpoints

### Get User Profile
```
GET /users/profile
Authorization: Bearer {token}

Response (200 OK):
{
  "id": "uuid",
  "username": "string",
  "email": "string",
  "fullName": "string",
  "avatar": "url",
  "status": "online|offline|away",
  "lastSeen": "timestamp",
  "createdAt": "timestamp"
}
```

### Update User Profile
```
PUT /users/profile
Authorization: Bearer {token}
Content-Type: application/json

Request Body:
{
  "fullName": "string",
  "avatar": "url",
  "status": "string"
}

Response (200 OK):
{
  "message": "Profile updated successfully",
  "user": { ... }
}
```

### Search Users
```
GET /users/search?q={query}&limit=20&offset=0
Authorization: Bearer {token}

Response (200 OK):
{
  "users": [
    {
      "id": "uuid",
      "username": "string",
      "fullName": "string",
      "avatar": "url"
    }
  ],
  "total": 100,
  "limit": 20,
  "offset": 0
}
```

## Message Endpoints

### Send Message
```
POST /messages
Authorization: Bearer {token}
Content-Type: application/json

Request Body:
{
  "conversationId": "uuid",
  "content": "string",
  "type": "text|image|file",
  "attachments": [
    {
      "url": "string",
      "type": "string",
      "size": "number"
    }
  ]
}

Response (201 Created):
{
  "id": "uuid",
  "conversationId": "uuid",
  "senderId": "uuid",
  "content": "string",
  "type": "text|image|file",
  "attachments": [],
  "createdAt": "timestamp",
  "status": "sent"
}
```

### Get Messages
```
GET /messages?conversationId={id}&limit=50&before={messageId}
Authorization: Bearer {token}

Response (200 OK):
{
  "messages": [
    {
      "id": "uuid",
      "conversationId": "uuid",
      "senderId": "uuid",
      "content": "string",
      "type": "text|image|file",
      "attachments": [],
      "createdAt": "timestamp",
      "status": "sent|delivered|read",
      "editedAt": "timestamp|null"
    }
  ],
  "hasMore": true,
  "oldestMessageId": "uuid"
}
```

### Update Message Status
```
PUT /messages/{messageId}/status
Authorization: Bearer {token}
Content-Type: application/json

Request Body:
{
  "status": "delivered|read"
}

Response (200 OK):
{
  "message": "Status updated successfully"
}
```

### Delete Message
```
DELETE /messages/{messageId}
Authorization: Bearer {token}

Response (200 OK):
{
  "message": "Message deleted successfully"
}
```

## Conversation Endpoints

### Create Conversation
```
POST /conversations
Authorization: Bearer {token}
Content-Type: application/json

Request Body:
{
  "type": "direct|group",
  "participants": ["userId1", "userId2"],
  "name": "string", // for group chats
  "avatar": "url" // for group chats
}

Response (201 Created):
{
  "id": "uuid",
  "type": "direct|group",
  "name": "string",
  "avatar": "url",
  "participants": [
    {
      "id": "uuid",
      "username": "string",
      "fullName": "string",
      "avatar": "url"
    }
  ],
  "createdAt": "timestamp",
  "lastMessage": null
}
```

### Get Conversations
```
GET /conversations?limit=20&offset=0
Authorization: Bearer {token}

Response (200 OK):
{
  "conversations": [
    {
      "id": "uuid",
      "type": "direct|group",
      "name": "string",
      "avatar": "url",
      "participants": [...],
      "lastMessage": {
        "id": "uuid",
        "content": "string",
        "senderId": "uuid",
        "createdAt": "timestamp"
      },
      "unreadCount": 5,
      "updatedAt": "timestamp"
    }
  ],
  "total": 50,
  "limit": 20,
  "offset": 0
}
```

### Get Conversation Details
```
GET /conversations/{conversationId}
Authorization: Bearer {token}

Response (200 OK):
{
  "id": "uuid",
  "type": "direct|group",
  "name": "string",
  "avatar": "url",
  "participants": [...],
  "createdAt": "timestamp",
  "settings": {
    "muted": false,
    "archived": false
  }
}
```

## File Upload Endpoints

### Upload File
```
POST /upload
Authorization: Bearer {token}
Content-Type: multipart/form-data

Request Body:
- file: binary
- type: "avatar|message|attachment"

Response (201 Created):
{
  "url": "https://cdn.example.com/files/uuid",
  "thumbnailUrl": "https://cdn.example.com/thumbnails/uuid",
  "type": "image|video|document",
  "size": 1024000,
  "mimeType": "image/jpeg",
  "uploadedAt": "timestamp"
}
```

### Get File
```
GET /files/{fileId}
Authorization: Bearer {token}

Response: Binary file data or redirect to CDN
```

## WebSocket Events

### Connection
```
ws://api.example.com/ws?token={jwt_token}
```

### Client Events (Send to Server)

#### Join Conversation
```json
{
  "type": "join_conversation",
  "conversationId": "uuid"
}
```

#### Leave Conversation
```json
{
  "type": "leave_conversation",
  "conversationId": "uuid"
}
```

#### Typing Indicator
```json
{
  "type": "typing",
  "conversationId": "uuid",
  "isTyping": true
}
```

#### Message Seen
```json
{
  "type": "message_seen",
  "messageId": "uuid",
  "conversationId": "uuid"
}
```

### Server Events (Receive from Server)

#### New Message
```json
{
  "type": "new_message",
  "message": {
    "id": "uuid",
    "conversationId": "uuid",
    "senderId": "uuid",
    "content": "string",
    "createdAt": "timestamp"
  }
}
```

#### Message Status Update
```json
{
  "type": "message_status",
  "messageId": "uuid",
  "status": "delivered|read",
  "userId": "uuid"
}
```

#### User Typing
```json
{
  "type": "user_typing",
  "conversationId": "uuid",
  "userId": "uuid",
  "username": "string",
  "isTyping": true
}
```

#### User Status Change
```json
{
  "type": "user_status",
  "userId": "uuid",
  "status": "online|offline|away",
  "lastSeen": "timestamp"
}
```

## Error Responses

### 400 Bad Request
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Validation error",
    "details": {
      "field": "error message"
    }
  }
}
```

### 401 Unauthorized
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Invalid or expired token"
  }
}
```

### 403 Forbidden
```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "You don't have permission to access this resource"
  }
}
```

### 404 Not Found
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Resource not found"
  }
}
```

### 429 Too Many Requests
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests",
    "retryAfter": 60
  }
}
```

### 500 Internal Server Error
```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "An unexpected error occurred"
  }
}
```