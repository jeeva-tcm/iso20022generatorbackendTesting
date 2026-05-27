import asyncio
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.validator import ISOValidator

async def test_user_payload():
    with open(r"c:\Users\HP\Desktop\iso final\iso20022generatorbackend\scratch\user_payload.xml", "r", encoding="utf-8") as f:
        xml_content = f.read()

    validator = ISOValidator()
    report = await validator.validate(xml_content, mode="Full 1-3", message_type="Auto-detect")
    
    print("\n--- Layer Status ---")
    # print(report.layer_status)
    
    print("\n--- Issues ---")
    for issue in report.issues:
        print(issue)

if __name__ == "__main__":
    asyncio.run(test_user_payload())
