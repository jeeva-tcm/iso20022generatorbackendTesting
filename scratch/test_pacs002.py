import requests

url = "http://127.0.0.1:8001/bulk-generate"
payload = {
    "message_type": "pacs.002",
    "count": 5,
    "selected_blocks": ["instructing_agent", "instructed_agent", "debtor", "creditor"]
}
resp = requests.post(url, json=payload, timeout=120)
data = resp.json()
msgs = data.get("messages", [])
print(f"Status: {resp.status_code}, Messages: {len(msgs)}")
if msgs:
    # Check BAH BIC matching in first message
    from lxml import etree
    root = etree.fromstring(msgs[0].encode("utf-8"))
    ns_hdr = "urn:iso:std:iso:20022:tech:xsd:head.001.001.02"
    ns_doc = "urn:iso:std:iso:20022:tech:xsd:pacs.002.001.10"
    fr = root.findtext(f".//{{{ns_hdr}}}Fr/{{{ns_hdr}}}FIId/{{{ns_hdr}}}FinInstnId/{{{ns_hdr}}}BICFI")
    to = root.findtext(f".//{{{ns_hdr}}}To/{{{ns_hdr}}}FIId/{{{ns_hdr}}}FinInstnId/{{{ns_hdr}}}BICFI")
    ig = root.findtext(f".//{{{ns_doc}}}TxInfAndSts/{{{ns_doc}}}InstgAgt/{{{ns_doc}}}FinInstnId/{{{ns_doc}}}BICFI")
    id_ = root.findtext(f".//{{{ns_doc}}}TxInfAndSts/{{{ns_doc}}}InstdAgt/{{{ns_doc}}}FinInstnId/{{{ns_doc}}}BICFI")
    print(f"Fr={fr} == InstgAgt={ig}: {fr==ig}")
    print(f"To={to} == InstdAgt={id_}: {to==id_}")
    print("PASS" if fr==ig and to==id_ else "FAIL - BIC mismatch")
