
import copy
from lxml import etree

xml = """<root>
  <child>val</child>
  <other>
    <subChild>val</subChild>
  </other>
</root>"""

parser = etree.XMLParser(remove_blank_text=False)
root = etree.fromstring(xml.encode(), parser)

root_copy = copy.deepcopy(root)

with open("output_test.txt", "w") as f:
    f.write(f"Original: {root[0].tag}, line {root[0].sourceline}\n")
    f.write(f"Copy: {root_copy[0].tag}, line {root_copy[0].sourceline}\n")
