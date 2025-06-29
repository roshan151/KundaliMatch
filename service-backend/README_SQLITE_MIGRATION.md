# SQLite Migration for KundaliMatch Backend

This document describes the migration from Snowflake to SQLite for the KundaliMatch backend service.

## What Was Changed

### 1. Database Adapter
- **Before**: Used `snowflake_utils.py` with SnowConnect class for Snowflake database
- **After**: Created `sqlite_adapter.py` with SQLiteConnect class that communicates with SQLite HTTP service

### 2. SQL Compatibility
- **Parameter binding**: Changed from Snowflake `%s` style to SQLite `?` style
- **Boolean values**: Changed from Python `True/False` to SQLite `1/0`  
- **Hash functions**: Replaced `SHA2(%s, 256)` with Python's `hash_email_sha256()` function
- **Connection methods**: Updated `.conn.commit()` to `.commit()` for the new adapter

### 3. New Files Created
- `sqlite_adapter.py` - SQLite HTTP service client adapter
- `setup_sqlite_schema.py` - Database schema creation script
- `README_SQLITE_MIGRATION.md` - This documentation

## Prerequisites

1. **Python packages**: The backend now requires `requests` for HTTP communication
   ```bash
   pip install requests
   ```

2. **SQLite HTTP Service**: Must be running on port 8030
   ```bash
   cd ../service-sqlite
   python sqlite_service.py
   ```

## Setup Instructions

### 1. Start the SQLite Service
```bash
# In terminal 1
cd service-sqlite
python sqlite_service.py
```

### 2. Create Database Schema
```bash
# In terminal 2
cd service-backend
python setup_sqlite_schema.py
```

### 3. Start the Backend Service
```bash
# In the same terminal
python backend.py
```

## Architecture Overview

```
Backend Service (backend.py)
        ↓
SQLite Adapter (sqlite_adapter.py)
        ↓ HTTP requests
SQLite HTTP Service (service-sqlite/sqlite_service.py)
        ↓
SQLite Database (sqlite_service.db)
```

## Key Benefits

1. **Simplified deployment**: No need for cloud database credentials
2. **Local development**: Everything runs locally
3. **Cost reduction**: No cloud database costs
4. **Easy backup**: Simple file-based database
5. **No vendor lock-in**: Standard SQLite format

## Compatibility

The migration maintains full API compatibility:
- All REST endpoints work exactly the same
- Request/response formats unchanged
- Authentication and encryption unchanged
- File upload/download functionality unchanged

## Database Schema

### PROFILE Table
- Stores user profile information
- Primary key: `UID`
- Includes encrypted phone/email fields
- Supports image paths, location data, and preferences

### MATCHING Table  
- Stores user matching/recommendation data
- Composite primary key: `(UID1, UID2)`
- Tracks alignment, skip, and block actions
- Includes scoring and conversation data

## Troubleshooting

### SQLite Service Not Running
```
Error: Cannot connect to SQLite service at http://localhost:8030
```
**Solution**: Start the SQLite service first (see step 1 above)

### Database Schema Missing
```
Error: no such table: PROFILE
```
**Solution**: Run the schema setup script (see step 2 above)

### Connection Errors
- Ensure no firewall blocking port 8030
- Check that SQLite service started successfully
- Verify no other service using port 8030

## Performance Considerations

- SQLite HTTP service handles one request at a time
- For production use, consider connection pooling
- Database file grows with data - monitor disk space
- Regular VACUUM operations may help performance

## Migration Verification

To verify the migration worked correctly:

1. Check SQLite service health:
   ```bash
   curl http://localhost:8030/
   ```

2. List database tables:
   ```bash
   curl http://localhost:8030/tables
   ```

3. Test backend health:
   ```bash
   curl http://localhost:5000/
   ```

## Rollback Plan

To rollback to Snowflake:
1. Restore original `backend.py` from version control
2. Ensure Snowflake credentials are configured
3. Restart the backend service

The SQLite adapter is designed to be a drop-in replacement, so rollback should be straightforward. 