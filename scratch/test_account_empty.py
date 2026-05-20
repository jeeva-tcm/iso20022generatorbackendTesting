"""Verify Tier 1 catches empty account containers and other newly-listed empties."""
import sys, os
THIS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(THIS, ".."))
sys.path.insert(0, ROOT)

from app.services.validator import ISOValidator
from app.services.models import ValidationReport

XML = """<?xml version="1.0" encoding="UTF-8"?>
<BusMsgEnvlp xmlns="urn:swift:xsd:envelope">
  <AppHdr xmlns="urn:iso:std:iso:20022:tech:xsd:head.001.001.02">
    <Fr><FIId><FinInstnId><BICFI>SNDRGB2LXXX</BICFI></FinInstnId></FIId></Fr>
    <To><FIId><FinInstnId><BICFI>RCVRGB2LXXX</BICFI></FinInstnId></FIId></To>
    <BizMsgIdr>B1</BizMsgIdr><MsgDefIdr>pacs.008.001.13</MsgDefIdr>
    <BizSvc>swift.cbprplus.02</BizSvc><CreDt>2026-05-20T10:00:00+00:00</CreDt>
  </AppHdr>
  <Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.13">
    <FIToFICstmrCdtTrf>
      <GrpHdr><MsgId>M1</MsgId><CreDtTm>2026-05-20T10:00:00+00:00</CreDtTm><NbOfTxs>1</NbOfTxs>
        <SttlmInf><SttlmMtd>INDA</SttlmMtd></SttlmInf></GrpHdr>
      <CdtTrfTxInf>
        <PmtId><EndToEndId>E1</EndToEndId></PmtId>
        <PmtTpInf></PmtTpInf>
        <IntrBkSttlmAmt Ccy="USD">100</IntrBkSttlmAmt>
        <Dbtr><Nm>X</Nm><PstlAdr><Ctry>US</Ctry></PstlAdr></Dbtr>
        <DbtrAcct><Id></Id></DbtrAcct>
        <DbtrAgt><FinInstnId><BICFI>AAAAUS33XXX</BICFI></FinInstnId></DbtrAgt>
        <CdtrAgt><FinInstnId><BICFI>BBBBGB2LXXX</BICFI></FinInstnId></CdtrAgt>
        <Cdtr><Nm>Y</Nm><PstlAdr><Ctry>GB</Ctry></PstlAdr></Cdtr>
        <CdtrAcct><Id><Othr><Id></Id></Othr></Id></CdtrAcct>
        <RmtInf></RmtInf>
        <SvcLvl></SvcLvl>
      </CdtTrfTxInf>
    </FIToFICstmrCdtTrf>
  </Document>
</BusMsgEnvlp>
"""

v = ISOValidator()
report = ValidationReport("T", "pacs.008.001.13", "Full 1-3")
v._validate_empty_required_containers(XML, report)
print(f"Issues found: {len(report.issues)}")
for i in report.issues:
    print(f"  [{i['severity']}] {i['code']} line={i['path']} :: {i['message']}")
