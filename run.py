#===================================================================
# IMPORTS
#===================================================================
from presidio_analyzer import (
    Pattern,
    PatternRecognizer,
    RecognizerRegistry,
    AnalyzerEngine,
)
from flask import (
    Flask, 
    request, 
    jsonify
)
from presidio_anonymizer.entities import (
    RecognizerResult,
    OperatorResult,
    OperatorConfig
)
from presidio_anonymizer import AnonymizerEngine, DeanonymizeEngine
from collections import Counter, defaultdict
from werkzeug.utils import secure_filename
from tinydb import TinyDB, Query
import hashlib
import pandas as pd
import pprint
import os

#==================================================================
# TUNING PII ANALYZER
#==================================================================

malaysia_phone_pattern = Pattern(
    name="malaysia_phone_pattern",
    regex=r"(?:\+60|0)1\d{1,2}[-\s]?\d{7,8}",
    score=0.9
)

class MalaysiaPhoneRecognizer(PatternRecognizer):
    def __init__(self):
        super().__init__(
            supported_entity="PHONE_NUMBER",
			patterns=[malaysia_phone_pattern],
			context=["WhatsApp", "mobile", "tel", "telefon", "nombor", "hp", "handphone", "hubungi"],
            name="Malaysia Phone Recognizer",
        )

passport_pattern = Pattern(
    name="non_malaysian_passport_pattern",
    regex=r"\b[A-Z]\d{7,8}\b",
    score=0.9
)

class GenericPassportRecognizer(PatternRecognizer):
    def __init__(self):
        super().__init__(
            supported_entity="US_PASSPORT",
            patterns=[passport_pattern],
            name="Generic Passport Recognizer",
        )

ic_pattern = Pattern(
    name="malaysian_ic_pattern",
    regex=r"\b\d{6}-\d{2}-\d{4}\b",
    score=0.9
)

IC_CONTEXT = [
    "IC",
    "IC Number",
    "National ID",
    "Identification Number",
    "NRIC Card",
    "MyKad",
    "Malaysian IC",
    "No. KP",
    "ID No.",
    "ID Number",
    "Identification Card",
    "Personal ID",
    "Citizen ID"
]

class MalaysianICRecognizer(PatternRecognizer):
    def __init__(self):
        super().__init__(
            supported_entity="IC_NUMBER",
            name="Malaysian IC Recognizer",
            patterns=[ic_pattern],
            context=IC_CONTEXT
        )

address_pattern = Pattern(
    name="malaysia_address_pattern",
    regex=r"\b(?:Jalan|Lorong|Taman|Persiaran|Lebuh|Kg|Kampung|Lrg|Blok)\b.*",
    score=1.0,
)

class MalaysiaAddressRecognizer(PatternRecognizer):
    def __init__(self):
        super().__init__(
            supported_entity="LOCATION",
            patterns=[address_pattern],
            name="Malaysia Address Recognizer",
            context=[
                # 🗺️ States
                "Selangor", "Johor", "Kedah", "Kelantan", "Melaka",
                "Negeri Sembilan", "Pahang", "Penang", "Pulau Pinang",
                "Perak", "Perlis", "Sabah", "Sarawak", "Terengganu",
                # 🏙️ Federal Territories
                "Kuala Lumpur", "Putrajaya", "Labuan",
                # 🏘️ Address/road-related terms
                "Jalan", "Lorong", "Taman", "Persiaran", "Lebuh", "Lebuhraya",
                "Kampung", "Kg", "Lrg", "Blok", "Desa", "Bandar", "Daerah",
                "Poskod", "Alamat", "Pekan", "Fasa", "Seksyen", "Lot", "No",
                # 📍 Cities (sample)
                "Shah Alam", "Ipoh", "Seremban", "George Town", "Alor Setar",
                "Kuantan", "Johor Bahru", "Kota Bharu", "Kuching", "Miri",
                "Kota Kinabalu", "Butterworth", "Putrajaya", "Labuan",
            ],
        )

analyzer = AnalyzerEngine()
analyzer.registry.add_recognizer(MalaysiaPhoneRecognizer())
analyzer.registry.add_recognizer(GenericPassportRecognizer())
analyzer.registry.add_recognizer(MalaysianICRecognizer())
analyzer.registry.add_recognizer(MalaysiaAddressRecognizer())
anonymizer = AnonymizerEngine()
denonymizer = DeanonymizeEngine()

#===================================================================
#CONSTANT
#==================================================================


#===================================================================
# INIT
#==================================================================

app = Flask(__name__)
db = TinyDB('db.json')

os.makedirs("static/icon", exist_ok=True)
os.makedirs("static/upload", exist_ok=True)
os.makedirs("temp", exist_ok=True)

#==================================================================
# Analyze Function
#==================================================================

def analyzeTxt(job):
    with open(f"./temp/{job["filename"]}", "r", encoding="utf-8") as f:
        TxtFile = f.read()
    
    Partner = Query()
    partner = db.search(Partner.partner == job["partner"])[0]
    
    results = analyzer.analyze(
            text=TxtFile,
            language="en",
            entities=partner["detection"],
            score_threshold=0.3
        )

    for r in results:
        new_review = {
            "detect": r.entity_type.removeprefix("US_"),
            "start": r.start,
            "end": r.end,
            "confidence": int(r.score * 100),
            "word": TxtFile[r.start : r.end]
        }
        new_review["ignore"] = new_review["confidence"] < 75
        job["review"].append(new_review)
            
#==================================================================
# Process Function
#==================================================================

def processTxtFile(data):
    
    #-------------------------------------------------------------
    # 1) Extract data to manually build analyzerResult-
    original = []
    for entry in data.get("review", []):
        if not entry.get("ignore", False):
            original.append({
                "start": entry["start"],
                "end": entry["end"]
            })
    original.sort(key=lambda x: x["start"])

    analyzeResult = [
        RecognizerResult(
            entity_type="PERSON",
            start=item["start"],
            end=item["end"],
            score=1.0
        )
        for item in original
    ]

    print("=== Reach Here 2===")
    #------------------------------------------------------------
    # 2) Open the file to be encrypt
    inpath = os.path.join("temp", data["filename"])
    with open(inpath, "r", encoding="utf-8") as f:
        TxtFile = f.read()
    
    print("=== Reach Here 3===")
    #-----------------------------------------------------------
    #3) Get Encryption key for that partner in database
    Partner = Query()
    partner = db.search(Partner.partner == data["partner"])[0]
    KEY = hashlib.sha256(partner["key"].encode()).digest()

    print("=== Reach Here 4===")
    #-----------------------------------------------------------
    #4) Encrypt...
    anonyResult = anonymizer.anonymize(
	    text=TxtFile, 
	    analyzer_results=analyzeResult, 
	    operators={"DEFAULT" : OperatorConfig ("encrypt", {"key": KEY})}
    )

    print("=== Reach Here 5===")
    #---------------------------------------------------------
    # 5) Save encrypted data(same Filename) & delete old file
    outpath = os.path.join("static/upload", data["filename"])
    with open(outpath, "w", encoding="utf-8") as outFile:
        outFile.write(anonyResult.text)
    os.remove(inpath)

    print("=== Reach Here 6===")
    #--------------------------------------------------------------
    # 6) Update database
    encrypt = []

    print("=== Confirmation ===")
    print(type(anonyResult.items[0]))
    for item in anonyResult.items:
        encrypt.append({"start": item.start, "end": item.end})
    encrypt.sort(key=lambda x: x["start"])

    # Log summary
    counter = defaultdict(int)
    for item in data.get("review", []):
        if not item.get("ignore", False):
            counter[item["detect"]] += 1
    log = [{"detect": k, "total": v} for k, v in counter.items()]

    file = {
        "filename": data["filename"],
        "type"   : data["type"],
        "anonymized": True,
        "download": outpath,
        "log": log,
        "original": original,
        "encrypt": encrypt
    }

    db.update(
        lambda record: record["files"].append(file),
        doc_ids=[partner.doc_id]
    )

    print("=== Reach Here 7===")

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
        profile["files"] = []
        db.insert(profile)
        return "OK", 200
    
    except Exception as e:
        print("Error:", e)
        return "Server Error", 500

@app.route("/upload", methods=["POST"])
def upload():
    try:
        partner = request.form.get("partner")
        file = request.files.get("file")

        if (
            not partner or 
            not file or
            not file.filename.strip()
        ):
            return "Bad Request", 400

        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in {".txt", ".csv", ".xls", ".xlsx"}:
            return "Unsupported file type", 400

        filename = secure_filename(file.filename)
        file.save(os.path.join("temp", filename))

        job = {
            "partner": partner,
            "filename": filename,
            "review": []
        }

        if ext == ".txt":
            job["type"] = "Text File"
            analyzeTxt(job)
        elif ext in {".csv", ".xls", ".xlsx"}:
            job["type"] = "Tabular File"

        return jsonify(job), 200

    except Exception as e:
        print(e)
        return "Server Error", 500

@app.route("/process", methods=["POST"])
def process():
    try:
        data = request.get_json(force=True)

        required_fields = {"partner", "filename", "type", "review"}
        if not all(field in data for field in required_fields):
            return "Bad Request", 400
        
        if data["type"] == "Text File":
            print("=== Reach Here 1===")
            processTxtFile(data)
        elif data["type"] == "Tabular File":
            pass
         
        return "OK", 200

    except Exception as e:
        print(e)
        return "Server Error", 500

#=================================================================

if __name__ == "__main__":
    app.run(debug=True)
