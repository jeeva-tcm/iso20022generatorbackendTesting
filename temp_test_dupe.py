from lxml import etree

xml = """<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
<FIToFICstmrCdtTrf>
    <GrpHdr>
        <MsgId>M</MsgId>
        <MsgId>M2</MsgId>
        <CreDtTm>2026-03-02T10:35:00+00:00</CreDtTm>
        <NbOfTxs>1</NbOfTxs>
        <SttlmInf><SttlmMtd>INDA</SttlmMtd></SttlmInf>
    </GrpHdr>
    <CdtTrfTxInf>
        <PmtId><InstrId>1</InstrId><EndToEndId>1</EndToEndId><TxId>1</TxId></PmtId>
        <IntrBkSttlmAmt Ccy="USD">1</IntrBkSttlmAmt>
        <ChrgBr>SLEV</ChrgBr>
    </CdtTrfTxInf>
</FIToFICstmrCdtTrf>
</Document>"""
try:
    schema = etree.XMLSchema(file='xsds/extracted/pacs.008.001.08.xsd')
    doc = etree.fromstring(xml.encode('utf-8'))
    schema.assertValid(doc)
except Exception as e:
    for err in getattr(e, 'error_log', [e]):
        print(f"LXML Error: {err.message}")
