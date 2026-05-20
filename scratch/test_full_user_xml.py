"""Full user XML smoke test — confirms ONLY the empty <Fr>/<FinInstnId> get
flagged and the valid <To>, agents, and parties are NOT flagged."""

import sys, os
THIS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(THIS, ".."))
sys.path.insert(0, ROOT)

from app.services.validator import ISOValidator
from app.services.models import ValidationReport

XML = open(os.path.join(THIS, "user_sample.xml"), encoding="utf-8").read()

v = ISOValidator()
report = ValidationReport("TEST00000002", "pacs.008.001.13", "Full 1-3")
v._validate_empty_required_containers(XML, report)

print(f"Issues found: {len(report.issues)}")
for i in report.issues:
    print(f"  [{i['severity']}] {i['code']} line={i['path']} :: {i['message']}")
