import re
import os
import json
import xml.etree.ElementTree as ET
from datetime import datetime

class MTMXConversionError(Exception):
    pass

class MT2MXConverter:
    def __init__(self, mappings_dir: str = None):
        if mappings_dir is None:
            # Default to the mappings folder alongside services
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.mappings_dir = os.path.join(base_dir, "mappings")
        else:
            self.mappings_dir = os.path.abspath(mappings_dir)

    def detect_mt_type(self, mt_message: str) -> str:
        """
        Attempts to detect the MT type from Block 2 (e.g. {2:I103...} or {2:O103...})
        If not found, fall back to looking for a common tag or asking user.
        For simplicity, if '{2:' is not there but we see tags like :32A:, :50K:, we might guess, 
        but let's do a strict or explicit detection.
        """
        match = re.search(r"\{2:[IO]([0-9]{3})", mt_message)
        if match:
            return match.group(1)
        
        # Fallback heuristic if headers are stripped: 
        # Check standard fields. If :50K: and :59: are present, maybe 103.
        # But for robustness, we can require the user to pass it if detection fails.
        return None

    def parse_mt_blocks(self, mt_message: str) -> dict:
        """
        Parses the text block of an MT message (Block 4) into a dictionary of tags.
        """
        fields = {}
        # Simple parser looking for :TAG: value
        # This regex looks for :2-3 chars + optional letter: at start of line
        pattern = re.compile(r"^:([0-9]{2}[a-zA-Z]?):(.*?(?=\n:[0-9]{2}[a-zA-Z]?:|\Z))", re.MULTILINE | re.DOTALL)
        
        # If message has {4: ... -}, extract just block 4
        block4_match = re.search(r"\{4:(.*?)\-?\}", mt_message, re.DOTALL)
        text_to_parse = block4_match.group(1) if block4_match else mt_message
        
        for match in pattern.finditer(text_to_parse):
            tag = match.group(1)
            value = match.group(2).strip()
            # If tag already exists, in a real system we might use lists. 
            # For simplicity, we overwrite or append. Let's append to a list.
            if tag in fields:
                if isinstance(fields[tag], list):
                    fields[tag].append(value)
                else:
                    fields[tag] = [fields[tag], value]
            else:
                fields[tag] = value
                
        return fields

    def load_mapping(self, mt_type: str) -> dict:
        mt_type = str(mt_type).strip()
        path = os.path.normpath(os.path.join(self.mappings_dir, f"MT{mt_type}.json"))
        
        if not os.path.exists(path):
            available = []
            if os.path.exists(self.mappings_dir):
                available = os.listdir(self.mappings_dir)
            
            raise MTMXConversionError(
                f"No mapping configuration found for MT{mt_type}. "
                f"Expected at {path}. "
                f"Available in {self.mappings_dir}: {available}"
            )
            
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def set_element_text(self, root: ET.Element, path: str, text: str, namespaces: dict):
        """
        Navigates or creates the XML path and sets the text.
        path is something like "FIToFICstmrCdtTrf/CdtTrfTxInf/PmtId/InstrId"
        """
        parts = path.split("/")
        current = root
        
        # Use namespace prefix if needed, but here we just create elements in the default namespace
        xmlns = namespaces.get("xmlns", "")
        
        for i, part in enumerate(parts):
            # Check if child exists
            # ElementTree grouping with namespaces can be tricky.
            # We will create tags with the full namespace URI: {urn:iso...}tag
            tag_with_ns = f"{{{xmlns}}}{part}" if xmlns else part
            
            child = current.find(tag_with_ns)
            if child is None:
                child = ET.SubElement(current, tag_with_ns)
            
            current = child
            
            if i == len(parts) - 1:
                current.text = text

    def set_element_attr(self, root: ET.Element, path: str, attr: str, attr_val: str, text: str, namespaces: dict):
        parts = path.split("/")
        current = root
        xmlns = namespaces.get("xmlns", "")
        for i, part in enumerate(parts):
            tag_with_ns = f"{{{xmlns}}}{part}" if xmlns else part
            child = current.find(tag_with_ns)
            if child is None:
                child = ET.SubElement(current, tag_with_ns)
            current = child
            if i == len(parts) - 1:
                current.text = text
                current.set(attr, attr_val)


    def validate_and_convert(self, mt_message: str, forced_mt_type: str = None) -> dict:
        mt_type = forced_mt_type or self.detect_mt_type(mt_message)
        if mt_type:
            # Strip MT prefix if present (e.g. MT103 -> 103, MT202COV -> 202COV)
            mt_type = re.sub(r'^MT', '', str(mt_type).strip(), flags=re.IGNORECASE)
            
        if not mt_type:
            # Fallback guessing if there's no header
            if ":50K:" in mt_message and ":59:" in mt_message:
                mt_type = "103"
            elif ":58A:" in mt_message and ":21:" in mt_message:
                mt_type = "202"
            else:
                return {"status": "error", "errors": ["Could not automatically detect MT message type. Please provide valid MT headers or specify type."]}

        try:
            mapping = self.load_mapping(mt_type)
        except MTMXConversionError as e:
            return {"status": "error", "errors": [str(e)]}

        parsed_fields = self.parse_mt_blocks(mt_message)
        errors = []
        
        # Setup XML Root
        namespaces = mapping.get("xml_namespaces", {})
        xmlns = namespaces.get("xmlns", "")
        root_tag = mapping["root_element"]
        mx_root = ET.Element(f"{{{xmlns}}}{root_tag}" if xmlns else root_tag)

        # Parse SWIFT block 1 and 2 for AppHdr sender/receiver
        block1_match = re.search(r"\{1:([A-Z0-9]+)\}", mt_message)
        if block1_match:
            b1 = block1_match.group(1)
            parsed_fields["_senderBic"] = b1[3:11] + ("XXX" if len(b1) <= 11 else b1[11:14] or "XXX")
            
        block2_match = re.search(r"\{2:([A-Z0-9]+)\}", mt_message)
        if block2_match:
            b2 = block2_match.group(1)
            if b2.startswith("I"):
                receiver = b2[4:12]
                parsed_fields["_receiverBic"] = receiver + ("XXX" if len(b2) < 15 else b2[12:15] or "XXX")
            else:
                receiver = b2[14:22]
                parsed_fields["_receiverBic"] = receiver + ("XXX" if len(b2) < 25 else b2[22:25] or "XXX")

        # Process mapping rules
        for rule in mapping.get("mappings", []):
            tag = rule["mt_tag"]
            is_mandatory = rule.get("mandatory", False)
            
            # Get the value
            if tag.startswith("_timestamp"):
                val = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00")
            elif tag.startswith("_static"):
                val = rule.get("value", "")
            else:
                if tag not in parsed_fields:
                    fallback = rule.get("fallback_tag")
                    if fallback and fallback in parsed_fields:
                        val = parsed_fields[fallback]
                    elif is_mandatory:
                        errors.append(f"Missing mandatory field :{tag}: ({rule.get('name')})")
                        continue
                    else:
                        continue
                else:
                    val = parsed_fields[tag]
                if isinstance(val, list):
                    val = val[0]
                
                if is_mandatory and (not val or not str(val).strip()):
                    errors.append(f"Mandatory field :{tag}: ({rule.get('name')}) is empty. Please provide a value.")
                    continue
                
            # Validate & Map
            rule_type = rule.get("type", "text")
            
            if rule_type == "static" or rule_type == "timestamp":
                # Path set direct
                self.set_element_text(mx_root, rule["mx_path"], val, namespaces)
                continue

            if rule_type == "text":
                max_len = rule.get("max_length")
                
                # Standard SWIFT MT to MX Code Translations
                # 1. Details of Charges (71A)
                if tag == "71A" and "ChrgBr" in rule.get("mx_path", ""):
                    charge_map = {"SHA": "SHAR", "OUR": "DEBT", "BEN": "CRED"}
                    val = charge_map.get(val.upper(), val)
                
                # 2. Add more translations as needed (e.g. 23B/CRED -> standard codes)
                
                self.set_element_text(mx_root, rule["mx_path"], val.replace("\\n", "\n"), namespaces)
                continue
            elif rule_type == "date_currency_amount":
                # MT Format: YYMMDDCCYY[amount] (e.g. 230915USD10000,50)
                # Amount comma replacement
                if len(val) < 10:
                    errors.append(f"Invalid date/currency/amount format in field :{tag}:")
                    continue
                    
                date_str = val[0:6]
                currency = val[6:9]
                amount_str = val[9:].replace(",", ".")
                
                # Check date
                try:
                    dt = datetime.strptime(date_str, "%y%m%d")
                    iso_date = dt.strftime("%Y-%m-%d")
                except ValueError:
                    errors.append(f"Invalid date format in field :{tag}:")
                    continue
                    
                # Check Currency (simple A-Z 3 char check)
                if not re.match(r"^[A-Z]{3}$", currency):
                    errors.append(f"Invalid currency code '{currency}' in field :{tag}:")
                    continue
                
                # Check amount
                try:
                    float(amount_str)
                except ValueError:
                    errors.append(f"Invalid amount format '{amount_str}' in field :{tag}:")
                    continue
                
                self.set_element_attr(mx_root, rule["mx_path_amount"], rule["currency_attribute"], currency, amount_str, namespaces)
                self.set_element_text(mx_root, rule["mx_path_date"], iso_date, namespaces)
                
            elif rule_type == "account_name_address":
                # Extremely simplified MT Name & Address parsing (e.g., /ACCOUNT\nNAME\nADDRESS)
                lines = val.split("\n", 1)
                if val.startswith("/"):
                    account = lines[0][1:]
                    rest = lines[1] if len(lines) > 1 else ""
                else:
                    account = "UNKNOWN"
                    rest = val
                
                name_addr = rest.split("\n", 1)
                name = name_addr[0]
                address = name_addr[1] if len(name_addr) > 1 else ""
                
                if "mx_path_name" in rule and name:
                    self.set_element_text(mx_root, rule["mx_path_name"], name, namespaces)
                if "mx_path_address" in rule and address:
                    self.set_element_text(mx_root, rule["mx_path_address"], address.replace("\n"," "), namespaces)
                if "mx_path_account" in rule and account:
                    self.set_element_text(mx_root, rule["mx_path_account"], account, namespaces)

            elif rule_type == "date":
                # MT Format: YYMMDD
                try:
                    dt = datetime.strptime(val, "%y%m%d")
                    iso_date = dt.strftime("%Y-%m-%d")
                    self.set_element_text(mx_root, rule["mx_path"], iso_date, namespaces)
                except ValueError:
                    errors.append(f"Invalid date format in field :{tag}: '{val}'")

            elif rule_type == "currency_amount":
                # MT Format: CCC[amount] (e.g. USD1234,56)
                if len(val) < 4:
                    errors.append(f"Invalid currency/amount format in field :{tag}:")
                    continue
                currency = val[0:3]
                amount_str = val[3:].replace(",", ".")
                try:
                    float(amount_str)
                    self.set_element_attr(mx_root, rule["mx_path"], rule["currency_attribute"] if "currency_attribute" in rule else "Ccy", currency, amount_str, namespaces)
                except ValueError:
                    errors.append(f"Invalid amount format in field :{tag}:")

            elif rule_type == "balance":
                # MT Format: [D/C]YYMMDDCCCAmount
                if len(val) < 11:
                    errors.append(f"Invalid balance format in field :{tag}:")
                    continue
                # Skip [D/C] and Date (7 chars total)
                currency = val[7:10]
                amount_str = val[10:].replace(",", ".")
                try:
                    float(amount_str)
                    self.set_element_attr(mx_root, rule["mx_path"], rule["currency_attribute"] if "currency_attribute" in rule else "Ccy", currency, amount_str, namespaces)
                except ValueError:
                    errors.append(f"Invalid amount in balance field :{tag}:")

            elif rule_type == "bic":
                self.set_element_text(mx_root, rule["mx_path_bic"], val, namespaces)

        if errors:
            return {"status": "error", "errors": errors}
            
        # Create Envelope and AppHdr
        # We'll build the XML with explicitly defined default namespaces for subtrees
        # to ensure L2 validation passes even without prefixes.
        
        # 1. Start with the root Envelope
        envelope = ET.Element("{urn:swift:xsd:envelope}BusMsgEnvlp")
        
        # 2. Build AppHdr with its own namespace
        head_ns = "urn:iso:std:iso:20022:tech:xsd:head.001.001.02"
        app_hdr = ET.SubElement(envelope, f"{{{head_ns}}}AppHdr")
        
        sender_bic = parsed_fields.get("_senderBic", "UNKNOWN")
        receiver_bic = parsed_fields.get("_receiverBic", "UNKNOWN")
        
        # Helper to create sub-elements with head namespace
        def head_sub(parent, tag, text=None):
            el = ET.SubElement(parent, f"{{{head_ns}}}{tag}")
            if text: el.text = text
            return el

        fr = head_sub(app_hdr, "Fr")
        fr_fi = head_sub(fr, "FIId")
        fr_finst = head_sub(fr_fi, "FinInstnId")
        head_sub(fr_finst, "BICFI", sender_bic)
        
        to = head_sub(app_hdr, "To")
        to_fi = head_sub(to, "FIId")
        to_finst = head_sub(to_fi, "FinInstnId")
        head_sub(to_finst, "BICFI", receiver_bic)
        
        head_sub(app_hdr, "BizMsgIdr", parsed_fields.get("20", "UNKNOWN"))
        head_sub(app_hdr, "MsgDefIdr", mapping["target_mx"])
        head_sub(app_hdr, "BizSvc", mapping.get("biz_svc", "swift.cbprplus.02"))
        head_sub(app_hdr, "CreDt", datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S+00:00"))
        
        # 3. Handle Mandatory GrpHdr Agents in the Document part
        # If the mapping defines paths for InstgAgt/InstdAgt but they aren't filled yet,
        # we pro-actively fill them from headers to satisfy CBPR+ rules.
        for rule in mapping.get("mappings", []):
            if "InstgAgt" in rule.get("mx_path", "") and rule.get("mt_tag") not in parsed_fields:
               self.set_element_text(mx_root, rule["mx_path"], sender_bic, namespaces)
            if "InstdAgt" in rule.get("mx_path", "") and rule.get("mt_tag") not in parsed_fields:
               self.set_element_text(mx_root, rule["mx_path"], receiver_bic, namespaces)

        # 4. Attach the Data Document
        envelope.append(mx_root)
        
        # 5. Serialization with carefully managed namespaces
        ET.register_namespace("", "urn:swift:xsd:envelope")
        # We don't register head/doc prefixes so ET might generate ns0/ns1
        
        if hasattr(ET, "indent"):
            ET.indent(envelope, space="    ", level=0)
            
        xml_string = ET.tostring(envelope, encoding="utf-8", xml_declaration=True).decode("utf-8")
        
        # 6. Post-Process to ensure Local Default Namespaces
        # This replaces the blind prefix stripping with a logic that injects xmlns to the core containers
        # so L2 validation always finds the tags in the correct namespace.
        
        # Inject xmlns to AppHdr if missing
        if 'AppHdr' in xml_string:
            match = re.search(r'<(?:\w+:)?AppHdr[^>]*>', xml_string)
            if match and 'xmlns=' not in match.group(0):
                tag_str = match.group(0)
                new_tag = tag_str[:-1] + f' xmlns="{head_ns}">'
                xml_string = xml_string.replace(tag_str, new_tag)
            
        # Inject xmlns to the Document root (e.g. pacs.008)
        root_tag = mapping["root_element"]
        if root_tag in xml_string:
            doc_ns = mapping["xml_namespaces"].get("xmlns", "")
            match = re.search(r'<(?:\w+:)?' + root_tag + r'[^>]*>', xml_string)
            if match and 'xmlns=' not in match.group(0):
                tag_str = match.group(0)
                new_tag = tag_str[:-1] + f' xmlns="{doc_ns}">'
                xml_string = xml_string.replace(tag_str, new_tag)

        # FINAL: Remove any remaining ET suffixes (ns0:, ns1:) safely
        xml_string = re.sub(r'<(/?)\w+:', r'<\1', xml_string)
        xml_string = re.sub(r'(\s+)\w+:(\w+(?==))', r'\1\2', xml_string)
        

        return {
            "status": "success",
            "detected_type": mt_type,
            "mx_message": xml_string
        }
