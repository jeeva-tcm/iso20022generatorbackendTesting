import os
import sys
import asyncio

# Ensure app is in python path
THIS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(THIS, ".."))
sys.path.insert(0, ROOT)

from app.services.bulk_generator import generate_single_xml
from app.services.validator import ISOValidator

async def main():
    print("Generating and validating pacs.004.001.09 XML messages...")
    v = ISOValidator()
    
    # Let's test with various selected blocks
    test_cases = [
        [],
        ["charges_information"],
        ["debtor_account"],
        ["charges_information", "debtor_account"],
        ["charges_information", "debtor_account", "creditor_account", "debtor_agent", "creditor_agent"],
        ["ultimate_debtor", "ultimate_creditor", "debtor_account", "creditor_account"]
    ]
    
    for idx, selected in enumerate(test_cases):
        print(f"\n--- Test Case {idx}: {selected} ---")
        try:
            xml = generate_single_xml("pacs.004.001.09", selected, idx)
            print("Generated XML (part):")
            # print TxInf part
            lines = xml.split("\n")
            tx_inf_lines = []
            capture = False
            for line in lines:
                if "<TxInf>" in line:
                    capture = True
                if capture:
                    tx_inf_lines.append(line)
                if "</TxInf>" in line:
                    capture = False
            print("\n".join(tx_inf_lines[:40]))
            if len(tx_inf_lines) > 40:
                print("...")
                print("\n".join(tx_inf_lines[-10:]))
            
            report = await v.validate(xml, message_type="pacs.004.001.09")
            res = report.to_dict()
            print(f"Validation status: {res.get('status')}")
            if res.get("status") == "FAIL":
                for issue in res.get("details", []):
                    print(f" - [{issue.get('severity')}] {issue.get('code')}: {issue.get('message')} at {issue.get('path')}")
            else:
                print("SUCCESS!")
        except Exception as e:
            print(f"Exception occurred: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
