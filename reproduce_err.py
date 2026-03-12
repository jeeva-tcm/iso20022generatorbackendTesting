
from lxml import etree
import re

# Define a schema with a restricted Cd element
xsd_str = """
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="Cd">
    <xs:simpleType>
      <xs:restriction base="xs:string">
        <xs:enumeration value="LEI"/>
        <xs:enumeration value="CUST"/>
        <xs:maxLength value="4"/>
      </xs:restriction>
    </xs:simpleType>
  </xs:element>
</xs:schema>
"""
schema = etree.XMLSchema(etree.fromstring(xsd_str.encode()))

# invalid XML
xml = "<Cd>Passport</Cd>"
doc = etree.fromstring(xml.encode())

try:
    schema.assertValid(doc)
except etree.DocumentInvalid as e:
    with open("error_log.txt", "w") as f:
        for err in e.error_log:
            f.write(f"MESSAGE: {err.message}\n")
            
            # Now test bad_value logic
            msg = err.message
            
            def bad_value(default=""):
                m = re.search(r"[Vv]alue\s+'([^']*)'", msg)
                if m: return m.group(1)
                m = re.search(r"Element\s+'[^']+':\s*'([^']*)'", msg)
                if m: return m.group(1)
                m = re.search(r":\s*'([^']*)'", msg)
                return m.group(1) if m else default

            def elem_name(default="A field"):
                m = re.search(r"Element '([^']+)'", msg)
                if not m: return default
                raw = m.group(1)
                return raw.split('}')[-1] if '}' in raw else raw

            raw_val = bad_value(default="___NOT_EMPTY___")
            f.write(f"BAD_VALUE: {raw_val}\n")
            f.write(f"ELEM_NAME: {elem_name()}\n")
            
            if raw_val == "" or (raw_val == "___NOT_EMPTY___" and ("''" in msg or '""' in msg)):
                f.write("MATCHED EMPTY CHECK 1\n")
