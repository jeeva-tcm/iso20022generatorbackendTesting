import asyncio
import os
import sys

# Add backend root to path
sys.path.append(os.getcwd())

from app.services.validator import ISOValidator

async def test_duplicate_validation():
    validator = ISOValidator()
    
    # pacs.008 sample with duplicate MsgId (max_occurs=1)
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<BusMsgEnvlp xmlns="urn:swift:xsd:envelope">
    <AppHdr xmlns="urn:iso:std:iso:20022:tech:xsd:head.001.001.02">
        <Fr><FIId><FinInstnId><BICFI>BBBBUS33XXX</BICFI></FinInstnId></FIId></Fr>
        <To><FIId><FinInstnId><BICFI>CCCCGB2LXXX</BICFI></FinInstnId></FIId></To>
        <BizMsgIdr>MSG-2026-001</BizMsgIdr>
        <MsgDefIdr>pacs.008.001.08</MsgDefIdr>
        <BizSvc>swift.cbprplus.01</BizSvc>
        <CreDt>2026-02-02T19:35:00Z</CreDt>
    </AppHdr>
    <Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
        <FIToFICstmrCdtTrf>
            <GrpHdr>
                <MsgId>MSG-2026-001</MsgId>
                <MsgId>DUPLICATE-MSG-ID</MsgId>
                <CreDtTm>2026-02-02T19:35:00Z</CreDtTm>
                <NbOfTxs>1</NbOfTxs>
                <SttlmInf><SttlmMtd>INDA</SttlmMtd></SttlmInf>
            </GrpHdr>
            <CdtTrfTxInf>
                <PmtId>
                    <InstrId>INSTR-001</InstrId>
                    <InstrId>DUPLICATE-INSTR-ID</InstrId>
                    <EndToEndId>E2E-001</EndToEndId>
                    <TxId>TX-001</TxId>
                    <UETR>550e8400-e29b-41d4-a716-446655440000</UETR>
                </PmtId>
                <IntrBkSttlmAmt Ccy="USD">100.00</IntrBkSttlmAmt>
                <InstdAmt Ccy="USD">100.00</InstdAmt>
                <ChrgBr>SLEV</ChrgBr>
                <Dbtr><Nm>John Doe</Nm><PstlAdr><Ctry>US</Ctry></PstlAdr></Dbtr>
                <DbtrAgt><FinInstnId><BICFI>BBBBUS33XXX</BICFI></FinInstnId></DbtrAgt>
                <CdtrAgt><FinInstnId><BICFI>CCCCGB2LXXX</BICFI></FinInstnId></CdtrAgt>
                <Cdtr><Nm>Jane Doe</Nm><PstlAdr><Ctry>GB</Ctry></PstlAdr></Cdtr>
            </CdtTrfTxInf>
        </FIToFICstmrCdtTrf>
    </Document>
</BusMsgEnvlp>"""

    print("Running validation...")
    report = await validator.validate(xml_content, mode="Full 1-3", message_type="pacs.008.001.08")
    
    print(f"Status: {report.status}")
    print(f"Errors: {report.errors}")
    
    print("\nIssues Found:")
    duplicate_tags = [i for i in report.issues if i['code'] == 'DUPLICATE_TAG']
    for issue in duplicate_tags:
        print(f"---")
        print(f"Severity: {issue['severity']}")
        print(f"Layer: {issue['layer']}")
        print(f"Code: {issue['code']}")
        print(f"Line: {issue['path']}")
        print(f"Message: {issue['message']}")
        print(f"Suggestion:\n{issue['fix_suggestion']}")

if __name__ == "__main__":
    asyncio.run(test_duplicate_validation())
