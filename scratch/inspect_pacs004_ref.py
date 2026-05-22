import xml.etree.ElementTree as ET

tree = ET.parse('xsds/extracted/pacs.004.001.14.xsd')
root = tree.getroot()

ns = {'xs': 'http://www.w3.org/2001/XMLSchema'}

for ct in root.findall('.//xs:complexType', ns):
    name = ct.get('name', '')
    if 'OriginalTransactionReference' in name:
        print(f"Found complexType: {name}")
        for elem in ct.findall('.//xs:element', ns):
            print(f"  Element: name={elem.get('name')}, type={elem.get('type')}, minOccurs={elem.get('minOccurs')}, maxOccurs={elem.get('maxOccurs')}")
