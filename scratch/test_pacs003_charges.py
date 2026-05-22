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
    print("Generating and validating 50 pacs.003.001.08 XML messages...")
    v = ISOValidator()
    
    for idx in range(50):
        # alternate selecting charges_information and not selecting it
        selected = ["charges_information"] if idx % 2 == 0 else []
        try:
            xml = generate_single_xml("pacs.003.001.08", selected, idx)
            
            # Check consistency of ChrgsInf and InstdAmt
            has_instd_amt = "<InstdAmt" in xml
            has_chrgs_inf = "<ChrgsInf>" in xml
            
            if has_chrgs_inf != has_instd_amt:
                print(f"[{idx}] INCONSISTENCY DETECTED: Has ChrgsInf: {has_chrgs_inf}, Has InstdAmt: {has_instd_amt}")
                print(xml)
                return
            
            report = await v.validate(xml, message_type="pacs.003.001.08")
            res = report.to_dict()
            if res.get("status") == "FAIL":
                print(f"[{idx}] Validation status: FAIL")
                for issue in res.get("details", []):
                    print(f" - [{issue.get('severity')}] {issue.get('code')}: {issue.get('message')}")
                return
        except Exception as e:
            print(f"[{idx}] Exception occurred: {e}")
            import traceback
            traceback.print_exc()
            return
            
    print("All 50 messages successfully generated and validated! No inconsistencies or validation failures found.")

if __name__ == "__main__":
    asyncio.run(main())
