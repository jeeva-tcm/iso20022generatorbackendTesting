import sys
import os
import asyncio

# Add backend to path
sys.path.append(os.getcwd())

from app.services.validator import ISOValidator

async def test_lei_refined():
    validator = ISOValidator()
    
    test_xmls = [
        # 1. Valid LEI (549300TRUWO2CD2G5692)
        """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
    <FIToFICstmrCdtTrf>
        <GrpHdr><MsgId>M1</MsgId><CreDtTm>2026-03-12T10:00:00</CreDtTm><NbOfTxs>1</NbOfTxs><SttlmInf><SttlmMtd>CLRG</SttlmMtd></SttlmInf></GrpHdr>
        <CdtTrfTxInf>
            <PmtId><EndToEndId>E1</EndToEndId></PmtId>
            <IntrBkSttlmAmt Ccy="EUR">100.00</IntrBkSttlmAmt>
            <Dbtr><Nm>D1</Nm></Dbtr>
            <Cdtr><Nm>C1</Nm></Cdtr>
            <DbtrAcct><Id><Othr><Id>549300TRUWO2CD2G5692</Id><SchmeNm><Cd>LEI</Cd></SchmeNm></Othr></Id></DbtrAcct>
        </CdtTrfTxInf>
    </FIToFICstmrCdtTrf>
</Document>""",
        # 2. Reserved Check Digits 00
        """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
    <FIToFICstmrCdtTrf>
        <GrpHdr><MsgId>M1</MsgId><CreDtTm>2026-03-12T10:00:00</CreDtTm><NbOfTxs>1</NbOfTxs><SttlmInf><SttlmMtd>CLRG</SttlmMtd></SttlmInf></GrpHdr>
        <CdtTrfTxInf>
            <PmtId><EndToEndId>E1</EndToEndId></PmtId>
            <IntrBkSttlmAmt Ccy="EUR">100.00</IntrBkSttlmAmt>
            <Dbtr><Nm>D1</Nm></Dbtr>
            <Cdtr><Nm>C1</Nm></Cdtr>
            <DbtrAcct><Id><Othr><Id>549300TRUWO2CD2G5600</Id><SchmeNm><Cd>LEI</Cd></SchmeNm></Othr></Id></DbtrAcct>
        </CdtTrfTxInf>
    </FIToFICstmrCdtTrf>
</Document>""",
        # 3. All Zeros
        """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
    <FIToFICstmrCdtTrf>
        <GrpHdr><MsgId>M1</MsgId><CreDtTm>2026-03-12T10:00:00</CreDtTm><NbOfTxs>1</NbOfTxs><SttlmInf><SttlmMtd>CLRG</SttlmMtd></SttlmInf></GrpHdr>
        <CdtTrfTxInf>
            <PmtId><EndToEndId>E1</EndToEndId></PmtId>
            <IntrBkSttlmAmt Ccy="EUR">100.00</IntrBkSttlmAmt>
            <Dbtr><Nm>D1</Nm></Dbtr>
            <Cdtr><Nm>C1</Nm></Cdtr>
            <DbtrAcct><Id><Othr><Id>00000000000000000000</Id><SchmeNm><Cd>LEI</Cd></SchmeNm></Othr></Id></DbtrAcct>
        </CdtTrfTxInf>
    </FIToFICstmrCdtTrf>
</Document>"""
    ]
    
    case_names = ["Valid LEI (549300TRUWO2CD2G5692)", "Reserved 00", "All Zeros"]
    
    for i, xml in enumerate(test_xmls):
        print(f"\\n--- Testing Case {i+1}: {case_names[i]} ---")
        report = await validator.validate(xml, mode="Full 1-3", message_type="pacs.008.001.08")
        found = False
        for issue in report.issues:
            if "LEI" in issue['code'] or "LEI" in issue['message']:
                print(f"Code: {issue['code']}, Line: {issue['path']}")
                print(f"Message: {issue['message']}")
                print(f"Fix: {issue['fix_suggestion']}")
                found = True
        if not found:
            print("No LEI issues found (Success for valid case)")

if __name__ == "__main__":
    asyncio.run(test_lei_refined())
