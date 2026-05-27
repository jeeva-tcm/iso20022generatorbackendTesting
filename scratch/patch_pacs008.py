import os

file_path = r'c:\Users\HP\Desktop\iso final\iso20022generatorbackend\app\services\mt_mx_converter.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Insert the method call right after _heal_camt_mandatory_fields
call_to_insert = "        self._heal_pacs008_mandatory_fields(mx_root, namespaces)\n"
if "self._heal_pacs008_mandatory_fields(mx_root, namespaces)" not in content:
    content = content.replace(
        "        self._heal_camt_mandatory_fields(mx_root, namespaces)\n",
        "        self._heal_camt_mandatory_fields(mx_root, namespaces)\n" + call_to_insert
    )

# 2. Append the new method to the end of the file
method_to_append = """
    def _heal_pacs008_mandatory_fields(self, root, namespaces):
        \"\"\"
        CBPR+ PACS008 rules require Dbtr/Nm and Cdtr/Nm.
        If MT103 provides only 50A or 59A (BIC only without name), the Name element will be missing.
        This healing injects NOTPROVIDED into Dbtr/Nm and Cdtr/Nm if they are missing for pacs.008.
        \"\"\"
        xmlns = namespaces.get("xmlns", "")
        if "pacs.008" not in xmlns:
            return
            
        for tx_inf in root.iter(f"{{{xmlns}}}CdtTrfTxInf" if xmlns else "CdtTrfTxInf"):
            # Heal Dbtr/Nm
            dbtr = self._find_child(tx_inf, "Dbtr")
            if dbtr is None:
                dbtr_tag = f"{{{xmlns}}}Dbtr" if xmlns else "Dbtr"
                dbtr = ET.SubElement(tx_inf, dbtr_tag)
                
            nm = self._find_child(dbtr, "Nm")
            if nm is None or not nm.text or not nm.text.strip():
                if nm is None:
                    nm_tag = f"{{{xmlns}}}Nm" if xmlns else "Nm"
                    # Insert Nm as the first child of Dbtr (or right after Id)
                    # For simplicity, we just append it, the final recursive sort will fix its position
                    nm = ET.SubElement(dbtr, nm_tag)
                nm.text = "NOTPROVIDED"

            # Heal Cdtr/Nm
            cdtr = self._find_child(tx_inf, "Cdtr")
            if cdtr is None:
                cdtr_tag = f"{{{xmlns}}}Cdtr" if xmlns else "Cdtr"
                cdtr = ET.SubElement(tx_inf, cdtr_tag)
                
            cdtr_nm = self._find_child(cdtr, "Nm")
            if cdtr_nm is None or not cdtr_nm.text or not cdtr_nm.text.strip():
                if cdtr_nm is None:
                    nm_tag = f"{{{xmlns}}}Nm" if xmlns else "Nm"
                    cdtr_nm = ET.SubElement(cdtr, nm_tag)
                cdtr_nm.text = "NOTPROVIDED"
"""

if "_heal_pacs008_mandatory_fields" not in content.split("def _heal_camt_mandatory_fields")[1]: # just checking it's not already at the end
    content += method_to_append

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Added _heal_pacs008_mandatory_fields to mt_mx_converter.py")
