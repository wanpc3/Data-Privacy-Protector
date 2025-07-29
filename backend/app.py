from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import uuid
import json
from datetime import datetime
from PIL import Image
import pandas as pd
import docx
import PyPDF2
import re
from cryptography.fernet import Fernet
import base64
import hashlib

app = Flask(__name__)
CORS(app)

DATA_FILE = 'data.json'
PARTNER_LOGOS_FOLDER = 'partner_logos'

if not os.path.exists(PARTNER_LOGOS_FOLDER):
    os.makedirs(PARTNER_LOGOS_FOLDER)

#Encryption key
def generate_encryption_key():
    return Fernet.generate_key()

#Load data
def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w') as f:
            json.dump({'partners': [], 'files': []}, f)
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

#Save data
def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

#Upload file
@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files.get('file')
    partner_name = request.form.get('partner')
    if not file or not partner_name:
        return jsonify({'error': 'Missing file or partner'}), 400

    filename = file.filename
    file_ext = filename.rsplit('.', 1)[-1].lower()
    if file_ext != 'txt':
        return jsonify({'error': 'Only .txt files supported currently'}), 400

    content = file.read().decode('utf-8')

    data = load_data()
    partner = next((p for p in data['partners'] if p['name'] == partner_name), None)
    if not partner:
        return jsonify({'error': 'Partner not found'}), 404

    detection_settings = partner.get('detection_settings', [])

    review = []

    # Example regex patterns for some PII types
    patterns = {
        'EMAIL_ADDRESS': re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'),
        'PHONE_NUMBER': re.compile(r'\b\d{3}[-.\s]??\d{3}[-.\s]??\d{4}\b'),  # US style phone number example
        # Add more patterns here as needed
    }

    # Loop over enabled detection types and run detection
    for pii_type in detection_settings:
        pattern = patterns.get(pii_type)
        if pattern:
            for match in pattern.finditer(content):
                start, end = match.span()
                word = match.group()
                review.append({
                    'id': str(uuid.uuid4()),
                    'detect': pii_type,
                    'start': start,
                    'end': end,
                    'word': word,
                    'confidence': 0.95  # you can customize confidence or calculate it
                })

    # Generate file ID
    file_id = str(uuid.uuid4())

    file_entry = {
        'id': file_id,
        'partner_id': partner['id'],
        'filename': filename,
        'file_type': 'Text file',
        'state': 'Pending Review',
        'uploaded_at': datetime.utcnow().isoformat()
    }

    data['files'].append(file_entry)
    save_data(data)

    return jsonify({
        'file_id': file_id,
        'filename': filename,
        'type': 'Text file',
        'review': review
    })

#Get Partner
@app.route('/api/partners', methods=['GET'])
def get_partners():
    data = load_data()
    partners = []

    for partner in data['partners']:
        partner_files = [
            {
                'id': file['id'],
                'filename': file['filename'],
                'type': file['file_type'],
                'state': file['state'],
                'downloadLink': f"/download/{file['id']}" if file['state'] == 'Anonymized' else None
            }
            for file in data['files'] if file['partner_id'] == partner['id']
        ]
        partners.append({
            **partner,
            'files': partner_files,
            'detection_settings': partner.get('detection_settings', [])
        })

    return jsonify(partners)

#Create Partner
@app.route('/create-partner', methods=['POST'])
def create_partner():
    try:
        data = load_data()

        partner_name = request.form.get('partner')
        detection_settings = json.loads(request.form.get('detection', '[]'))
        encryption_key = request.form.get('key', '')
        file_password = request.form.get('password', '')

        if not partner_name:
            return jsonify({'error': 'Partner name is required'}), 400

        partner_id = str(uuid.uuid4())
        logo_path = None

        if 'icon' in request.files:
            logo_file = request.files['icon']
            if logo_file.filename:
                filename = secure_filename(f"{partner_id}_{logo_file.filename}")
                logo_path = os.path.join(PARTNER_LOGOS_FOLDER, filename)
                logo_file.save(logo_path)
                logo_path = f'/partner_logos/{filename}'

        if not encryption_key:
            encryption_key = base64.b64encode(generate_encryption_key()).decode()

        partner_entry = {
            'id': partner_id,
            'name': partner_name,
            'logo': logo_path,
            'encryption_key': encryption_key,
            'file_password': file_password,
            'detection_settings': detection_settings,
            'created_at': datetime.utcnow().isoformat()
        }

        data['partners'].append(partner_entry)
        save_data(data)

        return jsonify({
            'id': partner_id,
            'name': partner_name,
            'logo': logo_path,
            'message': 'Partner created successfully'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

#Partner logo
@app.route('/partner_logos/<filename>')
def serve_partner_logo(filename):
    """Serve partner logo files"""
    return send_from_directory(PARTNER_LOGOS_FOLDER, filename)

if __name__ == '__main__':
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w') as f:
            json.dump({'partners': [], 'files': []}, f)
    app.run(debug=True, host='0.0.0.0', port=5000)
