from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from tinydb import TinyDB, Query
import json
import os
import uuid
import traceback
import pandas as pd
import re
import spacy

app = Flask(__name__)
CORS(app)

# Assuming TinyDB setup looks something like this:
db = TinyDB('partners_db.json')
partners_table = db.table('partners')
files_table = db.table('files') # NEW: Table to store file-specific data
Partner = Query()
File = Query() # Query object for the files table

# Define a path to save uploaded icons (e.g., inside 'static' folder)
UPLOAD_FOLDER = 'static/partner_icons' # This should be defined globally
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER) # Ensure this runs successfully at app startup
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
FILE_STORAGE_FOLDER = 'static/uploaded_files' # NEW: Folder for uploaded data files
ANONYMIZED_FILES_FOLDER = 'static/anonymized_files' # NEW: Folder for anonymized files
DEANONYMIZED_FILES_FOLDER = 'static/deanonymized_files' # NEW: Folder for de-anonymized files

for folder in [UPLOAD_FOLDER, FILE_STORAGE_FOLDER, ANONYMIZED_FILES_FOLDER, DEANONYMIZED_FILES_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['FILE_STORAGE_FOLDER'] = FILE_STORAGE_FOLDER
app.config['ANONYMIZED_FILES_FOLDER'] = ANONYMIZED_FILES_FOLDER
app.config['DEANONYMIZED_FILES_FOLDER'] = DEANONYMIZED_FILES_FOLDER

nlp = None # Initialize nlp to None
try:
    nlp = spacy.load("en_core_web_sm")
    print("spaCy model 'en_core_web_sm' loaded successfully.")
except Exception as e:
    print(f"Error loading spaCy model: {e}. PII detection for Text files will be limited or disabled.")


# Helper function for file type detection (corrected for 'in' operator)
def get_file_type_from_extension(filename):
    ext = filename.split('.').pop().lower()
    if ext in ['txt']:
      return 'Text file'
    elif ext in ['jpg', 'jpeg', 'png', 'bmp']:
      return 'Image file'
    elif ext in ['csv', 'xlsx', 'xlsm', 'xls']:
      return 'Tabular file'
    elif ext in ['doc', 'docx', 'pdf']:
      return 'Document file'
    return 'Unknown file'

# --- API ENDPOINTS ---

# Endpoint: / (GET) - To get the updated list (Partners and their files)
@app.route('/', methods=['GET'])
def get_all_data():
    all_partners = partners_table.all()
    # Attach files to their respective partners
    for partner in all_partners:
        # Fetch files associated with this partner
        partner_files = files_table.search(File.partner_id == partner['id'])
        # Sort files, e.g., by upload date or filename
        partner['files'] = sorted(partner_files, key=lambda f: f.get('upload_date', '')) # Add a 'upload_date' field when saving files

    return jsonify(all_partners), 200

# Endpoint: /api/partners (GET) - Get all partners
@app.route('/api/partners', methods=['GET'])
def get_partners():
    # This endpoint is redundant if '/' provides all data, but keeping it as per previous conversation.
    # It might be used for just partner names without file details.
    all_partners = partners_table.all()
    # Note: This endpoint does not include files, as per initial setup.
    return jsonify(all_partners)

@app.route('/create-partner', methods=['POST'])
def create_partner():
    print("\n--- Incoming POST Request to /create-partner (Icon Debug) ---")
    print(f"Request Files (raw): {request.files}") # See all files received

    partner_name = request.form.get('partner')
    data_encryption_key = request.form.get('key')
    file_password = request.form.get('password')
    detection_settings_str = request.form.get('detection')

    if not partner_name:
        print("Backend: Partner name is required! Returning 400.")
        return jsonify({"error": "Partner name is required"}), 400

    detection_settings = []
    if detection_settings_str:
        detection_settings = [s.strip() for s in detection_settings_str.split(',') if s.strip()]


    logo_path = '/icons/question-mark.png'
    if 'icon' in request.files:
        icon_file = request.files['icon']
        print(f"Icon file found in request.files. Filename: '{icon_file.filename}'")

        if icon_file.filename != '':
            # It's good practice to secure the filename, though uuid makes it unique
            # from werkzeug.utils import secure_filename # import this if you want to use it
            # filename = secure_filename(icon_file.filename)
            filename = str(uuid.uuid4()) + os.path.splitext(icon_file.filename)[1]
            file_save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            print(f"Attempting to save icon to full path: {file_save_path}")

            try:
                icon_file.save(file_save_path)
                logo_path = f'/static/partner_icons/{filename}' # Path for frontend to load
                print(f"Icon saved successfully. Frontend logo_path: {logo_path}")
            except Exception as e:
                print(f"ERROR: Failed to save icon file to disk! Exception: {e}")
                # You might want to return a more specific error to the frontend here
                # return jsonify({"error": f"Failed to save icon file: {str(e)}"}), 500
        else:
            print("Backend: 'icon' file field present, but filename is empty (user didn't select a file).")
    else:
        print("Backend: 'icon' file field NOT found in request.files.")

    partner_id = str(uuid.uuid4())

    if partners_table.search(Partner.name == partner_name):
        print(f"Backend: Partner with name '{partner_name}' already exists! Returning 409.")
        return jsonify({"error": f"Partner with name '{partner_name}' already exists"}), 409

    new_partner = {
        'id': partner_id,
        'name': partner_name,
        'logo': logo_path, # This will be the default or the saved icon path
        'dataEncryptionKey': data_encryption_key,
        'filePassword': file_password,
        'detectionSettings': detection_settings,
    }
    partners_table.insert(new_partner)
    print(f"Backend: Successfully added partner: {partner_name} with logo_path: {logo_path}. Returning 201.")
    return jsonify(new_partner), 201


@app.route('/upload', methods=['POST'])
def upload_file_and_analyze():
    partner_name = request.form.get('partner')
    if not partner_name:
        print("Error: 'partner' field missing in form data.")
        return jsonify({"error": "Partner name is required for file upload"}), 400

    if 'file' not in request.files:
        print("Error: No 'file' part in the request.")
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']
    if file.filename == '':
        print("Error: No selected file.")
        return jsonify({"error": "No selected file"}), 400

    # Validate file extension against supported types
    supported_extensions = ['txt', 'csv', 'xlsx', 'xls', 'jpg', 'jpeg', 'png', 'bmp', 'doc', 'docx', 'pdf']
    if file.filename.split('.')[-1].lower() not in supported_extensions:
        print(f"Unsupported file type: {file.filename}")
        return jsonify({"error": "Unsupported file type"}), 400

    try:
        filename = file.filename
        file_id = str(uuid.uuid4())
        file_type = get_file_type_from_extension(filename) # Now this would correctly return 'Tabular file' for .csv

        original_file_path = os.path.join(app.config['FILE_STORAGE_FOLDER'], f"{file_id}_{filename}")
        file.save(original_file_path)
        print(f"Original file saved to: {original_file_path}")

        detected_pii_results = []

        if file_type == 'Text file':
            file.seek(0)
            file_content = file.read().decode('utf-8')
            print(f"Analyzing Text file: {filename}")

            if nlp: # <--- CHECK IF nlp IS NOT NONE BEFORE USING IT
                doc = nlp(file_content)

                for ent in doc.ents:
                    detected_type = None
                    if ent.label_ == "PERSON":
                        detected_type = "PERSON"
                    elif ent.label_ in ["GPE", "LOC", "ADDRESS"]:
                        detected_type = "ADDRESS"
                    elif ent.label_ == "ORG":
                        detected_type = "ORGANIZATION"

                    if detected_type:
                        detected_pii_results.append({
                            "detect": detected_type,
                            "start": ent.start_char,
                            "end": ent.end_char,
                            "confidence": 0.75,
                            "word": ent.text
                        })
                
                # Add the tab-delimited parsing here for your specific data
                lines = file_content.strip().split('\n')
                for line in lines:
                    parts = line.split('\t')
                    if len(parts) == 2:
                        name_part = parts[0].strip()
                        address_part = parts[1].strip()

                        # Enhance Name detection (spaCy might already catch this, but explicit is good)
                        if name_part and len(name_part) > 2 and any(char.isalpha() for char in name_part):
                            detected_pii_results.append({
                                "detect": "PERSON",
                                "start": file_content.find(name_part),
                                "end": file_content.find(name_part) + len(name_part),
                                "confidence": 0.85, # Higher confidence for this structured part
                                "word": name_part
                            })

                        # Enhance Address detection (spaCy might catch this too)
                        if address_part:
                            detected_pii_results.append({
                                "detect": "ADDRESS", # Use 'ADDRESS' if that's your defined type
                                "start": file_content.find(address_part),
                                "end": file_content.find(address_part) + len(address_part),
                                "confidence": 0.9,
                                "word": address_part
                            })

        elif file_type == 'Tabular file':
            print(f"Analyzing Tabular file: {filename}")
            # Jason: Plug in your tabular PII detection logic here.
            file.seek(0) # Ensure file pointer is at the beginning for pandas
            try:
                # Assuming it's a CSV; adjust for Excel if needed (pd.read_excel)
                df = pd.read_csv(file)
                
                # Identify potential PII columns based on common names or header analysis
                # You can also use the partner's detectionSettings here (partner_obj['detectionSettings'])
                
                # Example: Check 'Email', 'Phone', 'Name' columns
                if 'Email' in df.columns:
                    # Collect top few email examples for display
                    top_emails = df['Email'].dropna().head(2).tolist()
                    detected_pii_results.append({
                        "detect": "EMAIL_ADDRESS",
                        "column": "Email",
                        "topData": top_emails,
                        "avgConfidence": 0.9 # Conceptual average confidence
                    })
                
                if 'Phone' in df.columns:
                    top_phones = df['Phone'].dropna().head(2).tolist()
                    detected_pii_results.append({
                        "detect": "PHONE_NUMBER",
                        "column": "Phone",
                        "topData": top_phones,
                        "avgConfidence": 0.85
                    })

                if 'Name' in df.columns:
                    top_names = df['Name'].dropna().head(2).tolist()
                    detected_pii_results.append({
                        "detect": "PERSON",
                        "column": "Name",
                        "topData": top_names,
                        "avgConfidence": 0.92
                    })

                # For IC_NUMBER, you'd need to check column names like 'IC Number', 'ID', etc.
                if 'CustomerID' in df.columns: # You can add a rule for CustomerID if it's sensitive
                    top_ids = df['CustomerID'].dropna().head(2).astype(str).tolist()
                    detected_pii_results.append({
                        "detect": "IC_NUMBER", # Or a more specific 'CUSTOMER_ID' if you define it
                        "column": "CustomerID",
                        "topData": top_ids,
                        "avgConfidence": 0.75
                    })

            except Exception as e:
                print(f"Error reading tabular file with pandas: {e}")
                # Fallback or error handling for invalid tabular file
                return jsonify({"error": "Failed to parse tabular file content"}), 400

        # Normalize confidence to 0.0-1.0 if detection library returns different range
        # Ensure 'start'/'end' are integers if applicable.
        final_review_data = []
        for item in detected_pii_results:
            normalized_confidence = item.get('confidence', item.get('avgConfidence', 0.0))
            if normalized_confidence > 1.0:
                normalized_confidence /= 100.0

            if file_type in ['Text file', 'Image file', 'Document file']:
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
                    "avgConfidence": normalized_confidence,
                    "ignore": False
                })

        # Store initial file metadata in TinyDB (before anonymization)
        # We need to find the partner_id to link files to partners
        partner_obj = partners_table.search(Partner.name == partner_name)
        partner_id_for_file = partner_obj[0]['id'] if partner_obj else None

        if not partner_id_for_file:
            return jsonify({"error": f"Partner '{partner_name}' not found for file storage"}), 404

        new_file_record = {
            'id': file_id,
            'partner_id': partner_id_for_file,
            'filename': filename,
            'type': file_type,
            'original_path': original_file_path,
            'anonymized_path': None,
            'state': 'Pending Review',
            'upload_date': datetime.now().isoformat(),
            'review_data': final_review_data, # Store the detection results for later 'proceed' action
            'auditLog': None,
            'reverse': [],
            'downloadLink': None
        }
        files_table.insert(new_file_record)
        print(f"File metadata stored in TinyDB: {file_id}")

        # Respond to frontend with the detected PII for review
        response_data = {
            "partner": partner_name,
            "filename": filename,
            "type": file_type,
            "review": final_review_data # This will be empty if no PII is detected or no logic is implemented
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
    print(f"Request Headers: {request.headers}")
    print(f"Request Content-Type: {request.content_type}")
    print(f"Request JSON Data: {request.get_json(silent=False)}")
    print("------------------------------------------\n")

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    partner_name = data.get('partner')
    filename = data.get('filename')
    file_type = data.get('type')
    reviewed_pii = data.get('review', []) # This is the array of PII with 'ignore' flags

    # Find the corresponding file record in TinyDB
    # We need a way to link the frontend's 'filename' and 'partner_name' back to a specific file_id
    # A more robust solution would be to pass the file_id from frontend after /upload
    # For now, let's assume filename+partner_name is unique enough for this conceptual stage.
    file_record = files_table.search(
        (File.filename == filename) &
        (File.state == 'Pending Review') # Ensure we're only processing pending files
    )
    if not file_record:
        return jsonify({"error": f"File '{filename}' not found or not in 'Pending Review' state."}), 404

    file_record = file_record[0] # Get the first (and hopefully only) matching record
    file_id = file_record['id']
    original_file_path = file_record['original_path']

    if not all([partner_name, filename, file_type, reviewed_pii is not None]):
        return jsonify({"error": "Missing required fields (partner, filename, type, review)"}), 400

    print(f"Proceeding anonymization for {filename} (Type: {file_type}) for partner {partner_name}")

    # --- CORE ANONYMIZATION LOGIC GOES HERE ---
    # This is where your friend would apply anonymization techniques.
    # Read the original file, apply changes based on reviewed_pii (ignoring flagged items).
    anonymized_file_content = ""
    reverse_info = [] # To store info needed for de-anonymization (e.g., original positions and encrypted data)
    detected_entities_summary = {} # For audit log

    try:
        with open(original_file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()

        # Iterate through reviewed_pii and apply anonymization
        # This is a highly simplified example. Real anonymization is complex.
        current_content = list(original_content) # Convert to list for mutable char array
        offset = 0 # Offset for maintaining character positions if content length changes
        for item in sorted(reviewed_pii, key=lambda x: x.get('start', 0)): # Sort by start position
            if not item.get('ignore', False):
                detect_type = item.get('detect')
                word = item.get('word')
                start = item.get('start')
                end = item.get('end')

                if start is not None and end is not None:
                    # Adjust start/end based on previous anonymizations (if characters are removed/added)
                    adjusted_start = start + offset
                    adjusted_end = end + offset

                    # --- Anonymization Strategy (Conceptual) ---
                    # For simplicity, let's replace with 'X's or a generic token
                    # In reality, this would be encryption or redaction
                    replacement_text = f"[[ANON_{detect_type}]]" # Placeholder for anonymized text
                    original_segment = original_content[start:end] # Original segment before any modification

                    # Conceptual Encryption (replace with actual encryption)
                    encrypted_segment = f"ENCRYPTED_{original_segment}" # Dummy encryption

                    # Update the current_content (conceptual replacement)
                    current_content[adjusted_start:adjusted_end] = list(replacement_text)

                    # Update offset for subsequent items
                    offset += len(replacement_text) - (end - start)

                    # Store reverse information for de-anonymization
                    reverse_info.append({
                        "original": {"start": start, "end": end}, # Original positions
                        "encrypt": {"start": adjusted_start, "end": adjusted_start + len(replacement_text)}, # Encrypted positions
                        "original_value": original_segment, # Store original value (highly sensitive, usually encrypted)
                        "encrypted_value": encrypted_segment # Store encrypted value
                    })

                detected_entities_summary[detect_type] = detected_entities_summary.get(detect_type, 0) + 1

        anonymized_file_content = "".join(current_content)

        # Save the anonymized file
        anonymized_filename = f"anonymized_{file_id}_{filename}"
        anonymized_file_path = os.path.join(app.config['ANONYMIZED_FILES_FOLDER'], anonymized_filename)
        with open(anonymized_file_path, 'w', encoding='utf-8') as f:
            f.write(anonymized_file_content)
        print(f"Anonymized file saved to: {anonymized_file_path}")

        # Update the file record in TinyDB
        files_table.update({
            'state': 'Anonymized',
            'anonymized_path': anonymized_file_path,
            'downloadLink': f'/download/{file_id}', # Example download link
            'auditLog': {
                "intendedFor": partner_name,
                "anonymizedMethod": "Encryption", # As per your spec
                "detectedEntitiesSummary": [{"entity": k, "count": v} for k, v in detected_entities_summary.items()]
            },
            'reverse': reverse_info # Store information for de-anonymization
        }, File.id == file_id)

        print(f"Successfully completed anonymization for {filename}. Returning 200 OK.")
        return jsonify({"message": "Anonymization process completed successfully", "file_id": file_id}), 200

    except Exception as e:
        print(f"An unexpected error occurred during anonymization: {e}")
        traceback.print_exc()
        # Optionally, update file state to 'Anonymization Failed'
        files_table.update({'state': 'Anonymization Failed'}, File.id == file_id)
        return jsonify({"error": f"Internal server error during anonymization: {str(e)}"}), 500


# Endpoint: /anonymize (POST) - To trigger anonymization from scratch or re-anonymize
# This endpoint seems designed for a simpler direct anonymization without prior review.
# If /proceed is for post-review, /anonymize could be for auto-anonymize.
# Or, if this is a toggle, it needs to check current state.
@app.route('/anonymize', methods=['POST'])
def direct_anonymize():
    print("\n--- Incoming POST Request to /anonymize ---")
    print(f"Request Form Data: {request.form}")
    print(f"Request Files: {request.files}")
    print("------------------------------------------\n")

    partner_name = request.form.get('partner')
    file = request.files.get('file')

    if not partner_name or not file:
        return jsonify({"error": "Partner name and file are required"}), 400

    filename = file.filename
    file_id = str(uuid.uuid4())
    file_type = get_file_type_from_extension(filename)

    # Save original file (or re-save if already uploaded)
    original_file_path = os.path.join(app.config['FILE_STORAGE_FOLDER'], f"{file_id}_{filename}")
    file.save(original_file_path)

    # Conceptual PII detection (similar to /upload, but might use partner's default settings)
    # This part would involve re-doing detection if this endpoint is meant for direct anonymization.
    # For now, let's assume it detects something.
    detected_pii_for_anonymize = [
        {"detect": "PERSON", "start": 0, "end": 10, "confidence": 0.9, "word": "Auto Name"},
    ]

    anonymized_file_content = "[[AUTOMATICALLY_ANONYMIZED_CONTENT]]" # Simplified for demo
    anonymized_filename = f"auto_anonymized_{file_id}_{filename}"
    anonymized_file_path = os.path.join(app.config['ANONYMIZED_FILES_FOLDER'], anonymized_filename)
    with open(anonymized_file_path, 'w', encoding='utf-8') as f:
        f.write(anonymized_file_content)

    # Generate audit log summary for auto-anonymization
    auto_audit_summary = {"PERSON": 1} # Dummy count

    # Store file record in TinyDB, mark as Anonymized
    partner_obj = partners_table.search(Partner.name == partner_name)
    partner_id_for_file = partner_obj[0]['id'] if partner_obj else None

    if not partner_id_for_file:
        return jsonify({"error": f"Partner '{partner_name}' not found for file storage"}), 404

    new_file_record = {
        'id': file_id,
        'partner_id': partner_id_for_file,
        'filename': filename,
        'type': file_type,
        'original_path': original_file_path,
        'anonymized_path': anonymized_file_path,
        'state': 'Anonymized',
        'upload_date': datetime.now().isoformat(),
        'review_data': detected_pii_for_anonymize, # Store detection results
        'auditLog': {
            "intendedFor": partner_name,
            "anonymizedMethod": "Encryption",
            "detectedEntitiesSummary": [{"entity": k, "count": v} for k, v in auto_audit_summary.items()]
        },
        'reverse': [{"original": {"start": 0, "end": 10}, "encrypt": {"start": 0, "end": len(anonymized_file_content)}, "original_value": "Auto Name", "encrypted_value": anonymized_file_content}],
        'downloadLink': f'/download/{file_id}'
    }
    files_table.insert(new_file_record)
    print(f"File {filename} directly anonymized and recorded.")
    return jsonify({"message": "File anonymized successfully", "file_id": file_id}), 200


# Endpoint: /denonymize (POST) - To de-anonymize a file
@app.route('/denonymize', methods=['POST'])
def direct_denonymize():
    print("\n--- Incoming POST Request to /denonymize ---")
    print(f"Request Form Data: {request.form}")
    print(f"Request Files: {request.files}")
    print("------------------------------------------\n")

    partner_name = request.form.get('partner')
    file = request.files.get('file') # Assuming file is sent back (e.g., the anonymized one)

    if not partner_name or not file:
        return jsonify({"error": "Partner name and file are required"}), 400

    filename = file.filename
    # In a real scenario, you'd identify the file_id from the filename or a hidden field
    # For now, let's assume you're operating on a known file_id that corresponds
    # to the anonymized file that was previously processed.
    # This also needs to retrieve 'reverse' info from TinyDB

    # Conceptual de-anonymization logic (inverse of anonymization)
    # This part would involve using the 'reverse' info stored in TinyDB to restore original content.
    deanonymized_file_content = "[[DEANONYMIZED_CONTENT]]" # Simplified for demo

    deanonymized_filename = f"deanonymized_{filename}"
    deanonymized_file_path = os.path.join(app.config['DEANONYMIZED_FILES_FOLDER'], deanonymized_filename)
    with open(deanonymized_file_path, 'w', encoding='utf-8') as f:
        f.write(deanonymized_file_content)

    # Update file record in TinyDB, mark as De-anonymized
    # You'd typically find the file record by `filename` and `partner_id` or a specific file_id
    # files_table.update({'state': 'De-anonymized', 'deanonymized_path': deanonymized_file_path}, File.id == SOME_FILE_ID)
    print(f"File {filename} de-anonymized and recorded.")
    return jsonify({"message": "File de-anonymized successfully"}), 200


# Endpoint: /api/files/<file_id>/auditlog (GET) - Get audit log for a specific file
@app.route('/api/files/<file_id>/auditlog', methods=['GET'])
def get_file_auditlog(file_id):
    print(f"Fetching audit log for file_id: {file_id}")
    file_record = files_table.get(File.id == file_id)

    if file_record and file_record.get('auditLog'):
        # Frontend expects 'filename', 'fileType' in auditData object
        audit_data_response = {
            "filename": file_record['filename'],
            "fileType": file_record['type'],
            **file_record['auditLog']
        }
        return jsonify(audit_data_response), 200
    else:
        return jsonify({"error": "Audit log not found for this file"}), 404

# Endpoint: /download/<file_id> (GET) - To download anonymized/de-anonymized file
@app.route('/download/<file_id>', methods=['GET'])
def download_file(file_id):
    file_record = files_table.get(File.id == file_id)
    if not file_record:
        return jsonify({"error": "File not found"}), 404

    # Determine which file to download based on state, preference for anonymized
    file_to_send_path = None
    if file_record.get('state') == 'Anonymized' and file_record.get('anonymized_path'):
        file_to_send_path = file_record['anonymized_path']
    elif file_record.get('state') == 'De-anonymized' and file_record.get('deanonymized_path'):
        file_to_send_path = file_record['deanonymized_path']
    elif file_record.get('original_path'): # Fallback to original if no processed version
        file_to_send_path = file_record['original_path']

    if file_to_send_path and os.path.exists(file_to_send_path):
        directory = os.path.dirname(file_to_send_path)
        filename = os.path.basename(file_to_send_path)
        return send_from_directory(directory, filename, as_attachment=True)
    else:
        return jsonify({"error": "File not found on server or path invalid"}), 404

# Endpoint: /api/files/<file_id>/state (PUT) - To toggle file state (Anonymized/De-anonymized)
# This assumes the anonymize/deanonymize functions handle the actual file processing
# and this PUT merely updates the state and switches which file is considered "active".
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
        return jsonify({"message": f"File already in {new_state} state."}), 200

    # Simulate actual de-anonymization/re-anonymization if state changes
    # In a real scenario, you'd trigger the /anonymize or /denonymize functions here
    # or have the logic directly embedded if it's simple state change based on existing files.
    if new_state == 'De-anonymized':
        print(f"Toggling file {file_id} to De-anonymized. (Conceptual de-anonymization triggered)")
        # Here, you would call your internal de-anonymization logic
        # For demo: check if original_path exists and is accessible
        if file_record.get('original_path') and os.path.exists(file_record['original_path']):
            # For this simplified toggle, we assume the de-anonymized file is essentially the original
            # or a restored version. You might need to generate it if not pre-made.
            deanonymized_file_path = os.path.join(app.config['DEANONYMIZED_FILES_FOLDER'], f"deanonymized_{file_id}_{file_record['filename']}")
            # Simply copy the original file to de-anonymized folder for demo
            import shutil
            shutil.copy(file_record['original_path'], deanonymized_file_path)

            files_table.update({
                'state': new_state,
                'deanonymized_path': deanonymized_file_path,
                'downloadLink': f'/download/{file_id}' # Update download link to point to this state
            }, File.id == file_id)
        else:
            return jsonify({"error": "Original file not found for de-anonymization"}), 500

    elif new_state == 'Anonymized':
        print(f"Toggling file {file_id} to Anonymized. (Conceptual re-anonymization triggered)")
        # Similar to above, if you have a pre-anonymized version or need to re-anonymize.
        if file_record.get('anonymized_path') and os.path.exists(file_record['anonymized_path']):
            files_table.update({
                'state': new_state,
                'downloadLink': f'/download/{file_id}' # Update download link
            }, File.id == file_id)
        else:
            return jsonify({"error": "Anonymized file not found to revert to"}), 500


    print(f"File {file_id} state updated to {new_state}.")
    return jsonify({"message": f"File state updated to {new_state}"}), 200


if __name__ == '__main__':
    from datetime import datetime # Import datetime here as well for use in main block
    app.run(debug=True, port=5000)