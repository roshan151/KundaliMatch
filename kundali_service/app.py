import os
import json
import numpy as np
from absl import logging as log 
from kundali_score import Kundali
from flask import Flask, request, jsonify

log.set_verbosity(log.INFO)

app = Flask(__name__)
@app.route('/get:score', methods=['POST'])
def get_score():
    metadata = request.form.get('metadata')
    if not metadata:
        return jsonify({'error': 'Missing metadata'}), 400
    try:
        json_data = json.loads(metadata)
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON'}), 400
    
    dob1, dob2, tob1, tob2 = json_data['DOB1'], json_data['DOB2'], json_data['TOB1'], json_data["TOB2"]
    lat1, lat2, long1, long2 = json_data['LAT1'], json_data['LAT2'], json_data['LONG1'], json_data['LONG2']
    log.info('Extracted data')

    kundali_obj = Kundali(dob1, dob2, tob1, tob2, lat1, lat2, long1, long2)
    log.info('Created kundali object')

    score = kundali_obj.get_guna_score(kundali_obj)

    return jsonify({'score' : score})

if __name__ == '__main__':
    
    app.run(host='0.0.0.0', port=8000)
