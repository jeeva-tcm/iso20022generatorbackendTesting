
from lxml import etree
import re
import os

# Create a dummy XSD that mimics the constraint on Cd
xsd_content = """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
    <xs:element name="Cd">
        <xs:simpleType>
            <xs:restriction base="xs:string">
                <xs:maxLength value="4"/>
            </xs:restriction>
        </xs:simpleType>
    </xs:element>
</xs:schema>"""

with open("temp_cd.xsd", "w") as f:
    f.write(xsd_content)

xml_content = "<Cd>Passport</Cd>"
schema = etree.XMLSchema(etree.parse("temp_cd.xsd"))
parser = etree.XMLParser(schema=schema)

try:
    etree.fromstring(xml_content.encode('utf-8'), parser)
except etree.XMLSyntaxError as e:
    # This usually happens for well-formedness. For validation we use schema.validate
    pass

doc = etree.fromstring(xml_content.encode('utf-8'))
if not schema.validate(doc):
    for error in schema.error_log:
        print(f"RAW ERROR: {error.message}")
        msg = error.message
        # Test my bad_value logic again
        def bad_value(msg):
            m = re.search(r"(?:[Vv]alue|The\s+value)\s+'([^']*)'", msg)
            if m:
                val = m.group(1)
                if not (val.isdigit() and len(val) < 4):
                     return val
            quotes = re.findall(r"'([^']*)'", msg)
            if quotes:
                ignore = {'facet', 'enumeration', 'maxLength', 'minLength', 'pattern', 'base', 'type', 
                          'atomic', 'element', 'attribute', 'length', 'exceeds', 'allowed', 
                          'maximum', 'Identifier', 'value', 'Cd'}
                candidates = []
                for q in quotes:
                    clean = q.split('}')[-1] if '}' in q else q
                    if clean not in ignore: # wait, 'Cd' is tag_name
                        if not(clean.isdigit() and len(clean) < 4):
                             candidates.append(q)
                if candidates:
                    return max(candidates, key=len)
            return "STILL_NOT_FOUND"

        print(f"EXTRACTED: {bad_value(msg)}")
