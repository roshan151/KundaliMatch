import os
import json
import time
import yaml
import random
import base64
import asyncio
from flask import send_file
from datetime import datetime
import requests
import boto3
import hashlib
from botocore.exceptions import NoCredentialsError
from uuid import uuid4
from PIL import Image
import threading
from geopy.geocoders import Nominatim
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from config import config
from flask import Flask, request, jsonify, make_response
from snowflake_utils import SnowConnect
from urllib.parse import urlparse
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.fernet import Fernet

# from dotenv import load_dotenv
# load_dotenv()

import re
from twilio.jwt.access_token.grants import ChatGrant
from twilio.jwt.access_token import AccessToken
from twilio.rest import Client

import logging as log

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

def get_secrets(secret_name):
    """Load sensitive secrets from AWS Secrets Manager"""
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
secrets = get_secrets(config.aws_secrets_group)
encryption_and_twilio_secrets = get_secrets(config.encryption_and_twilio_group)

# Configure AWS s3
s3 = boto3.client(
    's3',
    aws_access_key_id=secrets["S3_ACCESS_ID"],
    aws_secret_access_key=secrets['S3_ACCESS_KEY']
)


# Initialize encryption key
def get_encryption_key():
    """Get or create encryption key"""
    key = encryption_and_twilio_secrets['ENCRYPTION_KEY']
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

# Setup your LLM (choose gpt-4o / gpt-3.5-turbo etc.)
llm = ChatOpenAI(
    model=config.OPENAI_MODEL_NAME, 
    temperature=0.7,
    openai_api_key=secrets['OPENAI_API_KEY']
)

def run_async_task(coro):
    asyncio.run(coro)

def upload_file_to_s3(file_path, filename):
    try:
        # TODO replace with snowflake {unique key}-image1

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
            'DOB1' : user_1[1],
            'DOB2' : user_2[1],
            'TOB1' : user_1[2].strftime("%H:%M"), 
            'TOB2' : user_2[2].strftime("%H:%M"),
            'LAT1' : user_1[3],
            'LAT2' : user_2[3],
            'LONG1' : user_1[4],
            'LONG2' : user_2[4]
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
    personal_score = get_personal_score(user_1[5], user_2[5])

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
    # Setup snowflake
    profile_connect = SnowConnect(config.PROFILE_TABLE_WAREHOUSE, config.PROFILE_TABLE_DATABASE, config.PROFILE_TABLE_SCHEMA)
    
    insert_sql = f"INSERT INTO {config.PROFILE_TABLE} (UID, PASSWORD, NAME, PHONE, EMAIL, EMAIL_HASH, CITY, COUNTRY, PROFESSION, BIRTH_CITY, BIRTH_COUNTRY, DOB, TOB, GENDER, HOBBIES, LAT, LONG, IMAGES, CREATED, LOGIN) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    uid = str(uuid4())
    
    # Encrypt sensitive data
    password = encrypt_password(json_data['password'])
    encrypted_email = encrypt_sensitive_data(email)
    hashed_email = hash_email_sha256(email) # Need hashed email to search on email in snowflake
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

    profile_connect.cursor.execute(insert_sql, (uid, password, name, encrypted_phone, encrypted_email, hashed_email, city, country, profession, birth_city, birth_country, dob, tob, gender, hobbies, lat, long, images, timestamp, timestamp))
    profile_connect.conn.commit()
    
    if gender == 'male':
        fetch = 'female'
    else:
        fetch = 'male'

    select_self = F"SELECT UID, DOB, TOB, LAT, LONG, HOBBIES FROM {config.PROFILE_TABLE} WHERE UID = '{uid}'"
    profile_connect.cursor.execute(select_self)

    # Fetch all results
    results = profile_connect.cursor.fetchall()
    self_result = results[-1]
    
    select_sql = f"SELECT UID, DOB, TOB, LAT, LONG, HOBBIES, NAME FROM {config.PROFILE_TABLE} WHERE GENDER = '{fetch}'"
    profile_connect.cursor.execute(select_sql)

    # Fetch all results
    results = profile_connect.cursor.fetchall()
    profile_connect.close()

    matched_uids, matched_names = [], []
    scores = []

    for row in results:
        #kundali_obj = Kundali(dob, row['DOB'], tob, row["TOB"], lat, row["LAT"], long, row["LONG"])
        #kundali_score = kundali_obj.get_guna_score()/config.TOTAL_GUN

        matched_uids.append(row[0])
        matched_names.append(row[-1])
        score = compute_score(self_result, row)
        scores.append(score)


    # SORT LIST AND GET TOP TEN MATCHES
    sorted_pairs = sorted(zip(matched_uids, scores, matched_names), key=lambda x: x[1], reverse=True)
    recommendations = sorted_pairs[:config.MAX_MATCHES]

    log.info(f'Recommendations: {recommendations}')

    matching_connect  = SnowConnect(config.MATCHING_TABLE_WAREHOUSE, config.MATCHING_TABLE_DATABASE, config.MATCHING_TABLE_SCHEMA)
    # Post recommendations to matching table

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    insert_sql_matching = f"INSERT INTO {config.MATCHING_TABLE} (UID1, NAME1, UID2, NAME2, SCORE, CREATED, UPDATED, ALIGN1, ALIGN2, SKIP1, SKIP2, BLOCK1, BLOCK2) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    for item in recommendations:
        matching_connect.cursor.execute(insert_sql_matching, (uid, name, item[0], str(item[2]), str(item[1]), timestamp, timestamp, False, False, False, False, False, False ) )

    matching_connect.conn.commit()
    matching_connect.close()

    return {'UID' : uid}, None

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
                updated_time.append(datetime.strptime(item["updated"]))
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

    profile_connect = SnowConnect(config.PROFILE_TABLE_WAREHOUSE, config.PROFILE_TABLE_DATABASE, config.PROFILE_TABLE_SCHEMA)
    select_sql = f"SELECT UID, PASSWORD, NOTIFICATIONS, EMAIL, PHONE FROM {config.PROFILE_TABLE} WHERE EMAIL_HASH = SHA2(%s, 256)"

    #log.info(f'Encrypted email: {type(encrypted_email)}, Value: {encrypted_email}')
    profile_connect.cursor.execute(select_sql, (email,))
    result = profile_connect.cursor.fetchone()

    if not result:
        return jsonify({'LOGIN': 'UNSUCCESSFUL', 'ERROR': 'Email not found.'})
    
    if not verify_password(result[1], password):
        return jsonify({'LOGIN': 'UNSUCCESSFUL', 'ERROR': 'Password is Incorrect.'})

    uid = result[0]
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    update_sql = f"UPDATE {config.PROFILE_TABLE} SET LOGIN = '{current_time}' WHERE UID = '{uid}'"
    profile_connect.cursor.execute(update_sql)
    profile_connect.conn.commit()
    profile_connect.close()

    notifications_url = result[2]
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

    # Decrypt email and phone for response
    decrypted_email = decrypt_sensitive_data(result[3])
    decrypted_phone = decrypt_sensitive_data(result[4])

    return jsonify({
        'LOGIN': 'SUCCESSFUL', 
        'UID': uid, 
        'NOTIFICATIONS': notifications, 
        'EMAIL': decrypted_email,
        'PHONE': decrypted_phone,
        'ERROR': 'OK'
    })

@app.route('/get:user/<uid>', methods=['GET'])
def get_user(uid):
    profile_connect = SnowConnect(config.PROFILE_TABLE_WAREHOUSE, config.PROFILE_TABLE_DATABASE, config.PROFILE_TABLE_SCHEMA)
    select_sql = f"SELECT NAME, DOB, CITY, COUNTRY, IMAGES, HOBBIES, PROFESSION, GENDER, NOTIFICATIONS, EMAIL, PHONE FROM {config.PROFILE_TABLE} WHERE UID = '{uid}'"
    profile_connect.cursor.execute(select_sql)
    result = profile_connect.cursor.fetchone()

    if not result:
        return jsonify({'error': 'User not found'}), 404

    image_path_list = [i.strip() for i in str(result[4]).split(',')]
    user_data = {
        'UID': uid,
        'NAME': result[0],
        'DOB': result[1],
        'CITY': result[2],
        'COUNTRY': result[3],
        'IMAGES': image_path_list,
        'HOBBIES': result[5],
        'PROFESSION': result[6],
        'GENDER': result[7],
        'EMAIL': decrypt_sensitive_data( result[9] ),
        'PHONE' : decrypt_sensitive_data( result[10] ),
        'ERROR': 'OK'
    }

    profile_connect.conn.commit()
    profile_connect.close()

    return jsonify(user_data)

def fetch_queue(uid, queue_requested):
    matching_connect = SnowConnect(config.MATCHING_TABLE_WAREHOUSE, config.MATCHING_TABLE_DATABASE, config.MATCHING_TABLE_SCHEMA)
    sql = f"SELECT UID1, UID2, SCORE, UPDATED, ALIGN1, ALIGN2, SKIP1, SKIP2, BLOCK1, BLOCK2, NAME1, NAME2 FROM {config.MATCHING_TABLE} WHERE UID1 = '{uid}' OR UID2 = '{uid}'"
    cursor = matching_connect.conn.cursor()
    cursor.execute(sql)
    results = cursor.fetchall()
    cursor.close()

    cards = []
    for row in results:
        uid1, uid2, score, updated, a1, a2, s1, s2, b1, b2, n1, n2 = row
        usr_idx = 0 if uid == uid1 else 1
        rec_idx = 1 - usr_idx
        usr_align, rec_align = (a1, a2) if usr_idx == 0 else (a2, a1)
        usr_skip, rec_skip = (s1, s2) if usr_idx == 0 else (s2, s1)

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
        name = n2 if uid1 == uid else n1

        cards.append({
            'recommendation_uid': recommendation_uid,
            'name': name,
            'score': score,
            'chat_enabled': usr_align and rec_align,
            'user_align': usr_align
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

# TODO This generates a summary of all users in the user queues, their names, hobbies, profession, age and score
# This will be provided to chat:initiate and chat:preference
def summarize_queues(uid):
    recommendations = get_recommendations(uid)
    awaiting = get_awaiting(uid)
    matches = get_matches(uid)
    summary = f'User has following recommendations for potential matches'

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

    profile_connect = SnowConnect(config.PROFILE_TABLE_WAREHOUSE, config.PROFILE_TABLE_DATABASE, config.PROFILE_TABLE_SCHEMA)

    columns = ['UID', 'NAME', 'DOB', 'CITY', 'COUNTRY', 'IMAGES', 'HOBBIES', 'PROFESSION', 'GENDER']
    columns_string = ', '.join(columns)
    select_sql = f"SELECT {columns_string} FROM {config.PROFILE_TABLE} WHERE UID= '{uid}'"
    profile_connect.cursor.execute(select_sql)

    results = profile_connect.cursor.fetchall()

    if len(results) > 1:
        log.info(f'Result is not unique')
        result = results[-1]
    elif len(results) == 1:
        result = results[0]
    else:
        log.info(f'No result for uid: {uid}')
        return jsonify({'error': f'no results found for uid: {uid}'}), 400

    profile_connect.close()

    output = {}
    for idx, name in enumerate(columns):
        if name == 'IMAGES':
            continue
        output[name] = result[idx]

    # Convert image S3 paths to base64-encoded image data
    image_paths = result[columns.index('IMAGES')]
    image_path_list = [i.strip() for i in image_paths.split(',')]

    output['IMAGES'] = image_path_list
    output['error'] = 'OK'

    return jsonify(output)

async def update_notifications_or_chats(uid, new_notifications_or_chats, column):

    column = column.lower()

    if column == 'notifications':
        col = 'NOTIFICATIONS'
    elif column == 'initiate_chats':
        col = 'INITIATE_CHATS'
    elif column == 'preference_chats':
        col = 'PREFERENCE_CHATS'
    else:
        log.warning(f"Unsupported datatype/snowflake column: {column}. Supported datatypes are ['notifications', 'initiate_chats', 'preference_chats']")
        return None
    
    profile_connect = SnowConnect(config.PROFILE_TABLE_WAREHOUSE, config.PROFILE_TABLE_DATABASE, config.PROFILE_TABLE_SCHEMA)
    select_sql = f"SELECT UID, CREATED, PASSWORD, LOGIN, {col} FROM {config.PROFILE_TABLE} WHERE UID = '{uid}'"
    profile_connect.cursor.execute(select_sql)

    results = profile_connect.cursor.fetchall()
    
    process = True
    if len(results)>1:
        log.warning(f'uid {uid} is not unique')
        result = results[-1]
    elif len(results)==1:
        result = results[0]
    else:
        process = False
        log.warning(f'uid {uid} not found')

    if process:
        notifications_or_chats_url = result[-1]

        if notifications_or_chats_url is None or notifications_or_chats_url in ['', 'None']:

            notifications_or_chats = []
            new_s3_obj = True

        else:
            
            notifications_or_chats_url_parsed = urlparse(notifications_or_chats_url)
            notifications_or_chats_url = notifications_or_chats_url_parsed.path.lstrip('/')

            # Download image from S3 as bytes
            s3_object = s3.get_object(Bucket=BUCKET_NAME, Key=notifications_or_chats_url)
            yaml_content = s3_object['Body'].read()

            # Parse YAML
            notifications_or_chats = yaml.safe_load(yaml_content)
            new_s3_obj = False

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
        assert action in ['align', 'skip']
    except:
        return jsonify({'error': 'Invalid JSON or missing uid/recommendation_uid/action'}), 400
    
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    valid_cols = ['UID1', 'UID2', 'SCORE', 'UPDATED', 'ALIGN1', 'ALIGN2', 'SKIP1', 'SKIP2', 'BLOCK1', 'BLOCK2', 'NAME1', 'NAME2']
    matching_connect = SnowConnect(config.MATCHING_TABLE_WAREHOUSE, config.MATCHING_TABLE_DATABASE, config.MATCHING_TABLE_SCHEMA)
    
    sql_fetch = f"SELECT UID1, UID2, SCORE, UPDATED, ALIGN1, ALIGN2, SKIP1, SKIP2, BLOCK1, BLOCK2, NAME1, NAME2 FROM {config.MATCHING_TABLE} WHERE (UID1 = '{uid}' AND UID2 = '{rec_uid}') OR (UID1 = '{rec_uid}' AND UID2= '{uid}')"
    matching_connect.cursor.execute(sql_fetch)
    results = matching_connect.cursor.fetchall()
    
    if len(results)>1:
        log.warning(f'Mathing table row is not unique {uid}, {rec_uid}')
        result = results[-1]
    elif len(results)==1:
        result = results[0]
    else:
        return jsonify({"error": f"No row in matching table {uid}, {rec_uid}"}), 400
    
    if str(result[0]) == str(uid):
        log.info(f'First uid is user: {result[0]}')
        primary = 0
        rec_idx = 1

    elif str(result[1]) == str(uid):

        log.info(f'Second uid is user: {result[1]}')
        primary = 1
        rec_idx = 0
    else:
        log.info(f'No match for usr uid {uid}, {result[0]}, {result[1]}\n{result}')

    recommended_user_name = result[10+rec_idx]

    if action == 'skip':

        delete_sql = f"DELETE FROM {config.MATCHING_TABLE} WHERE UID1 = '{result[0]}' AND UID2 ='{result[1]}'"
        matching_connect.cursor.execute(delete_sql)
        queue = 'None'
        message = f'{recommended_user_name} will not be recommended to you.'

        user_align = False

    # Right now we do not provide option to retract your response
    elif action == 'align':
        align_col = f'ALIGN{primary+1}'

        if align_col not in valid_cols:
            log.warning(f'{align_col} not a valid column')

        update_sql = f"UPDATE {config.MATCHING_TABLE} SET {align_col} = {True}, UPDATED = '{current_time}' WHERE UID1 = '{result[0]}' AND UID2 = '{result[1]}'"
        matching_connect.cursor.execute(update_sql)

        if result[4+rec_idx] == True:
            queue = 'MATCHED'
            message = f'You have been matched with the {recommended_user_name}.'

        else:
            queue = 'AWAITING'
            message = f'Align request has been sent to {recommended_user_name}'

        user_align = True

    matching_connect.conn.commit()
    matching_connect.close()

    # Creates and destroys event loop
    #asyncio.run(put_yaml_to_s3(uid, [{'message' : message, 'updated' : current_time}]))

    threading.Thread(target=run_async_task, args=(update_notifications_or_chats(uid, [{'message' : message, 'updated' : current_time}], 'notifications'),)).start()

    return jsonify({'error' : 'OK', 'queue' : queue, 'user_align' : user_align, 'message' : message, "updated" : current_time})

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
    
    #log.info(f"Username: {os.getenv('SNOWFLAKE_USERNAME')}, Account_id: {os.getenv('SNOWFLAKE_ACCOUNT_ID')}")

    # Decrypt email using the encryption key
    decrypted_email = decrypt_sensitive_data(email)

    profile_connect = SnowConnect(config.PROFILE_TABLE_WAREHOUSE, config.PROFILE_TABLE_DATABASE, config.PROFILE_TABLE_SCHEMA)

    # Compare with encrypted email in database
    sql_fetch = f"SELECT UID FROM {config.PROFILE_TABLE} WHERE EMAIL=%s"
    profile_connect.cursor.execute(sql_fetch, (decrypted_email,))
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
    set_clause = ', '.join([f"{key} = %s" for key in fields.keys()])
    values = list(fields.values())
    values.append(uid)  # for WHERE clause

    update_sql = f"UPDATE {config.PROFILE_TABLE} SET {set_clause} WHERE UID = %s"

    try:
        profile_connect = SnowConnect(config.PROFILE_TABLE_WAREHOUSE, config.PROFILE_TABLE_DATABASE, config.PROFILE_TABLE_SCHEMA)
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
        profile_connect = SnowConnect(config.PROFILE_TABLE_WAREHOUSE, config.PROFILE_TABLE_DATABASE, config.PROFILE_TABLE_SCHEMA)
        profile_connect.cursor.execute(f"SELECT UID, DOB, TOB, LAT, LONG, HOBBIES, GENDER, NAME FROM {config.PROFILE_TABLE} WHERE UID = %s", (uid,))
        current_user = profile_connect.cursor.fetchone()
        
        if current_user:
            uid, dob, tob, lat, long, hobbies, gender, user_name = current_user

            # Fetch all matches where this user is involved
            matching_connect = SnowConnect(config.MATCHING_TABLE_WAREHOUSE, config.MATCHING_TABLE_DATABASE, config.MATCHING_TABLE_SCHEMA)
            match_query = f"SELECT UID1, UID2 FROM {config.MATCHING_TABLE} WHERE UID1 = %s OR UID2 = %s"
            matching_connect.cursor.execute(match_query, (uid, uid))
            match_rows = matching_connect.cursor.fetchall()

            recommended_uids, recommended_names, new_scores = [], [], []
            for uid1, uid2 in match_rows:
                # Determine the other user
                other_uid = uid2 if uid1 == uid else uid1
                

                # Fetch other user's data
                profile_connect.cursor.execute(f"SELECT UID, DOB, TOB, LAT, LONG, HOBBIES, GENDER, NAME FROM {config.PROFILE_TABLE} WHERE UID = %s", (other_uid,))
                other_user = profile_connect.cursor.fetchone()

                if other_user:
                    # Compute new score (you should have this logic in place)
                    new_score = compute_score(current_user, other_user)

                    recommended_uids.append(other_uid)
                    new_scores.append(new_score)
                    recommended_names.append(other_user[-1])

                    # Update score in matching table
                    update_match_sql = f"UPDATE {config.MATCHING_TABLE} SET SCORE = %s WHERE (UID1 = %s AND UID2 = %s) OR (UID1 = %s AND UID2 = %s)"
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
    
                recommended_uids.append(row[0])
                score = compute_score(current_user, row)
                new_scores.append(score)
                recommended_names.append(-1)

            # SORT LIST AND GET TOP TEN MATCHES
            sorted_pairs = sorted(zip(recommended_uids, new_scores, recommended_names), key=lambda x: x[1], reverse=True)
            recommendations = sorted_pairs[:config.MAX_MATCHES]
            insert_sql_matching = f"INSERT INTO {config.MATCHING_TABLE} (UID1, UID2, SCORE, CREATED, UPDATED, ALIGN1, ALIGN2, SKIP1, SKIP2, BLOCK1, BLOCK2, NAME1, NAME2) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"

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
    

@app.route("/chat:initiate/<string:uid>", methods = ["GET"])
def chat_initiate(uid):

    if uid is None:
        return jsonify({"error": "Missing 'uid' in url"}), 400

    profile_connect = SnowConnect(config.PROFILE_TABLE_WAREHOUSE, config.PROFILE_TABLE_DATABASE, config.PROFILE_TABLE_SCHEMA)

    columns = ['UID', 'NAME', 'DOB', 'CITY', 'COUNTRY', 'HOBBIES', 'PROFESSION', 'GENDER', 'INITIATE_CHATS']
    columns_string = ', '.join(columns)
    select_sql = f"SELECT {columns_string} FROM {config.PROFILE_TABLE} WHERE UID = '{uid}'"
    profile_connect.cursor.execute(select_sql)

    results = profile_connect.cursor.fetchall()

    if len(results) > 1:
        log.info(f'Result is not unique')
        result = results[-1]
    elif len(results) == 1:
        result = results[0]
    else:
        log.info(f'No result for uid: {uid}')
        return jsonify({'error': f'no results found for uid: {uid}'}), 400
    
    name = result[1]
    hobbies = result[5]

    profile_connect.close()

    chats_url = result[-1]

    previous_chats = load_previous_chats(chats_url)
    prompts = load_prompts(config.PROMPTS_YAML)

    system_prompt = prompts['initiate_system_prompt'].format(name = name, hobbies = hobbies, previous_chats = previous_chats)

    # Start with system message if no history
    messages = []
    messages.append(SystemMessage(content=system_prompt))
    # Get response from LLM
    try:
        response = llm(messages)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    assistant_msg = response.content

    history = [{"role": "system", "content" : system_prompt}, {"role" : "assistant", "content" : assistant_msg}]

    return jsonify({"role": "assistant", "message": assistant_msg, "history": history, "continue" : True })


def continue_chat(user_input, history):
    
    messages = []
    # Add chat history (reconstruct LangChain message objects)
    count = 0
    for msg in history:
        if 'role' not in msg:
            log.warning(f'No role found: {msg}')
            continue
        if msg['role'] == 'user':
            if 'content' in msg:
                messages.append(HumanMessage(content=msg['content']))
            elif 'message' in msg:
                messages.append(HumanMessage(content=msg['message']))
            else:
                log.warning(f'Niether content nor message in message, {msg}')

        elif msg['role'] == 'assistant':
            if 'content' in msg:
                messages.append(AIMessage(content=msg['content']))
            elif 'message' in msg:
                messages.append(AIMessage(content=msg['message']))
            else:
                log.warning(f'Niether content nor message in message, {msg}')

        elif msg['role'] == 'system':
            if 'content' in msg:
                messages.append(SystemMessage(content=msg['content']))
            elif 'message' in msg:
                messages.append(SystemMessage(content=msg['message']))
            else:
                log.warning(f'Niether content nor message in message, {msg}')
        else:
            log.warning(f'invalid role found: {msg}')

        count += 1

    # Add the latest user input
    messages.append(HumanMessage(content=user_input))

    if count <= config.MAX_DESTINY_CHAT:

        # Get response from LLM
        try:
            response = llm(messages)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

        assistant_msg = response.content
        cont = True

    else:
        assistant_msg = 'I have been instructed to keep the conversations short. Thank you for chatting with me! This information helps us find better matches for you.'
        cont = False

    # Update history
    updated_history = history + [
        {"role": "user", "message": user_input},
        {"role": "assistant", "message": assistant_msg}
    ]
    return assistant_msg, updated_history, cont

@app.route("/chat/initiate:continue", methods=["POST"])
def continue_initiate():

    try:
        json_data = request.get_json()
        uid = json_data.get('uid')
        user_input = json_data.get('user_input')
        history = json_data.get('history')
    except:
        return jsonify({'error': 'Invalid JSON or missing uid/user_input/history'}), 400
    
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    if user_input.lower() in ['bye', 'exit', 'quit', 'goodbye', 'end']:
        endphrase_list = ['Thank you for chatting with me! This information helps us find better matches for you.', 'See you later! we will further discuss your hoobie some other time.']
        goodbye = random.choice(endphrase_list)

        threading.Thread(target=run_async_task, args=(update_notifications_or_chats(uid, [{'history' : history, 'updated' : current_time}], 'INITIATE_CHATS'),)).start()
        history.extend([{"role" : "user", "content": f"{user_input}"}, {"role" : "Code", "goodbye": f"{goodbye}"}])
        # TODO Call upload to s3 function
        return jsonify({
            "message": goodbye,
            "history": history,
            "continue": False
        })
    
    assistant_msg, updated_history, cont = continue_chat(user_input, history)

    
    if 'thank you for chatting with me' in assistant_msg.lower() or cont == False:
        threading.Thread(target=run_async_task, args=(update_notifications_or_chats(uid, [{'history' : updated_history, 'updated' : current_time}], 'INITIATE_CHATS'),)).start()
        cont = False

    return jsonify({
        "message": assistant_msg,
        "history": updated_history,
        "continue": cont
    })

@app.route("/chat/preference:continue", methods=["POST"])
def continue_preference():

    try:
        json_data = request.get_json()
        uid = json_data.get('uid')
        user_input = json_data.get('user_input')
        history = json_data.get('history', [])
    except:
        return jsonify({'error': 'Invalid JSON or missing uid/user_input/history'}), 400
    
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    system = False
    if len(history)>0:
        for item in history:
            if "role" in item and item["role"] == "system":
                system = True
                break

    if system == True:

        if user_input.lower() in ['bye', 'exit', 'quit', 'goodbye', 'end']:

            endphrase_list = ['Thank you for chatting with me! This information helps us find better matches for you.', 'See you later! we will further discuss your hoobie some other time.']
            goodbye = random.choice(endphrase_list)

            threading.Thread(target=run_async_task, args=(update_notifications_or_chats(uid, [{'history' : history, 'updated' : current_time}], 'PREFERENCE_CHATS'),)).start()
            history.extend([{"role" : "user", "content": f"{user_input}"}, {"role" : "Code", "goodbye": f"{goodbye}"}])
            # TODO Call upload to s3 function
            return jsonify({
                "message": goodbye,
                "history": history,
                "continue": False
            })
            
        assistant_msg, updated_history, cont = continue_chat(user_input, history)

        if 'thank you for chatting with me' in assistant_msg.lower() or cont == False:
            threading.Thread(target=run_async_task, args=(update_notifications_or_chats(uid, [{'history' : updated_history, 'updated' : current_time}], 'PREFERENCE_CHATS'),)).start()
            cont = False

        return jsonify({
            "message": assistant_msg,
            "history": updated_history,
            "continue": cont
        })

    else:

        profile_connect = SnowConnect(config.PROFILE_TABLE_WAREHOUSE, config.PROFILE_TABLE_DATABASE, config.PROFILE_TABLE_SCHEMA)

        columns = ['UID', 'NAME', 'DOB', 'CITY', 'COUNTRY', 'HOBBIES', 'PROFESSION', 'GENDER', 'PREFERENCE_CHATS']
        columns_string = ', '.join(columns)
        select_sql = f"SELECT {columns_string} FROM {config.PROFILE_TABLE} WHERE UID = '{uid}'"
        profile_connect.cursor.execute(select_sql)

        results = profile_connect.cursor.fetchall()

        if len(results) > 1:
            log.info(f'Result is not unique')
            result = results[-1]
        elif len(results) == 1:
            result = results[0]
        else:
            log.info(f'No result for uid: {uid}')
            return jsonify({'error': f'no results found for uid: {uid}'}), 400
        
        name = result[1]
        profile_connect.close()

        chats_url = result[-1]

        previous_chats = load_previous_chats(chats_url)
        prompts = load_prompts(config.PROMPTS_YAML)

        system_prompt = prompts['preference_system_prompt'].format(name = name, previous_chats = previous_chats)

        # Start with system message if no history
        messages = []
        messages.append(SystemMessage(content=system_prompt))

        messages.append(HumanMessage(content=user_input))

        # Get response from LLM
        try:
            response = llm(messages)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        
        assistant_msg = response.content

        history = [{"role": "system", "content" : system_prompt}, {"role" : "user", "content" : user_input}, {"role" : "assistant", "content" : assistant_msg}]

        return jsonify({"role": "assistant", "message": assistant_msg, "history": history, "continue" : True })

@app.route('/e2echat:token/<string:uid>', methods=['GET'])
def generate_chat_token(uid):
    """Generate a Twilio Conversations access token"""
    try:
        if not uid:
            return jsonify({"error": "Missing 'uid' in url"}), 400

        token = AccessToken(
            encryption_and_twilio_secrets['TWILIO_ACCOUNT_SID'],
            encryption_and_twilio_secrets['TWILIO_API_KEY'],
            encryption_and_twilio_secrets['TWILIO_API_SECRET'],
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
            encryption_and_twilio_secrets['TWILIO_API_KEY'],
            encryption_and_twilio_secrets['TWILIO_API_SECRET'],
            encryption_and_twilio_secrets['TWILIO_ACCOUNT_SID']
        )

        # Connect to Snowflake
        matching_connect = SnowConnect(
            config.MATCHING_TABLE_WAREHOUSE,
            config.MATCHING_TABLE_DATABASE,
            config.MATCHING_TABLE_SCHEMA
        )

        # Check if conversation already exists
        select_sql = f"""
            SELECT CONVERSATION_SID 
            FROM {config.MATCHING_TABLE} 
            WHERE (UID1 = %s AND UID2 = %s) OR (UID1 = %s AND UID2 = %s)
        """
        matching_connect.cursor.execute(select_sql, (uid1, uid2, uid2, uid1))
        result = matching_connect.cursor.fetchone()

        if result and result[0]:
            conversation_sid = result[0]
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
                SET CONVERSATION_SID = %s 
                WHERE (UID1 = %s AND UID2 = %s) OR (UID1 = %s AND UID2 = %s)
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
    
    app.run(host='0.0.0.0', port=8080)
