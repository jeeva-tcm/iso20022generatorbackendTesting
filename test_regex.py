import re

mt_message = "{1:F01BBBBUS33AXXX0000000000}{2:I#CCCCGB2LXXXXN}\\n:20:REF17\\n:32A:261231USD1500,00\\n:50K:/US\\nSENDER\\n:59:/GB\\nREC\\n:71A:SHA\\n-}"

pattern = re.compile(r"^:([0-9]{2}[a-zA-Z]?):(.*?(?=\n:[0-9]{2}[a-zA-Z]?:|\Z))", re.MULTILINE | re.DOTALL)

print("Starting regex...")
for match in pattern.finditer(mt_message):
    print("Found:", match.group(1))
print("Regex done.")
