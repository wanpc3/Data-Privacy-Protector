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
    jsonify,
    send_file
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
import numpy as np
import msoffcrypto
import pyzipper
import pprint
import os
import io

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
    regex=(
                r"\b(?:"
                # Address-related terms
                r"Jalan|Lorong|Taman|Persiaran|Lebuh|Lebuhraya|Kampung|Kg|Lrg|Blok|"
                r"Desa|Bandar|Daerah|Poskod|Alamat|Pekan|Fasa|Seksyen|Lot|No"
                r")\b.*?\b(?:"
                # States, Federal Territories, Cities
                r"Selangor|Johor|Kedah|Kelantan|Melaka|Negeri Sembilan|Pahang|"
                r"Penang|Pulau Pinang|Perak|Perlis|Sabah|Sarawak|Terengganu|"
                r"Kuala Lumpur|Putrajaya|Labuan|"
                r"Shah Alam|Ipoh|Seremban|George Town|Alor Setar|Kuantan|"
                r"Johor Bahru|Kota Bharu|Kuching|Miri|Kota Kinabalu|Butterworth"
                r")\b"
            ),
            score=1.0
)

class MalaysiaAddressRecognizer(PatternRecognizer):
    def __init__(self):
        super().__init__(
            supported_entity="LOCATION",
            patterns=[address_pattern],
            name="Malaysia Address Recognizer",
        )

analyzer = AnalyzerEngine()
analyzer.registry.add_recognizer(MalaysiaPhoneRecognizer())
analyzer.registry.add_recognizer(GenericPassportRecognizer())
analyzer.registry.add_recognizer(MalaysianICRecognizer())
analyzer.registry.recognizers.insert(0, MalaysiaAddressRecognizer())
anonymizer = AnonymizerEngine()
denonymizer = DeanonymizeEngine()

#===================================================================
# UNITS
#==================================================================

def normalize_values(values):
    first = values[0]
    
    if isinstance(first, np.integer):
        return [int(v) for v in values]
    elif isinstance(first, np.floating):
        return [float(v) for v in values]
    return values

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
    #1) Open file to analyze
    path = os.path.join("temp", job["filename"])
    with open(path, "r", encoding="utf-8") as f:
        TxtFile = f.read()
    
    #---------------------------------------------------------
    # 2) Get partner detection list
    Partner = Query()
    partner = db.search(Partner.partner == job["partner"])[0]
    
    # --------------------------------------------------------
    #3) Analyze

    results = analyzer.analyze(
            text=TxtFile,
            language="en",
            entities=partner["detection"],
            score_threshold=0.3
        )

    #-----------------------------------------------------
    #4) Generate review report

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


def analyzeTable(job):
    #0) Check partner from database
    Partner = Query()
    partner = db.search(Partner.partner == job["partner"])[0]

    #-----------------------------------------------------------------------
    #1) Open file to analyze
    ext = os.path.splitext(job["filename"])[1].lower()
    path = os.path.join("temp", job["filename"])

    if ext in {".xls", ".xlsx"}:
        with open(path, "rb") as f:
            office_file = msoffcrypto.OfficeFile(f)

            if office_file.is_encrypted():
                office_file.load_key(password=partner["password"])
                decrypted = io.BytesIO()
                office_file.decrypt(decrypted)
                df = pd.read_excel(decrypted, engine="openpyxl")
            else:
                df = pd.read_excel(path)
    else:
        df = pd.read_csv(path)
    
    #---------------------------------------------
    #2 Sample data for analysis

    for col in df.columns:
        series = df[col][df[col].notna() & (df[col].astype(str).str.strip() != "")]
        if series.empty:
            continue

        n = len(series)
        thirds = n // 3

        # Index segments
        top_indices = series.iloc[:thirds].index
        mid_indices = series.iloc[thirds:2*thirds].index
        bottom_indices = series.iloc[2*thirds:].index

        def get_random_nonempty(indices):
            subset = series.loc[indices].dropna()
            if not subset.empty:
                return subset.sample(1).values[0]
            return None

        # Sampled values
        top_val = get_random_nonempty(top_indices)
        mid_val = get_random_nonempty(mid_indices)
        bot_val = get_random_nonempty(bottom_indices)

        values = normalize_values([top_val, mid_val, bot_val])
        job["review"].append({
            "column": col,
            "words": values,
            "results":[]
        })
    
    #-------------------------------------------------------
    #4) Analyze

    for data in job["review"]:
        vals = data["words"]

        for v in vals:
            analyzeResult = analyzer.analyze(
                text=str(v),
                language="en",
                entities=partner["detection"],
                score_threshold=0.3
            )

            # May detect multiple entity we only take the highest score
            if any(analyzeResult):
                best = max(analyzeResult, key=lambda r: r.score)
                data["results"].append({
                    "entity": best.entity_type,
                    "score": best.score,
                })

    # Clean data. Remove none-PII column
    # Find majority entity and avg the score
    job["review"] = [entry for entry in job["review"] if len(entry.get("results", [])) > 1]

    for data in job["review"]:
        result = data["results"]
        entity_counts = Counter([r["entity"] for r in result if r is not None])
        majority_entity = entity_counts.most_common(1)[0][0]
        matching_scores = [r["score"] for r in result if r["entity"] == majority_entity]
        avg_score = sum(matching_scores) / len(matching_scores)
        data["entity"] = majority_entity.removeprefix("US_")
        data["confidence"] = int(avg_score * 100)
    
    for entry in job["review"]:
        entry["ignore"] = entry["confidence"] < 75
        if "results" in entry:
            del entry["results"]

#==================================================================
# Process Function
#==================================================================

def processTxt(data):
    
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

    #------------------------------------------------------------
    # 2) Open the file to be encrypt
    inpath = os.path.join("temp", data["filename"])
    with open(inpath, "r", encoding="utf-8") as f:
        TxtFile = f.read()
    
    #-----------------------------------------------------------
    #3) Get Encryption key for that partner in database
    Partner = Query()
    partner = db.search(Partner.partner == data["partner"])[0]
    KEY = hashlib.sha256(partner["key"].encode()).digest()

    #-----------------------------------------------------------
    #4) Encrypt...
    anonyResult = anonymizer.anonymize(
	    text=TxtFile, 
	    analyzer_results=analyzeResult, 
	    operators={"DEFAULT" : OperatorConfig ("encrypt", {"key": KEY})}
    )

    #---------------------------------------------------------
    # 5) Save encrypted data(same Filename) & delete old file
    outpath = os.path.join("static/upload", data["filename"])
    with open(outpath, "w", encoding="utf-8") as outFile:
        outFile.write(anonyResult.text)
    os.remove(inpath)

    #--------------------------------------------------------------
    # 6) Update database
    encrypt = []
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

def processTable(data):
    #3) Get key & password that partner in database
    Partner = Query()
    partner = db.search(Partner.partner == data["partner"])[0]
    KEY = hashlib.sha256(partner["key"].encode()).digest()

    #-------------------------------------------------------------
    # 1) For table, need entity & column name to anonymize
    log = []
    for entry in data.get("review", []):
        if not entry.get("ignore", False):
            log.append({
                "column": entry["column"],
                "detect": entry["entity"]
            })

    #------------------------------------------------------------
    # 2) Open the Tabular file to be encrypt
    ext = os.path.splitext(data["filename"])[1].lower()
    inpath = os.path.join("temp", data["filename"])

    if ext in {".xls", ".xlsx"}:
        with open(inpath, "rb") as f:
            office_file = msoffcrypto.OfficeFile(f)

            if office_file.is_encrypted():
                office_file.load_key(password=partner["password"])
                decrypted = io.BytesIO()
                office_file.decrypt(decrypted)
                df = pd.read_excel(decrypted, engine="openpyxl")
            else:
                df = pd.read_excel(inpath)
    else:
        df = pd.read_csv(inpath)


    #-----------------------------------------------------------
    #4) Encrypt columns
    target_columns = [entry["column"] for entry in log]

    for col in target_columns:
        if col in df.columns:
            for i, value in df[col].items():
                if pd.notna(value) and str(value).strip():
                    value = str(value)
                    anonyResult = anonymizer.anonymize(
                        text=value, 
                        analyzer_results= [RecognizerResult(
                                            entity_type="PERSON",
                                            start=0,end=len(value) - 1,
                                            score=1.0
                                            )],
                        operators={"DEFAULT" : OperatorConfig ("encrypt", {"key": KEY})}
                    )
                    df.at[i, col] = anonyResult.text
    
    #---------------------------------------------------------
    # 5) Save encrypted data(same Filename) & delete old file
    outpath = os.path.join("static/upload", data["filename"])
    if ext in {".xls", ".xlsx"}:
        df.to_excel(outpath, index=False)
    else:
        df.to_csv(outpath, index=False)
    os.remove(inpath)

    #--------------------------------------------------------------
    # 6) Update database
    file = {
        "filename": data["filename"],
        "type"   : data["type"],
        "anonymized": True,
        "download": outpath,
        "log": log,
    }

    db.update(
        lambda record: record["files"].append(file),
        doc_ids=[partner.doc_id]
    )
    
#=================================================================
# Deanonymize
#================================================================

def deanonymizeTxt(data):
    #1) Open file that want to be decrypted
    path = data["file"]["download"]
    with open(path, "r", encoding="utf-8") as f:
        TxtFile = f.read()
    
    #----------------------------------------------------------
    #2) Manually generate OperatorResult for reversal
    reverse = [
        OperatorResult(
            entity_type="PERSON",
            start=item["start"],
            end=item["end"],
            text=TxtFile[item["start"]:item["end"]],
            operator="encrypt"
        )
        for item in data["file"]["encrypt"]
    ]

    #-------------------------------------------------------------
    #3 Preceed to decrypt (de-anonymize)
    KEY = hashlib.sha256(data["partner"]["key"].encode()).digest()
    deanonyResult = denonymizer.deanonymize(
        text=TxtFile,
        entities=reverse,
        operators={"DEFAULT" : OperatorConfig ("decrypt", {"key": KEY})}
    )

    #----------------------------------------------------------------------------
    #4 Override the file
    with open(path, "w", encoding="utf-8") as outFile:
        outFile.write(deanonyResult.text)
    
    #--------------------------------------------------------------------------
    #5 Update database to say this file state change to de-anonymize
    files = data["partner"]["files"]
    for idx, f in enumerate(files):
        if f["filename"] == data["file"]["filename"]:
            files[idx]["anonymized"] = False
            break
    db.update({"files": files}, doc_ids=[data["partner"].doc_id])

def deanonymizeTable(data):
    #1) Open file
    path = data["file"]["download"]

    ext = os.path.splitext(data["file"]["filename"])[1].lower()
    if ext in {".xls", ".xlsx"}:
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path)
    
    #-------------------------------------------------------------
    #2 Preceed to decrypt (de-anonymize)
    target_columns = [entry["column"] for entry in data["file"]["log"]]
    KEY = hashlib.sha256(data["partner"]["key"].encode()).digest()

    for col in target_columns:
        if col in df.columns:
            for i, value in df[col].items():
                if pd.notna(value) and str(value).strip():
                    value = str(value)
                    deanonyResult = denonymizer.deanonymize(
                        text=value,
                        entities=[OperatorResult(
                                        entity_type="PERSON",
                                        start=0,end=len(value) - 1,
                                        text=value,
                                        operator="encrypt")],
                        operators={"DEFAULT" : OperatorConfig ("decrypt", {"key": KEY})}
                    )
                    df.at[i, col] = deanonyResult.text
    
    #----------------------------------------------------------
    #3) Override the file
    if ext in {".xls", ".xlsx"}:
        df.to_excel(path, index=False)
    else:
        df.to_csv(path, index=False)

    #------------------------------------------------------------
    #4 Update database to say this file state change to de-anonymize
    files = data["partner"]["files"]
    for idx, f in enumerate(files):
        if f["filename"] == data["file"]["filename"]:
            files[idx]["anonymized"] = False
            break
    db.update({"files": files}, doc_ids=[data["partner"].doc_id]) 


#=================================================================
# Anonymize
#================================================================

def anonymizeTxt(data):
    #1) Open file that want to be decrypted
    path = data["file"]["download"]
    with open(path, "r", encoding="utf-8") as f:
        TxtFile = f.read()

    #--------------------------------------------------------
    #2) Manually generate RecognizerResult for reversal
    analyzeResult = [
        RecognizerResult(
            entity_type="PERSON",
            start=item["start"],
            end=item["end"],
            score=1.0
        )
        for item in data["file"]["original"]
    ]

    #-------------------------------------------------------------
    #4 Preceed to encrypt (re-anonymize)
    KEY = hashlib.sha256(data["partner"]["key"].encode()).digest()
    anonyResult = anonymizer.anonymize(
        text=TxtFile, 
        analyzer_results=analyzeResult, 
        operators={"DEFAULT" : OperatorConfig ("encrypt", {"key": KEY})}
    )

    #----------------------------------------------------------------------------
    #4 Override the file
    with open(path, "w", encoding="utf-8") as outFile:
        outFile.write(anonyResult.text)
    
    #--------------------------------------------------------------------------
    #5 Update database to say this file state change to de-anonymize
    files = data["partner"]["files"]
    for idx, f in enumerate(files):
        if f["filename"] == data["file"]["filename"]:
            files[idx]["anonymized"] = True
            break
    db.update({"files": files}, doc_ids=[data["partner"].doc_id])

def anonymizeTable(data):
    #1) Open file
    path = data["file"]["download"]

    ext = os.path.splitext(data["file"]["filename"])[1].lower()
    if ext in {".xls", ".xlsx"}:
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path)
    
    #-------------------------------------------------------------
    #2 Preceed to encrypt (re-anonymize)
    target_columns = [entry["column"] for entry in data["file"]["log"]]
    KEY = hashlib.sha256(data["partner"]["key"].encode()).digest()

    for col in target_columns:
        if col in df.columns:
            for i, value in df[col].items():
                if pd.notna(value) and str(value).strip():
                    value = str(value)
                    anonyResult = anonymizer.anonymize(
                        text=value, 
                        analyzer_results= [RecognizerResult(
                                            entity_type="PERSON",
                                            start=0,end=len(value) - 1,
                                            score=1.0
                                            )],
                        operators={"DEFAULT" : OperatorConfig ("encrypt", {"key": KEY})}
                    )
                    df.at[i, col] = anonyResult.text
    
    #----------------------------------------------------------
    #3) Override the file
    if ext in {".xls", ".xlsx"}:
        df.to_excel(path, index=False)
    else:
        df.to_csv(path, index=False)

    #------------------------------------------------------------
    #4 Update database to say this file state change to de-anonymize
    files = data["partner"]["files"]
    for idx, f in enumerate(files):
        if f["filename"] == data["file"]["filename"]:
            files[idx]["anonymized"] = True
            break
    db.update({"files": files}, doc_ids=[data["partner"].doc_id])  


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
            analyzeTable(job)

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
            processTxt(data)
        elif data["type"] == "Tabular File":
            processTable(data)
         
        return "OK", 200

    except Exception as e:
        print(e)
        return "Server Error", 500

@app.route("/deanonymize", methods=["POST"])
def deanony():
    try:
        meta = {
            "partner":   request.form.get("partner"),
            "filename":  request.form.get("filename"),
        }
        if not all(meta.values()):
            return "Bad Request", 400

        #1) Get partner object, with that get file object from database
        Partner = Query()
        partner = db.search(Partner.partner == meta["partner"])[0]

        file = next((f for f in partner.get("files", []) if f.get("filename") == meta["filename"]), None)

        data = {
            "partner": partner,
            "file": file
        }
        if file["type"] == "Text File":
            deanonymizeTxt(data)
        elif file["type"] == "Tabular File":
            deanonymizeTable(data)

        return "OK", 200

    except Exception as e:
        print("Error:", e)
        return "Server Error", 500

@app.route("/anonymize", methods=["POST"])
def anony():
    try:
        meta = {
            "partner":   request.form.get("partner"),
            "filename":  request.form.get("filename"),
        }
        if not all(meta.values()):
            return "Bad Request", 400

        #1) Get partner object, with that get file object from database
        Partner = Query()
        partner = db.search(Partner.partner == meta["partner"])[0]

        file = next((f for f in partner.get("files", []) if f.get("filename") == meta["filename"]), None)

        data = {
            "partner": partner,
            "file": file
        }
        if file["type"] == "Text File":
            anonymizeTxt(data)
        elif file["type"] == "Tabular File":
            anonymizeTable(data)

        return "OK", 200

    except Exception as e:
        print("Error:", e)
        return "Server Error", 500

@app.route("/download", methods=["POST"])
def download_zip():
    try:
        data = request.form.get("partner")
        if not data:
            return "Bad Request", 400

        print("==== run0 =====")
        Partner = Query()
        partner = db.search(Partner.partner == data)[0]

        print("==== run1 =====")
        files = [file["download"] for file in partner.get("files", [])]
        if not files:
            return "No files uploaded", 400
        
        print("==== run2 =====")
        zip_buffer = io.BytesIO()
        with pyzipper.AESZipFile(zip_buffer, 'w', compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as zf:
            zf.setpassword(partner["password"].encode())
            for path in files:
                arcname = os.path.basename(path)
                zf.write(path, arcname=arcname)

        print("==== run3 =====")
        zip_buffer.seek(0)
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"{partner["partner"]}.zip"
        )
    
    except Exception as e:
        print("Error:", e)
        return "Server Error", 500


#=================================================================

if __name__ == "__main__":
    app.run(debug=True)
