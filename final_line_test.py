
from lxml import etree
import copy

xml = """
<root>
  <header>ignore</header>
  <payload>
    <item>valid</item>
    <emptyId></emptyId>
  </payload>
</root>"""

parser = etree.XMLParser(remove_blank_text=False)
doc = etree.fromstring(xml.strip().encode(), parser)
payload = doc.find("payload")

print(f"Payload sourceline: {payload.sourceline}") # Should be 4 if we strip()
# Wait, let's keep it exact.
xml = """
<root>
  <header>ignore</header>
  <payload>
    <item>valid</item>
    <emptyId></emptyId>
  </payload>
</root>"""
doc = etree.fromstring(xml.encode(), parser)
payload = doc.find("payload")

# <root> is line 2
# <header> is line 3
# <payload> is line 4

print(f"Original payload line: {payload.sourceline}") 
print(f"Original emptyId line: {payload.find('emptyId').sourceline}")

payload_copy = copy.deepcopy(payload)
print(f"Copy payload line: {payload_copy.sourceline}")
print(f"Copy emptyId line: {payload_copy.find('emptyId').sourceline}")

xsd_str = """<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="payload">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="item" type="xs:string"/>
        <xs:element name="emptyId">
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

schema = etree.XMLSchema(etree.fromstring(xsd_str.encode()))
try:
    schema.assertValid(payload_copy)
except etree.DocumentInvalid as e:
    for err in e.error_log:
        print(f"Error line: {err.line}")
