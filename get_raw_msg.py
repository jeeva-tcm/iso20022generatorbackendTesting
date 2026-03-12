
from lxml import etree
xsd_str = '<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"><xs:element name="Cd"><xs:simpleType><xs:restriction base="xs:string"><xs:maxLength value="4"/></xs:restriction></xs:simpleType></xs:element></xs:schema>'
xsd = etree.XMLSchema(etree.fromstring(xsd_str))
doc = etree.fromstring('<Cd>Passport</Cd>')
xsd.validate(doc)
print(f"RAW: {xsd.error_log[0].message}")
