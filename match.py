import os
import json
import time
import random
from dotenv import load_dotenv

import boto3
from botocore.exceptions import NoCredentialsError
from uuid import uuid4
from PIL import Image
from geopy.geocoders import Nominatim
from absl import logging as log 
#from kundali_score import Kundali
from config import config
from flask import Flask, request, jsonify
from snowflake_utils import SnowConnect

load_dotenv()
log.set_verbosity(log.INFO)

# Configure AWS (automatically uses ~/.aws/credentials or env vars)
s3 = boto3.client('s3',
    aws_access_key_id=os.getenv('S3_ACCESS_ID'),
    aws_secret_access_key=os.getenv('S3_ACCESS_KEY'))

BUCKET_NAME = os.getenv('BUCKET')
REGION = os.getenv("REGION")  # e.g., 'us-east-1'

CURRENT_DIR = os.getcwd()

PROFILE_DB_COLUMNS= {'CITY': 0,
 'COUNTRY':1,
 'CREATED':2,
 'DOB':3,
 'EMAIL':4,
 'GENDER':5,
 'HOBBBIES':6,
 'IMAGES':7,
 'LAT':8,
 'LOGIN':9,
 'LONG':10,
 'NAME':11,
 'PHONE':12,
 'TOB':13,
 'UID':14}

MATCHING_TABLE_COLUMNS = {
    'UID1' : 0,
    'UID2' : 1,
    'SCORE' : 2,
    'CREATED' : 3,
    'UPDATED': 4,
    'WHATSAPP1': 5,
    'WHATSAPP2' :6,
    'INSTA1' : 7,
    'INSTA2' : 8,
    'SNAP1' : 9,
    'SNAP2' : 10
}

def upload_image_to_s3(file_path, filename, bucket_name=BUCKET_NAME):
    try:
        # TODO replace with snowflake {unique key}-image1

        # Upload file to S3
        s3.upload_file(file_path, bucket_name, filename)

        # Construct public URL
        url = f"https://{bucket_name}.s3.{REGION}.amazonaws.com/{filename}"
        return url
    
    except NoCredentialsError:
        log.info("AWS credentials not found.")
        return None
    except Exception as e:
        log.info(f"Upload failed: {e}")
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
    

    insert_sql = f"INSERT INTO {config.PROFILE_TABLE} (UID, NAME, PHONE, EMAIL, CITY, COUNTRY, DOB, TOB, GENDER, HOBBIES, LAT, LONG, IMAGES, CREATED, LOGIN) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    uid= str(uuid4())
    name =json_data['name'].lower() 
    phone = str(json_data['phone'])
    email = json_data['email'].lower()
    city = json_data['city'].lower() 
    country = json_data['country'].lower() 
    dob = str(json_data['dob'])
    tob = str(json_data['tob']) # Time of birth
    gender = json_data['gender'].lower()
    hobbies = json_data.get('hobbies', [])
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    #logintime = ''
    lat, long = get_lat_long(f'{city}, {country}')
    lat, long = str(lat), str(long)

    # Get S3 url for image files
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

    else:
        log.info('No images found')
        images = []

    # Convert list to string to be parsed as json
    if len(images)> 0:
        images = ','.join(images)
    else:
        images = ''
    if len(hobbies) > 0:
        hobbies = str(','.join(hobbies))
    else:
        hobbies = ''

    # for idx, i in enumerate([uid, name, phone, email, city, country, dob, tob, gender, hobbies, lat, long, images, timestamp, timestamp]):
    #     log.info(f'{i}:{type(i)}')

    profile_connect.cursor.execute(insert_sql, (uid, name, phone, email, city, country, dob, tob, gender, hobbies, lat, long, images, timestamp, timestamp))
    profile_connect.conn.commit()
    

    # RECOMMENDATION LOGIC
    # Fetch all rows of opposite gender:
    if gender == 'male':
        fetch = 'female'
    else:
        fetch = 'male'
    
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
        kundali_score = get_kundali_score() # Placeholder
        personal_score = get_personal_score(hobbies, row)
        #uid_col = PROFILE_DB_COLUMNS['UID']
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
    insert_sql_matching = f"INSERT INTO {config.MATCHING_TABLE} (UID1, UID2, SCORE, CREATED, UPDATED, WHATSAPP1, WHATSAPP2, INSTA1, INSTA2, SNAP1, SNAP2) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    for item in recommendations:
        # for i in [uid, item[0], str(item[1]), timestamp, timestamp, 'False', 'False', 'False', 'False', 'False', 'False']:
        #     log.info(f'{i}:{type(i)}')
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

    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    profile_connect = SnowConnect(config.PROFILE_TABLE_WAREHOUSE, config.PROFILE_TABLE_DATABASE, config.PROFILE_TABLE_SCHEMA)
    
    select_sql = f"SELECT UID, CREATED, LOGIN FROM {config.PROFILE_TABLE} WHERE EMAIL = '{email}'"
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
        return {'Login': 'Unsuccessful'}

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

    sql_fetch = f"SELECT * FROM {config.MATCHING_TABLE} WHERE UID1 = '{uid}' OR UID2 = '{uid}'"
    cursor_matching = matching_connect.conn.cursor()

    cursor_matching.execute(sql_fetch)
    results = cursor_matching.fetchall()

    # We need 4 queues in UI - recommendations, notifications, awaiting responses, matched.
    # Segregate recommendations from notifications
    recommendations, notifications, matched, awaiting = [], [], [], []
    if len(results)>0:
        for result in results:
            if result[MATCHING_TABLE_COLUMNS['WHATSAPP1']] == False and result[MATCHING_TABLE_COLUMNS['WHATSAPP2']] == False and result[MATCHING_TABLE_COLUMNS['INSTA1']] == False and result[MATCHING_TABLE_COLUMNS['INSTA2']] == False and result[MATCHING_TABLE_COLUMNS['SNAP1']] == False and result[MATCHING_TABLE_COLUMNS['SNAP2']] == False:
                recommendations.append(result)
            elif (result[MATCHING_TABLE_COLUMNS['WHATSAPP1']] == True and result[MATCHING_TABLE_COLUMNS['WHATSAPP2']] == True) or (result[MATCHING_TABLE_COLUMNS['INSTA1']] == True and result[MATCHING_TABLE_COLUMNS['INSTA2']] == True) or (result[MATCHING_TABLE_COLUMNS['SNAP1']] == True and result[MATCHING_TABLE_COLUMNS['SNAP2']] == True):
                matched.append(result)
            elif result[MATCHING_TABLE_COLUMNS['UPDATED']] > current_time:
                notifications.append(result)
            else:
                awaiting.append(result)
    
    matching_connect.conn.commit()
    matching_connect.close()
    

    return {'LOGIN': 'SUCCESSFUL', 'UID' : uid, 'RECOMMENDATIONS' : recommendations, 'NOTIFICATIONS' : notifications, 'MATCHED' : matched, 'AWAITING' : awaiting}, None

@app.route('/get:profile', methods=['POST'])
def get_profile():
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
    
    profile_connect = SnowConnect(config.PROFILE_TABLE_WAREHOUSE, config.PROFILE_TABLE_DATABASE, config.PROFILE_TABLE_SCHEMA)
    
    select_sql = f"SELECT * FROM {config.PROFILE_TABLE} WHERE UID= '{uid}'"
    profile_connect.cursor.execute(select_sql)

    # GET LAST LOGIN AND UID OF USER
    results = profile_connect.cursor.fetchall()

    if len(results) > 1:
        log.info(f'Result is not unique')
        result = results[-1]
    elif len(results) == 1:
        result = results[0]
    else:
        log.info(f'No result for uid: {uid}')

    output = {}
    for key, value in PROFILE_DB_COLUMNS.items():
        output[key] = str(result[value])

    profile_connect.close()
    return jsonify(output)

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
    
    recommendation = json_data.get('recommendation')
    if recommendation is None:
        return jsonify({"error": "Missing 'uid' field"}), 400

    current_time = time.time()

    # Action can be whatsapp1, whatsapp2, insta1, insta2, snap1, snap2, or skip
    action = json_data.get('action', None)
    if action is None:
        return jsonify({"error": "Missing 'action' field"}), 400
    
    matching_connect = SnowConnect(config.MATCHING_TABLE_WAREHOUSE, config.MATCHING_TABLE_DATABASE, config.MATCHING_TABLE_SCHEMA)

    if action == 'SKIP':

        delete_sql = f"DELETE FROM {config.MATCHING_TABLE} WHERE UID1 = {recommendation['UID1']} AND UID2 = {recommendation['UID2']}"
        matching_connect.cursor.execute(delete_sql)
        #matching_connect.cursor.commit()

    # Right now we do not provide option to retract your response
    elif action in ['WHATSAPP1', 'WHATSAPP2', 'INSTA1', 'INSTA2', 'SNAP1', 'SNAP2']:
        update_sql = f"UPDATE {config.MATCHING_TABLE} SET {action} = {current_time} WHERE UID = {uid}"
        recommendation[action] = True
        matching_connect.cursor.execute(update_sql)
        #matching_connect.cursor.commit()

    else:
        log.error(f'Unrecognized action: {action}')
        return jsonify({"error": "Missing 'action' field"}), 400

    matching_connect.conn.commit()
    matching_connect.close()

    return None, None

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

    email = json_data.get('email', None)
    if email is None:
        return jsonify({"error": "Missing 'email' field"}), 400
    print(f"Username: {os.getenv('SNOWFLAKE_USERNAME')}, Account_id: {os.getenv('SNOWFLAKE_ACCOUNT_ID')}")
    log.info(f"Username: {os.getenv('SNOWFLAKE_USERNAME')}, Account_id: {os.getenv('SNOWFLAKE_ACCOUNT_ID')}")

    profile_connect = SnowConnect(config.PROFILE_TABLE_WAREHOUSE, config.PROFILE_TABLE_DATABASE, config.PROFILE_TABLE_SCHEMA)

    sql_fetch = f"SELECT * FROM {config.PROFILE_TABLE} WHERE EMAIL='{email}'"
    profile_connect.cursor.execute(sql_fetch)
    results = profile_connect.cursor.fetchall()

    profile_connect.conn.commit()
    profile_connect.close()

    if len(results) > 0:
        return {'verify' : False}
    else:
        return {'verify' : True}

if __name__ == '__main__':
    
    app.run(host='0.0.0.0', port=8080)
