import asyncio
from app.services.mt_mx_converter import MT2MXConverter
from app.services.validator import ISOValidator

async def main():
    converter = MT2MXConverter()
    val = ISOValidator()
    
    # Minimal MT103
    mt = """{1:F01BANKDEFMAXXX0000000000}{2:I103BANKGHU0XXXXN}{4:
:20:123456
:23B:CRED
:32A:210310USD100,00
:50K:/12345678
SMITH CORP
:59:/87654321
JOHN DOE
:71A:SHA
-}"""

    res = converter.validate_and_convert(mt)
    mx = res.get("mx_message")
    if not mx:
        print("No MX generated!")
        print(res)
        return
        
    print("Validating MX...")
    try:
        report = await val.validate(mx)
        print("Success:", report.status)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
