import os
import json
from datetime import datetime, time
import numpy as np
#from absl import logging as log 
from kundali_score import Kundali
from flask import Flask, request, jsonify

import logging as log

log.basicConfig(
    format='%(levelname)s [%(filename)s:%(lineno)d] %(message)s',
    level=log.INFO
    )
#log.set_verbosity(log.INFO)


def parse_date(value):
    """Converts input to YYYY-MM-DD string."""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    
    if isinstance(value, dict):
        try:
            return datetime(value["year"], value["month"], value["day"]).strftime("%Y-%m-%d")
        except Exception:
            raise ValueError("Invalid date dictionary format")

    if isinstance(value, str):
        # Case: JSON string like '{"day":9,"month":9,"year":1993}'
        try:
            maybe_dict = json.loads(value)
            if isinstance(maybe_dict, dict) and all(k in maybe_dict for k in ['day', 'month', 'year']):
                return datetime(maybe_dict["year"], maybe_dict["month"], maybe_dict["day"]).strftime("%Y-%m-%d")
        except json.JSONDecodeError:
            pass  # Not a JSON string, try regular date formats

        # Try common string formats
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue

        raise ValueError(f"Date string '{value}' does not match expected formats")

    raise TypeError("Unsupported type for date")


def parse_time(value):
    """Converts input to HH:MM:SS string."""
    if isinstance(value, time):
        return value.strftime("%H:%M:%S")
    elif isinstance(value, datetime):
        return value.time().strftime("%H:%M:%S")
    elif isinstance(value, str):
        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(value, fmt).time().strftime("%H:%M:%S")
            except ValueError:
                continue
        raise ValueError(f"Time string '{value}' does not match expected formats")
    else:
        raise TypeError("Unsupported type for time")
    
app = Flask(__name__)
@app.route('/get:score', methods=['POST'])
def get_score():
    json_data = request.get_json()
    if not json_data:
        return jsonify({'error': 'Missing data'}), 400
    
    try:
        dob1 = parse_date(json_data['DOB1'])
        dob2 = parse_date(json_data['DOB2'])
        tob1 = parse_time(json_data['TOB1'])
        tob2 = parse_time(json_data['TOB2'])
        lat1 = float(json_data['LAT1'])
        lat2 = float(json_data['LAT2'])
        long1 = float(json_data['LONG1'])
        long2 = float(json_data['LONG2'])
    except (KeyError, ValueError, TypeError) as e:
        return jsonify({'error': f'Invalid input: {e}'}), 400

    log.info('Extracted data')

    kundali_obj = Kundali(dob1, dob2, tob1, tob2, lat1, lat2, long1, long2)
    log.info('Created kundali object')

    score = kundali_obj.get_guna_score()
    log.info(type(score))
    log.info(score)
    return jsonify({'score' : score})

if __name__ == '__main__':
    
    app.run(host='0.0.0.0', port=8000)
