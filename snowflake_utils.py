import os
import snowflake.connector

class SnowConnect:
    def __init__(self, TABLE_WAREHOUSE, TABLE_DATABASE, TABLE_SCHEMA):
        self.conn = snowflake.connector.connect(
            user=os.getenv('SNOWFLAKE_USERNAME'),
            password=os.getenv('SNOWFLAKE_SECRET'),
            account=os.getenv('SNOWFLAKE_ACCOUNT_ID'),
            warehouse=TABLE_WAREHOUSE,
            database=TABLE_DATABASE,
            schema=TABLE_SCHEMA
            )

        self.cursor = self.conn.cursor()
    
    def close(self):
        self.conn.close()
        self.cursor.close()
        

