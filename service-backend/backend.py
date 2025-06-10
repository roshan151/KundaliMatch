import os
import json
import time
import yaml
import random
import base64
import io
from flask import send_file
from datetime import datetime
from dotenv import load_dotenv
import requests
import boto3
from botocore.exceptions import NoCredentialsError
from uuid import uuid4
from PIL import Image
from geopy.geocoders import Nominatim
#from absl import logging as log 

from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage

# from twilio.jwt.access_token import AccessToken
# from twilio.jwt.access_token.grants import ChatGrant

from config import config
from flask import Flask, request, jsonify, make_response
from snowflake_utils import SnowConnect

from urllib.parse import urlparse

load_dotenv()

import logging as log

log.basicConfig(
    format='%(levelname)s [%(filename)s:%(lineno)d] %(message)s',
    level=log.INFO
    )

#log.set_verbosity(log.INFO)
# Configure AWS s3
s3 = boto3.client(
        's3',
        aws_access_key_id=os.getenv('S3_ACCESS_ID'),
        aws_secret_access_key=os.getenv('S3_ACCESS_KEY')
    )

BUCKET_NAME = os.getenv('BUCKET')
REGION = os.getenv("REGION")
CURRENT_DIR = os.getcwd()

# Setup your LLM (choose gpt-4o / gpt-3.5-turbo etc.)
llm = ChatOpenAI(model=config.OPENAI_MODEL_NAME, temperature=0.7)

def upload_image_to_s3(file_path, filename):
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
    
def download_image_from_s3(filename, download_path):
    try:
        # Download file from S3
        s3.download_file(BUCKET_NAME, filename, download_path)
        log.info(f"Downloaded {filename} to {download_path}")
        return download_path

    except NoCredentialsError:
        log.info("AWS credentials not found.")
        return None
    except Exception as e:
        log.info(f"Download failed: {e}")
        return None
    
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
    # Recieve multipart request
    # Get JSON part from form data
    metadata = request.form.get('metadata')
    if not metadata:
        return jsonify({'error': 'Missing metadata'}), 400
    try:
        json_data = json.loads(metadata)
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON'}), 400

    # Recieve encoded images
    profile_images = request.files.getlist("images")

    log.info(f'Profile Images: {len(profile_images)}')
    # Setup snowflake
    profile_connect = SnowConnect(config.PROFILE_TABLE_WAREHOUSE, config.PROFILE_TABLE_DATABASE, config.PROFILE_TABLE_SCHEMA)
    
    insert_sql = f"INSERT INTO {config.PROFILE_TABLE} (UID, PASSWORD, NAME, PHONE, EMAIL, CITY, COUNTRY, PROFESSION, BIRTH_CITY, BIRTH_COUNTRY, DOB, TOB, GENDER, HOBBIES, LAT, LONG, IMAGES, CREATED, LOGIN) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    uid= str(uuid4())
    password = str(json_data['password'])
    name =json_data['name'].lower() 
    phone = str(json_data['phone'])
    email = json_data['email'].lower()
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
                url = upload_image_to_s3(path, f'profile_pictures/{uid}/image-{idx}.png')
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

    profile_connect.cursor.execute(insert_sql, (uid, password, name, phone, email, city, country, profession, birth_city, birth_country, dob, tob, gender, hobbies, lat, long, images, timestamp, timestamp))
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


@app.route('/account:login', methods=['POST'])
def login():
    # We will use user email to fetch all data
    metadata = request.form.get('metadata')
    if not metadata:
        return jsonify({'error': 'Missing metadata'}), 400
    try:
        json_data = json.loads(metadata)
    except Exception as e:
        raise Exception(e)

    email = json_data.get('email', None)
    if email is None:
        return jsonify({"error": "Missing 'email' field"}), 400
    
    password = json_data.get('password', None)
    if password is None:
        return jsonify({"error": "Missing 'password' field"}), 400

    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    profile_connect = SnowConnect(config.PROFILE_TABLE_WAREHOUSE, config.PROFILE_TABLE_DATABASE, config.PROFILE_TABLE_SCHEMA)
    
    select_sql = f"SELECT UID, CREATED, PASSWORD, LOGIN FROM {config.PROFILE_TABLE} WHERE EMAIL = '{email}'"
    profile_connect.cursor.execute(select_sql)

    # GET LAST LOGIN AND UID OF USER
    results = profile_connect.cursor.fetchall()
    if len(results)>1:
        log.warning(f'Email {email} is not unique')
        result = results[-1]
    elif len(results)==1:
        result = results[0]
    else:
        log.info(f'No user with email { email } found')
        return jsonify({'LOGIN': 'UNSUCCESSFUL', 'ERROR' : 'Email not found.'})
    
    if password != result[2]:
        return jsonify({'LOGIN': 'UNSUCCESSFUL', 'ERROR' : 'Password is Incorrect.'})

    uid = result[0]
    created = result[1]
    last_login = result[3]

    if last_login is None:
        last_login = created

    last_login = ensure_datetime(last_login)
    
    update_sql = f"UPDATE {config.PROFILE_TABLE} SET LOGIN = '{current_time}' WHERE UID = '{uid}'"
    profile_connect.cursor.execute(update_sql)
    profile_connect.conn.commit()
    profile_connect.close()

    matching_connect  = SnowConnect(config.MATCHING_TABLE_WAREHOUSE, config.MATCHING_TABLE_DATABASE, config.MATCHING_TABLE_SCHEMA)

    sql_fetch = f"SELECT UID1, UID2, SCORE, UPDATED, ALIGN1, ALIGN2, SKIP1, SKIP2, BLOCK1, BLOCK2, NAME1, NAME2 FROM {config.MATCHING_TABLE} WHERE UID1 = '{uid}' OR UID2 = '{uid}'"
    cursor_matching = matching_connect.conn.cursor()
    cursor_matching.execute(sql_fetch)
    results = cursor_matching.fetchall()

    # We need 4 queues in UI - recommendations, notifications, awaiting responses, matched.
    # Segregate recommendations from notifications
    recommendations, notifications, matched, awaiting = [], [], [], []
    if len(results)>0:
        for result in results:
            # Last element is True or False Letting UI know if threy need to allow chat feature

            rec_idx = 0 if result[1] == uid else 1
            usr_idx = 1 if rec_idx == 0 else 1
            recommended_id = result[rec_idx]
            rec_align = result[4+rec_idx] ## This is align bitton of recommended profile
            usr_align = result[4+usr_idx]   # This is align bitton of user
            rec_skip = result[6+rec_idx] ## This is skip bitton of recommended profile
            usr_skip = result[6+usr_idx] # This is skip bitton of user
            score = result[2]
            rec_name = result[10+rec_idx]

            updated_time = ensure_datetime(result[3])

            message = None

            if usr_skip == True or rec_skip == True: # This is skip bitton
                continue

            if usr_align == False and rec_align == False: # This is align buttons of both users
                recommendations.append([recommended_id, score, usr_align, rec_align, usr_skip, rec_skip, False])
            
            elif usr_align == True and rec_align == True: # Checking if both align
                if updated_time > last_login:
                    message = f'NOTIFICATION: You have aligned with {rec_name}'
                matched.append([recommended_id, score, usr_align, rec_align, usr_skip, rec_skip, True])

            else:
                if updated_time > last_login:
                    if rec_align == True:
                        message = f'NOTIFICATION: {rec_name} requested to align with you'
                awaiting.append([recommended_id, score, usr_align, rec_align, usr_skip, rec_skip, True])
    
    matching_connect.conn.commit()
    matching_connect.close()
    
    return {'LOGIN': 'SUCCESSFUL', 'UID' : uid, 'RECOMMENDATIONS' : recommendations, 'MATCHED' : matched, 'AWAITING' : awaiting, 'MESSAGE' : message, 'ERROR' : 'OK'}

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
    image_data_list = []

    log.info(f'Len image paths: {len(image_paths)}, {image_paths}')
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

    output['IMAGES'] = image_data_list
    output['error'] = 'OK'

    return jsonify(output)

@app.route('/find:profiles', methods=['POST'])
def find_profiles():
    metadata = request.form.get('metadata')
    if not metadata:
        return jsonify({'error': 'Missing metadata'}), 400
    try:
        json_data = json.loads(metadata)
    except Exception as e:
        raise Exception(e)
    uids = json_data.get('uid', None)

    if uids is None:
        return jsonify({"error": "Missing 'uid' in url"}), 400
    
    if isinstance(uids, list):
    
        profile_connect = SnowConnect(config.PROFILE_TABLE_WAREHOUSE, config.PROFILE_TABLE_DATABASE, config.PROFILE_TABLE_SCHEMA)
        columns = ['UID', 'NAME', 'DOB', 'CITY', 'COUNTRY', 'IMAGES', 'HOBBIES', 'PROFESSION', 'GENDER']
        columns_string = ', '.join(columns)

        # GET LAST LOGIN AND UID OF USER
        
        outputs = []
        for uid in uids:
            select_sql = f"SELECT {columns_string} FROM {config.PROFILE_TABLE} WHERE UID= '{uid}'"
            profile_connect.cursor.execute(select_sql)
            results = profile_connect.cursor.fetchall()

            if len(results) > 1:
                log.info(f'Result is not unique for uid {uid}')
                result = results[-1]
            elif len(results) == 1:
                result = results[0]
            else:
                log.info(f'No result for uid: {uid}')
                result = None

            if result is None:
                output = {'error' : f'No result for uid: {uid}'}
            else:
                output = {}
                for idx, name in enumerate(columns):
                    output[name] = result[idx]
                output['error'] = 'OK'

            outputs.append(output)
        response_output = {'results' : outputs, 'error' : 'OK'}
        profile_connect.close()

    return jsonify(response_output)

@app.route('/account:action', methods=['POST'])
def action():
    metadata = request.form.get('metadata')
    if not metadata:
        return jsonify({'error': 'Missing metadata'}), 400
    try:
        json_data = json.loads(metadata)
    except Exception as e:
        raise Exception(e)

    uid = json_data.get('uid', None)
    if uid is None:
        return jsonify({"error": "Missing 'uid' field"}), 400
    
    rec_uid = json_data.get('recommendation_uid' , None)
    if rec_uid is None:
        return jsonify({"error": "Missing 'recommendation_uid' field"}), 400
    
    action = json_data.get('action' , None)
    if action is None:
        return jsonify({"error": "Missing action field"}), 400
    
    if isinstance(action, str):
        action = action.lower()
        if action not in ['skip', 'align']:
            return jsonify({"error": "action field invalid, expects skip or align"}), 400
    else:
        return jsonify({"error": "action is not string"}), 400
    
    # user_name = json_data.get('user_name' , None)
    # if user_name is None:
    #     return jsonify({"error": "Missing action field"}), 400
    
    # if isinstance(user_name, str) and len(user_name) > 0:
    #     user_name = user_name.lower()
        
    # else:
    #     return jsonify({"error": "user_name not provided"}), 400
    
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    # Action can be whatsapp1, whatsapp2, insta1, insta2, snap1, snap2, or skip
    action = json_data.get('action', None)
    if action is None:
        return jsonify({"error": "Missing 'action' field"}), 400
    
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
    
    primary = 0 if result[0] == uid else 1
    rec_idx = 1 if primary == 0 else 0
    recommended_user_name = result[10+rec_idx]
    if action == 'skip':

        delete_sql = f"DELETE FROM {config.MATCHING_TABLE} WHERE UID1 = '{result[0]}' AND UID2 ='{result[1]}'"
        matching_connect.cursor.execute(delete_sql)
        queue = 'None'
        message = f'{recommended_user_name} will not be recommended to you.'

    # Right now we do not provide option to retract your response
    elif action == 'align':
        align_col = f'ALIGN{primary+1}'
        update_sql = f"""
                        UPDATE {config.MATCHING_TABLE}
                        SET {align_col} = TRUE, UPDATED = '{current_time}'
                        WHERE UID1 = '{result[0]}' AND UID2 = '{result[1]}'
                        """
        matching_connect.cursor.execute(update_sql)

        if result[4] == True and result[5] == True:
            queue = 'MATCHED'
            message = f'You have been matched with the {recommended_user_name}.'
        else:
            queue = 'AWAITING'
            message = f'Align request has been sent to {recommended_user_name}'

    matching_connect.conn.commit()
    matching_connect.close()

    return jsonify({'error' : 'OK', 'queue' : queue, 'message' : message})


# Before making the create:account call, UI should make verify:email call to ensure emails are unique 
@app.route('/verify:email', methods=['POST'])
def verify_email():
    
    metadata = request.form.get('metadata')
    
    if not metadata:
        return jsonify({'error': 'Missing metadata'}), 400
    try:
        json_data = json.loads(metadata)
    except Exception as e:
        raise Exception(e)

    email = json_data.get( 'email', None )
    if email is None:
        return jsonify({"error": "Missing 'email' field"}), 400
    
    log.info(f"Username: {os.getenv('SNOWFLAKE_USERNAME')}, Account_id: {os.getenv('SNOWFLAKE_ACCOUNT_ID')}")

    profile_connect = SnowConnect(config.PROFILE_TABLE_WAREHOUSE, config.PROFILE_TABLE_DATABASE, config.PROFILE_TABLE_SCHEMA)

    sql_fetch = f"SELECT UID FROM {config.PROFILE_TABLE} WHERE EMAIL='{email}'"
    profile_connect.cursor.execute(sql_fetch)
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
    if 'email' in json_data and isinstance(json_data['email'], str) and json_data['email'] != '':
        return jsonify({'error' : 'You cannot modify email'})

    for field in allowed_fields:
        if field in json_data:
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
                url = upload_image_to_s3(path, f'profile_pictures/{uid}/image-{idx}.png')
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
    

@app.route("/chat:initiate/<string:uid>", methods = ["GET"])
def chat_initiate(uid):
    if uid is None:
        return jsonify({"error": "Missing 'uid' in url"}), 400

    profile_connect = SnowConnect(config.PROFILE_TABLE_WAREHOUSE, config.PROFILE_TABLE_DATABASE, config.PROFILE_TABLE_SCHEMA)

    columns = ['UID', 'NAME', 'DOB', 'CITY', 'COUNTRY', 'HOBBIES', 'PROFESSION', 'GENDER']
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
    
    name = result[1]
    hobbies = result[5]

    profile_connect.close()

    prompts = load_prompts(config.PROMPTS_YAML)
    system_prompt = prompts['system_prompt'].format(name = name, hobbies = hobbies)

    # Start with system message if no history
    messages = []
    messages.append(SystemMessage(content=system_prompt))
    # Get response from LLM
    try:
        response = llm(messages)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    assistant_msg = response.content

    return jsonify({"role": "assistant", "message": assistant_msg})

@app.route("/chat:continue", methods=["POST"])
def chat():
    data = request.get_json()

    user_input = data.get("user_input")
    history = data.get("history", [])

    if not user_input:
        return jsonify({"error": "Missing 'user_input'"}), 400
    
    if not history:
        return jsonify({"error": "Missing 'history'"}), 400

    messages = []
    # Add chat history (reconstruct LangChain message objects)
    for msg in history:
        if msg['role'] == 'user':
            messages.append(HumanMessage(content=msg['message']))
        elif msg['role'] == 'assistant':
            messages.append(AIMessage(content=msg['message']))

    # Add the latest user input
    messages.append(HumanMessage(content=user_input))

    # Get response from LLM
    try:
        response = llm(messages)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    assistant_msg = response.content

    # Update history
    updated_history = history + [
        {"role": "user", "message": user_input},
        {"role": "assistant", "message": assistant_msg}
    ]

    return jsonify({
        "reply": assistant_msg,
        "history": updated_history
    })


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response

if __name__ == '__main__':
    
    app.run(host='0.0.0.0', port=8080)
