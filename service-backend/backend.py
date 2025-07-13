import os
import re
import json
import time
import yaml
import random
import base64
import asyncio
import requests
import boto3
import hashlib
import pandas as pd
from uuid import uuid4
from PIL import Image
import threading
import logging as log
from psycopg2 import sql
from flask import send_file
from datetime import datetime

from twilio.jwt.access_token.grants import ChatGrant
from twilio.jwt.access_token import AccessToken
from twilio.rest import Client
from botocore.exceptions import NoCredentialsError
from geopy.geocoders import Nominatim

from typing import Dict, List
from flask import Flask, request, jsonify, make_response
from urllib.parse import urlparse
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.fernet import Fernet


from destiny_agent import chat_flow, FilterAgent

# Custom components
from config import config
from sqlite_adapter import SQLConnect

log.basicConfig(
    format='%(levelname)s [%(filename)s:%(lineno)d] %(message)s',
    level=log.INFO
)

# Initialize Argon2 password hasher
ph = PasswordHasher(
    time_cost=3,        # Number of iterations
    memory_cost=65536,  # Memory usage in KiB
    parallelism=4,      # Number of parallel threads
    hash_len=32,        # Length of the hash in bytes
    salt_len=16         # Length of the salt in bytes
)

BUCKET_NAME = config.BUCKET
REGION = config.REGION
CURRENT_DIR = os.getcwd()

# Get secrets from AWS Secrets manager
# def get_secrets(secret_name):
#     """Load sensitive secrets from AWS Secrets Manager using IAM credentials"""

#     # Create a boto3 session using IAM credentials
#     session = boto3.session.Session(
#         region_name=REGION
#     )

#     client = session.client(service_name='secretsmanager')

#     try:
#         get_secret_value_response = client.get_secret_value(
#             SecretId=secret_name
#         )
#     except Exception as e:
#         log.error(f"Error getting secrets: {e}")
#         raise e
#     else:
#         if 'SecretString' in get_secret_value_response:
#             re
# Get secrets from local .env file
def get_secrets(secret_name):
    """Load sensitive secrets from local .env file"""
    from dotenv import load_dotenv
    load_dotenv()
    keys = os.environ.keys()
    secrets = {}
    for key in keys:
        secrets[key] = os.getenv(key)

    return secrets


# Load secrets
secrets = get_secrets(config.aws_secrets_group)

# Configure AWS s3
s3 = boto3.client(
    's3',
    aws_access_key_id=secrets["S3_ACCESS_ID"],
    aws_secret_access_key=secrets['S3_ACCESS_KEY']
)

filter_agent = FilterAgent(openai_api_key = secrets['OPENAI_API_KEY'], log = log)

# Initialize encryption key
def get_encryption_key():
    """Get or create encryption key"""
    key = secrets['ENCRYPTION_KEY']
    if not key:
        #key = Fernet.generate_key()
        raise Exception("No encryption key found in environment. Please set ENCRYPTION_KEY environment variable.")
    return key

# Initialize Fernet cipher
cipher_suite = Fernet(get_encryption_key())

def encrypt_sensitive_data(data):
    """Encrypt sensitive data using Fernet"""
    if not data:
        return None
    try:
        return cipher_suite.encrypt(str(data).encode()).decode()
    except Exception as e:
        log.error(f"Error encrypting data: {e}")
        return None

def decrypt_sensitive_data(encrypted_data):
    """Decrypt sensitive data using Fernet"""
    if not encrypted_data:
        return None
    try:
        return cipher_suite.decrypt(encrypted_data.encode()).decode()
    except Exception as e:
        log.error(f"Error decrypting data: {e}")
        return None

def encrypt_password(password):
    """Hash password using Argon2"""
    if not password:
        return None
    try:
        return ph.hash(str(password))
    except Exception as e:
        log.error(f"Error hashing password: {e}")
        return None

def verify_password(stored_hash, provided_password):
    """Verify a password against its hash"""
    #log.info(f"stored hash: {stored_hash}, provided password: {provided_password}")
    try:
        if not stored_hash or not provided_password:
            #log.warning(f"Missing stored hash or provided password: {stored_hash}, {provided_password}")
            return False
            
        # Ensure the stored hash is a string
        stored_hash = str(stored_hash)
        
        # Try to verify the password
        ph.verify(stored_hash, provided_password)
        return True
    except VerifyMismatchError:
        log.warning("Password verification failed - hash mismatch")
        return False
    except Exception as e:
        log.error(f"Error verifying password: {str(e)}")
        return False

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_phone(phone):
    """Validate phone number format"""
    # Remove any non-digit characters
    phone = re.sub(r'\D', '', phone)
    # Check if the phone number has a valid length (adjust based on your requirements)
    return len(phone) >= 10 and len(phone) <= 15

def hash_email_sha256(email: str) -> str:
    # Normalize email (optional but recommended)
    normalized_email = email.strip().lower()
    # Encode and hash
    sha256_hash = hashlib.sha256(normalized_email.encode('utf-8')).hexdigest()
    return sha256_hash

# Initialize Argon2 password hasher
ph = PasswordHasher(
    time_cost=3,        # Number of iterations
    memory_cost=65536,  # Memory usage in KiB
    parallelism=4,      # Number of parallel threads
    hash_len=32,        # Length of the hash in bytes
    salt_len=16         # Length of the salt in bytes
)

def run_async_task(coro):
    asyncio.run(coro)

def upload_file_to_s3(file_path, filename):
    try:
        # TODO replace with unique key-image1

        # Upload file to S3
        s3.upload_file(file_path, BUCKET_NAME, filename)

        # Construct public URL
        url = f"https://{BUCKET_NAME}.s3.{REGION}.amazonaws.com/{filename}"
        return url
    
    except NoCredentialsError:
        log.info("AWS credentials not found.")
        return None
    except Exception as e:
        log.info(f"Upload failed: {e}")
        return None
    
# def download_image_from_s3(filename, download_path):
#     try:
#         # Download file from S3
#         s3.download_file(BUCKET_NAME, filename, download_path)
#         log.info(f"Downloaded {filename} to {download_path}")
#         return download_path

#     except NoCredentialsError:
#         log.info("AWS credentials not found.")
#         return None
#     except Exception as e:
#         log.info(f"Download failed: {e}")
#         return None
    
def process_image(image_path, png_filename):
    try:
        with Image.open(image_path) as img:
            img_format = img.format.lower()
            if img_format not in config.ALLOWED_FORMATS:
                log.info(f"Warning: Unsupported format '{img_format}' for file {image_path}")
                return None

            # Convert to PNG
            png_path = os.path.join(CURRENT_DIR, png_filename)
            img.convert("RGBA").save(png_path, "PNG")
            return png_path

    except Exception as e:
        log.info(f"Error processing {image_path}: {e}")

def get_lat_long(address):
    try:
        geolocator = Nominatim(user_agent="geo_locator")
        location = geolocator.geocode(address, timeout=config.MAX_GEOCODE_TIMEOUT)
        if location:
            return location.latitude, location.longitude
        else:
            return '', ''
    except Exception as e:
        log.info(f'Unable to get lat, long: {e}')
        return '', ''

# BACKUP - this is just backup for kundali service if request service fails
def get_kundali_score():
    return random.uniform(0.1, 0.9)
    
# TODO- Build personal scoring logic using hobbies
def get_personal_score(hobbies, row):
    return random.uniform(0.1, 0.9)

def compute_score(user_1 : list, user_2 : list):
    input_kundali = {
            'DOB1' : user_1['DOB'],
            'DOB2' : user_2['DOB'],
            'TOB1' : user_1['TOB'], 
            'TOB2' : user_2['TOB'],
            'LAT1' : user_1['LAT'],
            'LAT2' : user_2['LAT'],
            'LONG1' : user_1['LONG'],
            'LONG2' : user_2['LONG']
        }

    kundali_score = None
    try:
        log.info(f'Input data: {input_kundali}')
        response = requests.post(   
                        f'{config.KUNDALI_SERVICE_URL}:{config.KUNDALI_SERVICE_PORT}/get:score', 
                            headers = {'content-type' : 'application/json'},
                            json = input_kundali
                        )
        if response.status_code == 200:
            response_json = response.json()
            if 'score' in response_json:
                kundali_score = response_json['score']
        else:
            log.info(f'Kundali Service errored: {response._content}')
        
    except Exception as e:
        log.warning(f'Unable to get response from kundali service: {e}')

    if kundali_score is None:
        log.info(f'Kundali score is None.')
        kundali_score = get_kundali_score()

    # TODO - Personal score scoring through hobbies
    personal_score = get_personal_score(user_1['HOBBIES'], user_2['HOBBIES'])

    return round(((kundali_score/config.TOTAL_GUN)*config.KUNDALI_WEIGHT + personal_score*config.PERSONAL_WEIGHT)*config.SCORE_OUT_OF, 1)


app = Flask(__name__)

@app.before_request
def handle_preflight():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response, 200

@app.route('/')
def health_check():
    return 'OK', 200

# @app.route('/twillio:token', methods=['POST'])
# def generate_token():
#     identity = request.json.get('identity')

#     token = AccessToken(
#         account_sid='YOUR_ACCOUNT_SID',
#         api_key='YOUR_API_KEY',
#         api_secret='YOUR_API_SECRET',
#         identity=identity
#     )

#     chat_grant = ChatGrant(service_sid='YOUR_SERVICE_SID')
#     token.add_grant(chat_grant)

#     return jsonify({'token': token.to_jwt().decode()})

@app.route('/account:create', methods=['POST'])
def create():
    # Receive multipart request
    # Get JSON part from form data
    metadata = request.form.get('metadata')
    if not metadata:
        return jsonify({'error': 'Missing metadata'}), 400
    try:
        json_data = json.loads(metadata)
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON'}), 400

    # Validate email and phone
    email = json_data.get('email', '').lower()
    phone = str(json_data.get('phone', ''))
    
    if not validate_email(email):
        return jsonify({'error': 'Invalid email format'}), 400
    if not validate_phone(phone):
        return jsonify({'error': 'Invalid phone number format'}), 400

    # Receive encoded images
    profile_images = request.files.getlist("images")

    log.info(f'Profile Images: {len(profile_images)}')
    # Setup SQLite connection
    profile_connect = SQLConnect(url = config.SQL_SERVICE_URL, port = config.SQL_SERVICE_PORT)
    
    insert_sql = f"INSERT INTO {config.PROFILE_TABLE} (UID, PASSWORD, NAME, PHONE, EMAIL, EMAIL_HASH, CITY, COUNTRY, PROFESSION, BIRTH_CITY, BIRTH_COUNTRY, DOB, TOB, GENDER, HOBBIES, LAT, LONG, IMAGES, CREATED, LOGIN, FILTERS) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    uid = str(uuid4())
    
    # Encrypt sensitive data
    password = encrypt_password(json_data['password'])
    encrypted_email = encrypt_sensitive_data(email)
    hashed_email = hash_email_sha256(email) # Need hashed email to search on email in database
    encrypted_phone = encrypt_sensitive_data(phone)
    
    name = json_data['name'].lower() 
    city = json_data['city'].lower() 
    country = json_data['country'].lower() 
    birth_city = json_data['birth_city'].lower()
    birth_country = json_data['birth_country'].lower()
    profession = json_data['profession'].lower()
    dob = str(json_data['dob']) # Fix format in UI yyyy-mm-dd
    tob = str(json_data['tob']) # Fix format in UI hh:mm Time of birth
    gender = json_data['gender'].lower()
    hobbies = json_data.get('hobbies', [])

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    #latitude and longitude is calculated for birth city and birth country
    lat, long = get_lat_long(f'{birth_city}, {birth_country}')
    lat, long = str(lat), str(long)

    # Get S3 url for image files
    images =[]
    if profile_images:
        png_paths = []
        for idx, image in enumerate(profile_images[:config.MAX_IMAGES]):
            path = process_image(image, f'image-{idx}.png')

            if path is not None:
                url = upload_file_to_s3(path, f'profile_pictures/{uid}/image-{idx}.png')
                images.append(str(url))
                png_paths.append(str(path))
        
        # Remove local images
        for path in png_paths:
            os.remove(path)

    log.info(f'Number of images: {len(images)}')

    # Convert list to string to be parsed as json
    if len(images)> 0:
        images = ','.join(images)
    else:
        images = ''

    if len(hobbies) > 0:
        hobbies = str(','.join(hobbies))
    else:
        hobbies = ''

    profile_connect.cursor.execute(insert_sql, (uid, password, name, encrypted_phone, encrypted_email, hashed_email, city, country, profession, birth_city, birth_country, dob, tob, gender, hobbies, lat, long, images, timestamp, timestamp, ''))
    profile_connect.conn.commit()

    # Asynchronous task to identify matches for user and populate to matching table.
    threading.Thread(target=run_async_task, args=(populate_matches(uid, gender),)).start()
    
    return {'UID' : uid}, None

async def populate_matches(uid, gender):
    '''
    Find matches for the user, compute scores and populate top n matches to matching table.
    '''
    if gender == 'male':
        fetch = 'female'
    else:
        fetch = 'male'

    # Select self user data using RDS
    profile_connect = SQLConnect(url = config.SQL_SERVICE_URL, port = config.SQL_SERVICE_PORT)

    select_self = F"SELECT UID, NAME, DOB, TOB, LAT, LONG, HOBBIES FROM {config.PROFILE_TABLE} WHERE UID = '{uid}'"
    profile_connect.cursor.execute(select_self)

    # Fetch all results
    self_result = profile_connect.cursor.fetchone()
    name = self_result["NAME"]
    
    select_sql = f"SELECT UID, DOB, TOB, LAT, LONG, HOBBIES, NAME FROM {config.PROFILE_TABLE} WHERE GENDER = '{fetch}'"
    log.info(f'Executing query: {select_sql}')
    profile_connect.cursor.execute(select_sql)
    results = profile_connect.cursor.fetchall()
    profile_connect.close()

    if len(results) > 0:
        log.info(f'Number of matches: {len(results)}')

        matched_uids, matched_names, scores = [], [], []

        for row in results:
            #kundali_obj = Kundali(dob, row['DOB'], tob, row["TOB"], lat, row["LAT"], long, row["LONG"])
            #kundali_score = kundali_obj.get_guna_score()/config.TOTAL_GUN

            matched_uids.append(row['UID'])
            matched_names.append(row['NAME'])
            score = compute_score(self_result, row)
            scores.append(score)


        # SORT LIST AND GET TOP TEN MATCHES
        sorted_pairs = sorted(zip(matched_uids, scores, matched_names), key=lambda x: x[1], reverse=True)
        recommendation_zip = sorted_pairs[:config.MAX_MATCHES]

        recommendation_cards = []
        for item in recommendation_zip:
            rec_uid = item[0]
            score = item[1]
            rec_name = item[2]
            recommendation_cards.append({
                'recommendation_uid': rec_uid,
                'name': rec_name,
                'score': score,
                'reason':  '', 
                'chat_enabled': False,
                'user_align': False,
                'blocked_by_match' : False, 
                'blocked_by_user' : False,
                'rec_idx' : 1,
                'usr_idx' : 0
            })

        matches, filtered, matches_and_filtered = filter_cards(uid, recommendation_cards)

        if len(matches) > 0:

            log.info(f'Recommendations: {matches}')

            matching_connect = SQLConnect(url = config.SQL_SERVICE_URL, port = config.SQL_SERVICE_PORT)
            # Post recommendations to matching table

            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            insert_sql_matching = f"INSERT INTO {config.MATCHING_TABLE} (UID1, NAME1, UID2, NAME2, SCORE, CREATED, UPDATED, ALIGN1, ALIGN2, SKIP1, SKIP2, BLOCK1, BLOCK2, REASON1, REASON2, FILTERED) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            
            for item in matches:
                if 'USER_REASON' in item:
                    usr_reason = item['USER_REASON']
                    rec_reason = item['REC_REASON']
                else:
                    usr_reason = 'Not Present'
                    rec_reason = 'Not Present'

                matching_connect.cursor.execute(insert_sql_matching, (uid, name, item['UID'], str(item['NAME']), str(item['RECOMMENDATION_SCORE']), timestamp, timestamp, False, False, False, False, False, False, usr_reason, rec_reason, False ) )
            
            for item in filtered:
                if 'USER_REASON' in item:
                    usr_reason = item['USER_REASON']
                    rec_reason = item['REC_REASON']
                else:
                    usr_reason = 'Not Present'
                    rec_reason = 'Not Present'

                matching_connect.cursor.execute(insert_sql_matching, (uid, name, item['UID'], str(item['NAME']), str(item['RECOMMENDATION_SCORE']), timestamp, timestamp, False, False, False, False, False, False, usr_reason, rec_reason, True ) )

            matching_connect.conn.commit()
            matching_connect.close()
        else:
            log.info('Filter rejected all cards')

        

def ensure_datetime(value):
    if isinstance(value, datetime):
        return value
    elif isinstance(value, str):
        # Adjust the format to match your string timestamp format
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    else:
        raise TypeError(f"Unsupported type for datetime conversion: {type(value)}")

async def put_yaml_to_s3(key, yaml_content):
    try:
        updated_yaml_bytes = yaml.dump(yaml_content).encode('utf-8')

        # Step 4: Write back to the same S3 key (overwrite)
        s3.put_object(Bucket=BUCKET_NAME, Key=key, Body=updated_yaml_bytes)
        log.info(f'Yaml object { key } updated in S3')

    except Exception as e:
        log.warning(f'ERROR: Unable to update { key } to s3 due to { e }')

def sort_notifications(notifications):
    updated_time = []
    messages = []

    for item in notifications:
        if "updated" in item and "message" in item:
            try:
                updated_time.append(item["updated"])
                messages.append(item["message"])
            except Exception as e:
                log.warning(f'Unable to process notification: {item}, Error: {e}')

    sorted_notifications = sorted(zip(updated_time, messages), key = lambda x: x[0], reverse=True)
    required_notifications = sorted_notifications[:config.MAX_NOTIFICATIONS]
    notifications = [{"message" : item[1], "updated" : item[0]} for item in required_notifications]

    return notifications


@app.route('/account:login', methods=['POST'])
def login():
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400

    json_data = request.get_json()
    if not json_data:
        return jsonify({'error': 'Missing JSON data'}), 400

    email = json_data.get('email', '').lower()
    password = json_data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Missing email or password'}), 400

    if not validate_email(email):
        return jsonify({'error': 'Invalid email format'}), 400

    # Setup SQLite connection
    profile_connect = SQLConnect(url = config.SQL_SERVICE_URL, port = config.SQL_SERVICE_PORT)

    
    # Use SHA256 hash for email lookup - compute hash in Python for SQLite compatibility
    hashed_email = hash_email_sha256(email)
    select_sql = f"SELECT UID, PASSWORD, NOTIFICATIONS, EMAIL, PHONE, LOGIN FROM {config.PROFILE_TABLE} WHERE EMAIL_HASH = ?"

     
    profile_connect.cursor.execute(select_sql, (hashed_email,))
    result = profile_connect.cursor.fetchone()

    if not result:
        return jsonify({'LOGIN': 'UNSUCCESSFUL', 'ERROR': 'Email not found.'})
    
    if not verify_password(result['UID'], password):
        return jsonify({'LOGIN': 'UNSUCCESSFUL', 'ERROR': 'Password is Incorrect.'})

    uid = result['UID']
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    
    # Update login time using RDS
    update_sql = f"UPDATE {config.PROFILE_TABLE} SET LOGIN = '{current_time}' WHERE UID = '{uid}'"
    profile_connect.cursor.execute(update_sql)
    profile_connect.conn.commit()
    profile_connect.close()

    notifications_url = result['NOTIFICATIONS']
    if notifications_url:
        try:
            key = urlparse(notifications_url).path.lstrip('/')
            s3_object = s3.get_object(Bucket=BUCKET_NAME, Key=key)
            yaml_content = s3_object['Body'].read()
            notifications = yaml.safe_load(yaml_content)
        except Exception:
            notifications = []
    else:
        notifications = []

    if len(notifications) > 0:
        notifications = sort_notifications(notifications)

    # Ensure both are datetime objects
   
    last_login = result['LOGIN']
    if isinstance(last_login, str):
        last_login = datetime.fromisoformat(last_login)

    new_notifications, counter = [], 0
    for notify in notifications:
        updated = notify["updated"]
        
        # Convert if they are strings
        if isinstance(updated, str):
            updated = datetime.fromisoformat(updated)

        if updated > last_login:
            counter += 1
            new_notifications.append(notify)
        else:
            break

    if counter < config.MAX_NOTIFICATIONS and len(notifications) > counter:

        old_notifications = notifications[counter:counter+config.MAX_NOTIFICATIONS]
    else:
        old_notifications = []
        

    # Decrypt email and phone for response
    decrypted_email = decrypt_sensitive_data(result['EMAIL'])
    decrypted_phone = decrypt_sensitive_data(result['PHONE'])

    return jsonify({
        'LOGIN': 'SUCCESSFUL', 
        'UID': uid, 
        'NEW_NOTIFICATIONS': new_notifications, 
        'OLD_NOTIFICATIONS': old_notifications,
        'EMAIL': decrypted_email,
        'PHONE': decrypted_phone,
        'ERROR': 'OK'
    })

def get_user_data(uid):
    """
    Internal function to get raw user data without Flask response wrapper.
    Used for internal processing where raw data is needed.
    """
    # Setup SQLite connection
    profile_connect = SQLConnect(url = config.SQL_SERVICE_URL, port = config.SQL_SERVICE_PORT)
    select_sql = f"SELECT NAME, DOB, CITY, COUNTRY, IMAGES, HOBBIES, PROFESSION, GENDER, NOTIFICATIONS, EMAIL, PHONE, FILTERS FROM {config.PROFILE_TABLE} WHERE UID = '{uid}'"
    profile_connect.cursor.execute(select_sql)
    result = profile_connect.cursor.fetchone()

    if not result:
        profile_connect.close()
        return None

    image_path_list = [i.strip() for i in str(result['IMAGES']).split(',')]
    user_data = {
        'UID': uid,
        'NAME': result['NAME'],
        'DOB': result['DOB'],
        'CITY': result['CITY'],
        'COUNTRY': result['COUNTRY'],
        'IMAGES': image_path_list,
        'HOBBIES': result['HOBBIES'],
        'PROFESSION': result['PROFESSION'],
        'GENDER': result['GENDER'],
        'FILTERS' : result['FILTERS'],
        'EMAIL': decrypt_sensitive_data( result['EMAIL'] ),
        'PHONE' : decrypt_sensitive_data( result['PHONE'] ),
        'ERROR': 'OK'
    }

    profile_connect.conn.commit()
    profile_connect.close()

    return user_data

@app.route('/get:user/<uid>', methods=['GET'])
def get_user(uid):
    """
    Flask route to get user data. Returns JSON response for API calls.
    """
    user_data = get_user_data(uid)
    
    if not user_data:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify(user_data)


# TODO - Use LLM to filter cards 
# Provide saved filters of user (not more than 5) - User can ask LLM to edit these filters
# LLM analyzes all cards together, thios gives it better context of each card
# ALso ask why is a good match
def filter_cards(uid, recommendation_cards, new_filter : str = None, filter = True):
    
    user_details = get_user_data(uid)
    if not user_details:
        log.error(f"User not found: {uid}")
        return jsonify({'error': 'User not found'}), 404
    
    user_filters_str = user_details['FILTERS']

    if isinstance(user_filters_str, str):
        user_filters = user_filters_str.split(',')
    else:
        user_filters = []

    user_details.pop('EMAIL', None)
    user_details.pop('PHONE', None)
    user_details.pop('ERROR', None)
    user_details.pop('UID', None)
    user_details.pop('IMAGES', None)

    if new_filter and isinstance(new_filter, str) and len(new_filter) > 0:
        user_filters.append(new_filter)

    log.info('Enhancing cards to populate.')
    
    enhanced_cards = []
    #log.info(recommendation_cards)
    for card in recommendation_cards:
        rec_uid = card["recommendation_uid"]
        card_details = get_user_data(rec_uid)
        if not card_details:
            log.warning(f"User not found for recommendation: {rec_uid}")
            continue
        card_details.pop('EMAIL', None)
        card_details.pop('PHONE', None)
        card_details.pop('ERROR', None)
        card_details.pop('IMAGES', None)
        card_details['UID'] = rec_uid
        if isinstance(card["score"],tuple):
            score = card["score"][0]
        else:
            score = card["score"]
        card_details['RECOMMENDATION_SCORE'] = score
        card_details["rec_idx"] = card["rec_idx"]
        card_details["usr_idx"] = card["usr_idx"]
        enhanced_cards.append(card_details)

    log.info(f'Cards to filter: {len(enhanced_cards)}')
    filter_success = True
    matches, filtered = [], []
    matches_and_filtered = {}
    
    if filter and isinstance(user_filters, list) and len(user_filters) > 0:
        try:
            log.info(f'applying filter: {user_details},\n{enhanced_cards}')
            matches_and_filtered = filter_agent(user_details, enhanced_cards)
            log.info(f'Filter applied. Result: {matches_and_filtered}')

            for i in enhanced_cards:
                if i['UID'] in matches_and_filtered['Matched'].keys():
                    usr_reason, rec_reason = matches_and_filtered['Matched'][i['UID']][0], matches_and_filtered['Matched'][i['UID']][1]
                    i['USER_REASON'] = usr_reason
                    i['REC_REASON'] = rec_reason
                    matches.append(i)

                elif i['UID'] in matches_and_filtered['Filtered'].keys():
                    usr_reason, rec_reason = matches_and_filtered['Filtered'][i['UID']][0], matches_and_filtered['Filtered'][i['UID']][1]
                    i['USER_REASON'] = usr_reason
                    i['REC_REASON'] = rec_reason
                    filtered.append(i)
        except Exception as e:
            log.warning(f'Filter Failed: {e}')
            filter_success = False

    if not isinstance(user_filters, list) or len(user_filters) == 0 or filter == False or filter_success == False:
        log.info(f'Skipping filter: Number of cards: {len(enhanced_cards)}, Filter: {filter}, filter success: {filter_success}')
        matches, filtered, matches_and_filtered = [], [], {}
        for i in enhanced_cards:
            i['USER_REASON'] = 'Not Present'
            i['REC_REASON'] = 'Not Present'
            matches.append(i)
                
        # if len(matches) == 0:
        #     matches = cards[:]
        #                    
    if new_filter:
        if user_filters_str:
            updated_filters = user_filters_str + ',' + new_filter
        else:
            updated_filters = new_filter
        threading.Thread(target=run_async_task, args=(update_filter(uid, updated_filters),)).start()
        # Asyncronous task to add
        log.info('Asyncronously updated user filter')

    return matches, filtered, matches_and_filtered

async def update_filter(uid, updated_filters: str):
    connect = SQLConnect(url = config.SQL_SERVICE_URL, port = config.SQL_SERVICE_PORT)
    query = f"UPDATE {config.PROFILE_TABLE} SET FILTERS = ? WHERE UID = ?"
    connect.cursor.execute(query, (updated_filters, uid))
    connect.conn.commit()
    connect.close()

def fetch_queue(uid, queue_requested):
    matching_connect = SQLConnect(url = config.SQL_SERVICE_URL, port = config.SQL_SERVICE_PORT)
    sql = f"SELECT UID1, UID2, SCORE, UPDATED, ALIGN1, ALIGN2, SKIP1, SKIP2, BLOCK1, BLOCK2, NAME1, NAME2, REASON1, REASON2, FILTERED FROM {config.MATCHING_TABLE} WHERE UID1 = '{uid}' OR UID2 = '{uid}'"
    matching_connect.cursor.execute(sql)
    results = matching_connect.cursor.fetchall()

    cards = []
    for row in results:
        uid1 = row['UID1']
        uid2 = row['UID2']
        score = row['SCORE'], 
        updated = row['UPDATED'], 

        if isinstance(row['FILTERED'], bool) and row['FILTERED'] == True:
            continue

        usr_idx = 0 if uid == uid1 else 1
        rec_idx = 1 - usr_idx

        usr_align, rec_align = (row['ALIGN1'], row['ALIGN2']) if usr_idx == 0 else (row['ALIGN2'], row['ALIGN1'])
        usr_skip, rec_skip = (row['SKIP1'], row['SKIP2']) if usr_idx == 0 else (row['SKIP2'], row['SKIP1'])
        usr_block, rec_block = (row['BLOCK1'], row['BLOCK2']) if usr_idx == 0 else (row['BLOCK2'], row['BLOCK1'])
        usr_reason, rec_reason = (row['REASON1'], row['REASON2']) if usr_idx == 0 else (row['REASON2'], row['REASON1'])

        if usr_skip or rec_skip:
            continue
        if usr_align and rec_align:
            queue = 'MATCHES'
        elif not usr_align and not rec_align:
            queue = 'RECOMMENDATIONS'
        else:
            queue = 'AWAITING'

        if queue != queue_requested:
            continue

        recommendation_uid = uid2 if uid1 == uid else uid1
        name = row['NAME2'] if uid1 == uid else row['NAME1']

        cards.append({
            'recommendation_uid': recommendation_uid,
            'name': name,
            'score': score,
            'reason':  usr_reason, 
            'chat_enabled': usr_align and rec_align,
            'user_align': usr_align,
            'blocked_by_match' : rec_block, 
            'blocked_by_user' : usr_block,
            'rec_idx' : rec_idx,
            'usr_idx' : usr_idx
        })

    matching_connect.conn.commit()
    matching_connect.close()
    return cards

@app.route('/get:awaiting/<uid>', methods=['GET'])
def get_awaiting(uid):
    return jsonify({'cards': fetch_queue(uid, 'AWAITING')})

@app.route('/get:recommendations/<uid>', methods=['GET'])
def get_recommendations(uid):
    return jsonify({'cards': fetch_queue(uid, 'RECOMMENDATIONS')})

@app.route('/get:matches/<uid>', methods=['GET'])
def get_matches(uid):
    return jsonify({'cards': fetch_queue(uid, 'MATCHES')})


def live_filter(uid : str, new_filter : str):

    recommendations = fetch_queue(uid, 'RECOMMENDATIONS')

    matches, filtered, matches_and_filtered = filter_cards(uid, recommendations, new_filter)

    if len(matches) == 0:
        return {'RECOMMENDATIONS' : recommendations, 'RESPONSE' : 'User filters do not satisfy any match, Please remove some filters.' }
    else:
        log.info(f'Recommendations: {matches}')

        # Post recommendations to matching table
        matching_connect = SQLConnect(url = config.SQL_SERVICE_URL, port = config.SQL_SERVICE_PORT)
        
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        recommendations = []
        for item in matches:
            log.info(item)
            rec_uid = item["UID"]
            rec_idx = int(item["rec_idx"]) + 1
            usr_idx = int(item["usr_idx"]) + 1
        
            
            if 'USER_REASON' in item:
                usr_reason = item['USER_REASON']
                rec_reason = item['REC_REASON']
                
            else:
                usr_reason = 'Not Present'
                rec_reason = 'Not Present'
            
            item.pop('REC_REASON')
            recommendations.append(item)

            update_query = f"UPDATE {config.MATCHING_TABLE} SET REASON{usr_idx} = ?, REASON{rec_idx} = ?, UPDATED = ?, FILTERED = 0 WHERE UID{usr_idx} = ? AND UID{rec_idx} = ?"
            matching_connect.cursor.execute(update_query, (usr_reason, rec_reason, timestamp, uid, rec_uid))
        
        for item in filtered:
            
            rec_uid = item["UID"]
            rec_idx = int(item["rec_idx"]) + 1
            usr_idx = int(item["usr_idx"]) + 1
            if 'USER_REASON' in item:
                usr_reason = item['USER_REASON']
                rec_reason = item['REC_REASON']
            else:
                usr_reason = 'Not Present'
                rec_reason = 'Not Present'

            update_query = f"UPDATE {config.MATCHING_TABLE} SET REASON{usr_idx} = ?, REASON{rec_idx} = ?, UPDATED = ?, FILTERED = 1 WHERE UID{usr_idx} = ? AND UID{rec_idx} = ?"
            matching_connect.cursor.execute(update_query, (usr_reason, rec_reason, timestamp, uid, rec_uid))
        
        matching_connect.conn.commit()
        matching_connect.close()

        return {'RECOMMENDATIONS' : recommendations, 'RESPONSE' : 'Recommendations have been updated as per your request.' }

def get_encoded_images(image_paths):
    '''
        Download multiple images from s3
    '''

    image_data_list = []
    if isinstance(image_paths, str) and len(image_paths)>0:
        images = [image.strip() for image in image_paths.split(',')]

        log.info(f'Len Images: {len(images)}, {images}')
        if images and isinstance(images, list) and len(images) > 0:
            try:
                for path in images:
                    if path == '':
                        continue
                    try:
                        parsed = urlparse(path)
                        image_key = parsed.path.lstrip('/')
                        # Download image from S3 as bytes
                        s3_object = s3.get_object(Bucket=BUCKET_NAME, Key=image_key)
                        image_bytes = s3_object['Body'].read()
                        encoded_image = base64.b64encode(image_bytes).decode('utf-8')
                        image_data_list.append({
                            "filename": path,
                            "data": encoded_image
                        })
                    except Exception as e:
                        log.warning(f"Failed to load image {path}: {e}")
            except Exception as e:
                log.warning(f"Failed to parse IMAGES field: {e}")

    return image_data_list

@app.route('/get:profile/<string:uid>', methods=['GET'])
def get_profile(uid):
    if uid is None:
        return jsonify({"error": "Missing 'uid' in url"}), 400

    # Setup SQLite connection
    profile_connect = SQLConnect(url = config.SQL_SERVICE_URL, port = config.SQL_SERVICE_PORT)
    select_sql = f"SELECT UID, NAME, DOB, CITY, COUNTRY, IMAGES, HOBBIES, PROFESSION, GENDER FROM {config.PROFILE_TABLE} WHERE UID = '{uid}'"
    profile_connect.cursor.execute(select_sql)
    result = profile_connect.cursor.fetchone()

    profile_connect.close()

    # Convert image S3 paths to base64-encoded image data
    image_paths = result['IMAGES']
    image_path_list = [i.strip() for i in image_paths.split(',')]

    result['IMAGES'] = image_path_list
    result['error'] = 'OK'

    return jsonify(result)

async def update_notifications_or_chats(uid, new_notifications_or_chats, column):

    column = column.lower()

    if column == 'notifications':
        col = 'NOTIFICATIONS'
    elif column == 'initiate_chats':
        col = 'INITIATE_CHATS'
    elif column == 'preference_chats':
        col = 'PREFERENCE_CHATS'
    else:
        log.warning(f"Unsupported datatype/column: {column}. Supported datatypes are ['notifications', 'initiate_chats', 'preference_chats']")
        return None
    
    profile_connect = SQLConnect(url = config.SQL_SERVICE_URL, port = config.SQL_SERVICE_PORT)
    select_sql = f"SELECT UID, CREATED, PASSWORD, LOGIN, {col} FROM {config.PROFILE_TABLE} WHERE UID = '{uid}'"
    profile_connect.cursor.execute(select_sql)

    result = profile_connect.cursor.fetchone()
    
    process = True

    if process:
        notifications_or_chats_url = result[col]

        # Handle PostgreSQL NaN, None, empty strings, and string 'None'
        if (notifications_or_chats_url is None or 
            notifications_or_chats_url in ['', 'None'] or
            (isinstance(notifications_or_chats_url, float) and pd.isna(notifications_or_chats_url)) or
            str(notifications_or_chats_url).lower() in ['nan', 'null']):
            notifications_or_chats = []
            new_s3_obj = True

        else:

            try:
                notifications_or_chats_url_parsed = urlparse(notifications_or_chats_url)
                notifications_or_chats_url = notifications_or_chats_url_parsed.path.lstrip('/')

                # Download image from S3 as bytes
                s3_object = s3.get_object(Bucket=BUCKET_NAME, Key=notifications_or_chats_url)
                yaml_content = s3_object['Body'].read()

                # Parse YAML
                notifications_or_chats = yaml.safe_load(yaml_content)
                new_s3_obj = False
            except Exception as e:
                log.error(f'Unable to fetch notifications: {notifications_or_chats_url}, {e}')
                raise Exception(f'Unable to fetch notifications: {notifications_or_chats_url}, {e}')

        notifications_or_chats.extend(new_notifications_or_chats)

        if new_s3_obj:
            filename = f'{column}/{uid}_{column}.yaml'

            directory = os.getcwd()
            filepath = os.path.join(directory, f"{uid}_notifications.yaml")
            with open(filepath, 'w') as file:
                yaml.dump(notifications_or_chats, file)

            log.info(f'Saved to {filepath} : {notifications_or_chats}')

            path = upload_file_to_s3(filepath, filename)

            update_sql = f"UPDATE {config.PROFILE_TABLE} SET {col} = '{str(path)}' WHERE UID = '{uid}'"
            
            profile_connect.cursor.execute(update_sql)
            profile_connect.conn.commit()

        else:
            try:
                updated_yaml_bytes = yaml.dump(notifications_or_chats).encode('utf-8')

                # Step 4: Write back to the same S3 key (overwrite)
                s3.put_object(Bucket=BUCKET_NAME, Key=notifications_or_chats_url , Body=updated_yaml_bytes)
                log.info(f'Yaml object { notifications_or_chats_url  } updated in S3')

            except Exception as e:
                log.warning(f'ERROR: Unable to update { notifications_or_chats_url } to s3 due to { e }')

        profile_connect.close()

# TODO - Make async call to update notifications for the other user
@app.route('/account:action', methods=['POST'])
def action():
    try:
        json_data = request.get_json()
        uid = json_data.get('uid')
        rec_uid = json_data.get('recommendation_uid')
        action = json_data.get('action')
        assert action in ['align', 'skip', 'block']
    except:
        return jsonify({'error': 'Invalid JSON or missing uid/recommendation_uid/action'}), 400
    
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    valid_cols = ['UID1', 'UID2', 'SCORE', 'UPDATED', 'ALIGN1', 'ALIGN2', 'SKIP1', 'SKIP2', 'BLOCK1', 'BLOCK2', 'NAME1', 'NAME2']
    
    matching_connect = SQLConnect(url = config.SQL_SERVICE_URL, port = config.SQL_SERVICE_PORT)
    
    sql_fetch = f"SELECT UID1, UID2, SCORE, UPDATED, ALIGN1, ALIGN2, SKIP1, SKIP2, BLOCK1, BLOCK2, NAME1, NAME2 FROM {config.MATCHING_TABLE} WHERE (UID1 = '{uid}' AND UID2 = '{rec_uid}') OR (UID1 = '{rec_uid}' AND UID2= '{uid}')"
    matching_connect.cursor.execute(sql_fetch)
    result = matching_connect.cursor.fetchone()
    
    user_align = False
    uid1, uid2 = result["UID1"], result["UID2"]
    if str(uid1) == str(uid):
        user_name = result["NAME1"]
        recommended_user_name = result["NAME2"]
        user_block = result["BLOCK1"]
        rec_align = result["ALIGN2"]

        primary = 0
        rec_idx = 1

    elif str(uid2) == str(uid):
        user_name = result["NAME2"]
        recommended_user_name = result["NAME1"]
        user_block = result["BLOCK2"]
        rec_align = result["ALIGN1"]
        
        primary = 1
        rec_idx = 0
    else:
        log.error(f'No match for usr uid {uid}, {uid1}, {uid1}\n{result}')
        return jsonify({'Error' : f'No match for usr uid {uid}, {uid1}, {uid2}\n{result}'}), 400

    message_recommender = None
    message = None
    if action == 'skip':
        delete_sql = f"DELETE FROM {config.MATCHING_TABLE} WHERE UID1 = '{uid1}' AND UID2 ='{uid2}'"
        matching_connect.cursor.execute(delete_sql)
        queue = 'None'
        message = f'{recommended_user_name} will not be recommended to you.'

    # Right now we do not provide option to retract your response
    elif action == 'align':
        align_col = f'ALIGN{primary+1}'

        if align_col not in valid_cols:
            log.warning(f'{align_col} not a valid column')


        update_sql = f"UPDATE {config.MATCHING_TABLE} SET {align_col} = {True}, UPDATED = '{current_time}' WHERE UID1 = '{uid1}' AND UID2 = '{uid2}'"
        matching_connect.cursor.execute(update_sql)

        if rec_align == True:
            queue = 'MATCHED'
            message = f'You have been matched with {recommended_user_name}.'
            message_recommender = f'{user_name} has accepted your align request.'

        else:
            queue = 'AWAITING'
            message = f'Align request has been sent to {recommended_user_name}'
            message_recommender = f'You recieved an align request from {user_name}'

        user_align = True

    elif action == 'block':
        
        if user_block == True:
            user_block = False
            message = f'{recommended_user_name} has been Unblocked.'
        else:
            user_block = True
            message = f'{recommended_user_name} has been Blocked.'

        block_col = f'BLOCK{primary+1}'

        if block_col not in valid_cols:
            log.warning(f'{block_col} not a valid column')

        update_sql = f"UPDATE {config.MATCHING_TABLE} SET {block_col} = {True}, UPDATED = '{current_time}' WHERE UID1 = '{uid1}' AND UID2 = '{uid2}'"
        matching_connect.cursor.execute(update_sql)

        queue = 'MATCHED'

    matching_connect.conn.commit()
    matching_connect.close()

    # Creates and destroys event loop
    #asyncio.run(put_yaml_to_s3(uid, [{'message' : message, 'updated' : current_time}]))

    if message is not None:
        threading.Thread(target=run_async_task, args=(update_notifications_or_chats(uid, [{'message' : message, 'updated' : current_time}], 'notifications'),)).start()

    if message_recommender is not None:
        threading.Thread(target=run_async_task, args=(update_notifications_or_chats(rec_uid, [{'message' : message_recommender, 'updated' : current_time}], 'notifications'),)).start()

    return jsonify({'error' : 'OK', 'queue' : queue, 'user_align' : user_align, 'message' : message, "updated" : current_time, 'user_block' : user_block})

# Verify email both at signing up it should be True and while login it should be false
# Before making the create:account call, UI should make verify:email call to ensure emails are unique 
@app.route('/verify:email', methods=['POST'])
def verify_email():
    try:
        json_data = request.get_json()
        email = json_data.get('email')
        if not email:
            return jsonify({'error': 'Missing email'}), 400
    except:
        return jsonify({'error': 'Invalid JSON or missing email'}), 400
    


    # Hash email for lookup (since emails are hashed in database)
    hashed_email = hash_email_sha256(email)

    # Setup SQLite connection
    profile_connect = SQLConnect(url = config.SQL_SERVICE_URL, port = config.SQL_SERVICE_PORT)

    # Compare with encrypted email in database
    sql_fetch = f"SELECT UID FROM {config.PROFILE_TABLE} WHERE EMAIL=?"
    profile_connect.cursor.execute(sql_fetch, (hashed_email,))
    results = profile_connect.cursor.fetchall()

    profile_connect.conn.commit()
    profile_connect.close()

    if len(results) > 0:
        return { 'verify' : False }
    else:
        return { 'verify' : True }

@app.route('/account:update', methods=['POST'])
def update_account():
    metadata = request.form.get('metadata')
    if not metadata:
        return jsonify({'error': 'Missing metadata'}), 400
    try:
        json_data = json.loads(metadata)
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON'}), 400

    uid = json_data.get('uid')
    if not uid:
        return jsonify({'error': 'Missing UID for update'}), 400

    profile_images = request.files.getlist("images")
    fields = {}
    png_paths = []

    # Define expected fields and handle them
    allowed_fields = [
        'password', 'name', 'phone', 'city', 'country', 'profession',
        'birth_city', 'birth_country', 'dob', 'tob', 'gender', 'hobbies'
    ]

    # Validate and encrypt sensitive data
    if 'phone' in json_data:
        phone = str(json_data['phone'])
        if not validate_phone(phone):
            return jsonify({'error': 'Invalid phone number format'}), 400
        fields['PHONE'] = encrypt_sensitive_data(phone)

    if 'password' in json_data:
        fields['PASSWORD'] = encrypt_sensitive_data(json_data['password'])

    for field in allowed_fields:
        if field in json_data and field not in ['phone', 'password']:  # Skip already handled fields
            value = json_data[field]
            if isinstance(value, str) and value != '':
                value = value.lower()
            if field == 'hobbies' and isinstance(value, list):
                value = ','.join(value)
            fields[field.upper()] = str(value)

    # Get latitude and longitude if birth city/country is provided
    if 'birth_city' in json_data or 'birth_country' in json_data:
        birth_city = json_data.get('birth_city', '').lower()
        birth_country = json_data.get('birth_country', '').lower()
        lat, long = get_lat_long(f'{birth_city}, {birth_country}')
        fields['LAT'] = str(lat)
        fields['LONG'] = str(long)

    # Process images
    if profile_images:
        images = []
        for idx, image in enumerate(profile_images[:config.MAX_IMAGES]):
            path = process_image(image, f'image-{idx}.png')
            if path:
                url = upload_file_to_s3(path, f'profile_pictures/{uid}/image-{idx}.png')
                images.append(str(url))
                png_paths.append(path)

        # Remove local files
        for path in png_paths:
            os.remove(path)

        fields['IMAGES'] = ','.join(images)

    # If no fields to update
    if not fields:
        return jsonify({'error': 'No valid fields provided for update'}), 400

    # Build SQL UPDATE dynamically
    set_clause = ', '.join([f"{key} = ?" for key in fields.keys()])
    values = list(fields.values())
    values.append(uid)  # for WHERE clause

    update_sql = f"UPDATE {config.PROFILE_TABLE} SET {set_clause} WHERE UID = ?"

    try:
        profile_connect = SQLConnect(url = config.SQL_SERVICE_URL, port = config.SQL_SERVICE_PORT)
        profile_connect.cursor.execute(update_sql, values)
        profile_connect.conn.commit()
    except Exception as e:
        log.error(f"Failed to update profile: {e}")
        return jsonify({'error': 'Database error during update'}), 500
    

    # Define fields that impact matching
    matching_fields = {'DOB', 'TOB', 'LAT', 'LONG', 'HOBBIES'}
    update_score = False
    for field in matching_fields:
        if field in fields:
            update_score = True
            break

    # Check if matching-relevant fields were updated
    if update_score:
        log.info(f"Recalculating matching score for UID: {uid} due to updates.")

        # Re-fetch updated user profile
        profile_connect = SQLConnect(url = config.SQL_SERVICE_URL, port = config.SQL_SERVICE_PORT)
        profile_connect.cursor.execute(f"SELECT UID, DOB, TOB, LAT, LONG, HOBBIES, GENDER, NAME FROM {config.PROFILE_TABLE} WHERE UID = ?", (uid,))
        current_user = profile_connect.cursor.fetchone()
        
        if current_user:
            uid, dob, tob, lat, long, hobbies, gender, user_name = current_user

            # Fetch all matches where this user is involved
            matching_connect = SQLConnect(url = config.SQL_SERVICE_URL, port = config.SQL_SERVICE_PORT)
            match_query = f"SELECT UID1, UID2 FROM {config.MATCHING_TABLE} WHERE UID1 = ? OR UID2 = ?"
            matching_connect.cursor.execute(match_query, (uid, uid))
            match_rows = matching_connect.cursor.fetchall()

            recommended_uids, recommended_names, new_scores = [], [], []
            for uid1, uid2 in match_rows:
                # Determine the other user
                other_uid = uid2 if uid1 == uid else uid1
                
                # Fetch other user's data using RDS
                other_user_select_sql = f'SELECT UID, DOB, TOB, LAT, LONG, HOBBIES, GENDER, NAME FROM "{config.RDS_PROFILE_TABLE}" WHERE UID = ?'
                profile_connect.cursor.execute(other_user_select_sql, (other_uid,))
                other_user = profile_connect.cursor.fetchone()

                if other_user:
                    # Compute new score (you should have this logic in place)
                    new_score = compute_score(current_user, other_user)

                    recommended_uids.append(other_uid)
                    new_scores.append(new_score)
                    recommended_names.append(other_user[-1])

                    # Update score in matching table
                    update_match_sql = f"UPDATE {config.MATCHING_TABLE} SET SCORE = ? WHERE (UID1 = ? AND UID2 = ?) OR (UID1 = ? AND UID2 = ?)"
                    matching_connect.cursor.execute(update_match_sql, (new_score, uid, other_uid, other_uid, uid))
            
            if gender == 'male':
                fetch = 'female'
            else:
                fetch = 'male'

            recommended_uids = ['uid1', 'uid2', 'uid3']
            uids_sql = "(" + ",".join(f"'{uid}'" for uid in recommended_uids) + ")"

            select_sql = f"SELECT UID, DOB, TOB, LAT, LONG, HOBBIES, NAME FROM {config.PROFILE_TABLE} WHERE GENDER = '{fetch}' AND UID NOT IN {uids_sql}"
            profile_connect.cursor.execute(select_sql)

            # Fetch all results
            results = profile_connect.cursor.fetchall()
            profile_connect.close()

            previous_uids = recommended_uids[:]
            for row in results:
    
                recommended_uids.append(row['UID'])
                score = compute_score(current_user, row)
                new_scores.append(score)
                recommended_names.append(-1)

            # SORT LIST AND GET TOP TEN MATCHES
            sorted_pairs = sorted(zip(recommended_uids, new_scores, recommended_names), key=lambda x: x[1], reverse=True)
            recommendations = sorted_pairs[:config.MAX_MATCHES]
            insert_sql_matching = f"INSERT INTO {config.MATCHING_TABLE} (UID1, UID2, SCORE, CREATED, UPDATED, ALIGN1, ALIGN2, SKIP1, SKIP2, BLOCK1, BLOCK2, NAME1, NAME2) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"

            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            for idx, id_pair in enumerate(recommendations):
                if id_pair[0] not in previous_uids:
                    matching_connect.cursor.execute(insert_sql_matching, (uid, id_pair[0], str(id_pair[1]), timestamp, timestamp, False, False, False, False, False, False, user_name, id_pair[-1]) )
            matching_connect.conn.commit()
            matching_connect.close()

    return jsonify({'UID' : uid, 'error' : 'OK'}), 200

# DESTINY
# There are 3 different methods to implement chatting
# initiate - start conversation by first fetching details about the user from snoflake
# continue - continue the conversation, it expects history as a list of dicts, this is to be smoothest and does no database calls
# terminate - after the conversation pushes provided history to s3

def load_prompts(filepath: str) -> dict:
    with open(filepath, "r") as file:
        return yaml.safe_load(file)
    
def load_previous_chats(chats_url):

    if chats_url is None or (type(chats_url) == str and chats_url == ''):
        chats = []
        log.info(f'No chats url is None')

    elif type(chats_url) == str:
        
        chats_url_parsed = urlparse(chats_url)
        chats_url = chats_url_parsed.path.lstrip('/')

        try:
            # Download image from S3 as bytes
            s3_object = s3.get_object(Bucket=BUCKET_NAME, Key=chats_url)
            yaml_content = s3_object['Body'].read()

            # Parse YAML
            chats = yaml.safe_load(yaml_content)
            if chats is None:
                chats = []

        except Exception as e:
            log.warning(f'Unable to load chats url {chats_url}')
            chats = []
    else:
        log.warning(f'Chats url is not string: {chats_url}')
        chats = []
        

    # TODO: Filter last {n} chats and summarize all from 1 to n-1
    previous_chats =''
    if len(chats) >= 0:
        try:
            chat_num = 1
            for idx, item in enumerate(chats):
                if "history" in item:
                    chat_num += 1
                    previous_chats += f'Chat Number: {chat_num}, Date and Time: {item["updated"]}\n'
                    for convo in item["history"]:
                        if "role" in convo:
                            if convo["role"] in ["assistant", "user"]:
                                if "content" in convo:
                                    previous_chats += f'role : {convo["role"]}, content: {convo["content"]}'
                                if "message" in convo:
                                    previous_chats += f'role : {convo["role"]}, content: {convo["message"]}'
        except Exception as e:
            log.warning(f'Unable to get previous_chats from {chats}, {e}')


    return previous_chats
    

@app.route("/chat:app", methods=["GET", "POST"])
def chat_app():
    """
    Unified endpoint for app-initiated hobby conversations
    
    GET: Start new conversation
    POST: Continue existing conversation
    
    POST Body: {
        "uid": "user_id",
        "user_input": "user message",
        "history": [optional previous history]
    }
    """
    try:
        json_data = request.get_json()
        
        uid = json_data.get('uid')
        if not uid:
            return jsonify({"error": "Missing 'uid' parameter"}), 400
        
        user_input = json_data.get('user_input', '')
        history = json_data.get('history', [])

        if isinstance(user_input, str) and len(user_input) > 0 and isinstance(history, list) and len(history) > 0:
            # Continue app-initiated conversation
            
            result = chat_flow.initiate_chat(
                chat_type="app_initiated",
                uid=uid,
                user_input=user_input,
                history=history,
                log = log
            )

        else:
            result = chat_flow.initiate_chat(
                chat_type="app_initiated",
                uid=uid,
                log = log
            )
        
        if "error" in result:
            return jsonify(result), 400
            
        return jsonify({
            "message": result.get("message", ""),
            "history": result.get("history", []),
            "continue": result.get("continue", True)
        })
        
    except Exception as e:
        log.error(f"Error in chat_app: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/chat:user", methods=["POST"])
def chat_user():
    """
    Unified endpoint for user-initiated preference conversations
    
    POST Body: {
        "uid": "user_id",
        "user_input": "user message",
        "history": [optional previous history]
    }
    """
    try:
        json_data = request.get_json()
        uid = json_data.get('uid')
        user_input = json_data.get('user_input', '')
        history = json_data.get('history', [])
        log.info(f'Preference chat with {uid}, User Input: {user_input}')
        if not all([uid, user_input]) or len(user_input) == 0:
            return jsonify({'error': 'Missing uid or user_input'}), 400
        
        result = chat_flow.initiate_chat(
            chat_type="user_initiated",
            uid=uid,
            user_input=user_input,
            history=history,
            log= log
        )
        
        if "error" in result:
            return jsonify(result), 400
            
        # Include all response fields
        response = {
            "message": result.get("message", ""),
            "history": result.get("history", []),
            "continue": result.get("continue", True)
        }
        
        # Include filter-specific fields if present
        if result.get("filter_applied"):
            response["filter_applied"] = True
            response["recommendations"] = result.get("recommendations", [])
            
        return jsonify(response)
        
    except Exception as e:
        log.error(f"Error in chat_user: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/e2echat:token/<string:uid>', methods=['GET'])
def generate_chat_token(uid):
    """Generate a Twilio Conversations access token"""
    try:
        if not uid:
            return jsonify({"error": "Missing 'uid' in url"}), 400

        token = AccessToken(
            secrets['TWILIO_ACCOUNT_SID'],
            secrets['TWILIO_API_KEY'],
            secrets['TWILIO_API_SECRET'],
            identity=uid
        )

        chat_grant = ChatGrant(service_sid=config.TWILIO_CHAT_SERVICE_SID)
        token.add_grant(chat_grant)


        return jsonify({
            'token': token.to_jwt(),  # decode to string
            'error': 'OK'
        })

    except Exception as e:
        log.error(f"Error generating chat token: {e}")
        return jsonify({'error': str(e)}), 500

    
def safely_add_participant(client, conversation_sid, identity):
    try:
        client.conversations.v1.conversations(conversation_sid).participants.create(identity=identity)
    except Exception as e:
        if "Participant already exists" in str(e):
            log.warning(f"Participant {identity} already exists in conversation {conversation_sid}")
        else:
            raise


@app.route('/e2echat:conversation', methods=['POST'])
def get_conversation():
    """Get or create a conversation between two users via Twilio"""
    try:
        json_data = request.get_json()
        if not json_data:
            return jsonify({'error': 'Missing JSON data'}), 400

        uid1 = json_data.get('uid1')
        uid2 = json_data.get('uid2')
        if not uid1 or not uid2:
            return jsonify({'error': 'Missing uid1 or uid2'}), 400

        # Init Twilio client
        client = Client(
            secrets['TWILIO_API_KEY'],
            secrets['TWILIO_API_SECRET'],
            secrets['TWILIO_ACCOUNT_SID']
        )

        # Connect to SQLite
        matching_connect = SQLConnect(url = config.SQL_SERVICE_URL, port = config.SQL_SERVICE_PORT)

# Check if conversation already exists
        select_sql = f"""
            SELECT CONVERSATION_SID 
            FROM {config.MATCHING_TABLE} 
            WHERE (UID1 = ? AND UID2 = ?) OR (UID1 = ? AND UID2 = ?)
        """

        matching_connect.cursor.execute(select_sql, (uid1, uid2, uid2, uid1))
        result = matching_connect.cursor.fetchone()

        if result:
            conversation_sid = result['CONVERSATION_SID']
        else:
            # Create new conversation
            conversation = client.conversations.v1.conversations.create(
                friendly_name=config.TWILIO_SERVICE_NAME
            )
            conversation_sid = conversation.sid

            # Add participants if they're not already in the conversation

            safely_add_participant(client, conversation_sid, uid1)
            safely_add_participant(client, conversation_sid, uid2)

            log.info(f'Conversation SID: {conversation_sid}')
            # Store conversation SID in your DB
            update_sql = f"""
                UPDATE {config.MATCHING_TABLE} 
                SET CONVERSATION_SID = ? 
                WHERE (UID1 = ? AND UID2 = ?) OR (UID1 = ? AND UID2 = ?)
            """
            
            matching_connect.cursor.execute(update_sql, (conversation_sid, uid1, uid2, uid2, uid1))
            matching_connect.conn.commit()

        matching_connect.close()

        return jsonify({
            'conversation_sid': conversation_sid,
            'error': 'OK'
        })

    except Exception as e:
        log.error(f"Error managing conversation: {e}")
        return jsonify({'error': str(e)}), 500


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response

if __name__ == '__main__':
    
    app.run(host='0.0.0.0', port=8040)
