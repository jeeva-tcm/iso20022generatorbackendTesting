
from lxml import etree
import copy

xml = """<root>
  <child>val</child>
  <target>
    <item>val</item>
  </target>
</root>"""

parser = etree.XMLParser(remove_blank_text=False)
root = etree.fromstring(xml.encode(), parser)
target = root.find("target")

print(f"Original target line: {target.sourceline}")

target_copy = copy.deepcopy(target)
print(f"Copy target line: {target_copy.sourceline}")

# Check if Schema validation on the copy returns original lines
xsd_str = """<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="target">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="item">
          <xs:simpleType>
            <xs:restriction base="xs:string">
              <xs:length value="10"/>
            </xs:restriction>
          </xs:simpleType>
        </xs:element>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>"""

schema = etree.XMLSchema(etree.fromstring(xsd_str.encode()))
try:
    schema.assertValid(target_copy)
except etree.DocumentInvalid as e:
    for err in e.error_log:
        print(f"Error line: {err.line}")
