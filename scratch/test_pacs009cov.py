import requests
from app.services.validator import ISOValidator

validator = ISOValidator(xsd_dir='xsds/extracted')

url = "http://127.0.0.1:8001/bulk-generate"
payload = {
    "message_type": "pacs.009.001.08 COV",
    "count": 50,
    "selected_blocks": [
        "instructing_agent", "instructed_agent", "debtor", "debtor_agent",
        "creditor", "creditor_agent", "ultimate_debtor", "ultimate_creditor"
    ]
}

print("Generating 50 pacs.009 COV...")
resp = requests.post(url, json=payload)
if resp.status_code != 200:
    print("API Error:", resp.text)
    exit(1)

data = resp.json()
success = 0
for i, xml in enumerate(data.get("messages", [])):
    report = validator.validate(xml, "pacs.009")
    if report.is_valid:
        success += 1
    else:
        print(f"Failed {i}:")
        for err in report.issues:
            print("  ", err.issue_name, err.message)

print(f"Valid: {success}/50")
