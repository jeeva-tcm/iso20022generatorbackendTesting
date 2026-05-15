
import asyncio
import os
import sys

# Add the project root to sys.path
backend_root = r"c:\Users\HP\Desktop\iso final\iso20022generatorbackend"
sys.path.append(backend_root)

from app.services.bulk_generator import generate_single_xml
from app.services.validator import ISOValidator

async def test_messages():
    validator = ISOValidator()
    selected_blocks = []
    
    msg_types = [
        "pacs.008.001.13",
        "pacs.009.001.12",
        "pacs.004.001.14",
        "pacs.003.001.11",
        "pacs.002.001.15",
        "pacs.010.001.06",
        "camt.052.001.13",
        "camt.053.001.13",
        "camt.054.001.13",
        "camt.055.001.12",
        "camt.056.001.11",
        "camt.057.001.08",
        "pain.001.001.12",
        "pain.002.001.14",
        "pain.008.001.11",
    ]
    for message_type in msg_types:
        print(f"\n{'='*50}")
        print(f"Testing {message_type}...")
        xml = generate_single_xml(message_type, ["all"], 1)
        
        report = await validator.validate(xml, mode="Full 1-3", message_type="Auto-detect")
        
        print(f"Status: {report.status}")
        if report.status != "PASS":
            print("Issues:")
            for issue in report.issues:
                print(f"- [{issue.get('severity')}] {issue.get('code')}: {issue.get('message')} (Line: {issue.get('line')})")

if __name__ == "__main__":
    asyncio.run(test_messages())
