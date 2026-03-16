
import json
from schme_nm_validator import validateSchmeNm

test_cases = [
    {"Cd": "LEI"},
    {"Cd": "Passport"},
    {"Prtry": "INTERNAL"},
    {"Cd": "LEI", "Prtry": "INTERNAL"},
    {"Cd": "UNKNOWN"},
    {"Prtry": ""},
    {}
]

results = []
for tc in test_cases:
    results.append({
        "input": tc,
        "output": validateSchmeNm(tc)
    })

with open("schme_test_results.json", "w") as f:
    json.dump(results, f, indent=2)
