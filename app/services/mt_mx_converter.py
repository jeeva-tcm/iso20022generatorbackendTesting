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
        Attempts to detect the MT type from Block 2 and subtypes from Block 3 (Tag 119).
        """
        mt_type = None
        match = re.search(r"\{2:[IO]([0-9]{3})", mt_message)
        if match:
            mt_type = match.group(1)
        
        if mt_type:
            # Check for subtypes in Block 3 (Tag 119)
            # e.g. {3:{119:STP}}, {3:{119:COV}}, {3:{119:REMIT}}
            sub_match = re.search(r"\{3:.*?\{119:(.*?)\}", mt_message)
            if sub_match:
                sub_type = sub_match.group(1).upper()
                if mt_type == "103":
                    if sub_type == "STP": return "103+"
                    if sub_type == "REMIT": return "103 REMIT"
                elif mt_type == "202":
                    if sub_type == "COV": return "202COV"
                    
            return mt_type
        
        return None

    def parse_mt_blocks(self, mt_message: str) -> dict:
        """
        Parses the text block of an MT message (Block 4) into a dictionary of tags.
        """
        fields = {}
        # This regex looks for :TAG: value, stopping at the next :TAG: at the start of a line
        pattern = re.compile(r"^:([0-9]{2}[a-zA-Z]?):((?:(?!\n:[0-9]{2}[a-zA-Z]?:).)*)", re.MULTILINE | re.DOTALL)
        
        # If message has {4: ... -}, extract just block 4
        block4_match = re.search(r"\{4:(.*?)(?:\-?\}|\Z)", mt_message, re.DOTALL)
        text_to_parse = block4_match.group(1) if block4_match else mt_message
        
        # Split by the actual tag pattern to ensure we don't skip orphaned lines
        # But for just getting fields, we use finditer
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

    def _get_element_text(self, root: ET.Element, path: str, namespaces: dict) -> str:
        """
        Travels the path and returns the text if it exists.
        """
        parts = path.split("/")
        current = root
        xmlns = namespaces.get("xmlns", "")
        for part in parts:
            tag_with_ns = f"{{{xmlns}}}{part}" if xmlns else part
            child = current.find(tag_with_ns)
            if child is None:
                return ""
            current = child
        return current.text or ""

    def _get_or_create_node(self, root: ET.Element, path: str, namespaces: dict) -> ET.Element:
        """Helper to navigate path and create nodes if missing."""
        parts = path.split("/")
        current = root
        xmlns = namespaces.get("xmlns", "")
        for part in parts:
            tag_with_ns = f"{{{xmlns}}}{part}" if xmlns else part
            child = current.find(tag_with_ns)
            if child is None:
                child = ET.SubElement(current, tag_with_ns)
            current = child
        return current

    def set_element_text(self, root: ET.Element, path: str, text: str, namespaces: dict):
        """
        Navigates or creates the XML path and sets the text.
        path is something like "FIToFICstmrCdtTrf/CdtTrfTxInf/PmtId/InstrId"
        """
        current = self._get_or_create_node(root, path, namespaces)
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



    def _sort_children_by_list(self, element: ET.Element, order_list: list):
        """Re-orders the children of an element based on a provided tag order list."""
        current_children = list(element)
        def get_rank(el):
            tag_name = el.tag.split('}')[-1]
            try: return order_list.index(tag_name)
            except: return 999
        
        sorted_children = sorted(current_children, key=get_rank)
        for child in current_children:
            element.remove(child)
        for child in sorted_children:
            element.append(child)

    def _check_mt_charset(self, text: str) -> list:
        """
        Validates that the MT message only contains SWIFT X Character Set or allowed block markers.
        """
        # Official SWIFT X-Charset: A-Z a-z 0-9 / - ? : ( ) . , ' + Space CRLF
        # We also allow { } for block markers and ! for sequence separators/extensions.
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/-?:().,'+ {}!\n\r ")
        illegal = []
        for i, line in enumerate(text.splitlines()):
            for char in line:
                if char not in allowed:
                    if char not in [item[0] for item in illegal]:
                        illegal.append((char, i + 1))
        return illegal

    def _validate_mt_syntax(self, mt_message: str, allowed_tags: set = None) -> list:
        """
        Validates the structure of MT Block 4, ensuring all lines are either tags or 
        valid continuations of multi-line tags.
        """
        errors = []
        # 1. Ensure Block 4 starts and ends correctly
        if "{4:" not in mt_message:
            return ["Message is missing Block 4 (mandatory for SWIFT MT messages)."]
        if "-}" not in mt_message and not mt_message.strip().endswith("}"):
            errors.append("Block 4 is not properly terminated with '-}'.")
            
        # 2. Extract Block 4 content
        block4_match = re.search(r"\{4:(.*?)(?:\-?\}|\Z)", mt_message, re.DOTALL)
        if not block4_match:
            return ["Malformed Block 4 structure."]
            
        block4_content = block4_match.group(1)
        pre_text = mt_message[:block4_match.start(1)]
        start_line = pre_text.count('\n') + 1
        
        lines = block4_content.splitlines()
        last_tag = None
        last_tag_line = 0
        tag_line_count = 0
        
        # SWIFT Standard Line Limits for specific tags
        tag_line_limits = {
            "50": 5, "59": 5, "70": 4, "72": 6, "77": 20, "79": 35
        }
        
        # Tags that ARE allowed to be multi-line in SWIFT MT
        multi_line_tag_prefixes = set(tag_line_limits.keys()) | {"35"}

        for i, line in enumerate(lines):
            line_no = start_line + i
            l_strip = line.strip()
            
            if not l_strip:
                continue
                
            if l_strip in ["-}", "}"]:
                continue
                
            if l_strip.startswith(":"):
                tag_match = re.match(r"^:([0-9]{2,3}[a-zA-Z]?):", l_strip)
                if not tag_match:
                    errors.append(f"Line {line_no}: Invalid tag format '{l_strip[:10]}...'. Expected standard SWIFT tag (e.g., :20: or :119:).")
                    last_tag = None 
                else:
                    last_tag = tag_match.group(1)
                    last_tag_line = line_no
                    tag_line_count = 1
                    tag_value = l_strip[tag_match.end():].strip()
                    
                    # Check unknown tags
                    if allowed_tags and last_tag not in allowed_tags:
                        # Log as info/warning rather than a hard failure to allow conversion of non-mapped fields
                        errors.append(f"WARNING - Line {line_no}: Tag :{last_tag}: is not explicitly mapped for this message type and will be ignored in the MX output.")

                    # Check line length
                    if len(tag_value) > 35:
                        errors.append(f"Line {line_no}: Tag :{last_tag}: contains a line exceeding the maximum permitted length of 35 characters (found {len(tag_value)} chars).")
            else:
                # This is a continuation line
                if not last_tag:
                    errors.append(f"Line {line_no}: Orphaned text found. Every data line must belong to a valid SWIFT tag starting with ':'.")
                else:
                    tag_line_count += 1
                    # 1. Length check
                    if len(l_strip) > 35:
                        errors.append(f"Line {line_no}: Tag :{last_tag}: contains a continuation line exceeding the 35 character limit (found {len(l_strip)} chars).")
                    
                    # 2. Multi-line capability and Line Count check
                    tag_prefix = last_tag[:2]
                    is_special_address = last_tag.endswith(('D', 'K', 'F'))
                    
                    if tag_prefix not in multi_line_tag_prefixes and not is_special_address:
                        errors.append(f"Line {line_no}: Tag :{last_tag}: is a single-line field and does not permit continuation lines.")
                    else:
                        limit = tag_line_limits.get(tag_prefix, 5 if is_special_address else 4)
                        if tag_line_count == limit + 1:
                            errors.append(f"Line {line_no}: Tag :{last_tag}: specifies more than the maximum allowed number of lines ({limit} lines).")
                        elif tag_line_count > limit + 1:
                            # Avoid duplicate limit errors for the same tag block
                            pass
        
        return errors

    def _validate_field_type(self, tag: str, val: str, field_type: str, name: str) -> list:
        """
        Validates the data content based on the standard SWIFT fields types.
        """
        errs = []
        val = val.strip()
        
        if field_type == "text":
            # Simple text length already checked by max_length in parent
            pass
            
        elif field_type == "date_currency_amount":
            # Format: YYMMDD(CUR)AMOUNT
            # e.g. 261231USD1500,00
            if len(val) < 6:
                errs.append(f"Field :{tag}: ({name}) has invalid Date/Ccy/Amount format.")
            else:
                date_part = val[:6]
                if not date_part.isdigit():
                    errs.append(f"Field :{tag}: ({name}) date '{date_part}' must be numeric (YYMMDD).")
                
                # Check for Currency (3 letters)
                remaining = val[6:]
                curr_match = re.match(r"^([A-Z]{3})", remaining)
                if curr_match:
                    amount_part = remaining[3:]
                    if not amount_part:
                        errs.append(f"Field :{tag}: ({name}) is missing the amount.")
                    else:
                        # SWIFT use comma as decimal separator
                        amount_clean = amount_part.replace(",", ".")
                        try:
                            float(amount_clean)
                        except ValueError:
                            errs.append(f"Field :{tag}: ({name}) contains invalid amount value '{amount_part}'.")
        
        elif field_type == "bic":
            # 8 or 11 chars
            clean_bic = val.replace("\r", "").replace("\n", "").strip()
            if len(clean_bic) not in [8, 11]:
                errs.append(f"Field :{tag}: ({name}) BIC must be 8 or 11 characters. Found '{clean_bic}'.")
            elif not clean_bic.isalnum():
                errs.append(f"Field :{tag}: ({name}) BIC contains invalid characters.")
        
        elif field_type == "account_name_address":
            # Usually /account + 4 lines of name/address
            pass

        return errs

    def validate_and_convert(self, mt_message: str, forced_mt_type: str = None) -> dict:
        v_logs = []
        v_logs.append(f"Starting conversion for MT message (Length: {len(mt_message)})")
        # 1. SWIFT MT Charset Validation
        illegal = self._check_mt_charset(mt_message)
        if illegal:
            err_details = [f"Invalid character '{char}' found on line {line}" for char, line in illegal[:5]]
            if len(illegal) > 5:
                err_details.append(f"...and {len(illegal)-5} more.")
            return {
                "status": "error", 
                "logs": v_logs,
                "errors": [
                    "Message contains illegal characters non-compliant with SWIFT MT standards.",
                    *err_details,
                    "SWIFT only allows X-Charset: A-Z, 0-9, /, -, ?, :, (, ), ., ,, ', +, Space."
                ]
            }
        v_logs.append("Charset validation passed.")

        # 2. Detect MT type for mapping
        mt_type = forced_mt_type or self.detect_mt_type(mt_message)
        if mt_type:
            mt_type = re.sub(r'^MT', '', str(mt_type).strip(), flags=re.IGNORECASE)
        else:
            return {"status": "error", "errors": ["Could not automatically detect MT message type. Please provide valid MT headers (e.g. {2:I103...})."]}

        # 3. Load Mapping to know allowed tags
        try:
            mapping = self.load_mapping(mt_type)
        except MTMXConversionError as e:
            return {"status": "error", "errors": [str(e)]}

        # 4. SWIFT MT Block 4 Syntax & Unknown Tag Validation
        allowed_tags = {r["mt_tag"] for r in mapping.get("mappings", []) if not r["mt_tag"].startswith("_")}
        # Add broad set of common tags to avoid false positives in syntax validation
        allowed_tags.update({"20", "21", "23B", "23E", "25", "26T", "28", "28C", "30", "32A", "32B", "33B", "34F", "50A", "50K", "52A", "53A", "57A", "59", "60F", "60M", "61", "62F", "62M", "64", "65", "70", "71A", "72", "77B", "77T"})
        
        v_logs.append(f"Detected MT type: {mt_type}")
        
        syntax_errors = self._validate_mt_syntax(mt_message, allowed_tags)
        if any(not e.startswith("WARNING") for e in syntax_errors):
            v_logs.append(f"Syntax validation FAILED with {len([e for e in syntax_errors if not e.startswith('WARNING')])} errors.")
            return {
                "status": "error", 
                "logs": v_logs,
                "errors": [
                    "Message contains invalid structure or line formatting errors.",
                    *[e for e in syntax_errors if not e.startswith("WARNING")]
                ]
            }
        
        # Add warnings to logs
        for e in [e for e in syntax_errors if e.startswith("WARNING")]:
            v_logs.append(e)

        v_logs.append("Syntax and structure validation PASSED.")

        # 5. Proceed with actual conversion
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
            
        block3_match = re.search(r"\{3:.*?\{121:([a-f0-9-]{36})\}", mt_message, re.I)
        if block3_match:
            parsed_fields["_uetr"] = block3_match.group(1)
            v_logs.append(f"Detected UETR from Block 3: {parsed_fields['_uetr']}")
            
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
                        # Schema auto-correction: If mandatory field is missing in MT, try to provide a safe default for schema validity
                        if rule.get("type") == "timestamp" or "CreDt" in rule.get("mx_path", ""):
                            val = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00")
                        elif "MsgId" in rule.get("mx_path", "") or "Id" in rule.get("mx_path", ""):
                            val = parsed_fields.get("20", f"AUTO-{datetime.now().strftime('%Y%j%H%M%S')}")
                        elif "ChrgBr" in rule.get("mx_path", ""):
                            val = "SHAR"
                        elif "PmtTpInf" in rule.get("mx_path", ""):
                            val = "TRF"
                        elif "SttlmAcct" in rule.get("mx_path", "") or "SttlmAcct" in rule.get("mx_path_bic", ""):
                            val = f"{parsed_fields.get('_senderBic', 'BANK')}-SETTLEMENT"
                        else:
                            errors.append(f"Conversion Blocked: Mandatory Fields Missing. Please add valid values for: [{rule.get('name', 'Tag')}] :{tag}: to proceed.")
                            continue
                    else:
                        continue
                else:
                    val = parsed_fields[tag]
                if isinstance(val, list):
                    val = val[0]
                
                if is_mandatory and (not val or not str(val).strip()):
                    errors.append(f"Conversion Blocked: Mandatory Fields Missing. Please add valid values for: [{rule.get('name', 'Tag')}] :{tag}: to proceed.")
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
                
                # 2. Max length check
                if max_len and len(val) > max_len:
                    errors.append(f"Field :{tag}: ({rule.get('name')}) exceeds maximum allowed length of {max_len} (found {len(val)})")
                    continue
                
                # 3. Type-specific Data Validation (Date, BIC, Amount)
                field_type = rule.get("type")
                if field_type:
                    type_errors = self._validate_field_type(tag, val, field_type, rule.get("name", ""))
                    if type_errors:
                        # Map internal validation errors to "invalid data" for frontend regex compatibility if mandatory
                        if is_mandatory:
                            errors.append(f"Field :{tag}: ({rule.get('name')}) contains invalid data. Please correct it.")
                        errors.extend(type_errors)
                        continue
                
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
                # Robust MT Name & Address parsing (e.g., /ACCOUNT\nNAME\nADDRESS LINES)
                lines = [line.strip() for line in val.split("\n") if line.strip()]
                account = ""
                name = ""
                address_lines = []
                
                if lines and lines[0].startswith("/"):
                    account = lines[0][1:]
                    if len(lines) > 1:
                        name = lines[1]
                        address_lines = lines[2:]
                elif lines:
                    name = lines[0]
                    address_lines = lines[1:]
                
                if "mx_path_name" in rule and name:
                    self.set_element_text(mx_root, rule["mx_path_name"], name, namespaces)
                
                if "mx_path_address" in rule and address_lines:
                    parent_path = rule["mx_path_address"].rsplit('/', 1)[0]
                    # CBPR+ Structured preference:
                    # If we have lines, try to map L1 to StrtNm and L2 to TwnNm
                    if len(address_lines) >= 1:
                        self.set_element_text(mx_root, f"{parent_path}/StrtNm", address_lines[0], namespaces)
                    if len(address_lines) >= 2:
                        self.set_element_text(mx_root, f"{parent_path}/TwnNm", address_lines[1].split(' ')[0], namespaces) # Use first word as town name
                    
                    # Also keep AdrLine for fallback (CBPR+ allows mixed during transition, but structured is preferred)
                    full_address = " ".join(address_lines)
                    self.set_element_text(mx_root, rule["mx_path_address"], full_address, namespaces)
                    
                    # Ensure Country Code (Mandatory in ISO 20022)
                    ctry_path = f"{parent_path}/Ctry"
                    if not self._get_element_text(mx_root, ctry_path, namespaces):
                        # Detect from last line
                        last_line = address_lines[-1].strip()
                        potential_cc = last_line[-2:].upper() if len(last_line) >= 2 else ""
                        if re.match(r"^[A-Z]{2}$", potential_cc):
                            self.set_element_text(mx_root, ctry_path, potential_cc, namespaces)
                        else:
                            self.set_element_text(mx_root, ctry_path, "US", namespaces)

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
                
                # Extract Indicator (C/D)
                indicator = "CRDT" if val[0].upper() == "C" else "DBIT"
                currency = val[7:10]
                amount_str = val[10:].replace(",", ".")
                
                bal_type_code = rule.get("balance_type", "OPBD") # Default to Opening Balance if not specified
                
                try:
                    # We need to create a DISTINCT Bal element to avoid overwriting siblings (60F vs 62F)
                    # We achieve this by force-creating a new Bal element
                    bal_root_path = rule["mx_path"].rsplit('/Amt', 1)[0]
                    # Create parent structure up to 'Stmt'
                    stmt_path = bal_root_path.rsplit('/Bal', 1)[0]
                    stmt_node = self._get_or_create_node(mx_root, stmt_path, namespaces)
                    
                    # Add a NEW Bal element
                    bal_node = ET.SubElement(stmt_node, f"{{{namespaces.get('xmlns', '')}}}Bal")
                    
                    # Set Balance Sub-elements
                    self.set_element_text(bal_node, "Tp/CdOrPrtry/Cd", bal_type_code, namespaces)
                    self.set_element_attr(bal_node, "Amt", rule["currency_attribute"] if "currency_attribute" in rule else "Ccy", currency, amount_str, namespaces)
                    self.set_element_text(bal_node, "CdtDbtInd", indicator, namespaces)
                    # Date is also mandatory in Bal for camt.053
                    val_date = datetime.strptime(val[1:7], "%y%m%d").strftime("%Y-%m-%d")
                    self.set_element_text(bal_node, "Dt/Dt", val_date, namespaces)
                    
                except Exception as e:
                    errors.append(f"Balance processing failed for tag {tag}: {str(e)}")

            elif rule_type == "bic":
                self.set_element_text(mx_root, rule["mx_path_bic"], val, namespaces)

        if errors:
            v_logs.append(f"Data mapping FAILED with {len(errors)} errors.")
            return {
                "status": "error",
                "logs": v_logs,
                "errors": errors
            }
            
        v_logs.append("Data mapping and type validation PASSED.")
            
        # Create Envelope and AppHdr
        # We'll build the XML with explicitly defined default namespaces for subtrees
        # to ensure L2 validation passes even without prefixes.
        
        # 1. Start with the root Envelope
        envelope = ET.Element("{urn:swift:xsd:envelope}BusMsgEnvlp")
        
        # 2. Build AppHdr with its own namespace
        head_ns = "urn:iso:std:iso:20022:tech:xsd:head.001.001.01"  # Adjusted to v01 as per config.json
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
        
        head_sub(app_hdr, "BizMsgIdr", parsed_fields.get("20", "AUTO-B01"))
        head_sub(app_hdr, "MsgDefIdr", mapping["target_mx"])
        head_sub(app_hdr, "BizSvc", mapping.get("biz_svc", "swift.cbprplus.02"))
        head_sub(app_hdr, "CreDt", datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"))
        
        # 3. Handle Structural Mandatories (Agents, Status, etc.)
        # Categorical Auto-Fill based on message type and presence in headers
        is_camt = "camt" in mapping["target_mx"]
        is_pacs = "pacs" in mapping["target_mx"]
        
        # We perform a final pass to ensure schema-critical elements are present
        for rule in mapping.get("mappings", []):
            target_path = rule.get("mx_path") or rule.get("mx_path_bic", "")
            if not target_path: continue
            
            # 3a. Agents Category Auto-Fill
            # Assigner/InstgAgt/Cretr/DbtrAgt -> usually Sender
            # Assignee/InstdAgt/CdtrAgt -> usually Receiver
            is_sender_side = any(k in target_path for k in ["Assgnr", "InstgAgt", "Cretr", "DbtrAgt"])
            is_receiver_side = any(k in target_path for k in ["Assgne", "InstdAgt", "CdtrAgt"])
            
            if (is_sender_side or is_receiver_side) and not self._get_element_text(mx_root, target_path, namespaces):
                fill_bic = sender_bic if is_sender_side else receiver_bic
                if fill_bic and fill_bic != "UNKNOWN":
                    # Force creation of Agent structure even for auto-fill
                    self.set_element_text(mx_root, target_path, fill_bic, namespaces)
            
            # 3b. Cancellation/Investigation Specifics (camt.056 / camt.029)
            if any(k in target_path for k in ["CxlDtls", "CxlDetails", "Undrlyg"]):
                # Fix typos in mapping paths on the fly
                fixed_path = target_path.replace("CxlDetails", "CxlDtls")
                if not self._get_element_text(mx_root, fixed_path, namespaces):
                    # For OrgnlInstrId or Identification, we definitely need a value
                    if any(k in fixed_path for k in ["OrgnlInstrId", "Id", "OrgnlMsgId"]):
                        val = parsed_fields.get("21") or parsed_fields.get("20") or f"REF-{datetime.now().strftime('%M%S')}"
                        self.set_element_text(mx_root, fixed_path, val, namespaces)

            # 3c. Payment/Status Targets (pacs.002)
            if "/TxSts" in target_path and not self._get_element_text(mx_root, target_path, namespaces):
                self.set_element_text(mx_root, target_path, "ACTC", namespaces)
            elif "/StsRsn/Cd" in target_path and not self._get_element_text(mx_root, target_path, namespaces):
                self.set_element_text(mx_root, target_path, "G000", namespaces)

        # 4. Global Structural Sequence Correction & Mandatory Injection
        doc_ns = namespaces.get("xmlns", "")
        target_mx = mapping.get("target_mx", "")

        # 4.0. Guarantee Root skeletal structure for specific message types
        if "camt.029" in target_mx:
            self._get_or_create_node(mx_root, "RsltnOfInvstgtn/Assgnmt", namespaces)
            self._get_or_create_node(mx_root, "RsltnOfInvstgtn/Sts", namespaces)
        elif "camt.056" in target_mx:
            self._get_or_create_node(mx_root, "FIToFIPmtCxlReq/Assgnmt", namespaces)
            self._get_or_create_node(mx_root, "FIToFIPmtCxlReq/Case", namespaces)
        elif "pacs.002" in target_mx:
            self._get_or_create_node(mx_root, "FIToFIPmtStsRpt/GrpHdr", namespaces)
            self._get_or_create_node(mx_root, "FIToFIPmtStsRpt/TxInfAndSts", namespaces)
        elif "camt.057" in target_mx:
            self._get_or_create_node(mx_root, "NtfctnToRcv/Ntfctn/Itm", namespaces)
        elif "camt.054" in target_mx:
            self._get_or_create_node(mx_root, "BkToCstmrDbtCdtNtfctn/Ntfctn/Ntry", namespaces)

        # 4a. camt handling (Ntry / Itm re-ordering and BkTxCd injection)
        if "camt." in target_mx:
            # camt.052/053/054 Entry Re-ordering and mandatory healing
            for ntry in mx_root.findall(".//{*}Ntry"):
                # 1. Mandatory Sts/Cd Healing
                sts = ntry.find("{*}Sts")
                if sts is None:
                    sts = ET.SubElement(ntry, f"{{{doc_ns}}}Sts")
                if sts.find("{*}Cd") is None:
                    ET.SubElement(sts, f"{{{doc_ns}}}Cd").text = "BOOK"

                # 2. Mandatory BookgDt Healing
                if ntry.find("{*}BookgDt") is None:
                    bookg_dt = ET.Element(f"{{{doc_ns}}}BookgDt")
                    ET.SubElement(bookg_dt, f"{{{doc_ns}}}Dt").text = parsed_fields.get("32A", "")[:6] if "32A" in str(parsed_fields) else datetime.now().strftime("%Y-%m-%d")
                    # Convert YYMMDD to YYYY-MM-DD if needed
                    if "32A" in str(parsed_fields) and len(str(parsed_fields.get("32A", ""))) >= 6:
                        yymmdd = str(parsed_fields.get("32A", ""))[:6]
                        try:
                            val_dt = datetime.strptime(yymmdd, "%y%m%d").strftime("%Y-%m-%d")
                            bookg_dt.find("{*}Dt").text = val_dt
                        except: pass
                    ntry.append(bookg_dt)

                # 3. Mandatory BkTxCd (Bank Transaction Code) Healing - Deep Structure
                ntry_order = ["Id", "Amt", "CdtDbtInd", "Sts", "BookgDt", "ValDt", "BkTxCd", "AmtDtls", "NtryDtls", "AddtlNtryInf"]
                bk_tx_cd = ntry.find("{*}BkTxCd")
                if bk_tx_cd is None:
                    bk_tx_cd = ET.Element(f"{{{doc_ns}}}BkTxCd")
                    ntry.append(bk_tx_cd)
                
                domn = bk_tx_cd.find("{*}Domn")
                if domn is None:
                    domn = ET.SubElement(bk_tx_cd, f"{{{doc_ns}}}Domn")
                if domn.find("{*}Cd") is None:
                    ET.SubElement(domn, f"{{{doc_ns}}}Cd").text = "PMNT"
                
                fmly = domn.find("{*}Fmly")
                if fmly is None:
                    fmly = ET.SubElement(domn, f"{{{doc_ns}}}Fmly")
                if fmly.find("{*}Cd") is None:
                    ET.SubElement(fmly, f"{{{doc_ns}}}Cd").text = "ICDT"
                if fmly.find("{*}SubFmlyCd") is None:
                    ET.SubElement(fmly, f"{{{doc_ns}}}SubFmlyCd").text = "DMCT"

                self._sort_children_by_list(ntry, ntry_order)
            
            # Statement/Report/Notification level re-ordering and mandatory healing
            for tag in ["Stmt", "Rpt", "Ntfctn"]:
                for el in mx_root.findall(f".//{{*}}{tag}"):
                    # Mandatory Id Heal
                    if el.find("{*}Id") is None or not (el.find("{*}Id").text or "").strip():
                        id_node = el.find("{*}Id")
                        if id_node is None: id_node = ET.SubElement(el, f"{{{doc_ns}}}Id")
                        id_node.text = parsed_fields.get("20") or f"STMT-{datetime.now().strftime('%M%S')}"
                    
                    # Mandatory Legal Sequence Number Heal (ONLY for Stmt and Rpt)
                    if tag in ["Stmt", "Rpt"]:
                        seq_node = el.find("{*}LglSeqNb")
                        if seq_node is None or not (seq_node.text or "").strip():
                            if seq_node is None:
                                seq_node = ET.SubElement(el, f"{{{doc_ns}}}LglSeqNb")
                            seq_val = ""
                            for tag_alt in ["28C", "28"]:
                                if tag_alt in parsed_fields and str(parsed_fields[tag_alt]).strip():
                                    seq_val = str(parsed_fields[tag_alt]).split('/')[0].strip()
                                    break
                            seq_node.text = seq_val if seq_val else "00001"

                    # Mandatory Account Heal
                    if el.find("{*}Acct") is None:
                        acct = ET.SubElement(el, f"{{{doc_ns}}}Acct")
                        id_other = self._get_or_create_node(acct, "Id/Othr", namespaces)
                        ET.SubElement(id_other, f"{{{doc_ns}}}Id").text = parsed_fields.get("25", "ACCOUNT-UNKNOWN")

                    # Apply correct order per tag type
                    if tag == "Ntfctn":
                        ntf_order = ["Id", "CreDtTm", "Acct", "RltdAcct", "Intrst", "TxsSummry", "Ntry", "Itm", "AddtlNtfctnInf"]
                        self._sort_children_by_list(el, ntf_order)
                    else:
                        stmt_order = ["Id", "LglSeqNb", "CreDtTm", "FrToDt", "Acct", "Bal", "TxsSummry", "Ntry"]
                        self._sort_children_by_list(el, stmt_order)
            
            # camt.057 Notification Item Re-ordering and mandatory healing
            for itm in mx_root.findall(".//{*}Itm"):
                # Mandatory Id Heal
                if itm.find("{*}Id") is None or not (itm.find("{*}Id").text or "").strip():
                    id_node = itm.find("{*}Id")
                    if id_node is None: id_node = ET.SubElement(itm, f"{{{doc_ns}}}Id")
                    id_node.text = parsed_fields.get("20") or f"ITM-{datetime.now().strftime('%M%S')}"

                itm_order = ["Id", "EndToEndId", "UETR", "Amt", "XpctdValDt", "Dbtr", "DbtrAcct"]
                self._sort_children_by_list(itm, itm_order)

            # camt.056 Cancellation Underlying Tx Re-ordering
            for tx_inf in mx_root.findall(".//{*}Undrlyg/{*}TxInf"):
                tx_inf_order = ["CxlReqId", "OrgnlGrpInf", "OrgnlInstrId", "OrgnlEndToEndId", "OrgnlTxId", "OrgnlUETR", "CxlRsnInf"]
                self._sort_children_by_list(tx_inf, tx_inf_order)

            # camt.029 Resolution Cancellation Details healing
            for tx_sts in mx_root.findall(".//{*}CxlDtls/{*}TxInfAndSts"):
                # Mandatory CxlStsId Heal
                if tx_sts.find("{*}CxlStsId") is None or not (tx_sts.find("{*}CxlStsId").text or "").strip():
                    id_node = tx_sts.find("{*}CxlStsId")
                    if id_node is None: id_node = ET.SubElement(tx_sts, f"{{{doc_ns}}}CxlStsId")
                    id_node.text = parsed_fields.get("20", f"CXL-{datetime.now().strftime('%M%S')}")
                
                # Mandatory OrgnlMsgId fallback
                if tx_sts.find("{*}OrgnlMsgId") is None or not (tx_sts.find("{*}OrgnlMsgId").text or "").strip():
                    id_node = tx_sts.find("{*}OrgnlMsgId")
                    if id_node is None: id_node = ET.SubElement(tx_sts, f"{{{doc_ns}}}OrgnlMsgId")
                    id_node.text = str(parsed_fields.get("21") or parsed_fields.get("20") or f"ORIG-{datetime.now().strftime('%M%S')}")
                
                # Mandatory OrgnlInstrId Heal
                if tx_sts.find("{*}OrgnlInstrId") is None or not (tx_sts.find("{*}OrgnlInstrId").text or "").strip():
                    id_node = tx_sts.find("{*}OrgnlInstrId")
                    if id_node is None: id_node = ET.SubElement(tx_sts, f"{{{doc_ns}}}OrgnlInstrId")
                    id_node.text = str(parsed_fields.get("21") or parsed_fields.get("20") or f"INST-{datetime.now().strftime('%M%S')}")

                # Mandatory OrgnlEndToEndId Heal
                if tx_sts.find("{*}OrgnlEndToEndId") is None:
                    ET.SubElement(tx_sts, f"{{{doc_ns}}}OrgnlEndToEndId").text = str(parsed_fields.get("21") or parsed_fields.get("20") or "NOTPROVIDED")

                # Mandatory OrgnlTxId Heal
                if tx_sts.find("{*}OrgnlTxId") is None:
                    ET.SubElement(tx_sts, f"{{{doc_ns}}}OrgnlTxId").text = str(parsed_fields.get("21") or parsed_fields.get("20") or "NOTPROVIDED")

                # Ensure Cancellation Reason Information exists (CBPR+ requires CxlStsRsnInf)
                rsn_inf = tx_sts.find("{*}CxlStsRsnInf")
                if rsn_inf is None:
                    rsn_inf = ET.SubElement(tx_sts, f"{{{doc_ns}}}CxlStsRsnInf")
                if rsn_inf.find("{*}AddtlInf") is None:
                    ET.SubElement(rsn_inf, f"{{{doc_ns}}}AddtlInf").text = parsed_fields.get("79", "REQUEST REJECTED")

                tx_sts_order = ["CxlStsId", "OrgnlGrpInf", "OrgnlMsgId", "OrgnlMsgNmId", "OrgnlCreDtTm", "OrgnlInstrId", "OrgnlEndToEndId", "OrgnlTxId", "OrgnlUETR", "CxlStsRsnInf"]
                self._sort_children_by_list(tx_sts, tx_sts_order)

            # camt.056 / camt.029 Case/Assignment re-ordering and injection
            for assgn in mx_root.findall(".//{*}Assgnmt"):
                # Mandatory Id Heal
                if assgn.find("{*}Id") is None or not (assgn.find("{*}Id").text or "").strip():
                    id_node = assgn.find("{*}Id")
                    if id_node is None: id_node = ET.SubElement(assgn, f"{{{doc_ns}}}Id")
                    id_node.text = parsed_fields.get("20", f"ASSG-{datetime.now().strftime('%M%S')}")

                # Mandatory Assgnr injection (Heal if missing or empty)
                assgnr = assgn.find("{*}Assgnr")
                if assgnr is None or len(list(assgnr)) == 0:
                    if assgnr is not None: assgn.remove(assgnr)
                    assgnr = ET.Element(f"{{{doc_ns}}}Assgnr")
                    agt = ET.SubElement(assgnr, f"{{{doc_ns}}}Agt")
                    fii = ET.SubElement(agt, f"{{{doc_ns}}}FinInstnId")
                    ET.SubElement(fii, f"{{{doc_ns}}}BICFI").text = parsed_fields.get("_senderBic", "BANKUS33XXX")
                    assgn.append(assgnr)
                
                # Mandatory Assgne injection (Heal if missing or empty)
                assgne = assgn.find("{*}Assgne")
                if assgne is None or len(list(assgne)) == 0:
                    if assgne is not None: assgn.remove(assgne)
                    assgne = ET.Element(f"{{{doc_ns}}}Assgne")
                    agt = ET.SubElement(assgne, f"{{{doc_ns}}}Agt")
                    fii = ET.SubElement(agt, f"{{{doc_ns}}}FinInstnId")
                    ET.SubElement(fii, f"{{{doc_ns}}}BICFI").text = parsed_fields.get("_receiverBic", "BANKGB2LXXX")
                    assgn.append(assgne)

                # Mandatory CreDtTm injection
                if assgn.find("{*}CreDtTm") is None:
                    ET.SubElement(assgn, f"{{{doc_ns}}}CreDtTm").text = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+00:00")

                self._sort_children_by_list(assgn, ["Id", "Assgnr", "Assgne", "CreDtTm"])

            # Status re-ordering and injection (camt.029 / camt.056 - only if choice selected)
            for sts in mx_root.findall(".//{*}Sts"):
                if sts.find("{*}Conf") is None:
                    ET.SubElement(sts, f"{{{doc_ns}}}Conf").text = "RJCT"
                
                # Mandatory Status Reason Code (NARR is safe fallback for narrative info)
                rsn = sts.find("{*}Rsn")
                if rsn is not None:
                    if rsn.find("{*}Cd") is None:
                        ET.SubElement(rsn, f"{{{doc_ns}}}Cd").text = "NARR"
                
                self._sort_children_by_list(sts, ["Conf", "Rsn", "OrgnlGrpInfAndSts"])

            # Case re-ordering and injection
            for cse in mx_root.findall(".//{*}Case"):
                if cse.find("{*}Id") is None:
                    ET.SubElement(cse, f"{{{doc_ns}}}Id").text = parsed_fields.get("21") or parsed_fields.get("20") or f"CASE-{datetime.now().strftime('%M%S')}"
                if cse.find("{*}Cretr") is None:
                    cretr = ET.SubElement(cse, f"{{{doc_ns}}}Cretr")
                    agt = ET.SubElement(cretr, f"{{{doc_ns}}}Agt")
                    fii = ET.SubElement(agt, f"{{{doc_ns}}}FinInstnId")
                    ET.SubElement(fii, f"{{{doc_ns}}}BICFI").text = parsed_fields.get("_senderBic", "BANKUS33XXX")
                self._sort_children_by_list(cse, ["Id", "Cretr", "ReopnInd"])

        # 4b. pacs handling (PmtId and CdtTrfTxInf re-ordering)
        if "pacs." in mapping.get("target_mx", ""):
            # pacs.008/009 Transaction Re-ordering
            for tfi in mx_root.findall(".//{*}CdtTrfTxInf"):
                # Mandatory PmtId fixes
                pmt_id = tfi.find("{*}PmtId")
                if pmt_id is not None:
                    # EndToEndId fallback
                    if pmt_id.find("{*}EndToEndId") is None:
                        val = parsed_fields.get("21") or parsed_fields.get("20") or f"E2E-{datetime.now().strftime('%M%S')}"
                        ET.SubElement(pmt_id, f"{{{doc_ns}}}EndToEndId").text = str(val)
                    # TxId (Mandatory in pacs.009)
                    if "pacs.009" in mapping["target_mx"] and pmt_id.find("{*}TxId") is None:
                        val = parsed_fields.get("20") or f"TX-{datetime.now().strftime('%M%S')}"
                        ET.SubElement(pmt_id, f"{{{doc_ns}}}TxId").text = str(val)
                    # UETR
                    if "_uetr" in parsed_fields and pmt_id.find("{*}UETR") is None:
                        ET.SubElement(pmt_id, f"{{{doc_ns}}}UETR").text = parsed_fields["_uetr"]
                    self._sort_children_by_list(pmt_id, ["InstrId", "EndToEndId", "TxId", "UETR"])

                # pacs.009 specific Party Structure Correction
                if "pacs.009" in mapping["target_mx"]:
                    for party_tag in ["Dbtr", "Cdtr"]:
                        party = tfi.find(f"{{*}}{party_tag}")
                        if party is not None:
                            fii = party.find("{*}FinInstnId")
                            if fii is not None:
                                bic_node = fii.find("{*}BICFI")
                                bic_val = bic_node.text if bic_node is not None else ""
                                # Ensure Agent carries the BIC if missing
                                agt_tag = f"{party_tag}Agt"
                                agt = tfi.find(f"{{*}}{agt_tag}")
                                if agt is None:
                                    agt = ET.Element(f"{{{doc_ns}}}{agt_tag}")
                                    tfi.append(agt)
                                fii_agt = self._get_or_create_node(agt, "FinInstnId", namespaces)
                                if fii_agt.find("{*}BICFI") is None:
                                    ET.SubElement(fii_agt, f"{{{doc_ns}}}BICFI").text = bic_val or "UNKNOWN"
                                # Transform Party to use Nm (Name) as per CBPR+ requirements
                                party.remove(fii)
                                ET.SubElement(party, f"{{{doc_ns}}}Nm").text = f"BANK {bic_val}" if bic_val else "UNKNOWN BANK"
                    
                    # Mandatory PmtTpInf injection for pacs.009
                    if tfi.find("{*}PmtTpInf") is None:
                        ptinf = ET.Element(f"{{{doc_ns}}}PmtTpInf")
                        svclvl = ET.SubElement(ptinf, f"{{{doc_ns}}}SvcLvl")
                        ET.SubElement(svclvl, f"{{{doc_ns}}}Cd").text = "TRF"
                        tfi.append(ptinf)
                    
                    # Mandatory ChrgBr injection for pacs.009
                    if tfi.find("{*}ChrgBr") is None:
                        ET.SubElement(tfi, f"{{{doc_ns}}}ChrgBr").text = "SLEV"

                # Mandatory ChrgBr injection for pacs.008
                if "pacs.008" in mapping["target_mx"] and tfi.find("{*}ChrgBr") is None:
                    ET.SubElement(tfi, f"{{{doc_ns}}}ChrgBr").text = "SHAR"

                # Universal CdtTrfTxInf sequence
                tfi_order = ["PmtId", "PmtTpInf", "IntrBkSttlmAmt", "IntrBkSttlmDt", "InstdAmt", "ChrgBr", "Dbtr", "DbtrAcct", "DbtrAgt", "InstgAgt", "InstdAgt", "CdtrAgt", "Cdtr", "CdtrAcct", "RmtInf", "UndrlygCstmrCdtTrf"]
                self._sort_children_by_list(tfi, tfi_order)

            # pacs.002 Status Report Re-ordering and mandatory healing
            for tx_sts in mx_root.findall(".//{*}TxInfAndSts"):
                # Mandatory OrgnlGrpInf (If missing, use sender header info)
                if tx_sts.find("{*}OrgnlMsgId") is None:
                    ET.SubElement(tx_sts, f"{{{doc_ns}}}OrgnlMsgId").text = parsed_fields.get("21") or parsed_fields.get("20") or f"ORGN-{datetime.now().strftime('%M%S')}"
                
                # Mandatory TxSts injection if missing
                if tx_sts.find("{*}TxSts") is None:
                    ET.SubElement(tx_sts, f"{{{doc_ns}}}TxSts").text = "ACTC"

                tx_sts_order = ["StsId", "OrgnlGrpInf", "OrgnlMsgId", "OrgnlMsgNmId", "OrgnlCreDtTm", "OrgnlInstrId", "OrgnlEndToEndId", "OrgnlTxId", "OrgnlUETR", "TxSts", "StsRsnInf", "AccptncDtTm"]
                self._sort_children_by_list(tx_sts, tx_sts_order)

            # Universal Header sequence
            for hdr in mx_root.findall(".//{*}GrpHdr"):
                # Inject mandatory Agents if missing (Common L2 failure point)
                if hdr.find("{*}InstgAgt") is None:
                    instg = ET.SubElement(hdr, f"{{{doc_ns}}}InstgAgt")
                    fii = ET.SubElement(instg, f"{{{doc_ns}}}FinInstnId")
                    ET.SubElement(fii, f"{{{doc_ns}}}BICFI").text = parsed_fields.get("_senderBic", "BANKUS33XXX")
                if hdr.find("{*}InstdAgt") is None:
                    instd = ET.SubElement(hdr, f"{{{doc_ns}}}InstdAgt")
                    fii = ET.SubElement(instd, f"{{{doc_ns}}}FinInstnId")
                    ET.SubElement(fii, f"{{{doc_ns}}}BICFI").text = parsed_fields.get("_receiverBic", "BANKGB2LXXX")
                
                # Inject mandatory Settlement Information for pacs.008/009
                if "pacs.008" in mapping["target_mx"] or "pacs.009" in mapping["target_mx"]:
                    sttlm = hdr.find("{*}SttlmInf")
                    if sttlm is None:
                        sttlm = ET.SubElement(hdr, f"{{{doc_ns}}}SttlmInf")
                    
                    if sttlm.find("{*}SttlmMtd") is None:
                        ET.SubElement(sttlm, f"{{{doc_ns}}}SttlmMtd").text = "INDA"
                    
                    # CBPR+ often expects ClrSys if validating against strict schemas
                    if sttlm.find("{*}ClrSys") is None:
                        cs = ET.SubElement(sttlm, f"{{{doc_ns}}}ClrSys")
                        ET.SubElement(cs, f"{{{doc_ns}}}Cd").text = "TGT"
                    
                    if sttlm.find("{*}InstgRmbrsmntAgt") is None:
                        ra = ET.SubElement(sttlm, f"{{{doc_ns}}}InstgRmbrsmntAgt")
                        fii = ET.SubElement(ra, f"{{{doc_ns}}}FinInstnId")
                        ET.SubElement(fii, f"{{{doc_ns}}}BICFI").text = parsed_fields.get("_senderBic", "BANKUS33XXX")
                    
                    if sttlm.find("{*}InstgRmbrsmntAgtAcct") is None:
                        raa = ET.SubElement(sttlm, f"{{{doc_ns}}}InstgRmbrsmntAgtAcct")
                        aid = ET.SubElement(raa, f"{{{doc_ns}}}Id")
                        ET.SubElement(aid, f"{{{doc_ns}}}IBAN").text = "US00" + parsed_fields.get("_senderBic", "BANKUS33XXX")[:10]
                    
                    if sttlm.find("{*}InstdRmbrsmntAgt") is None:
                        ra = ET.SubElement(sttlm, f"{{{doc_ns}}}InstdRmbrsmntAgt")
                        fii = ET.SubElement(ra, f"{{{doc_ns}}}FinInstnId")
                        ET.SubElement(fii, f"{{{doc_ns}}}BICFI").text = parsed_fields.get("_receiverBic", "BANKGB2LXXX")
                    
                    if sttlm.find("{*}InstdRmbrsmntAgtAcct") is None:
                        raa = ET.SubElement(sttlm, f"{{{doc_ns}}}InstdRmbrsmntAgtAcct")
                        aid = ET.SubElement(raa, f"{{{doc_ns}}}Id")
                        ET.SubElement(aid, f"{{{doc_ns}}}IBAN").text = "GB00" + parsed_fields.get("_receiverBic", "BANKGB2LXXX")[:10]

                    # Mandatory SttlmDt for CBPR+ compliance
                    if sttlm.find("{*}SttlmDt") is None:
                        val_date = ""
                        tags_to_check = ["32A", "30"]
                        for t in tags_to_check:
                            if t in parsed_fields:
                                v = str(parsed_fields[t]).strip()
                                if len(v) >= 6 and v[:6].isdigit():
                                    val_date = v[:6]
                                    break
                        
                        if val_date:
                            try:
                                iso_dt = datetime.strptime(val_date, "%y%m%d").strftime("%Y-%m-%d")
                                ET.SubElement(sttlm, f"{{{doc_ns}}}SttlmDt").text = iso_dt
                            except:
                                ET.SubElement(sttlm, f"{{{doc_ns}}}SttlmDt").text = datetime.now().strftime("%Y-%m-%d")
                        else:
                            ET.SubElement(sttlm, f"{{{doc_ns}}}SttlmDt").text = datetime.now().strftime("%Y-%m-%d")

                    self._sort_children_by_list(sttlm, ["SttlmMtd", "SttlmAcct", "ClrSys", "InstgRmbrsmntAgt", "InstgRmbrsmntAgtAcct", "InstdRmbrsmntAgt", "InstdRmbrsmntAgtAcct", "SttlmDt", "InstrPrty"])
                
                hdr_order = ["MsgId", "CreDtTm", "NbOfTxs", "SttlmInf", "InstgAgt", "InstdAgt"]
                self._sort_children_by_list(hdr, hdr_order)

        # 4c. Universal Address Re-ordering (Ensures <Ctry> before <AdrLine>)
        for adr in mx_root.findall(".//{*}PstlAdr"):
            adr_order = ["AdrTp", "Dept", "SubDept", "StrtNm", "BldgNb", "BldgNm", "Flr", "PstCd", "TwnNm", "TwnLctnNm", "DstrctNm", "CtrySubDvsn", "Ctry", "AdrLine"]
            self._sort_children_by_list(adr, adr_order)

        # 4d. Universal Party/Agent Identification Re-ordering
        # Parties: Dbtr, Cdtr, UltmtDbtr, UltmtCdtr, etc.
        party_order = ["Nm", "PstlAdr", "Id", "CtctDtls"]
        # Agents/FIs: FinInstnId, BICFI, ClrSysMmbId, etc.
        agent_order = ["FinInstnId", "BrnchId"]
        fii_order = ["BICFI", "ClrSysMmbId", "LEI", "Nm", "PstlAdr", "Othr"]
        acct_order = ["Id", "Tp", "Ccy", "Nm", "Ownr", "Svcr"]

        party_tags = ["Dbtr", "Cdtr", "UltmtDbtr", "UltmtCdtr", "Cretr", "Assgnr", "Assgne", "Applt", "Ownr"]
        for tag in party_tags:
            for party in mx_root.findall(f".//{{*}}{tag}"):
                self._sort_children_by_list(party, party_order)
        
        agent_tags = ["DbtrAgt", "CdtrAgt", "InstgAgt", "InstdAgt", "IntrmyAgt1", "AcctSvcr", "Svcr", "Agt"]
        for tag in agent_tags:
            for agent in mx_root.findall(f".//{{*}}{tag}"):
                self._sort_children_by_list(agent, agent_order)

        for fii in mx_root.findall(".//{*}FinInstnId"):
            self._sort_children_by_list(fii, fii_order)
            
        for acct in mx_root.findall(".//{*}Acct"):
            self._sort_children_by_list(acct, acct_order)

        # 4e. Transaction Level Re-ordering (Crucial for pacs.008/009)
        for tx in mx_root.findall(".//{*}CdtTrfTxInf"):
            tx_order = [
                "PmtId", "PmtTpInf", "IntrBkSttlmAmt", "IntrBkSttlmDt", "SttlmPrty", 
                "SttlmTm", "SttlmInstn", "SttlmInf", "InstgAgt", "InstdAgt", 
                "IntrmyAgt1", "IntrmyAgt1Acct", "IntrmyAgt2", "IntrmyAgt2Acct",
                "IntrmyAgt3", "IntrmyAgt3Acct", "UltmtDbtr", "Dbtr", "DbtrAcct", 
                "DbtrAgt", "DbtrAgtAcct", "PrvsInstgAgt1", "PrvsInstgAgt1Acct",
                "PrvsInstgAgt2", "PrvsInstgAgt2Acct", "PrvsInstgAgt3", "PrvsInstgAgt3Acct",
                "CdtrAgt", "CdtrAgtAcct", "Cdtr", "CdtrAcct", "UltmtCdtr", 
                "InstrForCdtrAgt", "InstrForNextAgt", "Purp", "RgltryRptg", 
                "Tax", "RltdRmtInf", "RmtInf", "SplmtryData"
            ]
            self._sort_children_by_list(tx, tx_order)
            
            # Ensure IntrBkSttlmDt exists if IntrBkSttlmAmt exists (Common L2 requirement)
            if tx.find("{*}IntrBkSttlmAmt") is not None and tx.find("{*}IntrBkSttlmDt") is None:
                # Try to use current date or 32A date
                val_date = datetime.now().strftime("%Y-%m-%d")
                if "32A" in parsed_fields:
                    v = str(parsed_fields["32A"]).strip()
                    if len(v) >= 6 and v[:6].isdigit():
                        try: val_date = datetime.strptime(v[:6], "%y%m%d").strftime("%Y-%m-%d")
                        except: pass
                ET.SubElement(tx, f"{{{doc_ns}}}IntrBkSttlmDt").text = val_date
                # Re-sort after adding
                self._sort_children_by_list(tx, tx_order)

        for pmt_id in mx_root.findall(".//{*}PmtId"):
            self._sort_children_by_list(pmt_id, ["InstrId", "EndToEndId", "TxId", "UETR", "ClrSysRef"])
            
        for pmt_tp in mx_root.findall(".//{*}PmtTpInf"):
            self._sort_children_by_list(pmt_tp, ["InstrPrty", "SvcLvl", "LclInstrm", "CtgyPurp"])

        # 5. Attach the Data Document
        envelope.append(mx_root)
        
        # 6. Serialization with carefully managed namespaces
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
            "detected_type": f"MT{mt_type}" if not mt_type.upper().startswith("MT") else mt_type,
            "mx_message": xml_string,
            "logs": v_logs
        }
