#===================================================================
# IMPORTS
#===================================================================
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from tinydb import TinyDB, Query
import os

#===================================================================
#CONSTANT
#==================================================================

app = Flask(__name__)

#==================================================================
# INIT
#==================================================================

db = TinyDB('db.json')

#==================================================================
# ROUTES
#=================================================================

@app.route("/")
def index():
    return jsonify(db.all()), 200

@app.route("/create", methods=["POST"])
def create():
    try:
        profile = {
            "partner":   request.form.get("partner"),
            "key":       request.form.get("key"),
            "password":  request.form.get("password"),
            "detection": request.form.getlist("detection")
        }
        iconFile = request.files.get("icon")

        # Validation: check all fields and file presence
        if (
            not all(profile.values()) or
            not iconFile or
            not iconFile.filename.strip()
        ):
            return "Bad Request", 400

        # Validate extension
        ext = os.path.splitext(iconFile.filename)[1].lower()
        if ext not in {".jpg", ".jpeg", ".png"}:
            return "Unsupported file type", 400
        
        # Save file
        path = os.path.join("static/icon", secure_filename(profile["partner"] + ext))
        iconFile.save(path)
        profile["icon"] = path
        
        #Update new partner in db
        profile["uploads"] = []
        db.insert(profile)
        return "OK", 200
    
    except Exception as e:
        print("Error:", e)
        return "Server Error", 500


#@app.route("/upload", methods=["POST"])
#def upload():
#    try:
#        if 'file' not in request.files:
#            return "No file part", 400

#        file = request.files['file']

#        if file.filename == '':
#            return "No selected file", 400

#        # Extract extension without dot and normalize case
#        extension = os.path.splitext(file.filename)[1].lstrip('.').lower()

#        if extension not in ALLOWED_EXTENSION:
#            return "File type is not supported", 400

#        file.save(os.path.join("upload", file.filename))
#        return "OK", 200

#    except Exception as e:
#        print(e)
#        return "Server Error", 500


#=================================================================

if __name__ == "__main__":
    app.run(debug=True)
