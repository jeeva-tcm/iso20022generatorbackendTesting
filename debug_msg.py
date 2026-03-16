
from lxml import etree
import re

xsd_str = """
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="Cd">
    <xs:simpleType>
      <xs:restriction base="xs:string">
        <xs:maxLength value="4"/>
      </xs:restriction>
    </xs:simpleType>
  </xs:element>
</xs:schema>
"""
schema = etree.XMLSchema(etree.fromstring(xsd_str.encode()))
xml = "<Cd>Passport</Cd>"
doc = etree.fromstring(xml.encode())

try:
    schema.assertValid(doc)
except etree.DocumentInvalid as e:
    for err in e.error_log:
        msg = err.message
        print(f"MSG: {msg}")
        quotes = re.findall(r"'([^']*)'", msg)
        print(f"QUOTES: {quotes}")
