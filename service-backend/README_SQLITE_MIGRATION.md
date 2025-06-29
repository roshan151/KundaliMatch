# SQLite Migration Guide

This guide explains how to run the backend with SQLite instead of Snowflake.

## Overview

The backend has been migrated from Snowflake to SQLite with the following changes:

- **New SQLite Adapter**: `sqlite_adapter.py` - Mimics the Snowflake interface but connects to a SQLite HTTP service
- **Database Tables**: Converted to SQLite-compatible schema
- **Query Compatibility**: Automatically converts Snowflake-style queries (`%s`) to SQLite format (`?`)

## Setup Instructions

### 1. Start the SQLite Service

First, start the SQLite HTTP service:

```bash
cd service-sqlite
python sqlite_service.py
```

The service will run on `http://localhost:8030`

### 2. Initialize Database Tables

Run the initialization script to create the required tables:

```bash
cd service-backend
python init_sqlite_tables.py
```

This will create:
- `PROFILE_DB` table (user profiles)
- `MATCHING_TABLE` table (matching data)
- Appropriate indexes for performance

### 3. Start the Backend Service

Now you can start the backend service as usual:

```bash
cd service-backend
python backend.py
```

## What Changed

### Files Modified:
- `backend.py` - Updated import from `snowflake_utils` to `sqlite_adapter`
- `requirements.txt` - Removed `snowflake-connector-python` dependency

### Files Added:
- `sqlite_adapter.py` - SQLite adapter that mimics Snowflake interface
- `init_sqlite_tables.py` - Database initialization script
- `README_SQLite_Migration.md` - This guide

### Database Schema:
The SQLite tables maintain the same structure as the original Snowflake tables:

- **PROFILE_DB**: User profile information
- **MATCHING_TABLE**: User matching and relationship data

## Key Features

1. **Drop-in Replacement**: The SQLite adapter maintains the same interface as Snowflake
2. **Automatic Query Conversion**: Snowflake-style parameterized queries (`%s`) are automatically converted to SQLite format (`?`)
3. **HTTP-based Service**: SQLite operations go through a REST API for consistency
4. **Easy Migration**: Minimal changes to existing backend code

## Troubleshooting

### SQLite Service Not Running
If you get connection errors, ensure the SQLite service is running:
```bash
curl http://localhost:8030/
```

### Database Not Initialized
If you get table-related errors, run the initialization script:
```bash
python init_sqlite_tables.py
```

### Data Migration
To migrate existing data from Snowflake to SQLite, you would need to:
1. Export data from Snowflake to CSV
2. Load the CSV data into SQLite using the `/execute` endpoint

## Performance Notes

- SQLite is suitable for development and moderate production loads
- For high-scale production, consider PostgreSQL or other robust databases
- The HTTP service layer adds some latency compared to direct database connections

## Next Steps

1. Test all backend endpoints to ensure compatibility
2. Consider migrating the SQLite service to use direct SQLite connections for better performance
3. Add database backup and recovery procedures
4. Monitor performance and optimize queries as needed 