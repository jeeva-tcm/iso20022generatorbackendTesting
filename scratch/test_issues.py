import asyncio
import os
import sys

# Ensure app is in python path
THIS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(THIS, ".."))
sys.path.insert(0, ROOT)

from app.services.bulk_generator import generate_single_xml
from app.services.validator import ISOValidator

async def test_msg(msg_type, selected_blocks):
    print(f"\n--- Testing {msg_type} with blocks: {selected_blocks} ---")
    v = ISOValidator()
    xml = generate_single_xml(msg_type, selected_blocks, 0)
    print("Generated XML (part):")
    # Print the relevant parts depending on the message type
    if "pain.002" in msg_type:
        start = xml.find("<CstmrPmtStsRpt>")
        end = xml.find("</CstmrPmtStsRpt>") + 17
        print(xml[start:min(end, start+1000)])
    elif "pacs.010" in msg_type:
        start = xml.find("<CdtTrfTxInf>")
        if start == -1: start = xml.find("<GrpHdr>")
        end = xml.find("</CdtTrfTxInf>") + 14
        print(xml[start:min(end, start+1000)])
    elif "pain.008" in msg_type:
        start = xml.find("<PmtInf>")
        end = xml.find("</PmtInf>") + 9
        print(xml[start:min(end, start+1000)])
        
    report = await v.validate(xml, message_type=msg_type)
    res = report.to_dict()
    if res.get("status") == "FAIL":
        print(f"Validation status: FAIL")
        for issue in res.get("details", []):
            print(f" - [{issue.get('severity')}] {issue.get('code')} line={issue.get('line')}: {issue.get('message')}")
    else:
        print("SUCCESS!")

async def main():
    await test_msg("pacs.010.001.03", {"instructing_agent", "payment_type_information"})
    await test_msg("pain.002.001.10", {"original_payment_information", "original_transaction", "status_reason"})
    await test_msg("pain.008.001.08", {"payment_type_information", "debtor_agent", "ultimate_creditor"})

if __name__ == "__main__":
    asyncio.run(main())
