
from lxml import etree

xml = """<?xml version="1.0" encoding="UTF-8"?>
<root>
  <header>ignore</header>
  <payload>
    <item>val</item>
    <emptyItem></emptyItem>
  </payload>
</root>"""

xsd_str = """<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="payload">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="item" type="xs:string"/>
        <xs:element name="emptyItem">
          <xs:simpleType>
            <xs:restriction base="xs:string">
              <xs:minLength value="1"/>
            </xs:restriction>
          </xs:simpleType>
        </xs:element>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>"""

doc = etree.fromstring(xml.encode())
payload = doc.find("payload")
xsd = etree.XMLSchema(etree.fromstring(xsd_str.encode()))

try:
    xsd.assertValid(payload)
except etree.DocumentInvalid as e:
    for err in e.error_log:
        print(f"Error Line: {err.line}")
