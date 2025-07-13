# SQLite HTTP Service

A Flask-based HTTP service that provides a REST API for executing SQLite commands. The service runs on port 8030 and accepts SQL queries via HTTP requests.

## Features

- Execute arbitrary SQL queries via HTTP POST requests
- List all tables in the database
- Get table schema information
- Create database backups
- Health check endpoint
- CORS enabled for cross-origin requests
- Comprehensive error handling and logging

## Quick Start

### Using Docker (Recommended)

1. Build and run the service with persistent storage:
```bash
docker-compose up --build
```

The service uses Docker volumes to persist the SQLite database even when containers are stopped or recreated.

### Alternative Docker Methods

**Option 1: Using Named Volume (Recommended)**
```bash
# Create named volume
docker volume create sqlite_data

# Run with named volume
docker run -d \
  --name sqlite-service \
  -p 8030:8030 \
  -v sqlite_data:/app/data \
  sqlite-service
```

**Option 2: Using Bind Mount**
```bash
# Create local data directory
mkdir -p ./data

# Run with bind mount
docker run -d \
  --name sqlite-service \
  -p 8030:8030 \
  -v $(pwd)/data:/app/data \
  sqlite-service
```

### Manual Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the service:
```bash
python sqlite_service.py
```

The service will be available at `http://localhost:8030`

## API Endpoints

### Health Check
- **GET** `/`
- Returns service status and information

```bash
curl http://localhost:8030/
```

### Execute SQL Query
- **POST** `/execute`
- Execute any SQL query

**Request Body:**
```json
{
  "query": "SELECT * FROM sample_data",
  "params": ["optional", "parameters"]
}
```

**Examples:**

Select data:
```bash
curl -X POST http://localhost:8030/execute \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM sample_data"}'
```

Insert data:
```bash
curl -X POST http://localhost:8030/execute \
  -H "Content-Type: application/json" \
  -d '{"query": "INSERT INTO sample_data (name, value) VALUES (?, ?)", "params": ["New Item", "New Value"]}'
```

Create table:
```bash
curl -X POST http://localhost:8030/execute \
  -H "Content-Type: application/json" \
  -d '{"query": "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)"}'
```

### List Tables
- **GET** `/tables`
- Returns all tables in the database

```bash
curl http://localhost:8030/tables
```

### Get Table Schema
- **GET** `/schema/<table_name>`
- Returns schema information for a specific table

```bash
curl http://localhost:8030/schema/sample_data
```

### Create Backup
- **POST** `/backup`
- Creates a timestamped backup of the database

```bash
curl -X POST http://localhost:8030/backup
```

## Response Format

All responses follow this format:

**Success Response:**
```json
{
  "success": true,
  "data": [...],
  "rows_affected": 3,
  "query": "SELECT * FROM sample_data"
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Error message",
  "query": "INVALID SQL"
}
```

## Sample Data

The service initializes with a `sample_data` table containing:
- `id` (INTEGER PRIMARY KEY)
- `name` (TEXT)
- `value` (TEXT)  
- `created_at` (TIMESTAMP)

## Data Persistence

The SQLite database is stored in `/app/data/sqlite_service.db` inside the container. To persist data across container restarts:

### Using Docker Compose (Recommended)
The provided `docker-compose.yml` automatically creates a named volume `sqlite_data` that persists your database.

### Manual Volume Management
```bash
# List volumes
docker volume ls

# Inspect volume details
docker volume inspect sqlite_data

# Remove volume (⚠️ This deletes all data!)
docker volume rm sqlite_data
```

### Backup and Restore
```bash
# Create backup via API
curl -X POST http://localhost:8030/backup

# Manual backup (copy from volume)
docker run --rm -v sqlite_data:/data -v $(pwd):/backup alpine cp /data/sqlite_service.db /backup/backup.db

# Restore from backup
docker run --rm -v sqlite_data:/data -v $(pwd):/backup alpine cp /backup/backup.db /data/sqlite_service.db
```

## Configuration

- **Port:** 8030 (configurable in `sqlite_service.py`)
- **Database:** `/app/data/sqlite_service.db` (created automatically with persistent storage)
- **Host:** `0.0.0.0` (accepts connections from any IP)

## Security Notes

⚠️ **Warning:** This service accepts arbitrary SQL queries. In production:
- Implement authentication and authorization
- Use query validation and sanitization
- Restrict network access
- Consider using prepared statements only
- Monitor and log all queries

## Development

To extend the service:

1. Modify `sqlite_service.py` to add new endpoints
2. Update requirements.txt for new dependencies
3. Rebuild Docker container if using Docker

## Troubleshooting

**Port already in use:**
```bash
# Check what's using port 8030
lsof -i :8030

# Kill process if needed
kill -9 <PID>
```

**Database locked:**
- Ensure no other processes are accessing the SQLite file
- Check for zombie connections

**Permission errors:**
- Ensure write permissions for database file location
- Check Docker volume mounts

## Testing

Test the service with sample queries:

```bash
# Test health check
curl http://localhost:8030/

# Test query execution
curl -X POST http://localhost:8030/execute \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT COUNT(*) as total FROM sample_data"}'

# Test table listing
curl http://localhost:8030/tables
``` 