import os
import sys
import asyncio

sys.path.append(r'c:\Users\HP\Documents\ISO Stub Validator\iso20022generatorbackend')

from app.services.bulk_generator import generate_single_xml, _validate_charges_information, _normalize_charges_information
from app.services.validator import ISOValidator

# Initialize Validator
v = ISOValidator()

async def main():
    print("==================================================")
    print("Testing pacs.004.001.09 bulk generation and validation:")

    # 1. Test standard generation
    xml = generate_single_xml("pacs.004.001.09", [], 1)
    
    # Check what ChrgBr was generated
    chrg_br_idx = xml.find("<ChrgBr>")
    if chrg_br_idx != -1:
        chrg_br_val = xml[chrg_br_idx+8:chrg_br_idx+12]
        print(f"\nGenerated ChrgBr is: {chrg_br_val}")
    else:
        chrg_br_val = "UNKNOWN"
        print("\nWARNING: ChrgBr not found in XML!")

    print("\nGenerated XML preview:")
    if "<ChrgsInf>" in xml:
        idx = xml.find("<ChrgsInf>")
        print(xml[idx:idx+400])
    else:
        print("ChrgsInf not found (correct if ChrgBr was not CRED).")

    # Run Validator
    report = await v.validate(xml, message_type="pacs.004.001.09")
    result = report.to_dict()
    print(f"Validation Status: {result.get('status')}")
    if result.get("status") == "FAIL":
        print("Issues:")
        for issue in result.get("details", []):
            print(f"- [{issue.get('severity')}] {issue.get('code')}: {issue.get('message')}")

    # 2. Test negative test case - manually build a CRED with missing ChrgsInf and verify normalization
    bad_xml = """<?xml version="1.0" encoding="UTF-8"?>
<BusMsgEnvlp xmlns="urn:swift:xsd:envelope">
	<AppHdr xmlns="urn:iso:std:iso:20022:tech:xsd:head.001.001.02">
		<Fr>
			<FIId><FinInstnId><BICFI>BANKDEFFXXX</BICFI></FinInstnId></FIId>
		</Fr>
		<To>
			<FIId><FinInstnId><BICFI>BANKDEFFXXX</BICFI></FinInstnId></FIId>
		</To>
		<BizMsgIdr>BIZ123</BizMsgIdr>
		<MsgDefIdr>pacs.004.001.09</MsgDefIdr>
		<BizSvc>swift.cbprplus.02</BizSvc>
		<CreDt>2026-05-19T12:00:00Z</CreDt>
	</AppHdr>
	<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.004.001.09">
		<PmtRtr>
			<GrpHdr>
				<MsgId>MSG123</MsgId>
				<CreDtTm>2026-05-19T12:00:00Z</CreDtTm>
				<NbOfTxs>1</NbOfTxs>
				<SttlmInf>
					<SttlmMtd>INDA</SttlmMtd>
				</SttlmInf>
			</GrpHdr>
			<TxInf>
				<RtrId>RTR123</RtrId>
				<RtrdIntrBkSttlmAmt Ccy="EUR">100.00</RtrdIntrBkSttlmAmt>
				<ChrgBr>CRED</ChrgBr>
			</TxInf>
		</PmtRtr>
	</Document>
</BusMsgEnvlp>"""

    print("\nTesting Normalization of missing ChrgsInf when ChrgBr is CRED:")
    try:
        _validate_charges_information(bad_xml)
        print("Validation surprisingly PASSED on raw bad XML (should have failed)!")
    except Exception as e:
        print(f"Validation correctly FAILED on raw bad XML: {str(e)}")

    normalized_xml = _normalize_charges_information(bad_xml)
    print("\nNormalized XML TxInf block:")
    tx_idx = normalized_xml.find("<TxInf>")
    tx_end = normalized_xml.find("</TxInf>")
    print(normalized_xml[tx_idx:tx_end+8])

    try:
        _validate_charges_information(normalized_xml)
        print("Validation successfully PASSED on normalized XML!")
    except Exception as e:
        print(f"Validation FAILED on normalized XML: {str(e)}")

asyncio.run(main())
