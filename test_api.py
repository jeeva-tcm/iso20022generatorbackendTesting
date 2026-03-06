import asyncio
import os
import sys
import traceback
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

with open('python_logs.txt', 'w', encoding='utf-8') as flog:
    sys.stdout = flog
    sys.stderr = flog

    from app.services.validator import ISOValidator

    async def run():
        validator = ISOValidator()
        print("Testing latest.xml")
        
        with open('latest.xml', 'r', encoding='utf-8') as f:
            xml = f.read()
        
        report = await validator.validate(xml, "Full 1-3", "Auto-detect", "latest.xml")
        for i in report.issues:
            print(f"ISSUE [{i['layer']}] {i['severity']} {i['message']} {i['code']}")

    if __name__ == "__main__":
        try:
            asyncio.run(run())
        except Exception as e:
            traceback.print_exc()
