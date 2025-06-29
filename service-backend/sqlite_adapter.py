#!/usr/bin/env python3
"""
SQLite Adapter for Backend Service
This module provides a SnowConnect-compatible interface that communicates with the SQLite HTTP service.
"""

import requests
import logging as log
import json
from typing import Optional, List, Tuple, Any

class SQLiteCursor:
    """Cursor class that mimics database cursor behavior for SQLite HTTP service."""
    
    def __init__(self, sqlite_service_url: str = "http://localhost:8030"):
        self.sqlite_service_url = sqlite_service_url
        self.results = []
        self.rowcount = 0
        
    def execute(self, query: str, params: Optional[Tuple] = None):
        """Execute SQL query via SQLite HTTP service."""
        try:
            # Convert Snowflake/PostgreSQL style %s parameters to SQLite ? style
            if params:
                # Replace %s with ? for SQLite parameter binding
                sqlite_query = query.replace('%s', '?')
                # Convert tuple to list for JSON serialization
                sqlite_params = list(params) if params else None
            else:
                sqlite_query = query
                sqlite_params = None
            
            # Prepare request payload
            payload = {
                'query': sqlite_query,
                'params': sqlite_params
            }
            
            # Make request to SQLite service
            response = requests.post(
                f"{self.sqlite_service_url}/execute",
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    self.results = result.get('data', [])
                    self.rowcount = result.get('rows_affected', 0)
                    log.info(f"SQLite query executed successfully: {len(self.results)} rows")
                else:
                    error_msg = result.get('error', 'Unknown error')
                    log.error(f"SQLite query failed: {error_msg}")
                    raise Exception(f"SQLite error: {error_msg}")
            else:
                log.error(f"HTTP error: {response.status_code} - {response.text}")
                raise Exception(f"HTTP error {response.status_code}: {response.text}")
                
        except requests.exceptions.RequestException as e:
            log.error(f"Connection error to SQLite service: {e}")
            raise Exception(f"Connection error to SQLite service: {e}")
        except Exception as e:
            log.error(f"Error executing SQLite query: {e}")
            raise
    
    def fetchall(self) -> List[Tuple]:
        """Fetch all results from the last query."""
        if not self.results:
            return []
        
        # Convert list of dicts to list of tuples for compatibility
        return [tuple(row.values()) for row in self.results]
    
    def fetchone(self) -> Optional[Tuple]:
        """Fetch one result from the last query."""
        if not self.results:
            return None
        
        # Return first result as tuple
        result = self.results[0]
        return tuple(result.values()) if result else None
    
    def fetchmany(self, size: int) -> List[Tuple]:
        """Fetch specified number of results."""
        if not self.results:
            return []
        
        return [tuple(row.values()) for row in self.results[:size]]
    
    def close(self):
        """Close cursor (no-op for HTTP service)."""
        self.results = []
        self.rowcount = 0

class SQLiteConnect:
    """SQLite connection class that mimics SnowConnect interface."""
    
    def __init__(self, warehouse: str = None, database: str = None, schema: str = None):
        """Initialize SQLite connection.
        
        Args:
            warehouse: Ignored for SQLite (kept for compatibility)
            database: Ignored for SQLite (kept for compatibility) 
            schema: Ignored for SQLite (kept for compatibility)
        """
        self.sqlite_service_url = "http://localhost:8030"
        self.cursor = SQLiteCursor(self.sqlite_service_url)
        
        # Test connection to SQLite service
        try:
            response = requests.get(f"{self.sqlite_service_url}/", timeout=5)
            if response.status_code == 200:
                log.info("Successfully connected to SQLite HTTP service")
            else:
                log.warning(f"SQLite service returned status {response.status_code}")
        except requests.exceptions.RequestException as e:
            log.error(f"Failed to connect to SQLite service: {e}")
            raise Exception(f"Cannot connect to SQLite service at {self.sqlite_service_url}")
    
    def close(self):
        """Close connection."""
        if self.cursor:
            self.cursor.close()
        log.info("SQLite connection closed")
    
    def commit(self):
        """Commit transaction (no-op for HTTP service, auto-commits)."""
        pass
    
    def rollback(self):
        """Rollback transaction (not supported by HTTP service)."""
        log.warning("Rollback not supported by SQLite HTTP service")
        pass

# For backward compatibility, create an alias
SnowConnect = SQLiteConnect 