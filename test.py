from collections import defaultdict
from presidio_anonymizer.entities import (
    RecognizerResult,
    OperatorResult,
    OperatorConfig
)

data = {
    "partner": "TestPartner",
    "filename": "Credit_Score.txt",
    "type": "Text File",
    "review": [
        {
            "detect": "PERSON",
            "start": 16,
            "end": 21,
            "confidence": 1.0,
            "word": "Muhammad Zain",
            "ignore": True
        },
        {
            "detect": "CREDIT_CARD",
            "start": 46,
            "end": 58,
            "confidence": 0.6,
            "word": "Muhammad Zain",
            "ignore": False
        },
        {
            "detect": "LOCATION",
            "start": 11,
            "end": 19,
            "confidence": 0.9,
            "word": "Kuala Lumpur",
            "ignore": False
        },
        {
            "detect": "LOCATION",
            "start": 21,
            "end": 30,
            "confidence": 0.85,
            "word": "Cyberjaya",
            "ignore": False
        }
    ]
}

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

print ("\n\n========================")
for o in original:
	print(o)

print ("\n\n========================")
for a in analyzeResult:
	print(a)