import sys
import os
import asyncio
sys.path.insert(0, os.path.abspath(r'c:\Users\HP\Desktop\iso final\iso20022generatorbackend'))
from app.main import validator
from app.services.mt_mx_converter import MT2MXConverter
converter = MT2MXConverter(os.path.abspath(r'c:\Users\HP\Desktop\iso final\iso20022generatorbackend\app\mappings'))

mt103_sample = """{1:F01BBBBUS33AXXX0000000000}{2:I103CCCCGB2LXXXXN}{4:
:20:TXN-103-8899
:23B:CRED
:32A:261231USD15000,50
:50K:/US8899001122
ACME CORP
123 BUSINESS RD
NEW YORK, US
:59:/GB1122334455
GLOBAL SUPPLIES
456 INDUSTRIAL W
LONDON, GB
:71A:SHA
-}"""

mt103plus_sample = """{1:F01BBBBUS33AXXX0000000000}{2:I103CCCCGB2LXXXXN}{3:{121:550e8400-e29b-41d4-a716-446655447777}{119:STP}}{4:
:20:REF103STP001
:23B:CRED
:32A:261231USD2500,00
:50A:/US8899001122
BBBBUS33XXX
:59A:/GB1122334455
CCCCGB2LXXX
:71A:SHA
-}"""

async def main():
    print("Converting MT103...")
    from app.services.mt_mx_converter import MT2MXConverter
    converter = MT2MXConverter(os.path.abspath(r'c:\Users\HP\Desktop\iso final\iso20022generatorbackend\app\mappings'))
    res103 = converter.validate_and_convert(mt103_sample, forced_mt_type='MT103')
    xml103 = res103['mx_message']
    rep103 = await validator.validate(xml103, mode="Full 1-3", message_type="Auto-detect")
    
    print("Converting MT103+...")
    res103p = converter.validate_and_convert(mt103plus_sample, forced_mt_type='MT103+')
    xml103p = res103p['mx_message']
    rep103p = await validator.validate(xml103p, mode="Full 1-3", message_type="Auto-detect")

    print("\nMT103 XML len:", len(xml103))
    print("MT103+ XML len:", len(xml103p))
    
    canon103, _ = validator._normalize_message(xml103)
    canon103p, _ = validator._normalize_message(xml103p)
    
    type103 = validator._detect_message_type(xml103)
    type103p = validator._detect_message_type(xml103p)
    print("\nMT103 detected:", type103)
    print("MT103+ detected:", type103p)
    
    rules103 = validator._load_all_rules(type103)
    rules103p = validator._load_all_rules(type103p)
    l3_rules103 = [r for r in rules103 if r.get("layer") == 3]
    l3_rules103p = [r for r in rules103p if r.get("layer") == 3]
    print(f"MT103 layer 3 rules: {len(l3_rules103)}")
    print(f"MT103+ layer 3 rules: {len(l3_rules103p)}")
    
    print("\nBIC Rules:")
    for r in l3_rules103p:
        if r.get('type') == 'bic':
            print(f"Selector: {r.get('selector')}, Type: {r.get('type')}")
    
    with open("scratch/mt103.xml", "w") as f:
        f.write(xml103p)
    
    print("\nMT103 Issues Details:")
    for iss in rep103.issues:
        if isinstance(iss, dict):
            print(f"[{iss.get('severity')}] {iss.get('rule_id')}: {iss.get('message')}")
        else:
            print(f"[{iss.severity}] {iss.rule_id}: {iss.message}")
        
    print("\nMT103+ Issues Details:")
    for iss in rep103p.issues:
        if isinstance(iss, dict):
            print(f"[{iss.get('severity')}] {iss.get('rule_id')}: {iss.get('message')}")
        else:
            print(f"[{iss.severity}] {iss.rule_id}: {iss.message}")
    with open("scratch/mt103p.xml", "w") as f:
        f.write(xml103p)

    print("\nTesting BIC rule manually on MT103+:")
    bic_rules = [r for r in l3_rules103p if r.get('type') == 'bic']
    if bic_rules:
        bic_rule = bic_rules[0]
        from app.services.models import ValidationReport
        test_report = ValidationReport("test", "test", "test")
        validator._execute_rule_logic(bic_rule, canon103p, {}, validator.codelists, test_report)
        print(f"Manual test issues: {len(test_report.issues)}")
        for iss in test_report.issues:
            print(iss)

    print("\nMT103+ Layer Status:", rep103p.layer_status)

asyncio.run(main())
