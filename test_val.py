import asyncio
import os
import sys

# Move to backend folder
sys.path.append(os.path.abspath("."))
from app.services.validator import ISOValidator

async def test():
    validator = ISOValidator()
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<BusMsgEnvlp xmlns="urn:swift:xsd:envelope">
    <AppHdr xmlns="urn:iso:std:iso:20022:tech:xsd:head.001.001.02">
        <Fr><FIId><FinInstnId><BICFI>BBBBUS33XXX</BICFI></FinInstnId></FIId></Fr>
        <To><FIId><FinInstnId><BICFI>CCCCGB2LXXX</BICFI></FinInstnId></FIId></To>
        <BizMsgIdr>MSG-2026-B-001</BizMsgIdr>
        <MsgDefIdr>pacs.008.001.08</MsgDefIdr>
        <BizSvc>swift.cbprplus.02</BizSvc>
        <CreDt>2026-03-02T10:35:00+00:00</CreDt>
    </AppHdr>
    <Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
        <FIToFICstmrCdtTrf>
            <GrpHdr>
                <MsgId>MSG-2026-B-001</MsgId>
                <CreDtTm>2026-03-02T10:35:00+00:00</CreDtTm>
                <NbOfTxs>1</NbOfTxs>
                <SttlmInf>
                    <SttlmMtd>INDA</SttlmMtd>
                </SttlmInf>
            </GrpHdr>
            <CdtTrfTxInf>
                <PmtId>
                    <InstrId>INSTR-001</InstrId>
                    <EndToEndId>E2E-001</EndToEndId>
                    <TxId>TX-001</TxId>
                    <UETR>550e8400-e29b-41d4-a716-446655440000</UETR>
                </PmtId>
                <IntrBkSttlmAmt Ccy="USD">1500.00</IntrBkSttlmAmt>
                <IntrBkSttlmDt>2026-03-02</IntrBkSttlmDt>
                <ChrgBr>SLEV</ChrgBr>
                <Dbtr>
                    <Nm>John Doe Corp</Nm>
                    <PstlAdr>
                        <Ctry>ZZ</Ctry>
                    </PstlAdr>
                </Dbtr>
            </CdtTrfTxInf>
        </FIToFICstmrCdtTrf>
    </Document>
</BusMsgEnvlp>
"""
    report = await validator.validate(xml_content=xml, mode="Full 1-3", message_type="pacs.008.001.08")
    for issue in report.issues:
        print(f"[{issue.severity}] Layer {issue.layer}: {issue.code} -> {issue.message} ({issue.path})")

if __name__ == "__main__":
    asyncio.run(test())
