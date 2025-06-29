import requests
from config import config
import logging as log
import json

class SQLConnect:
    """SQLite adapter that provides SQL database connectivity"""
    
    def __init__(self, warehouse=None, database=None, schema=None):
        # SQLite service endpoint
        self.sqlite_service_url = f'{config.SQL_SERVICE_URL}:{config.SQL_SERVICE_PORT}'
        
        # Store connection info for logging (not used in SQLite)
        self.warehouse = warehouse
        self.database = database
        self.schema = schema
        
        # Initialize cursor-like object
        self.cursor = SQLiteCursor(self.sqlite_service_url)
        self.conn = SQLiteConnection(self.sqlite_service_url)
        
        log.info(f"SQLite connection initialized (replacing Snowflake: warehouse={warehouse}, database={database}, schema={schema})")

    def close(self):
        """Close the connection (no-op for HTTP-based SQLite service)"""
        log.info("SQLite connection closed")

class SQLiteConnection:
    """Mimics the connection object interface"""
    
    def __init__(self, service_url):
        self.service_url = service_url
        
    def commit(self):
        """Commit transaction - for SQLite service, this is handled per query"""
        # SQLite service commits automatically for each query
        pass
        
    def cursor(self):
        """Return cursor object - not typically used in our pattern"""
        return SQLiteCursor(self.service_url)

class SQLiteCursor:
    """Mimics the cursor object interface from Snowflake"""
    
    def __init__(self, service_url):
        self.service_url = service_url
        self.last_results = None
        
    def execute(self, query, params=None):
        """Execute SQL query through the SQLite HTTP service"""
        try:
            # Convert Snowflake-style parameterized queries to SQLite style
            if params:
                # Convert %s to ? for SQLite
                sqlite_query = query.replace('%s', '?')
            else:
                sqlite_query = query
            
            # Prepare request payload
            payload = {
                'query': sqlite_query
            }
            if params:
                payload['params'] = list(params) if isinstance(params, tuple) else params
            
            # Make HTTP request to SQLite service
            response = requests.post(f"{self.service_url}/execute", json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            if not result.get('success', False):
                raise Exception(f"SQLite query failed: {result.get('error', 'Unknown error')}")
            
            # Store results for fetching
            self.last_results = result.get('data', [])
            self.rowcount = result.get('rows_affected', 0)
            
            log.info(f"SQLite query executed successfully: {len(self.last_results)} rows")
            
        except requests.RequestException as e:
            log.error(f"Error connecting to SQLite service: {e}")
            raise Exception(f"SQLite service connection error: {e}")
        except Exception as e:
            log.error(f"Error executing SQLite query: {e}")
            raise
    
    def fetchone(self):
        """Fetch one row from the last executed query"""
        if self.last_results and len(self.last_results) > 0:
            # Return first row and remove it from results
            row_dict = self.last_results.pop(0)
            # Convert dictionary to tuple for Snowflake compatibility
            return tuple(row_dict.values()) if row_dict else None
        return None
    
    def fetchall(self):
        """Fetch all rows from the last executed query"""
        if self.last_results:
            results = self.last_results.copy()
            self.last_results = []  # Clear results after fetching
            # Convert dictionaries to tuples for Snowflake compatibility
            return [tuple(row.values()) if row else None for row in results]
        return []
    
    def close(self):
        """Close cursor (no-op for HTTP service)"""
        pass 