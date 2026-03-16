import sys
import os
import asyncio

# Add backend to path
sys.path.append(os.getcwd())

from app.services.validator import ISOValidator

async def test_acct_forbidden():
    validator = ISOValidator()
    
    test_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
    <FIToFICstmrCdtTrf>
        <GrpHdr><MsgId>M1</MsgId><CreDtTm>2026-03-12T10:00:00</CreDtTm><NbOfTxs>1</NbOfTxs><SttlmInf><SttlmMtd>CLRG</SttlmMtd></SttlmInf></GrpHdr>
        <CdtTrfTxInf>
            <PmtId><EndToEndId>E1</EndToEndId></PmtId>
            <IntrBkSttlmAmt Ccy="EUR">100.00</IntrBkSttlmAmt>
            <Dbtr>
                <Nm>D1</Nm>
                <Id><OrgId><Othr><Id>ORG123</Id></Othr></OrgId></Id>
            </Dbtr>
            <Cdtr><Nm>C1</Nm></Cdtr>
            <DbtrAcct>
                <Id><Othr><Id>ACCT_WRONG</Id><SchmeNm><Cd>BBAN</Cd></SchmeNm></Othr></Id>
            </DbtrAcct>
            <CdtrAcct>
                <Id><Othr><Id>ACCT_RIGHT</Id></Othr></Id>
            </CdtrAcct>
        </CdtTrfTxInf>
    </FIToFICstmrCdtTrf>
</Document>"""
    
    print("\n--- Testing Account SchmeNm Exclusion vs Org Requirement ---")
    report = await validator.validate(test_xml, mode="Full 1-3", message_type="pacs.008.001.08")
    
    has_org_missing_error = False
    has_acct_unsupported_error = False
    
    for issue in report.issues:
        print(f"[{issue['code']}] at {issue['path']}: {issue['message']}")
        if "SCHEME_MISSING" in issue['code'] and "/OrgId/" in issue['message']:
            has_org_missing_error = True
        if "SCHEME_NOT_SUPPORTED" in issue['code'] and "/DbtrAcct/" in issue['message']:
            has_acct_unsupported_error = True
    
    if has_org_missing_error:
        print("\n✅ OrgId missing SchmeNm correctly flagged.")
    if has_acct_unsupported_error:
        print("✅ DbtrAcct containing SchmeNm correctly flagged as unsupported.")
    
    if has_org_missing_error and has_acct_unsupported_error:
        print("\nOVERALL SUCCESS: Rules correctly differentiated. 🏆")
    else:
        print("\nFAILURE: Some rules did not trigger as expected.")

if __name__ == "__main__":
    asyncio.run(test_acct_forbidden())
