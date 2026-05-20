import os
import sys
import asyncio

sys.path.append(r'c:\Users\HP\Documents\ISO Stub Validator\iso20022generatorbackend')

from app.services.bulk_generator import generate_single_xml
from app.services.validator import ISOValidator

v = ISOValidator()

async def main():
    pass_count = 0
    fail_count = 0
    fail_reasons = {}

    print("Generating and validating 50 pacs.004.001.09 messages...")
    for idx in range(50):
        try:
            xml = generate_single_xml("pacs.004.001.09", [
                "instructing_agent",
                "instructed_agent",
                "debtor_agent",
                "creditor_agent",
                "ultimate_debtor",
                "ultimate_creditor",
                "charges_information"
            ], idx)
            report = await v.validate(xml, message_type="pacs.004.001.09")
            res = report.to_dict()
            if res.get("status") == "PASS":
                pass_count += 1
            else:
                fail_count += 1
                for issue in res.get("details", []):
                    code = issue.get("code")
                    msg = issue.get("message")
                    severity = issue.get("severity")
                    if severity in ["ERROR", "CRITICAL"]:
                        fail_reasons[code] = fail_reasons.get(code, 0) + 1
        except Exception as e:
            fail_count += 1
            fail_reasons[str(type(e).__name__)] = fail_reasons.get(str(type(e).__name__), 0) + 1

    print(f"\nPass count: {pass_count}")
    print(f"Fail count: {fail_count}")
    print("Failure reasons (errors/critical only):")
    for code, count in fail_reasons.items():
        print(f" - {code}: {count}")

asyncio.run(main())
