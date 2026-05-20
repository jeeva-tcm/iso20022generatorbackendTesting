import urllib.request
import json

url = "http://127.0.0.1:8001/bulk-generate"
data = {
    "message_type": "pacs.004.001.09",
    "count": 5,
    "selected_blocks": [
        "instructing_agent",
        "instructed_agent",
        "debtor_agent",
        "creditor_agent",
        "ultimate_debtor",
        "ultimate_creditor",
        "charges_information"
    ]
}

req = urllib.request.Request(
    url,
    data=json.dumps(data).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)

try:
    with urllib.request.urlopen(req) as response:
        res = json.loads(response.read().decode("utf-8"))
        print("Success! Status:", res.get("status"))
        print("Generated files:", len(res.get("messages", [])))
        for i, msg in enumerate(res.get("messages", [])[:2]):
            print(f"\nMessage {i+1} preview:")
            xml = msg.get("xml", "")
            # Find all PstlAdr
            idx = 0
            while True:
                idx = xml.find("<PstlAdr>", idx)
                if idx == -1:
                    break
                end = xml.find("</PstlAdr>", idx)
                print(xml[idx:end+10])
                idx = end + 10
except Exception as e:
    print("Failed with error:", str(e))
    # Read the error body if available
    if hasattr(e, "read"):
        print("Error body:", e.read().decode("utf-8"))
