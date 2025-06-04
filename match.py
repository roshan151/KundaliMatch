import os
import json
import time
import random
from dotenv import load_dotenv
import snowflake.connector
import boto3
from botocore.exceptions import NoCredentialsError
from uuid import uuid4
from PIL import Image
from geopy.geocoders import Nominatim
from absl import logging as log 
#from kundali_score import Kundali
from config import config
from flask import Flask, request, jsonify

load_dotenv()

# Configure AWS (automatically uses ~/.aws/credentials or env vars)
s3 = boto3.client('s3')

BUCKET_NAME = os.getenv('BUCKET')
REGION = os.getenv("REGION")  # e.g., 'us-east-1'

CURRENT_DIR = os.getcwd()

def upload_image_to_s3(file_path, bucket_name=BUCKET_NAME):
    try:
        # TODO replace with snowflake {unique key}-image1
        filename = f"{uuid4().hex}_{os.path.basename(file_path)}"

        # Upload file to S3
        s3.upload_file(file_path, bucket_name, filename, ExtraArgs={'ACL': 'public-read'})

        # Construct public URL
        url = f"https://{bucket_name}.s3.{REGION}.amazonaws.com/{filename}"
        return url
    
    except NoCredentialsError:
        log.info("AWS credentials not found.")
        return None
    except Exception as e:
        log.info(f"Upload failed: {e}")
        return None

def process_image(image_path):
    try:
        with Image.open(image_path) as img:
            img_format = img.format.lower()
            if img_format not in config.ALLOWED_FORMATS:
                log.info(f"Warning: Unsupported format '{img_format}' for file {image_path}")
                return None

            # Convert to PNG
            png_filename = f"{uuid4().hex}.png"
            png_path = os.path.join(CURRENT_DIR, png_filename)
            img.convert("RGBA").save(png_path, "PNG")
            return png_path

    except Exception as e:
        log.info(f"Error processing {image_path}: {e}")

def get_lat_long(address):
    geolocator = Nominatim(user_agent="geo_locator")
    location = geolocator.geocode(address)
    if location:
        return location.latitude, location.longitude
    else:
        return None, None

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

    # Get S3 url for image files
    if profile_images:
        png_paths = []
        for image in profile_images[:config.MAX_IMAGES]:
            path = process_image(image)

            if path is not None:
                url = upload_image_to_s3(path)
                images.append(url)
                png_paths.append(path)
        
        # Remove local images
        for path in png_paths:
            os.remove(path)

    else:
        images = []

    # Setup snowflake
    conn = snowflake.connector.connect(
        user=os.getenv('USERNAME'),
        password=os.getenv('PASSWORD'),
        account=os.getenv('ACCOUNT_ID'),
        warehouse=config.PROFILE_TABLE_WAREHOUSE,
        database=config.PROFILE_TABLE_DATABASE,
        schema=config.PROFILE_TABLE_SCHEMA
    )
    
    cursor = conn.cursor()

    insert_sql = f"INSERT INTO {config.PROFILE_TABLE} (UID, NAME, PHONE, EMAIL, CITY, COUNTRY, D0B, TOB, GENDER, HOBBIES, LAT, LONG, IMAGES, CREATED, LOGIN) VALUES (%s, %s, %s, %s, %s, %s, PARSE_JSON(%s), %s, %s, PARSE_JSON(%s), %s)"
    uid= uuid4()
    name =json_data['name'].lower() 
    phone = json_data['phone']
    email = json_data['email'].lower()
    city = json_data['city'].lower() 
    country = json_data['country'].lower() 
    dob = json_data['dob']
    tob = json_data['tob'] # Time of birth
    gender = json_data['gender'].lower()
    hobbies = json_data.get('hobbies', [])
    timestamp = time.time()
    lat, long = get_lat_long(f'{city}, {country}')
    cursor.execute(insert_sql, (uid, name, phone, email, city, country, dob, tob, gender, hobbies, lat, long, images, timestamp, None))

    conn.commit()
    cursor.close()
    conn.close()

    # RECOMMENDATION LOGIC
    # Fetch all rows of opposite gender:
    if gender == 'male':
        fetch = 'female'
    else:
        fetch = 'male'
    
    select_sql = f"SELECT dob, tob, lat, long, hobbies FROM {config.PROFILE_TABLE} WHERE GENDER = '{fetch}'"
    cursor.execute(select_sql)

    # Fetch all results
    results = cursor.fetchall()

    matched_uids = []
    scores = []

    for row in results:
        #kundali_obj = Kundali(dob, row['DOB'], tob, row["TOB"], lat, row["LAT"], long, row["LONG"])
        #kundali_score = kundali_obj.get_guna_score()/config.TOTAL_GUN
        kundali_score = get_kundali_score() # Placeholder
        personal_score = get_personal_score(hobbies, row)
        matched_uids.append(row['UID'])
        score = kundali_score*config.KUNDALI_WEIGHT + personal_score*config.PERSONAL_WEIGHT
        scores.append(score)

    # SORT LIST AND GET TOP TEN MATCHES
    sorted_pairs = sorted(zip(matched_uids, scores), key=lambda x: x[1], reverse=True)
    recommendations = sorted_pairs[:config.MAX_MATCHES]

    conn_matching= snowflake.connector.connect(
        user=os.getenv('USERNAME'),
        password=os.getenv('PASSWORD'),
        account=os.getenv('ACCOUNT_ID'),
        warehouse=config.MATCHING_TABLE_WAREHOUSE,
        database=config.MATCHING_TABLE_DATABASE,
        schema=config.MATCHING_TABLE_SCHEMA
    )
    # Post recommendations to matching table

    cursor_matching = conn_matching.cursor()
    timestamp = time.time()
    insert_sql_matching = f"INSERT INTO {config.MATCHING_TABLE} (UID1, UID2, SCORE, CREATED, UPDATED, WHATSAPP1, WHATSAPP2, INSTA1, INSTA2, SNAP1, SNAP2) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
    for item in recommendations:
        cursor.execute(insert_sql_matching, (uid, item[0], item[1], timestamp, timestamp, False, False, False, False, False, False ) )

    conn_matching.commit()
    cursor_matching.close()
    conn_matching.close()

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

    current_time = time.time()

    conn = snowflake.connector.connect(
        user=os.getenv('USERNAME'),
        password=os.getenv('PASSWORD'),
        account=os.getenv('ACCOUNT_ID'),
        warehouse=config.PROFILE_TABLE_WAREHOUSE,
        database=config.PROFILE_TABLE_DATABASE,
        schema=config.PROFILE_TABLE_SCHEMA
    )
    
    cursor = conn.cursor()
    select_sql = f"SELECT UID, CREATED, LOGIN FROM {config.PROFILE_TABLE} WHERE EMAIL = {email}"
    cursor.execute(select_sql)

    # GET LAST LOGIN AND UID OF USER
    results = cursor.fetchall()
    if len(results)>1:
        log.warning(f'Email {email} is not unique')
        result = results[-1]
    else:
        result = results[0]

    uid = result['UID']
    created = result['CREATED']
    last_login = result['LOGIN']

    if last_login is None:
        last_login = created
    
    conn.commit()
    cursor.close()
    conn.close()

    update_sql = f"UPDATE {config.MATCHING_TABLE} SET LOGIN = {current_time} WHERE UID = {uid}"
    cursor.execute(update_sql)

    # Fetch all data from existing recommendations
    conn_matching= snowflake.connector.connect(
        user=os.getenv('USERNAME'),
        password=os.getenv('PASSWORD'),
        account=os.getenv('ACCOUNT_ID'),
        warehouse=config.MATCHING_TABLE_WAREHOUSE,
        database=config.MATCHING_TABLE_DATABASE,
        schema=config.MATCHING_TABLE_SCHEMA
    )

    sql_fetch = f"SELECT * FROM {config.MATCHING_TABLE} WHERE UID1 = {uid} OR UID2 = {uid}"
    cursor_matching = conn_matching.cursor()

    cursor_matching.execute(sql_fetch)
    results = cursor_matching.fetchall()

    # We need 4 queues in UI - recommendations, notifications, awaiting responses, matched.
    # Segregate recommendations from notifications
    recommendations, notifications, matched, awaiting = [], [], [], []
    if len(results)>0:
        for result in results:
            if result['WHATSAPP1'] == False and result['WHATSAPP2'] == False and result['INSTA1'] == False and result['INSTA2'] == False and result['SNAP1'] == False and result['SNAP2'] == False:
                recommendations.append(result)
            elif (result['WHATSAPP1'] == True and result['WHATSAPP2'] == True) or (result['INSTA1'] == True and result['INSTA2'] == True) or (result['SNAP1'] == True and result['SNAP2'] == True):
                matched.append(result)
            elif result['UPDATED'] > current_time:
                notifications.append(result)
            else:
                awaiting.append(result)
    
    conn_matching.commit()
    cursor_matching.close()
    conn_matching.close()

    return {'UID' : uid, 'RECOMMENDATIONS' : recommendations, 'NOTIFICATIONS' : notifications, 'MATCHED' : matched, 'AWAITING' : awaiting}, None
    
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
    
    conn_matching= snowflake.connector.connect(
        user=os.getenv('USERNAME'),
        password=os.getenv('PASSWORD'),
        account=os.getenv('ACCOUNT_ID'),
        warehouse=config.MATCHING_TABLE_WAREHOUSE,
        database=config.MATCHING_TABLE_DATABASE,
        schema=config.MATCHING_TABLE_SCHEMA
    )
    cursor_matching = conn_matching.cursor()

    if action == 'SKIP':

        delete_sql = f"DELETE FROM {config.MATCHING_TABLE} WHERE UID1 = {recommendation['UID1']} AND UID2 = {recommendation['UID2']}"
        cursor_matching.execute(delete_sql)
        cursor_matching.commit()

    # Right now we do not provide option to retract your response
    elif action in ['WHATSAPP1', 'WHATSAPP2', 'INSTA1', 'INSTA2', 'SNAP1', 'SNAP2']:
        update_sql = f"UPDATE {config.MATCHING_TABLE} SET {action} = {current_time} WHERE UID = {uid}"
        recommendation[action] = True
        cursor_matching.execute(update_sql)
        cursor_matching.commit()

    else:
        log.error(f'Unrecognized action: {action}')
        return jsonify({"error": "Missing 'action' field"}), 400

    conn_matching.commit()
    cursor_matching.close()
    conn_matching.close()

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
    
    conn = snowflake.connector.connect(
        user=os.getenv('USERNAME'),
        password=os.getenv('PASSWORD'),
        account=os.getenv('ACCOUNT_ID'),
        warehouse=config.PROFILE_TABLE_WAREHOUSE,
        database=config.PROFILE_TABLE_DATABASE,
        schema=config.PROFILE_TABLE_SCHEMA
    )
    cursor = conn.cursor()

    sql_fetch = f'SELECT * FROM {config.PROFILE_TABLE} WHERE EMAIL={email}'
    cursor.execute(sql_fetch)
    results = cursor.fetchall()

    conn.commit()
    cursor.close()
    conn.close()

    if len(results) > 0:
        return {'verify' : False}
    else:
        return {'verify' : True}

if __name__ == '__main__':
    
    app.run(host='0.0.0.0', port=8080)
