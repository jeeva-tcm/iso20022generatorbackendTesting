import time
import re
import os
from lxml import etree
from typing import Optional
from .models import ValidationIssue, ValidationReport

class Layer2Mixin:
    # Cache: xsd_path → {tag_name: {label, mandatory, repeatable}}
    _xsd_tag_cache: dict = {}

    async def _run_layer_2(self, xml_content: str, report: ValidationReport, message_type: str) -> bool:
        """
        LAYER 2 — ISO Structure Validation (XSD)
        Strict implementation of the 10-Step Execution Order
        """
        start = time.time()
        issues = []
        
        try:
            # Step 1 — Load Schema Set
            xsd_full_path = self._get_xsd_path(message_type)
            if not xsd_full_path or not os.path.exists(xsd_full_path):
                report.add_issue(ValidationIssue("ERROR", 2, "Schema Not Found", "Missing Validation Template", f"Cannot find the validation template for message type '{message_type}'.", "The schema file (.xsd) for this message type is not available in the system. Contact support if this message type should be supported."))
                report.layer_status["2"] = {"status": "❌", "time": 0}
                return False

            # IMPORTANT: remove_blank_text MUST be False to preserve user's original line numbers
            parser = etree.XMLParser(remove_blank_text=False, no_network=True)
            full_xml_doc = etree.fromstring(xml_content.encode('utf-8'), parser)
            
            # Step 2 — Validate Root + Namespace
            # Check for <Document> or <BusMsg>
            target_node = full_xml_doc.xpath("//*[local-name()='Document' or local-name()='BusMsg']")
            if not target_node:
                # Check if root itself is Document/BusMsg
                if any(x in full_xml_doc.tag for x in ['Document', 'BusMsg']):
                    target_node = [full_xml_doc]
            
            if not target_node:
                report.add_issue(ValidationIssue("ERROR", 2, "Missing Document", "No Root Element", "Cannot find the main <Document> or <BusMsg> container in your XML.", "Your message structure is incorrect. ISO 20022 messages must have a <Document> wrapper element."))
                report.layer_status["2"] = {"status": "❌", "time": (time.time() - start) * 1000}
                return False

            main_node = target_node[0]
            line_offset = main_node.sourceline or 1
            
            # CRITICAL: Re-parse node to its own document to clear parent context 
            main_str = etree.tostring(main_node, encoding='utf-8')
            main_cleaned = etree.fromstring(main_str, parser)

            xsd_doc = etree.parse(xsd_full_path)
            schema = etree.XMLSchema(xsd_doc)

            # Build dynamic tag info for rich error messages (cached per XSD)
            tag_info = self._build_tag_info_from_xsd(xsd_full_path)
            
            # Extract namespacing carefully
            xml_ns = etree.QName(main_cleaned).namespace or ""
            # Robust XSD Namespace Detection
            xsd_ns = xsd_doc.getroot().get("targetNamespace")
            if not xsd_ns:
                raw_xsd = open(xsd_full_path, 'r', encoding='utf-8', errors='ignore').read()
                match = re.search(r'targetNamespace=["\']([^"\']+)["\']', raw_xsd)
                xsd_ns = match.group(1) if match else None

            # Step 3 to 9 — Automated Structural Validation
            try:
                # To support line-exactness while fixing namespace mismatches:
                # We validate a 'cleaned' version for errors, then map lines back to the original.
                validation_doc = main_cleaned
                if xsd_ns and xml_ns != xsd_ns:
                    validation_doc = self._mask_namespace(main_cleaned, xsd_ns)
                
                schema.assertValid(validation_doc)
            except etree.DocumentInvalid as e:
                for error in e.error_log:
                    # Map the relative error line back to the absolute line in the full document
                    real_line = line_offset + error.line - 1
                    
                    # Smart Line Correction:
                    # If we can identify the specific invalid value and tag, let's find the EXACT line in the original tree.
                    # This fixes issues where re-parsing destroys line numbers.
                    try:
                        # Extract Tag and Value from error message
                        # Typical lxml format:
                        #   Element 'ChrgBr': [facet 'enumeration'] The value 'JEEC'...
                        #   Element 'IntrBkSttlmAmt', attribute 'Ccy': [facet 'pattern'] The value 'USDDD'...
                        tag_match = re.search(r"Element '([^']+)'", error.message)
                        # Case-insensitive, matches both "attribute '...'" and "Attribute '...'"
                        attr_match = re.search(r"[Aa]ttribute '([^']+)'", error.message)
                        val_match  = re.search(r"[Vv]alue '([^']*)'" , error.message)

                        found_line = None

                        # ── CASE A: ATTRIBUTE ERROR (e.g. Ccy="USDDD") ──
                        # lxml: "Element 'IntrBkSttlmAmt', attribute 'Ccy': ... value 'USDDD'..."
                        if attr_match and val_match:
                            attr_name    = attr_match.group(1).split('}')[-1]
                            bad_attr_val = val_match.group(1)

                            if bad_attr_val.strip():
                                # Raw-text scan: find AttrName="BadValue" in the original XML
                                escaped_name = re.escape(attr_name)
                                escaped_val  = re.escape(bad_attr_val)
                                attr_pattern = re.compile(
                                    escaped_name + r'\s*=\s*["\']' + escaped_val + r'["\']'
                                )
                                attr_text_match = attr_pattern.search(xml_content)
                                if attr_text_match:
                                    found_line = xml_content.count('\n', 0, attr_text_match.start()) + 1

                            # Fallback: use sourceline of the parent element from main_node
                            if not found_line and tag_match:
                                parent_tag  = tag_match.group(1).split('}')[-1]
                                parent_nodes = main_node.xpath(
                                    f"descendant-or-self::*[local-name()='{parent_tag}']"
                                )
                                if parent_nodes:
                                    found_line = parent_nodes[0].sourceline

                        # ── CASE B: ELEMENT VALUE / STRUCTURE ERROR ──
                        elif tag_match:
                            tag_full = tag_match.group(1)
                            tag_name = tag_full.split('}')[-1] if '}' in tag_full else tag_full

                            candidates = main_node.xpath(
                                f"descendant-or-self::*[local-name()='{tag_name}']"
                            )
                            estimate = real_line

                            if val_match:
                                # High-Precision: match element text
                                bad_val = val_match.group(1)
                                best_match_line = None
                                min_dist = float('inf')
                                for c in candidates:
                                    if (c.text or "").strip() == bad_val:
                                        dist = abs((c.sourceline or 0) - estimate)
                                        if dist < min_dist:
                                            min_dist = dist
                                            best_match_line = c.sourceline
                                found_line = best_match_line

                                # Raw-text fallback: <Tag>BadVal</Tag>
                                if not found_line and bad_val.strip():
                                    elem_pattern = re.compile(
                                        '<' + tag_name + r'[^>]*>\s*' +
                                        re.escape(bad_val) +
                                        r'\s*</' + tag_name + '>'
                                    )
                                    elem_match = elem_pattern.search(xml_content)
                                    if elem_match:
                                        found_line = xml_content.count('\n', 0, elem_match.start()) + 1

                            elif candidates:
                                # Structure error: pick closest candidate to estimate
                                best_match_line = None
                                min_dist = float('inf')
                                for c in candidates:
                                    dist = abs((c.sourceline or 0) - estimate)
                                    if dist < min_dist:
                                        min_dist = dist
                                        best_match_line = c.sourceline
                                found_line = best_match_line

                        if found_line:
                            real_line = found_line

                    except Exception as _ex:
                        print(f"[DEBUG L2 LINE-CORRECTION EXCEPTION] {_ex}")
                        pass  # Fallback to calculated line

                    # ── Blank-line guard ──────────────────────────────────────
                    # If real_line lands on a blank/whitespace-only line in the
                    # original XML (common with pretty-printed messages), walk
                    # backwards to find the closest non-empty line so the
                    # editor highlights an actual tag instead of empty space.
                    try:
                        xml_lines = xml_content.splitlines()
                        ln = int(real_line) - 1  # 0-indexed
                        if 0 <= ln < len(xml_lines) and not xml_lines[ln].strip():
                            # Search backwards for the nearest non-blank line
                            for offset in range(1, 10):
                                prev = ln - offset
                                if prev >= 0 and xml_lines[prev].strip():
                                    real_line = prev + 1  # back to 1-indexed
                                    break
                    except Exception:
                        pass
                    # ─────────────────────────────────────────────────────────

                    friendly_msg, suggestion = self._simplify_error_message(error.message, tag_info)
                    issues.append(ValidationIssue("ERROR", 2, "SCHEMA_VAL", str(real_line), friendly_msg, suggestion))

            # Step 11 — Mandatory Header Logic (head.001)
            app_hdr_node = full_xml_doc.find(".//{*}AppHdr")
            if app_hdr_node is not None:
                h_line_offset = app_hdr_node.sourceline or 1
                h_ns = etree.QName(app_hdr_node).namespace or ""
                h_type = self.config.get("validation_rules", {}).get("default_header_type", "head.001.001.01")
                partial_ns = self.config.get("validation_rules", {}).get("header_namespace_partial", "head.001.001")
                
                if partial_ns in h_ns:
                    h_type = h_ns.split(":")[-1]
                
                h_path = self._get_xsd_path(h_type)
                if h_path:
                    try:
                        # 1. Prepare clean header for validation
                        h_str = etree.tostring(app_hdr_node, encoding='utf-8')
                        h_clean = etree.fromstring(h_str, parser)
                        
                        h_xsd_raw = etree.parse(h_path)
                        h_schema = etree.XMLSchema(h_xsd_raw)
                        h_xsd_ns = h_xsd_raw.getroot().get("targetNamespace")

                        # ✅ Build tag_info from the HEAD.001 XSD (NOT payload XSD)
                        # This ensures CharSet is seen as optional and Fr as mandatory
                        h_tag_info = self._build_tag_info_from_xsd(h_path)
                        
                        h_val_doc = h_clean
                        if h_xsd_ns and h_ns != h_xsd_ns:
                            h_val_doc = self._mask_namespace(h_clean, h_xsd_ns)

                        # 2. Validate
                        h_schema.assertValid(h_val_doc)
                    except etree.DocumentInvalid as deh:
                        for error in deh.error_log:
                            # Map relative line back to absolute line
                            h_real_line = h_line_offset + error.line - 1
                            # Use h_tag_info (head.001) — NOT payload tag_info
                            friendly_msg, suggestion = self._simplify_error_message(error.message, h_tag_info)
                            issues.append(ValidationIssue("ERROR", 2, "HEADER_VAL", str(h_real_line), friendly_msg, suggestion))
                    except Exception as eh:
                         issues.append(ValidationIssue("WARNING", 2, "HEADER_ERR", "/", f"AppHdr Warning: {str(eh)}"))

        except etree.XMLSyntaxError as e:
             issues.append(ValidationIssue("ERROR", 2, "XML_SYNTAX", str(e.lineno), f"XML Markup Error: {str(e)}"))
        except Exception as e:
             issues.append(ValidationIssue("ERROR", 2, "VAL_ERR", "/", f"Internal Layer 2 Error: {str(e)}"))

        # Final Collection & Success Assessment
        for issue in issues:
            report.add_issue(issue)

        success = not any(i.severity == "ERROR" for i in issues)
        report.layer_status["2"] = {"status": "✅" if success else "❌", "time": round((time.time() - start) * 1000, 2)}
        return success

    # ──────────────────────────────────────────────────────────────────────────
    # DYNAMIC XSD TAG ANALYSER
    # Reads any ISO 20022 XSD at runtime and builds a rich tag dictionary.
    # Result is cached so each XSD is only parsed once per server session.
    # ──────────────────────────────────────────────────────────────────────────

    def _camel_to_words(self, name: str) -> str:
        """Convert ISO 20022 CamelCase names to readable English words."""
        # Strip trailing version digits (e.g. GroupHeader131 → GroupHeader)
        name = re.sub(r'\d+$', '', name)
        # Split: uppercase letters that start a new word
        words = re.findall(r'[A-Z][a-z]+|[A-Z]+(?=[A-Z][a-z]|$)|[a-z]+|[A-Z]', name)
        return ' '.join(words) if words else name

    def _build_tag_info_from_xsd(self, xsd_path: str) -> dict:
        """
        Dynamically parse an XSD file and return a dict:
          { element_name: { 'label': str, 'mandatory': bool, 'repeatable': bool } }
        Cached per xsd_path so it runs only once per XSD file.
        """
        if xsd_path in Layer2Mixin._xsd_tag_cache:
            return Layer2Mixin._xsd_tag_cache[xsd_path]

        tag_info: dict = {}
        XS = 'http://www.w3.org/2001/XMLSchema'

        try:
            tree  = etree.parse(xsd_path)
            root  = tree.getroot()

            for elem in root.iter(f'{{{XS}}}element'):
                name = elem.get('name')
                if not name:
                    continue

                min_occ = elem.get('minOccurs', '1')  # default is '1' = mandatory
                max_occ = elem.get('maxOccurs', '1')
                type_nm = elem.get('type', name)       # fallback to element name

                is_mandatory  = min_occ != '0'
                is_repeatable = (max_occ == 'unbounded' or
                                 (max_occ.isdigit() and int(max_occ) > 1))

                # Generate plain-English label from the xs:complexType or xs:simpleType
                # that is referenced by this element — more descriptive than the tag alone
                label = self._camel_to_words(type_nm) if type_nm else self._camel_to_words(name)

                if name not in tag_info:  # keep first (most specific) definition
                    tag_info[name] = {
                        'label':      label,
                        'mandatory':  is_mandatory,
                        'repeatable': is_repeatable,
                        'min':        min_occ,
                        'max':        max_occ,
                    }

        except Exception as ex:
            print(f'[DEBUG] XSD tag parse failed: {ex}')

        Layer2Mixin._xsd_tag_cache[xsd_path] = tag_info
        return tag_info

    def _mask_namespace(self, element, new_ns: str):
        # Guard: lxml Comment/PI nodes have .tag = etree.Comment (a Cython function)
        # which is NOT a string. We must copy them as-is to avoid QName crash.
        if not isinstance(element.tag, str):
            return element  # Return comment/PI as-is (lxml will deep-copy it safely)
        attribs = {}
        for k, v in element.attrib.items():
            attribs[k] = v
        new_tag = f"{{{new_ns}}}{etree.QName(element).localname}"
        new_elem = etree.Element(new_tag, attrib=attribs)
        new_elem.text = element.text
        for child in element:
            new_elem.append(self._mask_namespace(child, new_ns))
        new_elem.tail = element.tail
        return new_elem

    def _simplify_error_message(self, message: str, tag_info: dict = None) -> tuple:
        """
        Dynamic Translation Engine: Converts technical XSD/lxml jargon into
        clear, human-readable, actionable English for end users.
        Uses tag_info (built from the actual XSD) for context-aware messages.
        Works for ALL ISO 20022 MX message types dynamically.
        """
        # Strip namespace URIs like {urn:iso:...:xsd:...} from message
        msg = re.sub(r'\{[^}]+\}', '', message)
        if tag_info is None:
            tag_info = {}

        # ── Static Tag Name Dictionary (Cross-Family coverage) ────────────
        # Priority 3 fallback after: 1. live XSD label, 2. this dict, 3. CamelCase split
        # Covers all major ISO 20022 MX message families dynamically.
        _STATIC_TAG_NAMES = {
            # ── COMMON ACROSS ALL FAMILIES ──────────────────────────────────
            "GrpHdr":       "Group Header",
            "MsgId":        "Message ID",
            "CreDtTm":      "Creation Date & Time",
            "CreDt":        "Creation Date",
            "NbOfTxs":      "Number of Transactions",
            "CtrlSum":      "Control Sum",
            "Id":           "Identification",
            "Nm":           "Name",
            "Cd":           "Code",
            "Prtry":        "Proprietary",
            "Issr":         "Issuer",
            "Ref":          "Reference",
            "Dt":           "Date",
            "Amt":          "Amount",
            "Ccy":          "Currency",
            "Ctry":         "Country",
            "Tp":           "Type",
            "Sts":          "Status",
            "Rsn":          "Reason",
            "Inf":          "Information",
            "AddtlInf":     "Additional Information",
            "Fr":           "From",
            "To":           "To",
            "OrgnlMsgId":   "Original Message ID",
            # ── PARTIES ─────────────────────────────────────────────────────
            "Dbtr":         "Debtor",
            "Cdtr":         "Creditor",
            "UltmtDbtr":    "Ultimate Debtor",
            "UltmtCdtr":    "Ultimate Creditor",
            "InitgPty":     "Initiating Party",
            "CdtrAgt":      "Creditor Agent",
            "DbtrAgt":      "Debtor Agent",
            "InstgAgt":     "Instructing Agent",
            "InstdAgt":     "Instructed Agent",
            "IntrmyAgt1":   "Intermediary Agent 1",
            "IntrmyAgt2":   "Intermediary Agent 2",
            "IntrmyAgt3":   "Intermediary Agent 3",
            "PrvsInstgAgt1":"Previous Instructing Agent 1",
            "FwdgAgt":      "Forwarding Agent",
            "Agt":          "Agent",
            "Pty":          "Party",
            # ── FINANCIAL INSTITUTION ───────────────────────────────────────
            "FinInstnId":   "Financial Institution Identification",
            "BICFI":        "BIC (Financial Institution)",
            "ClrSysMmbId":  "Clearing System Member ID",
            "FIId":         "Financial Institution ID",
            "BrnchId":      "Branch ID",
            "LEI":          "Legal Entity Identifier",
            # ── IDENTIFICATION ───────────────────────────────────────────────
            "OrgId":        "Organisation ID",
            "PrvtId":       "Private ID",
            "BirthDt":      "Date of Birth",
            "CityOfBirth":  "City of Birth",
            "CtryOfBirth":  "Country of Birth",
            "TaxId":        "Tax ID",
            "AnyBIC":       "Any BIC",
            # ── ACCOUNTS ────────────────────────────────────────────────────
            "DbtrAcct":     "Debtor Account",
            "CdtrAcct":     "Creditor Account",
            "DbtrAgtAcct":  "Debtor Agent Account",
            "CdtrAgtAcct":  "Creditor Agent Account",
            "Acct":         "Account",
            "IBAN":         "IBAN",
            "AcctId":       "Account ID",
            "AcctOwnr":     "Account Owner",
            "AcctSvcr":     "Account Servicer",
            # ── ADDRESS ─────────────────────────────────────────────────────
            "PstlAdr":      "Postal Address",
            "AdrLine":      "Address Line",
            "StrtNm":       "Street Name",
            "BldgNb":       "Building Number",
            "PstCd":        "Post Code",
            "TwnNm":        "Town Name",
            "CtrySubDvsn":  "Country Sub-Division",
            # ── PAYMENT ─────────────────────────────────────────────────────
            "PmtId":        "Payment Identification",
            "InstrId":      "Instruction ID",
            "EndToEndId":   "End-to-End ID",
            "TxId":         "Transaction ID",
            "UETR":         "Unique End-to-End Transaction Reference",
            "PmtTpInf":     "Payment Type Information",
            "SvcLvl":       "Service Level",
            "LclInstrm":    "Local Instrument",
            "CtgyPurp":     "Category Purpose",
            "Purp":         "Purpose",
            "InstrPrty":    "Instruction Priority",
            "CdtTrfTxInf":  "Credit Transfer Transaction",
            "DrctDbtTxInf": "Direct Debit Transaction",
            "TxInf":        "Transaction Information",
            "IntrBkSttlmAmt": "Interbank Settlement Amount",
            "IntrBkSttlmDt":  "Interbank Settlement Date",
            "InstdAmt":     "Instructed Amount",
            "TtlIntrBkSttlmAmt": "Total Interbank Settlement Amount",
            "XchgRate":     "Exchange Rate",
            "ChrgBr":       "Charge Bearer",
            "ChrgsInf":     "Charges Information",
            # ── SETTLEMENT ──────────────────────────────────────────────────
            "SttlmInf":     "Settlement Information",
            "SttlmMtd":     "Settlement Method",
            "SttlmAcct":    "Settlement Account",
            "SttlmPrty":    "Settlement Priority",
            "SttlmTmIndctn":"Settlement Time Indication",
            "SttlmTmReq":   "Settlement Time Request",
            "ClrSys":       "Clearing System",
            # ── REMITTANCE ──────────────────────────────────────────────────
            "RmtInf":       "Remittance Information",
            "Ustrd":        "Unstructured Remittance",
            "Strd":         "Structured Remittance",
            "CdtrRefInf":   "Creditor Reference Information",
            # ── CAMT (Cash Management) ──────────────────────────────────────
            "Stmt":         "Statement",
            "Ntry":         "Entry",
            "NtryDtls":     "Entry Details",
            "TxDtls":       "Transaction Details",
            "Bal":          "Balance",
            "Acct":         "Account",
            "AcctRpt":      "Account Report",
            "Rpt":          "Report",
            "FlrLmt":       "Floor Limit",
            "LqdtyMgmt":    "Liquidity Management",
            "Lmt":          "Limit",
            "ReqdAmt":      "Requested Amount",
            "ReqdLqdtyTfr": "Requested Liquidity Transfer",
            # ── PAIN (Payment Initiation) ────────────────────────────────────
            "PmtInf":       "Payment Information",
            "PmtMtd":       "Payment Method",
            "NbOfTxs":      "Number of Transactions",
            "ReqdExctnDt":  "Requested Execution Date",
            "ReqdColltnDt": "Requested Collection Date",
            "CdtTrfTxInf":  "Credit Transfer Transaction",
            "DrctDbtTxInf": "Direct Debit Transaction",
            "DrctDbtTx":    "Direct Debit Transaction",
            "MndtRltdInf":  "Mandate Related Information",
            "MndtId":       "Mandate ID",
            # ── PACS (Payment Clearing & Settlement) ────────────────────────
            "OrgnlGrpInfAndSts": "Original Group Information & Status",
            "OrgnlMsgNmId": "Original Message Name ID",
            "OrgnlCreDtTm": "Original Creation Date & Time",
            "TxInfAndSts":  "Transaction Information & Status",
            "OrgnlEndToEndId": "Original End-to-End ID",
            "OrgnlTxId":    "Original Transaction ID",
            "TxSts":        "Transaction Status",
            "StsRsnInf":    "Status Reason Information",
            "AddtlTxInf":   "Additional Transaction Information",
            # ── SESE (Securities Settlement) ────────────────────────────────
            "TradDtls":     "Trade Details",
            "FinInstrmId":  "Financial Instrument ID",
            "ISIN":         "ISIN",
            "PlcOfTrad":    "Place of Trade",
            "SttlmParams":  "Settlement Parameters",
            "DlvrgSttlmPties": "Delivering Settlement Parties",
            "RcvgSttlmPties":  "Receiving Settlement Parties",
            "SfkpgAcct":    "Safekeeping Account",
            # ── REGULATORY ──────────────────────────────────────────────────
            "RgltryRptg":   "Regulatory Reporting",
            "Tax":          "Tax",
            "TaxRcrd":      "Tax Record",
            "TaxAmt":       "Tax Amount",
            # ── head.001 APPLICATION HEADER ─────────────────────────────────
            "BizMsgIdr":    "Business Message Identifier",
            "MsgDefIdr":    "Message Definition Identifier",
            "BizSvc":       "Business Service",
            "CharSet":      "Character Set",
            "Sgntr":        "Signature",
            "DplctRef":     "Duplicate Reference",
            "Prty":         "Priority",
        }

        def tag_label(tag: str) -> str:
            """Returns 'TagName (Full English Name)' using 3-tier lookup:
            1. Live XSD-derived label  2. Static dict  3. CamelCase split"""
            # 1. Live XSD info (most accurate — derived from the actual validated XSD)
            if tag in tag_info:
                lbl = tag_info[tag]['label']
                # Only use it if it adds value (not just the tag name itself)
                if lbl and lbl.strip().lower() != tag.strip().lower():
                    return f"{tag} ({lbl})"

            # 2. Static fallback table (covers common abbreviations across all families)
            full = _STATIC_TAG_NAMES.get(tag)
            if full:
                return f"{tag} ({full})"

            # 3. CamelCase split — skip if tag is too short to be meaningful
            if len(tag) > 2:
                words = self._camel_to_words(tag)
                if words and words.lower() != tag.lower():
                    return f"{tag} ({words})"

            return tag  # Return as-is for very short tags like 'Fr', 'To', 'Id'

        def tag_mandatory(tag: str) -> bool:
            """Returns True if the XSD says this tag is mandatory."""
            return tag_info.get(tag, {}).get('mandatory', True)  # default: assume mandatory

        def tag_repeatable(tag: str) -> bool:

            """Returns True if the XSD allows this tag to repeat."""
            return tag_info.get(tag, {}).get('repeatable', False)


        # ── Helper: extract element name ──────────────────────────────────
        def elem_name(default="A field"):
            m = re.search(r"Element '([^']+)'", msg)
            return m.group(1).split('}')[-1] if m else default

        def attr_name(default="attribute"):
            m = re.search(r"[Aa]ttribute '([^']+)'", msg)
            return m.group(1).split('}')[-1] if m else default

        def bad_value(default=""):
            m = re.search(r"[Vv]alue '([^']*)'", msg)
            return m.group(1) if m else default

        # ── 1. EMPTY MANDATORY FIELD ──────────────────────────────────────
        # Only trigger when lxml literally reported value='' in the message.
        # Do NOT use `val == ""` as that would fire when bad_value() returns its
        # empty-string default (i.e. when there is no value at all in the message).
        if "value ''" in msg.lower() or 'value ""' in msg.lower():
            name = elem_name("A required field")
            return (
                f"❌ Mandatory field '{name}' is empty.",
                f"The field '{name}' cannot be left blank. Please enter a valid value before submitting."
            )

        # ── 2. BIC / BICFI ────────────────────────────────────────────────
        if any(x in msg.upper() for x in ["BICFI", "BICBE", "ANYBIC", "BIC"]):
            bic_val = bad_value()
            if "pattern" in msg.lower() or "facet" in msg.lower():
                if bic_val and len(bic_val) >= 6 and not (bic_val[4].isalpha() and bic_val[5].isalpha()):
                    return (
                        f"❌ Invalid BIC — bad country code: '{bic_val[4:6]}'.",
                        f"Characters 5–6 of a BIC must be a valid 2-letter ISO country code (e.g. 'GB', 'US', 'DE'). "
                        f"Found '{bic_val[4:6]}' in BIC '{bic_val}'. Correct this before resubmitting."
                    )
                if bic_val and len(bic_val) not in (8, 11):
                    return (
                        f"❌ BIC '{bic_val}' has wrong length ({len(bic_val)} chars).",
                        "A valid BIC must be exactly 8 or 11 characters: "
                        "4-char Bank Code + 2-letter Country + 2-char Location + optional 3-char Branch (e.g. BNKGB2LXXX)."
                    )
                return (
                    f"❌ Invalid BIC code format: '{bic_val}'.",
                    "The BIC must follow ISO 9362: 4-letter bank code, 2-letter country code, 2-char location code, "
                    "and optional 3-char branch code. Example: 'BNKGB2LXXX'."
                )
            if "length" in msg.lower() or "atomic type" in msg.lower():
                return (
                    "❌ BIC has incorrect length.",
                    "A BIC (Bank Identifier Code) must be exactly 8 or 11 characters long."
                )

        # ── 3. CURRENCY CODE (attribute) ──────────────────────────────────
        an = attr_name()
        if an.lower() in ("ccy", "currency") or "currency" in msg.lower():
            ccy_val = bad_value()
            if ccy_val:
                return (
                    f"❌ Invalid currency code '{ccy_val}'.",
                    f"'{ccy_val}' is not a recognised ISO 4217 currency code. "
                    f"Use a standard 3-letter code such as 'USD', 'EUR', 'GBP', 'JPY', 'INR', 'AED', etc."
                )
            return (
                "❌ Missing currency code (Ccy attribute).",
                "Add a valid ISO 4217 3-letter currency code as an attribute, e.g. Ccy=\"USD\"."
            )

        # ── 4. GENERIC ATTRIBUTE ERRORS ───────────────────────────────────
        if "attribute" in msg.lower():
            aname = attr_name()
            aval  = bad_value()
            if aname and aval:
                return (
                    f"❌ Invalid value '{aval}' for attribute '{aname}'.",
                    f"The attribute '{aname}' does not accept the value '{aval}'. "
                    f"Check the ISO 20022 standard for the list of allowed values for this attribute."
                )
            if aname:
                return (
                    f"❌ Missing required attribute '{aname}'.",
                    f"The attribute '{aname}' is required but not present in this element. "
                    f"For currency amounts, add Ccy=\"USD\" (or the appropriate currency code)."
                )
            return (
                "❌ A required attribute is missing or invalid.",
                "One or more required attributes (such as Ccy for amount fields) are missing or contain an invalid value."
            )

        # ── 5. DUPLICATE ELEMENT ──────────────────────────────────────────
        if "occurs more than allowed" in msg:
            name = elem_name("A field")
            return (
                f"❌ Duplicate field '{name}'.",
                f"The field '{name}' appears more than once in this section, which is not allowed. "
                f"Remove the extra copy and keep only one."
            )

        # ── 6. MISSING TAG or WRONG ORDER ─────────────────────────────────
        # lxml says "Element 'X' is not expected. Expected is (Y)." in two cases:
        #   a) Y ≠ X  →  Y is MISSING — X appeared in its place (most common)
        #   b) Y = X  →  X is a DUPLICATE
        if "is not expected" in msg:
            m = re.search(
                r"Element '([^']+)': This element is not expected\. Expected is(?: one of)? \(([^)]+)\)\.", msg
            )
            if m:
                found_elem_full = m.group(1)
                found_elem = found_elem_full.split('}')[-1] if '}' in found_elem_full else found_elem_full
                expected_str = m.group(2)

                # --- Duplicate: the found element IS in the expected list ---
                if found_elem in expected_str:
                    label = tag_label(found_elem)
                    return (
                        f"❌ Tag <{found_elem}> is duplicated.",
                        f"The tag <{label}> appears more than once in this section. "
                        f"Remove the extra copy and keep only one."
                    )

                # --- Missing: a completely different element was expected ---
                # lxml reports the FIRST tag in the sequence as expected — but it may be
                # OPTIONAL (e.g. CharSet in head.001). Walk through all expected candidates
                # to find the first MANDATORY one from the XSD.
                all_expected = [t.strip().strip('()') for t in expected_str.split(',')]

                # Find the first truly mandatory expected tag
                mandatory_missing = None
                for candidate in all_expected:
                    if tag_mandatory(candidate):   # uses live XSD info
                        mandatory_missing = candidate
                        break

                # If all candidates are optional (unlikely but possible), fall back to first
                first_expected = mandatory_missing or all_expected[0]
                missing_label  = tag_label(first_expected)
                found_label    = tag_label(found_elem)

                # If the reported-expected tag was optional but we found a mandatory one, note it
                originally_reported = all_expected[0]
                if mandatory_missing and mandatory_missing != originally_reported:
                    optional_note = (
                        f"Note: <{tag_label(originally_reported)}> is optional and was skipped; "
                        f"the required element is <{missing_label}>. "
                    )
                else:
                    optional_note = ""

                return (
                    f"❌ Missing mandatory tag <{first_expected}>.",
                    f"The tag <{missing_label}> is required here but was not found in the XML. "
                    f"Instead, <{found_label}> was encountered at this position. "
                    f"{optional_note}"
                    f"Add <{first_expected}>...</{first_expected}> before <{found_elem}> to fix this error."
                )

            # No match for the structured pattern — generic fallback
            name = elem_name("field")
            return (
                f"❌ Tag <{name}> is not expected at this position.",
                f"<{name}> cannot appear at this location in the message. "
                "Check the ISO 20022 schema for the correct field sequence."
            )

        # ── 7. MISSING MANDATORY CHILD FIELD ─────────────────────────────
        # lxml: "Element 'GrpHdr': Missing child element(s). Expected is (NbOfTxs)."
        if any(x in msg for x in ["Missing child element", "content is incomplete", "fails to occur"]):
            m = re.search(r"Element '([^']+)':.*Expected is(?: one of)? \(([^)]+)\)\.", msg)
            if not m:
                m = re.search(r"Element '([^']+)':.*'([^']+)' fails to occur", msg)
            if m:
                parent        = m.group(1)
                missing_all   = m.group(2)
                first_missing = missing_all.split(',')[0].strip().strip('()')
                parent_label  = tag_label(parent)
                missing_label = tag_label(first_missing)
                return (
                    f"❌ Mandatory tag <{first_missing}> is missing inside <{parent}>.",
                    f"The required tag <{missing_label}> was not found inside <{parent_label}>. "
                    f"Add <{first_missing}>...</{first_missing}> to complete this section. "
                    f"All expected tags in this section: {missing_all}."
                )
            return (
                "❌ A required tag is missing from this section.",
                "One or more mandatory tags are absent. "
                "Check the ISO 20022 schema to identify which tags must be present."
            )

        # ── 8. DATE FORMAT ────────────────────────────────────────────────
        if "date" in msg.lower() and "is not a valid value" in msg.lower():
            dv = bad_value()
            if "datetime" in msg.lower():
                return (
                    f"❌ Invalid date/time value: '{dv}'.",
                    "Date-time fields must use the format YYYY-MM-DDThh:mm:ss (e.g. 2026-11-20T14:30:00). "
                    "Ensure there is no trailing space and the 'T' separator is present."
                )
            return (
                f"❌ Invalid date value: '{dv}'.",
                "Date fields must use the format YYYY-MM-DD (e.g. 2026-11-20). "
                "Do not include time or timezone information in plain date fields."
            )

        # ── 9. AMOUNT / DECIMAL FORMAT ────────────────────────────────────
        if "decimal" in msg.lower() or ("amount" in msg.lower() and "is not a valid" in msg.lower()):
            av = bad_value()
            return (
                f"❌ Invalid amount value: '{av}'.",
                "Amount fields must contain a plain decimal number without currency symbols or commas "
                "(e.g. 1500.00). Do not add 'USD' or ',' inside the amount tag."
            )

        # ── 10. GENERIC ATOMIC TYPE / DATA FORMAT ─────────────────────────
        if "is not a valid value of the atomic type" in msg or "datatype" in msg:
            tv = bad_value()
            tn_m = re.search(r"atomic type '([^']+)'", msg)
            tn = tn_m.group(1).split('}')[-1] if tn_m else None
            name = elem_name()
            if tn:
                return (
                    f"❌ Field '{name}' has an invalid value: '{tv}'.",
                    f"This field requires type '{tn}'. Please verify the value '{tv}' matches the expected format."
                )
            return (
                f"❌ Invalid value '{tv}' in field '{name}'.",
                "The value does not match the required data type for this field. "
                "Check for extra spaces, wrong number format, or unsupported characters."
            )

        # ── 11. PATTERN / FORMAT MISMATCH ─────────────────────────────────
        if "pattern" in msg.lower() or "is not accepted by the pattern" in msg.lower():
            pv = bad_value()
            name = elem_name()
            field_hints = {
                "IBAN": "An IBAN starts with a 2-letter country code followed by 2 check digits and up to 30 digits (e.g. GB29NWBK60161331926819).",
                "MIC":  "A MIC (Market Identifier Code) must be exactly 4 uppercase letters (e.g. XLON).",
                "LEI":  "An LEI must be exactly 20 alphanumeric characters.",
                "ISIN": "An ISIN must be exactly 12 alphanumeric characters starting with a 2-letter country code.",
            }
            for key, hint in field_hints.items():
                if key in name.upper() or key in msg.upper():
                    return (f"❌ Invalid {key} format: '{pv}'.", hint)
            return (
                f"❌ Invalid format for field '{name}': '{pv}'.",
                f"The value '{pv}' does not match the required format for '{name}'. "
                "Check for illegal characters, wrong length, or an unsupported pattern."
            )

        # ── 12. ENUMERATION (code not in allowed set) ─────────────────────
        if "enumeration" in msg.lower() or "is not an element of the set" in msg.lower():
            ev = bad_value()
            name = elem_name()
            return (
                f"❌ Invalid code '{ev}' for field '{name}'.",
                f"'{ev}' is not a valid code for '{name}'. "
                "This field only accepts specific ISO 20022 codes. "
                "Check the standard for the list of allowed values (e.g. SLEV, SHAR, CRED, DEBT for ChrgBr)."
            )

        # ── 13. LENGTH CONSTRAINT ─────────────────────────────────────────
        if "length" in msg.lower() and ("maxlength" in msg.lower() or "minlength" in msg.lower() or "facet" in msg.lower()):
            name = elem_name()
            lv = bad_value()
            return (
                f"❌ Field '{name}' has an invalid length: '{lv}'.",
                f"The value '{lv}' is either too long or too short for '{name}'. "
                "Check the maximum and minimum character length allowed by the schema."
            )

        # ── 14. ELEMENT NOT ALLOWED / MISPLACED ───────────────────────────
        if "not allowed here" in msg or "not permitted" in msg.lower():
            name = elem_name()
            return (
                f"❌ Field '{name}' is not allowed in this location.",
                f"'{name}' cannot appear at this position in the message. "
                "Remove it or move it to the correct parent element as per the ISO 20022 schema."
            )

        # ── 15. SMART FALLBACK ────────────────────────────────────────────
        # Strip remaining raw lxml patterns to produce a readable fallback
        clean = msg
        clean = re.sub(r"Element '([^']+)':", r"Field '\1':", clean)
        clean = re.sub(r"\[facet '[^']+'\]\s*", "", clean)
        clean = re.sub(r"is not accepted by the pattern '[^']+'\.?", "has an invalid format.", clean)
        clean = re.sub(r"is not a valid value of the atomic type '[^']+'\.?", "contains an invalid value.", clean)
        clean = re.sub(r"is not an element of the set \{[^}]+\}\.?", "contains an invalid code.", clean)
        clean = clean.strip()

        return (
            f"❌ Validation error: {clean}",
            "Please review this field. Ensure the value follows the ISO 20022 standard format, "
            "uses allowed codes, and does not contain unsupported characters."
        )


