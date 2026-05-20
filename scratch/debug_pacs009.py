import asyncio
import os
import sys

# Add the project root to sys.path
backend_root = r"c:\Users\HP\Documents\ISO Stub Validator\iso20022generatorbackend"
sys.path.append(backend_root)

from app.services.bulk_generator import generate_single_xml
from app.services.validator import ISOValidator

async def test_pacs009():
    validator = ISOValidator()
    
    print("\n" + "="*50)
    print("Testing pacs.009.001.08_ADV bulk generation and validation:")
    
    # Generate bulk message for ADV
    xml_adv = generate_single_xml("pacs.009.001.08_ADV", [], 1)
    print("\nGenerated ADV XML preview:")
    # Print SttlmInf block
    sttlm_start = xml_adv.find("<SttlmInf>")
    sttlm_end = xml_adv.find("</SttlmInf>") + 11
    if sttlm_start != -1:
        print(xml_adv[sttlm_start:sttlm_end])
    else:
        print("SttlmInf block not found!")
        
    print("\nValidating generated ADV XML...")
    report_adv = await validator.validate(xml_adv, mode="Full 1-3", message_type="pacs.009.001.08_ADV")
    print(f"Status: {report_adv.status}")
    if report_adv.status != "PASS":
        print("Issues:")
        for issue in report_adv.issues:
             print(f"- [{issue.get('severity')}] {issue.get('code')}: {issue.get('message')} (Line: {issue.get('line')})")

    # Testing pacs.009.001.08_COV (Cover Payment)
    print("\n" + "="*50)
    print("Testing pacs.009.001.08_COV bulk generation and validation:")
    
    xml_cov = generate_single_xml("pacs.009.001.08_COV", ["underlying_customer_credit_transfer"], 1)
    print("\nGenerated COV XML preview:")
    sttlm_start_cov = xml_cov.find("<SttlmInf>")
    sttlm_end_cov = xml_cov.find("</SttlmInf>") + 11
    if sttlm_start_cov != -1:
        print(xml_cov[sttlm_start_cov:sttlm_end_cov])
    else:
        print("SttlmInf block not found!")
        
    print("\nValidating generated COV XML...")
    report_cov = await validator.validate(xml_cov, mode="Full 1-3", message_type="pacs.009.001.08_COV")
    print(f"Status: {report_cov.status}")
    if report_cov.status != "PASS":
        print("Issues:")
        for issue in report_cov.issues:
             print(f"- [{issue.get('severity')}] {issue.get('code')}: {issue.get('message')} (Line: {issue.get('line')})")

    # Test COV with invalid COVE settlement method and reimbursement agents
    print("\n" + "="*50)
    print("Testing pacs.009.001.08_COV with invalid COVE settlement and reimbursement agents:")
    invalid_cov_xml = xml_cov.replace(
        xml_cov[sttlm_start_cov:sttlm_end_cov],
        "<SttlmInf>\n\t\t\t\t\t<SttlmMtd>COVE</SttlmMtd>\n\t\t\t\t\t<InstgRmbrsmntAgt>\n\t\t\t\t\t\t<FinInstnId>\n\t\t\t\t\t\t\t<BICFI>BBBBUS33XXX</BICFI>\n\t\t\t\t\t\t</FinInstnId>\n\t\t\t\t\t</InstgRmbrsmntAgt>\n\t\t\t\t</SttlmInf>"
    )
    
    report_invalid_cov = await validator.validate(invalid_cov_xml, mode="Full 1-3", message_type="pacs.009.001.08_COV")
    print(f"Status: {report_invalid_cov.status}")
    print("Issues expected (PACS009_COV_SETTLEMENT_METHOD, PACS009_COV_DISALLOW_REIMBURSEMENT):")
    for issue in report_invalid_cov.issues:
         if issue.get('code') in ['PACS009_COV_SETTLEMENT_METHOD', 'PACS009_COV_DISALLOW_REIMBURSEMENT']:
             print(f"- [{issue.get('severity')}] {issue.get('code')}: {issue.get('message')}")

if __name__ == "__main__":
    asyncio.run(test_pacs009())
