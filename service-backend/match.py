import os
import json
import time
import random
import base64
import io
from flask import send_file

from dotenv import load_dotenv
import requests
import boto3
from botocore.exceptions import NoCredentialsError
from uuid import uuid4
from PIL import Image
from geopy.geocoders import Nominatim
#from absl import logging as log 
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

app = Flask(__name__)
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
    
    select_sql = f"SELECT UID, DOB, TOB, LAT, LONG, HOBBIES FROM {config.PROFILE_TABLE} WHERE GENDER = '{fetch}'"
    profile_connect.cursor.execute(select_sql)

    # Fetch all results
    results = profile_connect.cursor.fetchall()
    profile_connect.close()

    matched_uids = []
    scores = []

    for row in results:
        #kundali_obj = Kundali(dob, row['DOB'], tob, row["TOB"], lat, row["LAT"], long, row["LONG"])
        #kundali_score = kundali_obj.get_guna_score()/config.TOTAL_GUN

        input_kundali = {
            'DOB1' : self_result[1],
            'DOB2' : row[1],
            'TOB1' : self_result[2].strftime("%H:%M"), 
            'TOB2' : row[2].strftime("%H:%M"),
            'LAT1' : self_result[3],
            'LAT2' : row[3],
            'LONG1' : self_result[4],
            'LONG2' : row[4]
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
        personal_score = get_personal_score(hobbies, row)

        matched_uids.append(row[0])
        score = kundali_score*config.KUNDALI_WEIGHT + personal_score*config.PERSONAL_WEIGHT
        scores.append(score)

    # SORT LIST AND GET TOP TEN MATCHES
    sorted_pairs = sorted(zip(matched_uids, scores), key=lambda x: x[1], reverse=True)
    recommendations = sorted_pairs[:config.MAX_MATCHES]

    log.info(f'Recommendations: {recommendations}')

    matching_connect  = SnowConnect(config.MATCHING_TABLE_WAREHOUSE, config.MATCHING_TABLE_DATABASE, config.MATCHING_TABLE_SCHEMA)
    # Post recommendations to matching table

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    insert_sql_matching = f"INSERT INTO {config.MATCHING_TABLE} (UID1, UID2, SCORE, CREATED, UPDATED, ALIGN1, ALIGN2, SKIP1, SKIP2, BLOCK1, BLOCK2) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    for item in recommendations:
        matching_connect.cursor.execute(insert_sql_matching, (uid, item[0], str(item[1]), timestamp, timestamp, False, False, False, False, False, False ) )

    matching_connect.conn.commit()
    matching_connect.close()

    return {'UID' : uid}, None

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
    last_login = result[2]

    if last_login is None:
        last_login = created
    
    update_sql = f"UPDATE {config.PROFILE_TABLE} SET LOGIN = '{current_time}' WHERE UID = '{uid}'"
    profile_connect.cursor.execute(update_sql)

    profile_connect.conn.commit()
    profile_connect.close()

    matching_connect  = SnowConnect(config.MATCHING_TABLE_WAREHOUSE, config.MATCHING_TABLE_DATABASE, config.MATCHING_TABLE_SCHEMA)

    sql_fetch = f"SELECT UID1, UID2, SCORE, UPDATED, ALIGN1, ALIGN2, SKIP1, SKIP2, BLOCK1, BLOCK2 FROM {config.MATCHING_TABLE} WHERE UID1 = '{uid}' OR UID2 = '{uid}'"
    cursor_matching = matching_connect.conn.cursor()

    cursor_matching.execute(sql_fetch)
    results = cursor_matching.fetchall()

    # We need 4 queues in UI - recommendations, notifications, awaiting responses, matched.
    # Segregate recommendations from notifications
    recommendations, notifications, matched, awaiting = [], [], [], []
    if len(results)>0:
        for result in results:
            # Last element is True or False Letting UI know if threy need to allow chat feature

            recommended_id = result[0] if result[1] == uid else result[1]
            if result[6] == True or result[7] == True: # This is skip bitton
                continue

            if result[4] == False and result[5] == False: # This is align buttons of both users
                recommendations.append([recommended_id] + list(result[2:6]) + [False])
            
            elif result[4] == True and result[5] == True: # Checking if both align
                if result[3] > current_time:
                    notifications.append([recommended_id] + list(result[2:6]) + [True])
                else:
                    matched.append([recommended_id] + list(result[2:6]) + [True])

            else:
                if result[3] > current_time:
                    notifications.append([recommended_id] + list(result[2:6]) + [False])
                else:
                    awaiting.append([recommended_id] + list(result[2:6]) + [False])
    
    matching_connect.conn.commit()
    matching_connect.close()
    
    return {'LOGIN': 'SUCCESSFUL', 'UID' : uid, 'RECOMMENDATIONS' : recommendations, 'NOTIFICATIONS' : notifications, 'MATCHED' : matched, 'AWAITING' : awaiting, 'ERROR' : 'OK'}, None

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
    
    match = json_data.get('match')
    if match is None:
        return jsonify({"error": "Missing 'uid' field"}), 400

    current_time = time.time()

    # Action can be whatsapp1, whatsapp2, insta1, insta2, snap1, snap2, or skip
    action = json_data.get('action', None)
    if action is None:
        return jsonify({"error": "Missing 'action' field"}), 400
    
    matching_connect = SnowConnect(config.MATCHING_TABLE_WAREHOUSE, config.MATCHING_TABLE_DATABASE, config.MATCHING_TABLE_SCHEMA)

    if action == 'SKIP':

        delete_sql = f"DELETE FROM {config.MATCHING_TABLE} WHERE UID1 = {match['UID1']} AND UID2 = {match['UID2']}"
        matching_connect.cursor.execute(delete_sql)
        #matching_connect.cursor.commit()

    # Right now we do not provide option to retract your response
    elif action in ['WHATSAPP1', 'WHATSAPP2', 'INSTA1', 'INSTA2', 'SNAP1', 'SNAP2']:

        update_sql = f"UPDATE {config.MATCHING_TABLE} SET {action} = {current_time} WHERE UID1 = {match['UID1']}"
        match[action] = True
        matching_connect.cursor.execute(update_sql)
        #matching_connect.cursor.commit()

    else:
        log.error(f'Unrecognized action: {action}')
        return jsonify({"error": "Missing 'action' field"}), 400

    matching_connect.conn.commit()
    matching_connect.close()

    return jsonify({'error' : 'OK'})

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

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response

if __name__ == '__main__':
    
    app.run(host='0.0.0.0', port=8080)
