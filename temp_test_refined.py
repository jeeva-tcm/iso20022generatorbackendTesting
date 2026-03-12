import sys
import os
import asyncio

# Add backend to path
sys.path.append(os.getcwd())

from app.services.validator import ISOValidator

async def test_refined_paths():
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
                <Id><OrgId><Othr><Id>ORG123</Id></Othr></Id></Id>
            </Dbtr>
            <Cdtr>
                <Nm>C1</Nm>
                <Id><PrvtId><Othr><Id>PRVT456</Id></Othr></Id></Id>
            </Cdtr>
            <DbtrAcct>
                <Id><Othr><Id>ACCT_BAD</Id><SchmeNm><Cd>BBAN</Cd></SchmeNm></Othr></Id>
            </DbtrAcct>
            <CdtrAcct>
                <Id><Othr><Id>ACCT_GOOD</Id></Othr></Id>
            </CdtrAcct>
            <InstgAgt><FinInstnId><Othr><Id>AGENT789</Id></Othr></FinInstnId></InstgAgt>
        </CdtTrfTxInf>
    </FIToFICstmrCdtTrf>
</Document>"""
    
    print("\n--- Testing Refined Path Logic (Step 1992) ---")
    report = await validator.validate(test_xml, mode="Full 1-3", message_type="pacs.008.001.08")
    
    for issue in report.issues:
        print(f"[{issue['code']}] at {issue['path']}: {issue['message']}")

if __name__ == "__main__":
    asyncio.run(test_refined_paths())
