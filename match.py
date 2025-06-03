
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import os
import json
import time
from dotenv import load_dotenv
import snowflake.connector
import boto3
from botocore.exceptions import NoCredentialsError
from uuid import uuid4
from PIL import Image
from geopy.geocoders import Nominatim
from absl import logging as log 
from kundal_score import Kundali
from config import config

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
    
# TODO- Build personal scoring logic using hobbies
def get_personal_score(hobbies, row):
    return 0.5

app = Flask(__name__)
@app.route('/account:create', methods=['POST'])
def upload():
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

    insert_sql = f"INSERT INTO {config.PROFILE_TABLE} (UID, NAME, PHONE, EMAIL, CITY, COUNTRY, D0B, TOB, GENDER, HOBBIES, LAT, LONG, IMAGES, CREATED) VALUES (%s, %s, %s, %s, %s, %s, PARSE_JSON(%s), %s, %s, PARSE_JSON(%s), %s)"
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
    cursor.execute(insert_sql, (uid, name, phone, email, city, country, dob, tob, gender, hobbies, lat, long, images, timestamp))

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
        kundali_obj = Kundali(dob, row['DOB'], tob, row["TOB"], lat, row["LAT"], long, row["LONG"])
        kundali_score = kundali_obj.get_guna_score()/config.TOTAL_GUN
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

    insert_sql_matching = f"INSERT INTO {config.MATCHING_TABLE} (UID1, UID2, SCORE, WHATSAPP1, WHATSAPP2, INSTA1, INSTA2, SNAP1, SNAP2) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
    for item in recommendations:
        cursor.execute(insert_sql_matching, (uid, item[0], item[1], False, False, False, False, False, False ) )

    conn_matching.commit()
    cursor_matching.close()
    conn_matching.close()

    return None, None

if __name__ == '__main__':
    
    app.run(host='0.0.0.0', port=8080)
