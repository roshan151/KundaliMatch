#!/usr/bin/env python3
"""
SQLite HTTP Service
A Flask-based HTTP service that provides a REST API for executing SQLite commands.
Runs on port 8030 and accepts SQL queries via POST requests.
"""

import sqlite3
import json
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all domains

# Configuration
DB_PATH = '/app/data/sqlite_service.db'
PORT = 8030

def init_database():
    """Initialize the SQLite database with some basic tables if it doesn't exist."""
    try:
        # Ensure data directory exists
        data_dir = os.path.dirname(DB_PATH)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            logger.info(f"Created data directory: {data_dir}")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create a sample table for testing
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sample_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert some sample data if table is empty
        cursor.execute('SELECT COUNT(*) FROM sample_data')
        if cursor.fetchone()[0] == 0:
            sample_data = [
                ('Sample 1', 'Value 1'),
                ('Sample 2', 'Value 2'),
                ('Sample 3', 'Value 3')
            ]
            cursor.executemany('INSERT INTO sample_data (name, value) VALUES (?, ?)', sample_data)
        
        conn.commit()
        conn.close()
        logger.info(f"Database initialized successfully at {DB_PATH}")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")

def execute_sql(query, params=None):
    """Execute SQL query and return results."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        cursor = conn.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        # Check if it's a SELECT query or PRAGMA query
        if query.strip().upper().startswith(('SELECT', 'PRAGMA')):
            results = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return {
                'success': True,
                'data': results,
                'rows_affected': len(results),
                'query': query
            }
        else:
            # For INSERT, UPDATE, DELETE queries
            rows_affected = cursor.rowcount
            conn.commit()
            conn.close()
            return {
                'success': True,
                'rows_affected': rows_affected,
                'message': f'Query executed successfully. {rows_affected} rows affected.',
                'query': query
            }
            
    except sqlite3.Error as e:
        logger.error(f"SQLite error: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'query': query
        }
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}',
            'query': query
        }

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'SQLite HTTP Service',
        'port': PORT,
        'database': DB_PATH,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/execute', methods=['POST'])
def execute_query():
    """Execute SQL query endpoint."""
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({
                'success': False,
                'error': 'No SQL query provided. Send JSON with "query" field.'
            }), 400
        
        query = data['query']
        params = data.get('params', None)
        
        logger.info(f"Executing query: {query}")
        result = execute_sql(query, params)
        
        status_code = 200 if result['success'] else 400
        return jsonify(result), status_code
        
    except Exception as e:
        logger.error(f"Error in execute_query: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Request processing error: {str(e)}'
        }), 500

@app.route('/tables', methods=['GET'])
def list_tables():
    """List all tables in the database."""
    try:
        query = "SELECT name FROM sqlite_master WHERE type='table'"
        result = execute_sql(query)
        
        if result['success']:
            tables = [row['name'] for row in result['data']]
            return jsonify({
                'success': True,
                'tables': tables,
                'count': len(tables)
            })
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error listing tables: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error listing tables: {str(e)}'
        }), 500

@app.route('/schema/<table_name>', methods=['GET'])
def get_table_schema(table_name):
    """Get schema for a specific table."""
    try:
        query = f"PRAGMA table_info({table_name})"
        result = execute_sql(query)
        
        if result['success']:
            return jsonify({
                'success': True,
                'table': table_name,
                'schema': result.get('data', [])
            })
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error getting schema for table {table_name}: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error getting schema: {str(e)}'
        }), 500

@app.route('/backup', methods=['POST'])
def backup_database():
    """Create a backup of the database."""
    try:
        backup_path = f"{DB_PATH}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Simple file copy for backup
        import shutil
        shutil.copy2(DB_PATH, backup_path)
        
        return jsonify({
            'success': True,
            'message': f'Database backed up successfully',
            'backup_file': backup_path
        })
        
    except Exception as e:
        logger.error(f"Error creating backup: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Backup failed: {str(e)}'
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found',
        'available_endpoints': [
            'GET / - Health check',
            'POST /execute - Execute SQL query',
            'GET /tables - List all tables',
            'GET /schema/<table_name> - Get table schema',
            'POST /backup - Create database backup'
        ]
    }), 404

if __name__ == '__main__':
    # Initialize database on startup
    init_database()
    
    logger.info(f"Starting SQLite HTTP Service on port {PORT}")
    logger.info(f"Database file: {DB_PATH}")
    logger.info("Available endpoints:")
    logger.info("  GET / - Health check")
    logger.info("  POST /execute - Execute SQL query")
    logger.info("  GET /tables - List all tables")
    logger.info("  GET /schema/<table_name> - Get table schema")
    logger.info("  POST /backup - Create database backup")
    
    app.run(host='0.0.0.0', port=PORT, debug=True) 