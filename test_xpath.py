from lxml import etree
import traceback

root = etree.fromstring('<root><a>1</a></root>')
try:
    node = root.find(".//{*}tag")
except Exception as e:
    print(f"Error: {e}")
