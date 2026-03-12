
from lxml import etree

xml = """<?xml version="1.0" encoding="UTF-8"?>
<root>
  <header>ignore me</header>
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

parser = etree.XMLParser(remove_blank_text=False)
doc = etree.fromstring(xml.encode(), parser)
payload = doc.find("payload")

print(f"Doc root line: {doc.sourceline}")
print(f"Payload line: {payload.sourceline}")
print(f"EmptyItem line: {payload[1].sourceline}")

xsd = etree.XMLSchema(etree.fromstring(xsd_str.encode()))

try:
    xsd.assertValid(payload)
except etree.DocumentInvalid as e:
    for err in e.error_log:
        print(f"Error at line {err.line}: {err.message}")
