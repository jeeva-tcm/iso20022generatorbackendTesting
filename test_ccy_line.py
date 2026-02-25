"""
Quick test: verify that Ccy="USDDD" reports the correct line number.
Run from the backend/ directory:
  C:\Users\HP\AppData\Local\Programs\Python\Python314\python.exe test_ccy_line.py
"""
import asyncio, sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.services.validator import ISOValidator

XML = r"""<?xml version="1.0" encoding="UTF-8"?>
<BusMsgEnvlp xmlns="urn:swift:xsd:envelope">
	<AppHdr xmlns="urn:iso:std:iso:20022:tech:xsd:head.001.001.02">
		<Fr>
			<FIId>
				<FinInstnId>
					<BICFI>BBBBUS33XXX</BICFI>
				</FinInstnId>
			</FIId>
		</Fr>
		<To>
			<FIId>
				<FinInstnId>
				<BICFI>CCCCGB2LXXX</BICFI>
			</FinInstnId>
		</FIId>
	</To>
	<BizMsgIdr>MSG-2026-B-001</BizMsgIdr>
	<MsgDefIdr>pacs.008.001.08</MsgDefIdr>
	<BizSvc>swift.cbprplus.01</BizSvc>
	<CreDt>2026-02-02T10:35:00+00:00</CreDt>
</AppHdr>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
	<FIToFICstmrCdtTrf>
		<GrpHdr>
			<MsgId>MSG-2026-B-001</MsgId>
			<CreDtTm>2026-02-02T10:35:00+00:00</CreDtTm>
			<NbOfTxs>1</NbOfTxs>
			<SttlmInf>
				<SttlmMtd>INDA</SttlmMtd>
			</SttlmInf>
		</GrpHdr>
		<CdtTrfTxInf>
			<PmtId>
				<InstrId>INSTR-ID-999</InstrId>
				<EndToEndId>E2E-REF-777</EndToEndId>
				<TxId>TX-ID-555</TxId>
				<UETR>550e8400-e29b-41d4-a716-446655440000</UETR>
			</PmtId>
			<PmtTpInf>
				<SvcLvl>
					<Cd>SEPA</Cd>
				</SvcLvl>
			</PmtTpInf>
			<IntrBkSttlmAmt Ccy="USDDD">1500.00</IntrBkSttlmAmt>
			<IntrBkSttlmDt>2026-02-02</IntrBkSttlmDt>
			<ChrgBr>SHAR</ChrgBr>
			<InstgAgt><FinInstnId><BICFI>BBBBUS33XXX</BICFI></FinInstnId></InstgAgt>
			<InstdAgt><FinInstnId><BICFI>CCCCGB2LXXX</BICFI></FinInstnId></InstdAgt>
			<Dbtr><Nm>John Doe Corp</Nm></Dbtr>
			<DbtrAcct><Id><IBAN>US12345678901234567890</IBAN></Id></DbtrAcct>
			<DbtrAgt><FinInstnId><BICFI>BBBBUS33XXX</BICFI></FinInstnId></DbtrAgt>
			<CdtrAgt><FinInstnId><BICFI>CCCCGB2LXXX</BICFI></FinInstnId></CdtrAgt>
			<Cdtr><Nm>Jane Smith Ltd</Nm></Cdtr>
			<CdtrAcct><Id><IBAN>GB98765432109876543210</IBAN></Id></CdtrAcct>
			<Purp><Cd>SALA</Cd></Purp>
		</CdtTrfTxInf>
	</FIToFICstmrCdtTrf>
</Document>
</BusMsgEnvlp>"""

# Show which line IntrBkSttlmAmt Ccy="USDDD" is on
for i, line in enumerate(XML.splitlines(), 1):
    if 'USDDD' in line:
        print(f"\n>>> Ccy=\"USDDD\" is on line {i} of the XML: {line.strip()}\n")

async def main():
    v = ISOValidator()
    report = await v.validate(XML, mode="Full 1-3", message_type="Auto-detect")
    print("\n=== VALIDATION RESULTS ===")
    for issue in report.issues:
        d = issue.to_dict() if hasattr(issue, 'to_dict') else issue
        print(f"  Layer {d.get('layer')} | Line: {d.get('path')} | {d.get('message')}")

asyncio.run(main())
