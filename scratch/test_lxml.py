from lxml import etree
import sys

xsd_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns="urn:iso:std:iso:20022:tech:xsd:camt.054.001.08" xmlns:xs="http://www.w3.org/2001/XMLSchema" elementFormDefault="qualified" targetNamespace="urn:iso:std:iso:20022:tech:xsd:camt.054.001.08">
    <xs:element name="Document" type="BankToCustomerDebitCreditNotificationV08"/>
    <xs:complexType name="BankToCustomerDebitCreditNotificationV08">
        <xs:sequence>
            <xs:element name="BkToCstmrDbtCdtNtfctn" type="xs:string"/>
        </xs:sequence>
    </xs:complexType>
</xs:schema>"""

xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.08">
    <BkToCstmrStmt>Hello</BkToCstmrStmt>
</Document>"""

try:
    schema_doc = etree.fromstring(xsd_content)
    schema = etree.XMLSchema(schema_doc)
    doc = etree.fromstring(xml_content)
    schema.assertValid(doc)
except etree.DocumentInvalid as e:
    print("Document Invalid!")
    for err in e.error_log:
        print("LXML ERROR:", err.message)
except Exception as e:
    print("Other error:", e)
