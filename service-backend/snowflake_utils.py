import os
import snowflake.connector
import boto3
import json
import logging as log
from config import config

def get_secrets():
    """Load sensitive secrets from AWS Secrets Manager"""
    secret_name = "kundali-match-secrets"  # Replace with your secret name
    region_name = config.REGION

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except Exception as e:
        log.error(f"Error getting secrets: {e}")
        raise e
    else:
        if 'SecretString' in get_secret_value_response:
            secret = json.loads(get_secret_value_response['SecretString'])
            return secret

# Load secrets
secrets = get_secrets()

class SnowConnect:
    def __init__(self, warehouse, database, schema):
        self.conn = snowflake.connector.connect(
            user=config.SNOWFLAKE_USERNAME,
            password=secrets['SNOWFLAKE_SECRET'],
            account=config.SNOWFLAKE_ACCOUNT_ID,
            warehouse=warehouse,
            database=database,
            schema=schema
        )
        self.cursor = self.conn.cursor()
    
    def close(self):
        self.cursor.close()
        self.conn.close()
        

