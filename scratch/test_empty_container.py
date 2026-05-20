"""Quick smoke test for _validate_empty_required_containers.

Loads the user's reported XML, runs the new rule directly, and prints any
issues found. Should produce an ERROR for <FinInstnId/> inside <Fr>/<FIId>.
"""

import sys
import os

# Ensure the project root is importable
THIS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(THIS, ".."))
sys.path.insert(0, ROOT)

from app.services.validator import ISOValidator
from app.services.models import ValidationReport

USER_XML = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<BusMsgEnvlp xmlns=\"urn:swift:xsd:envelope\">
    <AppHdr xmlns=\"urn:iso:std:iso:20022:tech:xsd:head.001.001.02\">
        <Fr>
            <FIId>
                <FinInstnId>

                </FinInstnId>
            </FIId>
        </Fr>
        <To>
            <FIId>
                <FinInstnId>
                    <BICFI>FFFFGB2LXXX</BICFI>
                </FinInstnId>
            </FIId>
        </To>
        <BizMsgIdr>BIZDDHXJLP30ZL4FADO</BizMsgIdr>
        <MsgDefIdr>pacs.008.001.13</MsgDefIdr>
        <BizSvc>swift.cbprplus.02</BizSvc>
        <CreDt>2026-05-20T10:00:00+00:00</CreDt>
    </AppHdr>
    <Document xmlns=\"urn:iso:std:iso:20022:tech:xsd:pacs.008.001.13\">
        <FIToFICstmrCdtTrf>
            <GrpHdr>
                <MsgId>MSG1</MsgId>
                <CreDtTm>2026-05-20T10:00:00+00:00</CreDtTm>
                <NbOfTxs>1</NbOfTxs>
                <SttlmInf>
                    <SttlmMtd>INDA</SttlmMtd>
                </SttlmInf>
            </GrpHdr>
        </FIToFICstmrCdtTrf>
    </Document>
</BusMsgEnvlp>
"""

v = ISOValidator()
report = ValidationReport("TEST00000001", "pacs.008.001.13", "Full 1-3")
v._validate_empty_required_containers(USER_XML, report)

print(f"Issues found: {len(report.issues)}")
for issue in report.issues:
    print(f"  [{issue['severity']}] L{issue['layer']} {issue['code']} line={issue['path']}")
    print(f"    msg: {issue['message']}")
    print(f"    fix: {issue['fix_suggestion']}")

# Sanity: at least one ERROR for the empty FinInstnId under <Fr>
assert any(i["code"] in ("EMPTY_REQUIRED_CONTAINER", "EMPTY_PARTY_CONTAINER") for i in report.issues), \
    "Expected the new rule to flag the empty <FinInstnId> inside <Fr>"
print("\nOK — rule fires for the user's example.")
