"""End-to-end smoke test:
 1) User's original empty-FinInstnId XML still FAILS (already-fixed bug stays fixed).
 2) An XML with mismatched MsgDefIdr vs Document namespace FAILS with HEAD001 code.
 3) A well-formed pacs.008 (all mandatory fields present) PASSES the new helpers
    (it may still fail XSD if the XSD isn't perfectly matched for this version,
     but our new pre-Layer-2 helpers should NOT add false positives).
"""
import sys, os, asyncio
THIS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(THIS, ".."))
sys.path.insert(0, ROOT)

from app.services.validator import ISOValidator
from app.services.models import ValidationReport

v = ISOValidator()

# ── Test 1: user's empty-FinInstnId XML — must still fail ───────────────────
XML_USER = open(os.path.join(THIS, "user_sample.xml"), encoding="utf-8").read()
r1 = ValidationReport("T1", "pacs.008.001.13", "Full 1-3")
v._validate_empty_required_containers(XML_USER, r1)
print("=== Test 1: user's XML (empty <FinInstnId> in <Fr>) ===")
print(f"  Issues: {len(r1.issues)}  Status: {r1.status}")
for i in r1.issues:
    print(f"   [{i['severity']}] {i['code']} line={i['path']} :: {i['message']}")
assert r1.errors >= 2, "Test 1 regression — user's XML should still fail"

# ── Test 2: header / payload mismatch ───────────────────────────────────────
XML_MISMATCH = """<?xml version="1.0" encoding="UTF-8"?>
<BusMsgEnvlp xmlns="urn:swift:xsd:envelope">
  <AppHdr xmlns="urn:iso:std:iso:20022:tech:xsd:head.001.001.02">
    <Fr><FIId><FinInstnId><BICFI>SNDRGB2LXXX</BICFI></FinInstnId></FIId></Fr>
    <To><FIId><FinInstnId><BICFI>RCVRGB2LXXX</BICFI></FinInstnId></FIId></To>
    <BizMsgIdr>B1</BizMsgIdr>
    <MsgDefIdr>pacs.009.001.12</MsgDefIdr>
    <BizSvc>swift.cbprplus.02</BizSvc>
    <CreDt>2026-05-20T10:00:00+00:00</CreDt>
  </AppHdr>
  <Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.13">
    <FIToFICstmrCdtTrf/>
  </Document>
</BusMsgEnvlp>
"""
r2 = ValidationReport("T2", "pacs.008.001.13", "Full 1-3")
v._validate_apphdr_payload_match(XML_MISMATCH, r2)
print("\n=== Test 2: AppHdr.MsgDefIdr says pacs.009 but Document is pacs.008 ===")
print(f"  Issues: {len(r2.issues)}")
for i in r2.issues:
    print(f"   [{i['severity']}] {i['code']} line={i['path']} :: {i['message']}")
assert any(i['code'] == 'HEAD001_MSGDEFIDR_MISMATCH' for i in r2.issues), \
    "Test 2 expected HEAD001_MSGDEFIDR_MISMATCH to fire"

# ── Test 3: header / payload matched, valid pacs.008 — no Tier-1/Tier-3 noise ─
XML_GOOD = """<?xml version="1.0" encoding="UTF-8"?>
<BusMsgEnvlp xmlns="urn:swift:xsd:envelope">
  <AppHdr xmlns="urn:iso:std:iso:20022:tech:xsd:head.001.001.02">
    <Fr><FIId><FinInstnId><BICFI>SNDRGB2LXXX</BICFI></FinInstnId></FIId></Fr>
    <To><FIId><FinInstnId><BICFI>RCVRGB2LXXX</BICFI></FinInstnId></FIId></To>
    <BizMsgIdr>B1</BizMsgIdr>
    <MsgDefIdr>pacs.008.001.13</MsgDefIdr>
    <BizSvc>swift.cbprplus.02</BizSvc>
    <CreDt>2026-05-20T10:00:00+00:00</CreDt>
  </AppHdr>
  <Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.13">
    <FIToFICstmrCdtTrf>
      <GrpHdr>
        <MsgId>M1</MsgId><CreDtTm>2026-05-20T10:00:00+00:00</CreDtTm>
        <NbOfTxs>1</NbOfTxs>
        <SttlmInf><SttlmMtd>INDA</SttlmMtd></SttlmInf>
      </GrpHdr>
      <CdtTrfTxInf>
        <PmtId>
          <InstrId>I1</InstrId><EndToEndId>E1</EndToEndId>
          <TxId>T1</TxId><UETR>4a1a0945-5772-409a-83ba-240e666e0267</UETR>
        </PmtId>
        <IntrBkSttlmAmt Ccy="USD">100.00</IntrBkSttlmAmt>
        <IntrBkSttlmDt>2026-05-20</IntrBkSttlmDt>
        <ChrgBr>SHAR</ChrgBr>
        <Dbtr><Nm>Alice</Nm><PstlAdr><Ctry>US</Ctry><TwnNm>NY</TwnNm></PstlAdr></Dbtr>
        <DbtrAcct><Id><IBAN>DE05174185584659194925</IBAN></Id></DbtrAcct>
        <DbtrAgt><FinInstnId><BICFI>AAAAUS33XXX</BICFI></FinInstnId></DbtrAgt>
        <CdtrAgt><FinInstnId><BICFI>BBBBGB2LXXX</BICFI></FinInstnId></CdtrAgt>
        <Cdtr><Nm>Bob</Nm><PstlAdr><Ctry>GB</Ctry><TwnNm>London</TwnNm></PstlAdr></Cdtr>
        <CdtrAcct><Id><IBAN>GB29NWBK60161331926819</IBAN></Id></CdtrAcct>
      </CdtTrfTxInf>
    </FIToFICstmrCdtTrf>
  </Document>
</BusMsgEnvlp>
"""
r3 = ValidationReport("T3", "pacs.008.001.13", "Full 1-3")
v._validate_empty_required_containers(XML_GOOD, r3)
v._validate_apphdr_payload_match(XML_GOOD, r3)
print("\n=== Test 3: valid pacs.008 — Tier-1 + Tier-3 helpers should not flag anything ===")
print(f"  Issues: {len(r3.issues)}")
for i in r3.issues:
    print(f"   [{i['severity']}] {i['code']} line={i['path']} :: {i['message']}")
assert len(r3.issues) == 0, "Test 3 FALSE POSITIVE — valid message should not trigger new helpers"

print("\nAll three smoke tests passed.")
