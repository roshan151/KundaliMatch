import boto3
import json
import psycopg2
import logging as log
from psycopg2 import sql
from config import config
# Replace with your actual values


def get_secrets():
    """Load sensitive secrets from AWS Secrets Manager"""
    secret_name = config.rds_secrets_group  # Replace with your secret name
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

class RDS_Connect:

    def __init__(self, db_name): 
        try:
            self.conn = psycopg2.connect(
                host='localhost',#secrets['host'],
                database=db_name,
                user=secrets['engine'],
                password=secrets['password'],
                port=secrets['port']
            )
            print("✅ Connected to RDS PostgreSQL successfully.")

            # Optional: run a simple query
            self.cursor = self.conn.cursor()

        except Exception as e:
            log.error(f"❌ Unable to connect to the database: {e}")

    def close(self):
        self.cursor.close()
        self.conn.close()