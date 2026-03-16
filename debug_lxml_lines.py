
from lxml import etree
import copy
import sys

# XML with some leading lines to create an offset
xml = """<?xml version="1.0" encoding="UTF-8"?>
<root>
  <ignored>
    <data>nothing</data>
  </ignored>
  <payload>
    <item>valid</item>
    <emptyId></emptyId>
  </payload>
</root>"""

# XSD that validates the <payload> element
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

def run_test():
    with open("test_results.txt", "w") as f:
        parser = etree.XMLParser(remove_blank_text=False)
        doc = etree.fromstring(xml.encode(), parser)
        payload = doc.find("payload")

        f.write(f"Payload starts at absolute line: {payload.sourceline}\n") # Expected 7
        empty_id = payload.find("emptyId")
        f.write(f"emptyId is at absolute line: {empty_id.sourceline}\n") # Expected 9

        # Case 1: Validate a deepcopy of the fragment
        f.write("\n--- Case 1: Deepcopy Fragment ---\n")
        payload_copy = copy.deepcopy(payload)
        f.write(f"Copy root line: {payload_copy.sourceline}\n")
        f.write(f"Copy emptyId line: {payload_copy.find('emptyId').sourceline}\n")

        schema = etree.XMLSchema(etree.fromstring(xsd_str.encode()))
        try:
            schema.assertValid(payload_copy)
        except etree.DocumentInvalid as e:
            for err in e.error_log:
                f.write(f"Error line reported by lxml: {err.line}\n")
                # Current logic in layer2_validator.py:
                # real_line = line_offset + error.line - 1
                line_offset = payload.sourceline
                calculated_abs = line_offset + err.line - 1
                f.write(f"Calculated absolute line (offset={line_offset}): {calculated_abs}\n")

        # Case 2: Validate the original fragment (by reference)
        f.write("\n--- Case 2: Original Fragment Reference ---\n")
        try:
            schema.assertValid(payload)
        except etree.DocumentInvalid as e:
            for err in e.error_log:
                f.write(f"Error line reported by lxml: {err.line}\n")
                line_offset = payload.sourceline
                calculated_abs = line_offset + err.line - 1
                f.write(f"Calculated absolute line (offset={line_offset}): {calculated_abs}\n")

if __name__ == "__main__":
    run_test()
