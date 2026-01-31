# Wedding Face Recognition Backend

A production-ready FastAPI backend for a wedding photo face-recognition system with admin/user roles, Google Drive integration, and face recognition capabilities.

## Features

- **Dual-role authentication**: Admin and User roles with JWT-based authentication
- **Google Drive Integration**: Read-only access to wedding photos organized by days
- **Face Recognition**: Powered by dlib and face_recognition library
- **Face Indexing**: Automatically index faces from Google Drive photos
- **Face Matching**: Users can upload selfies to find their photos
- **Activity Logging**: Track all user actions (login, scan, download)
- **Admin Dashboard**: Statistics, activity logs, and photo management
- **Rate Limiting**: Prevent abuse of face scanning endpoint
- **Async Operations**: Fast, scalable async/await patterns throughout

## Tech Stack

- Python 3.11
- FastAPI
- Uvicorn (ASGI server)
- PostgreSQL with asyncpg
- SQLAlchemy 2.0 (async)
- face_recognition (dlib)
- Google Drive API
- JWT Authentication (python-jose)
- Passlib (bcrypt)
- Pydantic v2

## Project Structure

```
app/
 ├── main.py              # FastAPI application entry point
 ├── config.py            # Configuration management
 ├── database.py          # Database setup
 ├── models.py            # SQLAlchemy models
 ├── schemas.py           # Pydantic schemas
 ├── auth.py              # JWT and password hashing
 ├── dependencies.py      # Auth dependencies
 ├── drive_service.py     # Google Drive integration
 ├── face_engine.py       # Face recognition engine
 ├── admin_routes.py      # Admin endpoints
 ├── user_routes.py       # User endpoints
 ├── utils.py             # Helper functions
 └── logging_config.py    # Logging configuration
alembic/
 ├── versions/            # Database migrations
 └── env.py              # Alembic environment
```

## Prerequisites

- Python 3.11 or higher
- PostgreSQL 12 or higher
- Google Cloud Service Account with Drive API access
- Sufficient disk space for face embeddings

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/ankur-kaushik11/wedding-face-recognition-backend.git
cd wedding-face-recognition-backend
```

### 2. Create and activate virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

Note: Installing `dlib` may require cmake and additional build tools:
- Ubuntu/Debian: `sudo apt-get install cmake build-essential`
- macOS: `brew install cmake`
- Windows: Install Visual Studio Build Tools

### 4. Set up PostgreSQL database

```bash
# Create database
createdb wedding_photos

# Or using psql
psql -U postgres
CREATE DATABASE wedding_photos;
\q
```

### 5. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
DATABASE_URL=postgresql+asyncpg://postgres:yourpassword@localhost:5432/wedding_photos
SECRET_KEY=your-secret-key-at-least-32-characters-long-please-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
EVENT_PASSWORD=YourSecureEventPassword123
GOOGLE_DRIVE_CREDENTIALS_PATH=./service-account.json
GOOGLE_DRIVE_FOLDER_ID=your-google-drive-folder-id
FACE_SIMILARITY_THRESHOLD=0.6
FACE_DETECTION_MODEL=hog
MAX_UPLOAD_SIZE_MB=10
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
LOG_LEVEL=INFO
```

### 6. Set up Google Drive API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google Drive API
4. Create a Service Account
5. Download the service account JSON key file
6. Save it as `service-account.json` in the project root
7. Share your wedding photos folder with the service account email

### 7. Run database migrations

```bash
alembic upgrade head
```

### 8. Start the application

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at: `http://localhost:8000`

## API Documentation

Once the server is running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Authentication

**POST /auth/login**
```json
{
  "password": "YourEventPassword",
  "role": "admin"  // or "user"
}
```
Returns JWT token for authentication.

### User Endpoints

**POST /user/scan-face** (Rate limited: 5/minute)
- Upload a selfie to find matching photos
- Returns photos grouped by day

**GET /user/photos?day={day_name}**
- Get photos, optionally filtered by day

**POST /user/download-log**
- Log photo downloads for analytics

### Admin Endpoints

**GET /admin/stats**
- Get system statistics (photos, users, scans)

**GET /admin/activity?limit={limit}&user_id={user_id}**
- Get activity logs with filtering

**GET /admin/photos-summary**
- Get photos summary grouped by day

**POST /admin/reindex**
```json
{
  "force": false  // true to reindex all, false for new only
}
```
- Trigger photo indexing from Google Drive

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| DATABASE_URL | PostgreSQL connection URL with asyncpg driver | Required |
| SECRET_KEY | Secret key for JWT (min 32 chars) | Required |
| ALGORITHM | JWT algorithm | HS256 |
| ACCESS_TOKEN_EXPIRE_MINUTES | JWT expiry time | 1440 (24h) |
| EVENT_PASSWORD | Single password for all users | Required |
| GOOGLE_DRIVE_CREDENTIALS_PATH | Path to service account JSON | Required |
| GOOGLE_DRIVE_FOLDER_ID | Root folder ID with day folders | Required |
| FACE_SIMILARITY_THRESHOLD | Face matching threshold (0-1) | 0.6 |
| FACE_DETECTION_MODEL | hog (fast) or cnn (accurate) | hog |
| MAX_UPLOAD_SIZE_MB | Max upload size in MB | 10 |
| CORS_ORIGINS | Comma-separated CORS origins | localhost:3000 |
| LOG_LEVEL | Logging level | INFO |

## Database Schema

### Users Table
- id (UUID, primary key)
- role (enum: admin, user)
- last_login (timestamp)
- created_at (timestamp)

### Photos Table
- id (UUID, primary key)
- drive_file_id (string, unique)
- drive_url (string)
- day_name (string)
- face_embedding (array of floats, 128-dimensional)
- indexed_at (timestamp)

### Activity Logs Table
- id (UUID, primary key)
- user_id (UUID, foreign key)
- action (enum: login, face_scan, download)
- photo_count (integer, nullable)
- timestamp (timestamp)

## Face Recognition Flow

### Indexing (Admin)
1. Admin triggers reindex via POST /admin/reindex
2. System fetches day folders from Google Drive
3. For each photo in each folder:
   - Download thumbnail (not full resolution)
   - Detect faces using dlib
   - Generate 128-dimensional embeddings
   - Store in database with metadata
4. Return indexing statistics

### Matching (User)
1. User uploads a selfie via POST /user/scan-face
2. System detects face and generates embedding
3. Compares with all stored embeddings using cosine similarity
4. Returns photos where similarity >= threshold (0.6)
5. Groups results by day
6. Logs activity

## Development

### Running tests

```bash
python test_api.py
```

### Database migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Code formatting

```bash
# Install development dependencies
pip install black isort flake8

# Format code
black app/
isort app/

# Lint code
flake8 app/
```

## Production Deployment

### Security Checklist

- [ ] Use strong SECRET_KEY (min 32 random characters)
- [ ] Change EVENT_PASSWORD from default
- [ ] Enable HTTPS only (no HTTP)
- [ ] Configure proper CORS origins (no wildcards)
- [ ] Use environment-specific .env files
- [ ] Rotate service account credentials regularly
- [ ] Set up database backups
- [ ] Enable PostgreSQL SSL connections
- [ ] Use connection pooling appropriately
- [ ] Set up monitoring and alerting
- [ ] Configure rate limiting per requirements
- [ ] Use a reverse proxy (nginx) in front of Uvicorn

### Deployment with Docker (Optional)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    cmake \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production Server

```bash
# Install Gunicorn for production
pip install gunicorn

# Run with Gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Performance Tips

1. **Indexing**: Run during off-peak hours, can take time for large photo sets
2. **Face Detection Model**: Use "hog" for speed, "cnn" for accuracy (requires GPU)
3. **Database**: Add indexes on frequently queried columns
4. **Caching**: Consider Redis for session management and caching
5. **CDN**: Use CDN for serving photos from Google Drive
6. **Connection Pooling**: Tune pool_size and max_overflow based on load

## Troubleshooting

### Database connection errors
- Check DATABASE_URL format: `postgresql+asyncpg://user:pass@host:port/db`
- Ensure PostgreSQL is running: `sudo systemctl status postgresql`
- Verify credentials and database exists

### Google Drive API errors
- Verify service-account.json path is correct
- Check service account has access to the folder
- Ensure Google Drive API is enabled in Cloud Console

### Face recognition errors
- Install cmake and build tools for dlib
- Ensure images are valid JPEG/PNG format
- Check image file size < MAX_UPLOAD_SIZE_MB

### Import errors
- Activate virtual environment
- Reinstall requirements: `pip install -r requirements.txt --force-reinstall`

## License

MIT License

## Support

For issues and questions, please open an issue on GitHub.