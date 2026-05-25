import os
import sys
import json
import asyncio

# Add backend app directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from iso20022generatorbackend.app.services.validator import ISOValidator

async def test_validation():
    # Setup paths
    rules_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../app/resources/rules'))
    bics_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../bics'))
    xsd_base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../xsds'))
    
    config = {
        "rules_path": rules_path,
        "bics_path": bics_path,
        "xsd_base_path": xsd_base_path,
        "app_settings": {
            "max_file_size_kb": 2048,
            "scan_limit_chars": 10000,
            "max_xml_depth": 50
        },
        "validation_rules": {
            "default_header_type": "head.001.001.01",
            "header_namespace_partial": "head.001.001"
        }
    }
    
    # Initialize validator
    validator = ISOValidator()
    validator.rules_path = rules_path
    validator.codelists = {}
    validator.config = config
    validator.supported_bics = []
    
    # Load codelists
    import glob
    for fn in glob.glob(os.path.join(rules_path, "*.json")):
        name = os.path.basename(fn).replace(".json", "")
        with open(fn, 'r', encoding='utf-8') as f:
            validator.codelists[name] = json.load(f)

    # Read XML
    xml_file = os.path.join(os.path.dirname(__file__), 'valid_pacs008.xml')
    with open(xml_file, 'r', encoding='utf-8') as f:
        xml_content = f.read()
    
    # Replace dates to prevent past date errors (today is 2026-05-25)
    xml_content = xml_content.replace('2026-05-20', '2026-05-30')
        
    print("Running validation...")
    all_rules = validator._load_all_rules("pacs.008.001.08")
    print(f"Loaded {len(all_rules)} rules.")
    
    report = await validator.validate(xml_content, mode="Full 1-3", message_type="pacs.008.001.08")
    
    print("\nValidation Result Status:", report.status)
    print("Errors count:", report.errors)
    print("Warnings count:", report.warnings)
    print("Issues list raw:", report.issues)
    print("\nValidation Details (Path & Line):")
    for issue in report.issues:
        print(f"Code: {issue.get('code')}")
        print(f"  Path: {issue.get('path')}")
        print(f"  Line: {issue.get('line')}")
        print(f"  Msg:  {issue.get('message')}")
        print("-" * 50)

if __name__ == '__main__':
    asyncio.run(test_validation())
