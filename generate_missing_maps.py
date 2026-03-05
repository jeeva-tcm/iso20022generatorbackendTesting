import json
import os

mappings_dir = r"c:\Users\HP\Desktop\iso20022 Validator - Copy\backend\app\mappings"
mt_types = [
    ("103+", "pacs.008.001.08"),
    ("103 REMIT", "pacs.008.001.08"),
    ("200", "pacs.009.001.08"),
    ("210", "camt.057.001.06"),
    ("900", "camt.054.001.08"),
    ("910", "camt.054.001.08"),
    ("940", "camt.053.001.08"),
    ("950", "camt.053.001.08"),
    ("942", "camt.052.001.08"),
    ("199", "pacs.002.001.10"),
    ("299", "pacs.002.001.10"),
    ("192", "camt.056.001.08"),
    ("196", "camt.029.001.09")
]

for mt, mx in mt_types:
    if mt == "103 REMIT":
        filename = "MT103 REMIT.json"
    elif mt == "103+":
        filename = "MT103+.json"
    else:
        filename = f"MT{mt}.json"
        
    path = os.path.join(mappings_dir, filename)
    
    if not os.path.exists(path):
        data = {
          "source_mt": mt,
          "target_mx": mx,
          "xml_namespaces": {
            "xmlns": f"urn:iso:std:iso:20022:tech:xsd:{mx}"
          },
          "root_element": "Document",
          "mappings": [
            {
              "mt_tag": "20",
              "name": "Reference",
              "mandatory": False,
              "type": "text",
              "mx_path": "FICdtTrf/GrpHdr/MsgId"
            }
          ]
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
