from lxml import etree
import os

xsd_path = 'xsds/extracted/pacs.008.001.08.xsd'
if not os.path.exists(xsd_path):
    # Try alternate path if not in backend
    xsd_path = '../xsds/extracted/pacs.008.001.08.xsd'

xml = """<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
<FIToFICstmrCdtTrf>
    <GrpHdr>
        <MsgId>M1</MsgId>
        <MsgId>M2</MsgId>
        <CreDtTm>2026-03-02T10:35:00+00:00</CreDtTm>
        <NbOfTxs>1</NbOfTxs>
        <SttlmInf><SttlmMtd>INDA</SttlmMtd></SttlmInf>
    </GrpHdr>
</FIToFICstmrCdtTrf>
</Document>"""

try:
    print(f"Checking XSD at: {xsd_path}")
    schema = etree.XMLSchema(etree.parse(xsd_path))
    parser = etree.XMLParser(remove_blank_text=True)
    root = etree.fromstring(xml.encode('utf-8'), parser)
    schema.assertValid(root)
    print("XML is valid")
except Exception as e:
    print("Caught Exception")
    if hasattr(e, 'error_log'):
        for error in e.error_log:
            print(f"ERROR: {error.message}")
            print(f"LINE: {error.line}")
    else:
        print(f"ERROR: {str(e)}")
