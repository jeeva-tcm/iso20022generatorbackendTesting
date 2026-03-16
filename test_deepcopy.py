
from lxml import etree
import copy

xml = """<?xml version='1.0' encoding='utf-8'?>
<root>
    <child>
        <grandchild>
        </grandchild>
    </child>
    <child>
    </child>
</root>"""

parser = etree.XMLParser(remove_blank_text=False)
doc = etree.fromstring(xml.encode('utf-8'), parser)

with open("test_out.txt", "w") as f:
    f.write(f"Original root line: {doc.sourceline}\n")
    for i, child in enumerate(doc.xpath("//child")):
        f.write(f"Original child {i} line: {child.sourceline}\n")

    doc_copy = copy.deepcopy(doc)
    f.write(f"Copy root line: {doc_copy.sourceline}\n")
    for i, child in enumerate(doc_copy.xpath("//child")):
        f.write(f"Copy child {i} line: {child.sourceline}\n")
