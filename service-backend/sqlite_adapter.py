import requests
from config import config
import logging as log
import json

class SQLConnect:
    """Simplified SQLite adapter for database connectivity"""
    
    def __init__(self, url, port):
        # SQLite service endpoint
        self.sqlite_service_url = f'{url}:{port}'
        
        # Initialize cursor and connection objects
        self.cursor = SQLiteCursor(self.sqlite_service_url)
        self.conn = SQLiteConnection(self.sqlite_service_url)
        
        log.info("SQLite connection initialized")

    def close(self):
        """Close the connection (no-op for HTTP-based SQLite service)"""
        log.info("SQLite connection closed")

class SQLiteConnection:
    """SQLite connection object"""
    
    def __init__(self, service_url):
        self.service_url = service_url
        
    def commit(self):
        """Commit transaction - handled automatically by SQLite service"""
        pass
        
    def cursor(self):
        """Return cursor object"""
        return SQLiteCursor(self.service_url)

class SQLiteCursor:
    """SQLite cursor for executing queries"""
    
    def __init__(self, service_url):
        self.service_url = service_url
        self.last_results = None
        
    def execute(self, query, params=None):
        """Execute SQL query through the SQLite HTTP service"""
        try:
            # Prepare request payload
            payload = {'query': query}
            if params:
                payload['params'] = list(params) if isinstance(params, (tuple, list)) else params
            
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
            return self.last_results.pop(0)
        return None
    
    def fetchall(self):
        """Fetch all rows from the last executed query"""
        if self.last_results:
            results = self.last_results.copy()
            self.last_results = []  # Clear results after fetching
            return results
        return []
    
    def close(self):
        """Close cursor (no-op for HTTP service)"""
        pass 