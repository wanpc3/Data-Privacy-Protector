from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from tinydb import TinyDB, Query
import json
import os
import uuid
import traceback
import pandas as pd
import re
from datetime import datetime
import shutil
import io # Needed for in-memory Excel handling with pandas

app = Flask(__name__)
CORS(app)

DATA_DIR = 'data'
os.makedirs(DATA_DIR, exist_ok=True)

db = TinyDB('data/pmi_anonymizer_db.json')
partners_table = db.table('partners')
files_table = db.table('files')

# Define TinyDB Query objects
Partner = Query()
File = Query()

# Centralized folder configuration
app.config['ICON_UPLOAD_FOLDER'] = 'static/partner_icons'
app.config['ORIGINAL_FILES_FOLDER'] = 'static/uploaded_files'
app.config['ANONYMIZED_FILES_FOLDER'] = 'static/anonymized_files'
app.config['DEANONYMIZED_FILES_FOLDER'] = 'static/deanonymized_files' # For temporary de-anonymized versions

# Create all necessary folders
for folder in [
    app.config['ICON_UPLOAD_FOLDER'],
    app.config['ORIGINAL_FILES_FOLDER'],
    app.config['ANONYMIZED_FILES_FOLDER'],
    app.config['DEANONYMIZED_FILES_FOLDER']
]:
    os.makedirs(folder, exist_ok=True)

# --- Helper Functions ---
def get_file_type_from_extension(filename):
    ext = filename.split('.')[-1].lower() # Use [-1] for extension
    if ext in ['txt']:
        return 'Text file'
    elif ext in ['jpg', 'jpeg', 'png', 'bmp']:
        return 'Image file'
    elif ext in ['csv', 'xlsx', 'xlsm', 'xls']:
        return 'Tabular file'
    elif ext in ['doc', 'docx', 'pdf']:
        return 'Document file'
    return 'Unknown file'

# --- API Endpoints ---

# Consolidated endpoint for getting all partners and their files
@app.route('/api/partners', methods=['GET'])
def get_partners_and_files():
    all_partners = partners_table.all()
    for partner in all_partners:
        partner_files = files_table.search(File.partner_id == partner['id'])
        # Sort files by upload_date if available, otherwise by filename
        partner['files'] = sorted(partner_files, key=lambda f: f.get('upload_date', '0'), reverse=True)
        
        # Ensure correct logo path for frontend
        if 'logo' in partner and partner['logo'] and not partner['logo'].startswith('/static/'):
            # This handles cases where logo might just be a filename, converts to full static path
            partner['logo'] = f"/static/partner_icons/{os.path.basename(partner['logo'])}"
        elif 'logo' not in partner or not partner['logo']:
            partner['logo'] = '/static/icons/question-mark.png' # Fallback default
    return jsonify(all_partners), 200

# Endpoint to create a new partner
@app.route('/create-partner', methods=['POST'])
def create_partner():
    print("\n--- Incoming POST Request to /create-partner ---")
    
    partner_name = request.form.get('partner')
    data_encryption_key = request.form.get('key')
    file_password = request.form.get('password')
    detection_settings_str = request.form.get('detection') # This is sent as a comma-separated string

    if not partner_name:
        return jsonify({"error": "Partner name is required"}), 400

    detection_settings = [s.strip() for s in detection_settings_str.split(',') if s.strip()] if detection_settings_str else []

    logo_path = '/static/icons/question-mark.png' # Default logo path
    if 'icon' in request.files:
        icon_file = request.files['icon']
        if icon_file.filename != '':
            filename = str(uuid.uuid4()) + os.path.splitext(icon_file.filename)[1]
            file_save_path = os.path.join(app.config['ICON_UPLOAD_FOLDER'], filename)
            try:
                icon_file.save(file_save_path)
                logo_path = f'/static/partner_icons/{filename}'
            except Exception as e:
                print(f"ERROR: Failed to save icon file: {e}")
                # Don't fail the entire request for icon save error, use default
    
    if partners_table.search(Partner.name == partner_name):
        return jsonify({"error": f"Partner with name '{partner_name}' already exists"}), 409

    new_partner = {
        'id': str(uuid.uuid4()),
        'name': partner_name,
        'logo': logo_path,
        'dataEncryptionKey': data_encryption_key,
        'filePassword': file_password,
        'detectionSettings': detection_settings,
    }
    partners_table.insert(new_partner)
    print(f"Successfully added partner: {partner_name}")
    return jsonify(new_partner), 201

# Endpoint: /upload (POST) - Upload and Analyze File
@app.route('/upload', methods=['POST'])
def upload_file_and_analyze():
    partner_name = request.form.get('partner')
    if not partner_name:
        return jsonify({"error": "Partner name is required for file upload"}), 400

    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    supported_extensions = ['txt', 'csv', 'xlsx', 'xls', 'jpg', 'jpeg', 'png', 'bmp', 'doc', 'docx', 'pdf']
    if file.filename.split('.')[-1].lower() not in supported_extensions:
        return jsonify({"error": "Unsupported file type"}), 400

    try:
        filename = file.filename
        file_id = str(uuid.uuid4())
        file_type = get_file_type_from_extension(filename)

        original_file_path = os.path.join(app.config['ORIGINAL_FILES_FOLDER'], f"{file_id}_{filename}")
        file.save(original_file_path) # Save the uploaded file
        print(f"Original file saved to: {original_file_path}")

        detected_pii_results = []

        if file_type == 'Text file':
            with open(original_file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()

            # --- Text PII Detection (from your code) ---
            ic_number_pattern = r"\b\d{6}-\d{2}-\d{4}\b"
            for match in re.finditer(ic_number_pattern, file_content):
                detected_pii_results.append({"detect": "IC_NUMBER", "start": match.start(), "end": match.end(), "confidence": 0.95, "word": match.group()})

            passport_pattern = r"[A-Z]{1}[0-9]{8}"
            for match in re.finditer(passport_pattern, file_content):
                detected_pii_results.append({"detect": "US_PASSPORT", "start": match.start(), "end": match.end(), "confidence": 0.95, "word": match.group()})

            bank_account_pattern = r"\b\d{9,12}\b" # Very generic, refine this!
            for match in re.finditer(bank_account_pattern, file_content):
                detected_pii_results.append({"detect": "US_BANK_NUMBER", "start": match.start(), "end": match.end(), "confidence": 0.70, "word": match.group()})

            credit_card_pattern = r"\b(?:\d[ -]*?){13,16}\b" # Very generic, refine this!
            for match in re.finditer(credit_card_pattern, file_content):
                detected_pii_results.append({"detect": "CREDIT_CARD", "start": match.start(), "end": match.end(), "confidence": 0.80, "word": match.group()})

            email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
            for match in re.finditer(email_pattern, file_content):
                detected_pii_results.append({"detect": "EMAIL_ADDRESS", "start": match.start(), "end": match.end(), "confidence": 0.98, "word": match.group()})

            phone_pattern = r"\b(?:\+?6?0\d{1,2}[- ]?\d{7,8}|(?:\d{3}\)[- ]?\d{3}[- ]?\d{4}|\+1-\d{3}-\d{3}-\d{4}))\b"
            for match in re.finditer(phone_pattern, file_content):
                detected_pii_results.append({"detect": "PHONE_NUMBER", "start": match.start(), "end": match.end(), "confidence": 0.90, "word": match.group()})

            lines = file_content.strip().split('\n')
            current_offset = 0 
            for line in lines:
                parts = line.split('\t')
                if len(parts) == 2:
                    name_part = parts[0].strip()
                    address_part = parts[1].strip()

                    if name_part:
                        detected_pii_results.append({"detect": "PERSON", "start": current_offset + line.find(name_part), "end": current_offset + line.find(name_part) + len(name_part), "confidence": 0.90, "word": name_part})

                    if address_part:
                        detected_pii_results.append({"detect": "LOCATION", "start": current_offset + line.find(address_part), "end": current_offset + line.find(address_part) + len(address_part), "confidence": 0.88, "word": address_part})
                current_offset += len(line) + len(os.linesep) # Add line ending length for accurate offset

        elif file_type == 'Tabular file':
            print(f"Analyzing Tabular file: {filename}")
            try:
                df = None
                file_extension = filename.split('.')[-1].lower()
                if file_extension in ['csv']:
                    df = pd.read_csv(original_file_path)
                elif file_extension in ['xlsx', 'xls', 'xlsm']:
                    df = pd.read_excel(original_file_path)
                
                if df is not None:
                    # --- Tabular PII Detection (from your code) ---
                    if 'Email' in df.columns:
                        top_emails = df['Email'].dropna().head(2).tolist()
                        detected_pii_results.append({"detect": "EMAIL_ADDRESS", "column": "Email", "topData": top_emails, "avgConfidence": 0.9})
                    
                    if 'Phone' in df.columns:
                        top_phones = df['Phone'].dropna().head(2).tolist()
                        detected_pii_results.append({"detect": "PHONE_NUMBER", "column": "Phone", "topData": top_phones, "avgConfidence": 0.85})

                    if 'Name' in df.columns:
                        top_names = df['Name'].dropna().head(2).tolist()
                        detected_pii_results.append({"detect": "PERSON", "column": "Name", "topData": top_names, "avgConfidence": 0.92})

                    if 'CustomerID' in df.columns:
                        top_ids = df['CustomerID'].dropna().head(2).astype(str).tolist()
                        detected_pii_results.append({"detect": "IC_NUMBER", "column": "CustomerID", "topData": top_ids, "avgConfidence": 0.75})
                else:
                    return jsonify({"error": "Unsupported tabular file format."}), 400
            except Exception as e:
                print(f"Error reading tabular file with pandas: {e}")
                return jsonify({"error": "Failed to parse tabular file content"}), 400

        final_review_data = []
        for item in detected_pii_results:
            normalized_confidence = item.get('confidence', item.get('avgConfidence', 0.0))
            if normalized_confidence > 1.0:
                normalized_confidence /= 100.0

            if file_type in ['Text file', 'Image file', 'Document file']: # Assuming image/doc can have text too
                final_review_data.append({
                    "detect": item.get("detect"),
                    "start": int(item.get("start", 0)),
                    "end": int(item.get("end", 0)),
                    "confidence": normalized_confidence,
                    "word": item.get("word", ""),
                    "ignore": False
                })
            elif file_type == 'Tabular file':
                final_review_data.append({
                    "detect": item.get("detect"),
                    "column": item.get("column", ""),
                    "topData": item.get("topData", []),
                    "confidence": normalized_confidence, # Use 'confidence' for consistency with frontend
                    "ignore": False
                })

        partner_obj = partners_table.search(Partner.name == partner_name)
        partner_id_for_file = partner_obj[0]['id'] if partner_obj else None

        if not partner_id_for_file:
            print(f"Partner '{partner_name}' not found for file storage during upload.")
            return jsonify({"error": f"Partner '{partner_name}' not found for file storage"}), 404

        new_file_record = {
            'id': file_id,
            'partner_id': partner_id_for_file,
            'filename': filename,
            'type': file_type,
            'original_path': original_file_path,
            'anonymized_path': None,
            'deanonymized_path': None, # New field for path of de-anonymized copy if made
            'state': 'Pending Review',
            'upload_date': datetime.now().isoformat(),
            'review_data': final_review_data,
            'auditLog': None,
            'reverse': [],
            'downloadLink': None
        }
        files_table.insert(new_file_record)
        print(f"File metadata stored in TinyDB: {file_id}")

        response_data = {
            "file_id": file_id, # Frontend expects this for review process
            "partner": partner_name,
            "filename": filename,
            "type": file_type,
            "review": final_review_data
        }

        print("Successfully processed file and generated review data. Returning 200 OK.")
        return jsonify(response_data), 200

    except Exception as e:
        print(f"An unexpected error occurred during file upload/analysis: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Internal server error during file analysis: {str(e)}"}), 500

# Endpoint: /proceed (POST) - Proceed to Anonymize after human review
@app.route('/proceed', methods=['POST'])
def proceed_anonymization():
    print("\n--- Incoming POST Request to /proceed ---")
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    file_id = data.get('file_id') # Get file_id from frontend
    reviewed_pii = data.get('review', [])

    if not file_id:
        return jsonify({"error": "Missing file_id in payload"}), 400
    
    file_record = files_table.search(
        (File.id == file_id) & (File.state == 'Pending Review')
    )
    if not file_record:
        return jsonify({"error": f"File with ID '{file_id}' not found or not in 'Pending Review' state."}), 404

    file_record = file_record[0]
    filename = file_record['filename']
    file_type = file_record['type']
    original_file_path = file_record['original_path']
    partner_id = file_record['partner_id']
    partner_obj = partners_table.search(Partner.id == partner_id)
    partner_name = partner_obj[0]['name'] if partner_obj else "Unknown Partner"

    print(f"Proceeding anonymization for {filename} (ID: {file_id}, Type: {file_type}) for partner {partner_name}")

    anonymized_file_content = None
    reverse_info = []
    detected_entities_summary = {}

    try:
        if file_type == 'Text file':
            with open(original_file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            current_content = list(original_content)
            offset = 0 
            
            # Sort by start position to ensure correct offset calculation for text files
            for item in sorted(reviewed_pii, key=lambda x: x.get('start', 0)): 
                if not item.get('ignore', False):
                    detect_type = item.get('detect')
                    word = item.get('word')
                    start = item.get('start')
                    end = item.get('end')

                    if start is not None and end is not None:
                        adjusted_start = start + offset
                        adjusted_end = end + offset

                        replacement_text = f"[[ANON_{detect_type}]]" 
                        original_segment = original_content[start:end] 
                        # In a real scenario, encrypt original_segment here
                        
                        current_content[adjusted_start:adjusted_end] = list(replacement_text)

                        offset += len(replacement_text) - (end - start)

                        reverse_info.append({
                            "original": {"start": start, "end": end},
                            "anonymized": {"start": adjusted_start, "end": adjusted_start + len(replacement_text)},
                            "original_value": original_segment, # Store this securely if needed for de-anonymization
                            "anonymized_value": replacement_text 
                        })

                    detected_entities_summary[detect_type] = detected_entities_summary.get(detect_type, 0) + 1

            anonymized_file_content = "".join(current_content)

        elif file_type == 'Tabular file':
            df = None
            file_extension = filename.split('.')[-1].lower()
            if file_extension in ['csv']:
                df = pd.read_csv(original_file_path)
            elif file_extension in ['xlsx', 'xls', 'xlsm']:
                df = pd.read_excel(original_file_path)
            
            if df is not None:
                for item in reviewed_pii:
                    if not item.get('ignore', False):
                        detect_type = item.get('detect')
                        column_name = item.get('column')
                        
                        if column_name in df.columns:
                            # Replace cell values
                            # This is a simple redaction. For encryption, you'd apply a hash/token
                            df[column_name] = df[column_name].apply(lambda x: f"[[ANON_{detect_type}]]" if pd.notna(x) else x)
                            detected_entities_summary[detect_type] = detected_entities_summary.get(detect_type, 0) + 1
                
                # Save anonymized DataFrame to BytesIO or directly to file
                output_buffer = io.BytesIO()
                if file_extension in ['csv']:
                    df.to_csv(output_buffer, index=False, encoding='utf-8')
                    anonymized_file_content = output_buffer.getvalue()
                elif file_extension in ['xlsx', 'xls', 'xlsm']:
                    with pd.ExcelWriter(output_buffer, engine='xlsxwriter') as writer:
                        df.to_excel(writer, index=False, sheet_name='Sheet1')
                    anonymized_file_content = output_buffer.getvalue()
            else:
                return jsonify({"error": "Failed to read tabular file for anonymization."}), 500

        # Save the anonymized file to disk
        anonymized_filename_on_disk = f"anonymized_{file_id}_{filename}"
        anonymized_file_path = os.path.join(app.config['ANONYMIZED_FILES_FOLDER'], anonymized_filename_on_disk)
        
        if file_type == 'Text file' or (file_type == 'Tabular file' and file_extension == 'csv'):
            with open(anonymized_file_path, 'w', encoding='utf-8') as f:
                f.write(anonymized_file_content)
        elif file_type == 'Tabular file' and file_extension in ['xlsx', 'xls', 'xlsm']:
             with open(anonymized_file_path, 'wb') as f: # Write as binary for Excel
                f.write(anonymized_file_content)

        print(f"Anonymized file saved to: {anonymized_file_path}")

        # Update the file record in TinyDB
        files_table.update({
            'state': 'Anonymized',
            'anonymized_path': anonymized_file_path,
            'downloadLink': f'/download/{file_id}', # This URL will resolve to the anonymized file
            'auditLog': {
                "filename": filename, # Added filename for AuditLog.jsx
                "intendedFor": partner_name,
                "anonymizedMethod": "Redaction/Encryption", 
                "fileType": file_type, # Added fileType for AuditLog.jsx
                "detectedEntitiesSummary": [{"entity": k, "count": v} for k, v in detected_entities_summary.items()]
            },
            'reverse': reverse_info 
        }, File.id == file_id)

        print(f"Successfully completed anonymization for {filename}. Returning 200 OK.")
        return jsonify({"message": "Anonymization process completed successfully", "filename": filename, "file_id": file_id}), 200

    except Exception as e:
        print(f"An unexpected error occurred during anonymization: {e}")
        traceback.print_exc()
        files_table.update({'state': 'Anonymization Failed'}, File.id == file_id)
        return jsonify({"error": f"Internal server error during anonymization: {str(e)}"}), 500

# Endpoint: /anonymize (POST) - Direct anonymization (e.g., auto-anonymize)
@app.route('/anonymize', methods=['POST'])
def direct_anonymize():
    # This endpoint is kept for "auto-anonymize" but needs actual implementation
    # Currently uses dummy content and detection
    return jsonify({"error": "Direct anonymization not fully implemented with real logic."}), 501


# Endpoint: /denonymize (POST) - Direct de-anonymization
# This endpoint currently only creates a dummy de-anonymized file.
# The `toggle_file_state` handles the actual state change and copy logic.
@app.route('/denonymize', methods=['POST'])
def direct_denonymize():
    return jsonify({"error": "Direct de-anonymization not fully implemented with real logic."}), 501

# Endpoint to fetch audit log for a specific file
@app.route('/api/files/<file_id>/auditlog', methods=['GET'])
def get_file_auditlog(file_id): # <-- CORRECTED: file_id is now an argument
    print(f"Fetching audit log for file_id: {file_id}")
    file_record = files_table.get(File.id == file_id)

    if file_record and file_record.get('auditLog'):
        audit_data_response = {
            "filename": file_record['filename'], # Ensure filename from main record
            "fileType": file_record['type'],     # Ensure fileType from main record
            **file_record['auditLog'] # Merge existing audit log data
        }
        return jsonify(audit_data_response), 200
    else:
        # Changed the error message slightly to match the frontend's expectation more clearly
        return jsonify({"error": "Audit log not available for this file."}), 404

# Endpoint: /download/<file_id> (GET) - To download the appropriate file based on state
@app.route('/download/<file_id>', methods=['GET'])
def download_file(file_id):
    file_record = files_table.get(File.id == file_id)
    if not file_record:
        return jsonify({"error": "File not found"}), 404

    file_state = file_record.get('state')
    filename_on_disk = None
    download_name = file_record['filename'] # Default download name is original filename

    if file_state == 'Anonymized' and file_record.get('anonymized_path'):
        filename_on_disk = os.path.basename(file_record['anonymized_path'])
        directory = app.config['ANONYMIZED_FILES_FOLDER']
        download_name = f"anonymized_{download_name}"
    elif file_state == 'De-anonymized' and file_record.get('deanonymized_path'):
        filename_on_disk = os.path.basename(file_record['deanonymized_path'])
        directory = app.config['DEANONYMIZED_FILES_FOLDER']
        download_name = f"deanonymized_{download_name}"
    elif file_state == 'Pending Review' and file_record.get('original_path'): # Allow download of original
        filename_on_disk = os.path.basename(file_record['original_path'])
        directory = app.config['ORIGINAL_FILES_FOLDER']
        download_name = f"original_{download_name}"
    else:
        return jsonify({"error": "File not available for download in its current state or path missing."}), 404

    if filename_on_disk and os.path.exists(os.path.join(directory, filename_on_disk)):
        return send_from_directory(directory, filename_on_disk, as_attachment=True, download_name=download_name)
    else:
        return jsonify({"error": "File not found on server at specified path."}), 404

# Endpoint: /api/files/<file_id>/state (PUT) - To toggle file state (Anonymized/De-anonymized)
@app.route('/api/files/<file_id>/state', methods=['PUT'])
def toggle_file_state(file_id):
    data = request.get_json()
    new_state = data.get('state')

    if new_state not in ['Anonymized', 'De-anonymized']:
        return jsonify({"error": "Invalid state provided. Must be 'Anonymized' or 'De-anonymized'"}), 400

    file_record = files_table.get(File.id == file_id)
    if not file_record:
        return jsonify({"error": "File not found"}), 404

    current_state = file_record.get('state')
    if current_state == new_state:
        return jsonify({"message": f"File is already in {new_state} state."}), 200

    updated_fields = {'state': new_state}

    try:
        if new_state == 'De-anonymized':
            # Option 1: Copy original to deanonymized folder and update path
            if file_record.get('original_path') and os.path.exists(file_record['original_path']):
                deanonymized_filename = f"deanonymized_{file_id}_{file_record['filename']}"
                deanonymized_file_path = os.path.join(app.config['DEANONYMIZED_FILES_FOLDER'], deanonymized_filename)
                
                # Copy the original file to the deanonymized folder
                shutil.copy(file_record['original_path'], deanonymized_file_path)
                updated_fields['deanonymized_path'] = deanonymized_file_path
                # The downloadLink in the DB will remain /download/{file_id}, but the download_file endpoint
                # will now serve the file from deanonymized_path based on the updated state.
                message = f"File state updated to {new_state}. Original content is now active for download."
            else:
                return jsonify({"error": "Original file path not found to create de-anonymized version."}), 500

        elif new_state == 'Anonymized':
            # This means reverting from De-anonymized state back to Anonymized.
            # We assume the anonymized_path already exists from the initial anonymization.
            if file_record.get('anonymized_path') and os.path.exists(file_record['anonymized_path']):
                # No path change needed, just state update.
                message = f"File state updated to {new_state}. Anonymized content is now active for download."
            else:
                return jsonify({"error": "Anonymized file not found to revert to."}), 500

        files_table.update(updated_fields, File.id == file_id)
        print(f"File {file_id} state updated to {new_state}.")
        return jsonify({"message": message}), 200

    except Exception as e:
        print(f"Error toggling file state for {file_id}: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Failed to toggle file state: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)