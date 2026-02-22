import time
import uuid
import re
import os
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set
import zipfile
from lxml import etree

class ValidationIssue:
    def __init__(self, severity: str, layer: int, code: str, path: str, message: str, fix_suggestion: str = "", related_test: str = ""):
        self.severity = severity
        self.layer = layer
        self.code = code
        self.path = path
        self.message = message
        self.fix_suggestion = fix_suggestion
        self.related_test = related_test

    def to_dict(self):
        return {
            "severity": self.severity,
            "layer": self.layer,
            "code": self.code,
            "path": self.path,
            "message": self.message,
            "fix_suggestion": self.fix_suggestion,
            "related_test": self.related_test
        }

class ValidationReport:
    def __init__(self, validation_id: str, message_type: str, mode: str):
        self.validation_id = validation_id
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.message_type = message_type
        self.mode = mode
        self.status = "PASS"
        self.schema_version = "Unknown"
        self.errors = 0
        self.warnings = 0
        self.total_time_ms = 0
        self.layer_status = {}
        self.issues = []

    def add_issue(self, issue: ValidationIssue):
        self.issues.append(issue.to_dict())
        if issue.severity == "ERROR":
            self.errors += 1
            self.status = "FAIL"
        elif issue.severity == "WARNING":
            self.warnings += 1
            # User Request: Treat WARNING as PASS
            # if self.status != "FAIL":
            #     self.status = "WARNING"

    def to_dict(self):
        # Step 9: Generate Validation Report Format
        return {
            "validation_id": self.validation_id,
            "timestamp": self.timestamp,
            "status": self.status,
            "schema": self.schema_version,
            "message": self.message_type,
            "errors": self.errors,
            "warnings": self.warnings,
            "total_time_ms": round(self.total_time_ms, 2),
            "layer_status": self.layer_status,
            "details": self.issues
        }


class ISOValidator:
    def __init__(self):
        # Path configuration
        base_dir = os.path.dirname(os.path.abspath(__file__))
        backend_root = os.path.normpath(os.path.join(base_dir, "../../"))
        
        self.xsd_path = os.path.join(backend_root, "xsds", "extracted")
        self.rules_path = os.path.join(backend_root, "app", "resources", "rules")
        self.codelists_path = os.path.join(backend_root, "app", "resources", "codelists")
        self.bics_path = os.path.join(backend_root, "bics")
        
        # Load Configuration
        self.config_path = os.path.join(backend_root, "app", "resources", "config.json")
        self.config = self._load_config()
        
        # Step 4 Mapping: Version to SR Version (Dynamic)
        self.sr_mapping = self.config.get("sr_versions", {
            "pacs.008.001.08": "SR2025",
            "pacs.009.001.08": "SR2025"
        })
        
        # Cache for message types
        self._message_type_cache = []
        self._last_cache_update = 0
        self._cache_duration = 3600 # 1 hour
        
        # Load Reference Data
        self._ensure_xsds_extracted()
        self.supported_bics = self._load_bics()
        self.codelists = self._load_codelists()
        
        print(f"ISOValidator Initialized:")
        print(f" - XSD Path: {self.xsd_path}")
        print(f" - Config Loaded: {bool(self.config)}")
        print(f" - BICs Loaded: {len(self.supported_bics)}")

    def _load_config(self) -> Dict[str, Any]:
        """Loads the dynamic configuration file"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
        return {}

    def _load_bics(self) -> Set[str]:
        """Loads BIC codes from the entities.ftm.json file (JSONL format)"""
        bics = set()
        file_path = os.path.join(self.bics_path, "entities.ftm.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            data = json.loads(line)
                            swift_bics = data.get("properties", {}).get("swiftBic", [])
                            for bic in swift_bics:
                                bics.add(bic.upper())
                        except:
                            continue
            except Exception as e:
                print(f"Error loading BICs: {e}")
        return bics

    def _ensure_xsds_extracted(self):
        """
        High-Performance Extraction Engine:
        Automatically unzips all XSD blueprints from the ZIP library into 
        the 'extracted' directory for instant validation readiness.
        """
        source_dir = os.path.dirname(self.xsd_path)
        if not os.path.exists(self.xsd_path):
            os.makedirs(self.xsd_path)

        if not os.path.exists(source_dir):
            return

        print(f"Auto-Syncing XSD Library...")
        import zipfile
        for filename in os.listdir(source_dir):
            if filename.endswith(".zip"):
                zip_path = os.path.join(source_dir, filename)
                try:
                    with zipfile.ZipFile(zip_path, 'r') as zf:
                        # Extract only .xsd files that don't exist yet to save time
                        for member in zf.namelist():
                            if member.endswith(".xsd"):
                                base_name = os.path.basename(member)
                                if not base_name: continue
                                
                                target_file = os.path.join(self.xsd_path, base_name)
                                if not os.path.exists(target_file):
                                    with zf.open(member) as source, open(target_file, 'wb') as target:
                                        target.write(source.read())
                except Exception as e:
                    print(f"Warning: Could not extract {filename}: {e}")

    def _load_codelists(self) -> Dict[str, Any]:
        """Loads all JSON codelists from the resource directory"""
        lists = {}
        if os.path.exists(self.codelists_path):
            for filename in os.listdir(self.codelists_path):
                if filename.endswith(".json"):
                    try:
                        with open(os.path.join(self.codelists_path, filename), 'r') as f:
                            lists[filename.replace(".json", "")] = json.load(f)
                    except:
                        continue
        return lists

    def get_supported_messages(self) -> List[str]:
        """
        Scans the XSD directory and ZIP files for supported message types.
        Caches results for performance.
        """
        now = time.time()
        if self._message_type_cache and (now - self._last_cache_update < self._cache_duration):
            return self._message_type_cache

        messages = set()
        
        # 1. Scan extracted directory
        if os.path.exists(self.xsd_path):
            for root, dirs, files in os.walk(self.xsd_path):
                for file in files:
                    if file.endswith(".xsd"):
                        messages.add(file.replace(".xsd", ""))
        
        # 2. Scan ZIP files efficiently (just names)
        source_dir = os.path.dirname(self.xsd_path)
        if os.path.exists(source_dir):
            import zipfile
            for filename in os.listdir(source_dir):
                if filename.endswith(".zip"):
                    zip_path = os.path.join(source_dir, filename)
                    try:
                        with zipfile.ZipFile(zip_path, 'r') as zf:
                            for name in zf.namelist():
                                if name.endswith(".xsd"):
                                    base = os.path.basename(name).replace(".xsd", "")
                                    if base:
                                        messages.add(base)
                    except:
                        pass
        
        if not messages:
            # Enhanced fallback list from Config
            fallback = self.config.get("fallback_message_types", [
                "pacs.008.001.08", "pacs.009.001.08", "pacs.002.001.10"
            ])
            self._message_type_cache = sorted(fallback)
        else:
            self._message_type_cache = sorted(list(messages))
            
        self._last_cache_update = now
        return self._message_type_cache

    async def validate(self, xml_content: str, mode: str = "Full 1-3", message_type: str = "Auto-detect", filename: Optional[str] = None) -> ValidationReport:
        """
        Main 10-Step Validation Flow
        """
        start_time = time.time()
        
        # 0. Detect Identity or use provided type
        if not message_type or message_type == "Auto-detect":
            detected_type = self._detect_message_type(xml_content)
        else:
            detected_type = message_type

        # Keep full version in report for UI display
        # The _get_xsd_path function will handle version-blind matching internally

        validation_id = f"VAL-{time.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        report = ValidationReport(validation_id, detected_type, mode)

        try:
            # STEP 1 & 2: Safe XML Parse & Well-formedness (Layer 1)
            # STEP 3: Identity & Rejection logic is here
            try:
                if not await self._run_layer_1(xml_content, report, filename):
                    return self._finalize_report(report, start_time)
            except Exception as e:
                report.add_issue(ValidationIssue("ERROR", 1, "FATAL_L1", "/", f"Critical failure in Layer 1: {str(e)}", "Check if XML is properly formed."))
                return self._finalize_report(report, start_time)

            # Post-parsing cleanup: If type was "Unknown", try to refine from detected namespace
            try:
                if (report.message_type == "Unknown" or not report.message_type) and "Namespace" in report.metadata:
                    ns = report.metadata["Namespace"]
                    extracted = "Unknown"
                    if "xsd:" in ns:
                        extracted = ns.split("xsd:")[-1]
                    elif any(f in ns for f in ["pacs.", "camt.", "pain.", "sese.", "head."]):
                        parts = ns.split(":")
                        extracted = parts[-1]
                    
                    if extracted != "Unknown":
                        # Keep full version for display
                        report.message_type = extracted
                        detected_type = extracted
            except: 
                pass # Non-critical failure

            if mode != "Layer 1 only":
                try:
                    layer2_success = await self._run_layer_2(xml_content, report, detected_type)
                    if not layer2_success:
                         # ⛔ Rejection: If XSD fails, stop here (Requirement Step 4)
                         return self._finalize_report(report, start_time)
                except Exception as e:
                    report.add_issue(ValidationIssue("ERROR", 2, "FATAL_L2", "/", f"Critical failure in Layer 2 (XSD): {str(e)}", "Ensure the XSD library is available."))
                    return self._finalize_report(report, start_time)
            
            # STEP 5: Canonical Normalization for Rule Execution
            try:
                canonical_data, line_map = self._normalize_message(xml_content)
            except Exception as e:
                report.add_issue(ValidationIssue("ERROR", 3, "FATAL_L3", "/", f"Failed to normalize message: {str(e)}"))
                return self._finalize_report(report, start_time)

            # STEP 6-9: Dynamic Rule Engine (Layers 1-3)
            # Load all rules once
            try:
                all_rules = self._load_all_rules(detected_type)
                
                if mode == "Full 1-3":
                    for layer_id in [3]:
                        self._run_dynamic_layer(layer_id, all_rules, canonical_data, line_map, report)
                        
                        # Stop if this layer failed
                        layer_status = report.layer_status.get(str(layer_id), {}).get("status")
                        if layer_status == "❌":
                            break
            except Exception as e:
                report.add_issue(ValidationIssue("WARNING", 3, "RULE_ENGINE_ERR", "/", f"Rule Engine encountered an issue: {str(e)}", "Partial validation completed."))

        except Exception as e:
            report.add_issue(ValidationIssue("ERROR", 0, "SYSTEM_ERR", "/", f"General system failure: {str(e)}"))
            import traceback; traceback.print_exc()
            
        return self._finalize_report(report, start_time)

    def _normalize_message(self, xml_content: str) -> tuple:
        """
        Step 5: Canonical Message Creation
        Converts XML to a flat canonical JSON structure with indexed paths.
        Returns (data_map, line_map)
        """
        canonical = {}
        line_map = {}
        try:
            parser = etree.XMLParser(recover=True, remove_blank_text=True)
            root = etree.fromstring(xml_content.encode('utf-8'), parser)
            
            def get_clean_tag(tag):
                return tag.split('}')[-1] if '}' in tag else tag

            def flatten(element, path=""):
                if path:
                    line_map[path] = element.sourceline

                # 1. Attributes
                for k, v in element.attrib.items():
                    attr_name = get_clean_tag(k)
                    attr_path = f"{path}@{attr_name}" if path else f"@{attr_name}"
                    canonical[attr_path] = v
                    line_map[attr_path] = element.sourceline

                # 2. Text value
                if element.text and element.text.strip():
                    canonical[path] = element.text.strip()

                # 3. Children with indexing for repeats
                tag_counts = {}
                for child in element:
                    tag = get_clean_tag(child.tag)
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
                
                current_counts = {}
                for child in element:
                    tag = get_clean_tag(child.tag)
                    
                    # Construct indexed path: Tag[0], Tag[1] if multiple exist
                    if tag_counts[tag] > 1:
                        idx = current_counts.get(tag, 0)
                        indexed_tag = f"{tag}[{idx}]"
                        current_counts[tag] = idx + 1
                    else:
                        indexed_tag = tag
                        
                    new_path = f"{path}.{indexed_tag}" if path else indexed_tag
                    flatten(child, new_path)

            # ISO 20022 Messages typically contain AppHdr and Document
            # We flatten both into the same flat map for rule access
            for part in ["AppHdr", "Document"]:
                node = root.find(f".//{{*}}{part}")
                if node is not None:
                    flatten(node, part)
                    
            # If nothing found by part name, flatten the whole thing from root
            if not canonical:
                flatten(root, get_clean_tag(root.tag))
                
        except Exception as e:
            print(f"DEBUG: Normalization Error: {e}")
            
        return canonical, line_map

    def _detect_message_type(self, xml_content: str) -> str:
        """
        Robust Message Type Detection - Prioritizes Payload over Header
        """
        # Load dynamic scan limit
        scan_limit = self.config.get("app_settings", {}).get("scan_limit_chars", 10000)

        # 1. Broad Namespace Search (Handles single/double quotes)
        ns_patterns = self.config.get("validation_rules", {}).get("namespace_patterns", [
            r'xmlns[:\w]*\s*=\s*["\']urn:iso:std:iso:20022:tech:xsd:([^"\']+)["\']',
            r'xmlns[:\w]*\s*=\s*["\']urn:swift:xsd:([^"\']+)["\']'
        ])
        
        candidates = []
        for pattern in ns_patterns:
            for match in re.finditer(pattern, xml_content[:scan_limit]): # Dynamic Scan Limit
                val = match.group(1).strip()
                # Prioritize non-header and non-envelope types
                if all(x not in val.lower() for x in ["head.001", "envelope", "busmsgenvlp"]):
                    return val
                candidates.append(val)
        
        # If only head found so far, return it as last resort
        if candidates:
            return candidates[0]

        # 2. MsgDefIdr Tag Search (Often has the correct Business Type)
        match_hdr = re.search(r'<MsgDefIdr>([^<]+)</MsgDefIdr>', xml_content)
        if match_hdr:
            return match_hdr.group(1).strip()

        # 3. Root Tag Heuristic (e.g. <pacs.008.001.08 ...>)
        match_root = re.search(r'<([a-z]{4}\.[0-9]{3}\.[0-9]{3}\.[0-9]{2})', xml_content[:2000])
        if match_root:
            return match_root.group(1).strip()

        # 4. Family Fallback
        families = self.config.get("supported_families_fallback", ["pacs.008", "pacs.009", "pain.001", "camt.053"])
        for family in families:
            if family in xml_content[:5000]: # Search first 5K for performance
                return family
        
        return "Unknown"

    def _finalize_report(self, report: ValidationReport, start_time: float) -> ValidationReport:
        # Calculate total time as the sum of all layer times to ensure consistency in UI
        total_layers = sum(l.get("time", 0) for l in report.layer_status.values())
        report.total_time_ms = total_layers
        return report

    async def _run_layer_1(self, xml_content: str, report: ValidationReport, filename: Optional[str] = None) -> bool:
        """
        LAYER 1 — Technical / Payload Validation
        Strict alignment with user logic (Steps 1-8)
        """
        start = time.time()
        
        # 1. Payload Presence
        if not xml_content or not xml_content.strip():
            report.add_issue(ValidationIssue(
                "ERROR", 1, "Empty File", "Payload Missing",
                "The uploaded file is empty or no content was provided.",
                "Please upload a valid XML message file or paste XML content."
            ))
            report.layer_status["1"] = {"status": "❌", "time": (time.time() - start) * 1000}
            return False

        # 2. File Type Validation
        allowed_exts = ('.xml', '.xsd', '.txt')
        valid_ext = filename.lower().endswith(allowed_exts) if filename else True
        
        # Check content structure (must look like XML)
        has_xml_structure = xml_content.lstrip().startswith(('<', '<?xml'))
        
        if not valid_ext:
             report.add_issue(ValidationIssue(
                "ERROR", 1, "Wrong File Type", "Invalid Extension",
                f"The file '{filename}' is not supported.",
                "Please upload a file with .xml, .xsd, or .txt extension."
            ))
             report.layer_status["1"] = {"status": "❌", "time": (time.time() - start) * 1000}
             return False

        if not has_xml_structure:
             report.add_issue(ValidationIssue(
                "ERROR", 1, "Invalid Content", "XML Content Required",
                "The file content does not appear to be valid XML.",
                "The file must contain XML code starting with '<' or '<?xml'."
            ))
             report.layer_status["1"] = {"status": "❌", "time": (time.time() - start) * 1000}
             return False

        # 3. Payload Size
        size_kb = len(xml_content.encode('utf-8')) / 1024
        max_size = self.config.get("app_settings", {}).get("max_file_size_kb", 2048) # Default 2MB
        if size_kb > max_size:
             report.add_issue(ValidationIssue(
                 "ERROR", 1, "File Too Large", "Size Limit Exceeded", 
                 f"Your message is {size_kb:.1f} KB, which exceeds the maximum allowed size of {max_size} KB.",
                 f"Please reduce the message size. The limit is {max_size} KB."
             ))
             report.layer_status["1"] = {"status": "❌", "time": (time.time() - start) * 1000}
             return False

        # 4. UTF-8 Encoding
        # Strictly check for the presence and value of the encoding header
        header_match = re.search(r'<\?xml[^>]+encoding=["\']([^"\']+)["\']', xml_content, re.IGNORECASE)
        if not header_match:
             report.add_issue(ValidationIssue(
                "ERROR", 1, "Missing Header", "No XML Declaration",
                "Your XML file is missing the required declaration header.",
                "Add this line at the very top of your file: <?xml version=\"1.0\" encoding=\"UTF-8\"?>"
            ))
             report.layer_status["1"] = {"status": "❌", "time": (time.time() - start) * 1000}
             return False
        else:
            encoding = header_match.group(1).upper()
            if encoding != "UTF-8":
                report.add_issue(ValidationIssue(
                    "ERROR", 1, "Wrong Encoding", "Invalid Character Encoding",
                    f"Your file uses {encoding} encoding, but ISO 20022 messages must use UTF-8.",
                    "Change the encoding in your XML header to: <?xml version=\"1.0\" encoding=\"UTF-8\"?>"
                ))
                report.layer_status["1"] = {"status": "❌", "time": (time.time() - start) * 1000}
                return False

        # 5. Illegal Characters (ASCII 0-31 except tab/newline/cr)
        illegal_chars = re.findall(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', xml_content)
        if illegal_chars:
            report.add_issue(ValidationIssue(
                "ERROR", 1, "Invalid Characters", "Hidden Characters Found",
                "Your message contains invisible control characters that are not allowed.",
                "These hidden characters may have come from copy-pasting. Please use a plain text editor to clean your XML."
            ))
            report.layer_status["1"] = {"status": "❌", "time": (time.time() - start) * 1000}
            return False

        # 6. XML Well-Formedness
        try:
            xml_bytes = xml_content.encode('utf-8')
            parser = etree.XMLParser(recover=False, no_network=True, remove_blank_text=True)
            root = etree.fromstring(xml_bytes, parser)
            
            # 7. Envelope Detection (Document / BusMsg / AppHdr)
            # Support standard Document, SWIFT-style BusMsg, and Envelopes
            iso_nodes = root.xpath("//*[local-name()='Document' or local-name()='BusMsg' or local-name()='AppHdr' or local-name()='BusMsgEnvlp']")
            if not iso_nodes and any(x in root.tag for x in ['Document', 'BusMsg', 'AppHdr', 'BusMsgEnvlp']):
                iso_nodes = [root]
            
            if not iso_nodes:
                report.add_issue(ValidationIssue(
                    "ERROR", 1, "Missing Structure", "No ISO 20022 Container",
                    "Your XML is missing the required <Document> or <BusMsg> wrapper element.",
                    "ISO 20022 messages must have a <Document> root element. Check the message structure against standard templates."
                ))
                report.layer_status["1"] = {"status": "❌", "time": (time.time() - start) * 1000}
                return False

            # 8. Identity Extraction
            # Prioritize the payload node (Document/BusMsg) for the message identity
            payload_node = root.xpath("//*[local-name()='Document' or local-name()='BusMsg']")
            doc_node = payload_node[0] if payload_node else iso_nodes[0]
            
            ns = doc_node.nsmap.get(None) or ""
            
            # Namespace Validation
            if not re.match(r'^urn:iso:std:iso:20022:tech:xsd:[a-z]{4}\.\d{3}\.\d{3}\.\d{2}$', ns) and "head.001" not in ns:
                report.add_issue(ValidationIssue(
                    "ERROR", 1, "Wrong Namespace", str(doc_node.sourceline or 1),
                    f"The namespace '{ns}' doesn't match the ISO 20022 standard format.",
                    "Use the correct namespace format: urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08 (example for pacs.008)."
                ))

            # Metadata for later layers
            report.metadata = {"Namespace": ns}

        except etree.XMLSyntaxError as e:
            report.add_issue(ValidationIssue(
                "ERROR", 1, "XML Syntax Error", f"Line {e.lineno}",
                "Your XML has a syntax error - check for missing or incorrect tags.",
                f"Error details: {str(e)}. Common issues: unclosed tags, missing brackets, or typos in element names."
            ))
            report.layer_status["1"] = {"status": "❌", "time": (time.time() - start) * 1000}
            return False

        # Finish Layer 1
        success = report.status != "FAIL"
        report.layer_status["1"] = {"status": "✅" if success else "❌", "time": round((time.time() - start) * 1000, 2)}
        return success

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
            
            # Extract namespacing
            xml_ns = main_cleaned.nsmap.get(None) or ""
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
                        # Msg format: "Element 'ChrgBr': [facet 'enumeration'] The value 'JEEC'..."
                        tag_match = re.search(r"Element '([^']+)'", error.message)
                        val_match = re.search(r"value '([^']+)'|Value '([^']+)'", error.message)
                        
                        if tag_match:
                            tag_full = tag_match.group(1)
                            # Strip namespace {urn...} if present
                            tag_name = tag_full.split('}')[-1] if '}' in tag_full else tag_full
                            
                            candidates = main_node.xpath(f".//*[local-name()='{tag_name}']")
                            found_line = None
                            
                            if val_match:
                                # Case 1: Specific Value Error (High Precision)
                                bad_val = val_match.group(1) or val_match.group(2)
                                for c in candidates:
                                    if c.text and c.text.strip() == bad_val:
                                        found_line = c.sourceline
                                        break
                                
                                # Ultimate Fallback: Text Search for <Tag>Value</Tag>
                                if not found_line:
                                    pattern = re.compile(f"<{tag_name}[^>]*>\s*{re.escape(bad_val)}\s*</{tag_name}>")
                                    match = pattern.search(xml_content)
                                    if match:
                                        found_line = xml_content.count('\n', 0, match.start()) + 1
                                        
                            elif candidates:
                                # Case 2: Structure/Missing Error (No bad value to match)
                                # Just find the first instance of the problematic tag in the original tree.
                                # This is better than a random offset.
                                if candidates[0].sourceline:
                                    found_line = candidates[0].sourceline
                                    
                            if found_line:
                                real_line = found_line
                    except:
                        pass # Fallback to calculated line

                    friendly_msg, suggestion = self._simplify_error_message(error.message)
                    issues.append(ValidationIssue("ERROR", 2, "SCHEMA_VAL", str(real_line), friendly_msg, suggestion))

            # Step 11 — Mandatory Header Logic (head.001)
            app_hdr_node = full_xml_doc.find(".//{*}AppHdr")
            if app_hdr_node is not None:
                h_line_offset = app_hdr_node.sourceline or 1
                h_ns = app_hdr_node.nsmap.get(None) or ""
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
                        
                        h_val_doc = h_clean
                        if h_xsd_ns and h_ns != h_xsd_ns:
                            h_val_doc = self._mask_namespace(h_clean, h_xsd_ns)

                        # 2. Validate
                        h_schema.assertValid(h_val_doc)
                    except etree.DocumentInvalid as deh:
                        for error in deh.error_log:
                            # Map relative line back to absolute line
                            h_real_line = h_line_offset + error.line - 1
                            friendly_msg, suggestion = self._simplify_error_message(error.message)
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

    def _mask_namespace(self, element, new_ns: str):
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

    def _simplify_error_message(self, message: str) -> tuple:
        """
        Premium Translation Engine: Converts technical XSD/Lxml jargon into 
        Clean, Human-Readable Business English.
        """
        # Strip namespaces and internal technical brackets
        msg = re.sub(r'\{[^}]+\}', '', message)
        
        # --- 1. PRIORITY CASE: Mandatory Fields left empty ---
        # Often reported as: The value '' is not accepted by the pattern...
        if "value ''" in msg.lower() or "value \"\"" in msg.lower():
            match = re.search(r"Element '([^']+)':", msg)
            name = match.group(1) if match else "A required field"
            return (f"The field '{name}' is mandatory but was left empty.", 
                    f"Please provide a value for '{name}'. This field cannot be empty in a standard ISO 20022 message.")

        # --- 2. SPECIAL CASE: BIC/BICFI Failures ---
        if any(x in msg.upper() for x in ["BICFI", "BICBE", "ANYBIC", "BIC"]):
            # Extract the actual value if possible for deeper diagnosis
            val_match = re.search(r"value '([^']+)'", msg)
            val = val_match.group(1) if val_match else ""
            
            if "pattern" in msg.lower():
                # Specific diagnosis: Is it the 5th/6th character (Country Code)?
                if len(val) >= 6 and not (val[4].isalpha() and val[5].isalpha()):
                    return ("Invalid BIC Country Code.", 
                            f"The BIC '{val}' is 8/11 characters long, but characters 5 and 6 (the Country Code) must be letters only (e.g., 'GB', 'US', 'FR'). Found '{val[4:6]}'.")
                
                return ("Invalid BIC Code format.", 
                        "The BIC code provided does not match the ISO 9362 standard. A valid BIC must be exactly 8 or 11 characters long and consist of: 4-char bank code, 2-letter country code, 2-char location code, and optional 3-char branch code (e.g., BNKGB2LXXX).")
            
            if "atomic type" in msg.lower() or "length" in msg.lower():
                return ("Incorrect BIC Length.", "International identifiers (BIC) must be either 8 or 11 characters long.")

        # --- 3. Duplicate Fields ---
        if "occurs more than allowed" in msg:
            match = re.search(r"Element '([^']+)':", msg)
            name = match.group(1) if match else "A field"
            return (f"The field '{name}' is duplicated.", 
                    f"You have used '{name}' more than once in this section. Please remove the extra entry.")

        # --- 4. Sequence & Order (Misplacement) ---
        if "is not expected" in msg:
            match = re.search(r"Element '([^']+)': This element is not expected\. Expected is one of \(([^)]+)\)\.", msg)
            if match:
                elem, expected = match.group(1), match.group(2)
                # Check for likely duplicate based on 'expected' context
                if elem in expected:
                    return (f"The field '{elem}' is repeated.", 
                            f"It looks like you have added '{elem}' twice. Please check and remove the duplicate entry.")
                
                return (f"The field '{elem}' is in the wrong place.", 
                        f"Move the '{elem}' tag so it appears after one of these fields: {expected}. The standard requires a strict sequence.")
            
            return ("The message structure is in the wrong order.", "Some fields are misplaced. Please align them with the standard ISO 20022 sequence (XSD structure).")

        # --- 5. Missing Fields ---
        if any(x in msg for x in ["Missing child element", "content is incomplete", "fails to occur"]):
            match = re.search(r"Element '([^']+)':.*Expected is \(([^)]+)\)\.", msg)
            if not match:
                match = re.search(r"Element '([^']+)':.*'([^']+)' fails to occur", msg)
            
            if match:
                parent, missing = match.group(1), match.group(2)
                return (f"Missing mandatory data in the '{parent}' section.", 
                        f"The required tag(s) '{missing}' were not found. Please add this information to make the message valid.")
            
            return ("Required information is missing.", "Ensure all mandatory fields in this section are filled out according to the schema blueprints.")

        # --- 6. Data Formats (Dates, Amounts, Codes) ---
        if "is not a valid value of the atomic type" in msg or "datatype" in msg:
            if "date" in msg.lower() and not "datetime" in msg.lower():
                return ("Invalid Date format.", "Use the standard format: YYYY-MM-DD (e.g., 2026-11-20).")
            if "dateTime" in msg.lower():
                return ("Invalid Date & Time format.", "Use the format: YYYY-MM-DDThh:mm:ss (e.g., 2026-11-20T14:45:00).")
            if "decimal" in msg.lower() or "amount" in msg.lower():
                return ("Invalid Amount format.", "Use numbers with a decimal point (e.g., 1500.25). Do not use commas as thousands separators.")
            
            match = re.search(r"Value '([^']+)' is not a valid value of the atomic type '([^']+)'", msg)
            if match:
                val, type_name = match.group(1), match.group(2)
                return (f"Invalid value format: '{val}'.", f"This field requires a specific data type ({type_name}). Please verify the input formatting.")

            return ("The value format is incorrect.", "Check if you have used text where numbers are expected, or used invalid symbolic characters.")

        # --- 7. Length & Enumerations ---
        if "is not facet-valid" in msg or "facet 'enumeration'" in msg:
            if "length" in msg.lower():
                return ("Field length limit exceeded.", "The text provided is either too long or too short for this specific field. Please check the character count.")
            if "pattern" in msg.lower():
                # Attempt to extract field name from lxml prefix
                match = re.search(r"Element '([^']+)':", msg)
                name = match.group(1) if match else "Field content"
                return (f"The format for '{name}' is incorrect.", 
                        "The data provided does not match the required pattern (e.g., invalid characters, wrong starting letter, or incorrect ID format).")
            if "enumeration" in msg.lower():
                 # Match: Field 'ChrgBr': [facet 'enumeration'] The value 'JEEC' is not an element of the set ..
                 match_val = re.search(r"value '([^']+)'", msg)
                 val = match_val.group(1) if match_val else "provided"
                 
                 match_elem = re.search(r"Element '([^']+)'", msg)
                 elem = match_elem.group(1) if match_elem else "Field"
                 
                 return (f"Invalid value '{val}' for field '{elem}'.", 
                        f"The value '{val}' is not allowed for '{elem}'. Please use one of the standard ISO 20022 codes allowed for this field.")

        # --- 8. Attributes & Nesting ---
        if "attribute" in msg.lower():
            return ("Missing required detail (Attribute).", "A technical requirement inside the field (like a Currency Code 'Ccy') is missing. Please add it.")
        
        if "not allowed here" in msg:
            return ("Misplaced information.", "This field is not allowed in this specific section of the message. Remove it or move it to a valid parent element.")

        # Fallback for unhandled technical errors
        clean_msg = msg.replace("Element '", "Field '").replace("attribute '", "Detail '")
        # Strip regex patterns from output to keep it clean for end-users
        clean_msg = re.sub(r"The value '.*' is not accepted by the pattern '.*'\.", "The value format is invalid.", clean_msg)
        
        # Improve generic enumeration error if caught here
        if "is not an element of the set" in clean_msg:
             match_val = re.search(r"value '([^']+)'", clean_msg)
             val = match_val.group(1) if match_val else "provided"
             return (f"Invalid code '{val}'.", "This field only accepts specific strict codes (Enumeration). check the standard for allowed values.")

        return (clean_msg, "Please review this message block. Ensure standard character sets and ISO formats are followed.")

    def _get_xsd_path(self, message_type: str) -> Optional[str]:
        """
        Modified: Prioritizes family-based matching (pacs.008) over strict versions.
        """
        if not message_type or message_type == "Unknown":
            return None

        # 1. Extract Family (e.g., pacs.008 from pacs.008.001.08)
        parts = message_type.split(".")
        family = ".".join(parts[:2]) if len(parts) >= 2 else message_type
        
        # 2. Priority Search: Look for family.xsd directly (e.g., pacs.008.xsd)
        family_xsd = f"{family}.xsd"
        exact_xsd = f"{message_type}.xsd"
        
        # Check directly in the extracted folder first (User's preference)
        direct_path = os.path.join(self.xsd_path, family_xsd)
        if os.path.exists(direct_path):
            return direct_path
            
        exact_direct = os.path.join(self.xsd_path, exact_xsd)
        if os.path.exists(exact_direct):
            return exact_direct

        # 3. Fallback: Search recursively for ANY file starting with the family
        for root, dirs, files in os.walk(self.xsd_path):
            # Check for family.xsd if it exists deeper
            if family_xsd in files:
                return os.path.join(root, family_xsd)
            
            # Check for exact name if it exists deeper
            if exact_xsd in files:
                return os.path.join(root, exact_xsd)
                
            # Finally, pick the first file that feels like this family
            for f in files:
                if f.startswith(family) and f.endswith(".xsd"):
                    # Avoid picking unrelated variants if possible, but user said "only pacs.008"
                    return os.path.join(root, f)
        
        return None

    def _load_all_rules(self, message_type: str) -> List[Dict[str, Any]]:
        """
        Loads global rules + family rules + message-specific rules.
        """
        rules = []
        
        # 1. Load Global
        global_file = os.path.join(self.rules_path, "global.json")
        if os.path.exists(global_file):
            try:
                with open(global_file, "r") as f:
                    rules.extend(json.load(f))
            except: pass

        parts = message_type.split(".")
        
        # 2. Load Family Level (e.g., pacs.json)
        if len(parts) >= 1:
            family = parts[0]
            family_file = os.path.join(self.rules_path, f"{family}.json")
            if os.path.exists(family_file):
                try:
                    with open(family_file, "r") as f:
                        rules.extend(json.load(f))
                except: pass

        # 3. Load Message Specific (e.g., pacs.008.json)
        # Try pacs.008 first
        specific_name = ".".join(parts[:2]) if len(parts) >= 2 else message_type
        specific_file = os.path.join(self.rules_path, f"{specific_name}.json")
        
        # If not found, try full name just in case (e.g. pacs.008.001.08.json - rare but possible)
        if not os.path.exists(specific_file):
             specific_file = os.path.join(self.rules_path, f"{message_type}.json")

        if os.path.exists(specific_file):
            try:
                with open(specific_file, "r") as f:
                    rules.extend(json.load(f))
            except: pass
            
        return rules

    def _run_dynamic_layer(self, layer_id: int, rules: List[Dict[str, Any]], data: Dict[str, Any], line_map: Dict[str, int], report: ValidationReport):
        """
        Executes all rules assigned to a specific layer.
        """
        start = time.time()
        
        # Filter rules for the current layer (Rules are now strictly 1, 2, or 3)
        layer_rules = [r for r in rules if r.get("layer") == layer_id]
        
        # Load code lists for dynamic rules (Layer 3 always needs them for business/reference logic)
        codelists = {}
        if layer_id == 3:
            codelists = self._load_codelists()

        for rule in layer_rules:
            self._execute_rule_logic(rule, data, line_map, codelists, report)
        
        # Assessment for layer dashboard
        success = not any(i['layer'] == layer_id and i['severity'] == "ERROR" for i in report.issues)
        report.layer_status[str(layer_id)] = {
            "status": "✅" if success else "❌", 
            "time": round((time.time() - start) * 1000, 2)
        }

    def _execute_rule_logic(self, rule: Dict[str, Any], data: Dict[str, Any], line_map: Dict[str, int], codelists: Dict[str, list], report: ValidationReport):
        """
        Advanced Dynamic Rule Dispatcher.
        """
        # Defensive check: rule must be a dictionary
        if not isinstance(rule, dict):
             return

        rule_type = rule.get("type", "expression")
        selector = rule.get("selector")
        layer = rule.get("layer", 3)
        if layer in [4, 5]:
            layer = 3
        rule_id = rule.get("rule_id", "DYNAMIC_RULE")
        severity = rule.get("severity", "ERROR")
        desc = rule.get("description", "")

        def _get_line(key):
             # Try exact indexed match, then try parent path
             l = line_map.get(key) if isinstance(line_map, dict) else None
             if not l:
                  # Strip index for lookup [0]
                  clean = re.sub(r'\[\d+\]', '', key)
                  l = line_map.get(clean) if isinstance(line_map, dict) else None
             return str(l) if l else "/"

        # 1. Selector Based Rules (Multiple fields)
        if selector:
            regex = re.compile(selector)
            matching_keys = [k for k in data.keys() if regex.match(k)]
            
            for key in matching_keys:
                value = data[key]
                if rule_type == "codelist":
                    list_name = rule.get("list_name", "").lower()
                    if list_name in codelists:
                        cl_data = codelists[list_name]
                        # Handle both list formats: {"codes": [...]} and [...]
                        if isinstance(cl_data, dict):
                            valid_codes = cl_data.get("codes", [])
                        elif isinstance(cl_data, list):
                            valid_codes = cl_data
                        else:
                            valid_codes = []
                            
                        if value not in valid_codes:
                            report.add_issue(ValidationIssue(severity, layer, rule_id, _get_line(key), f"{desc} Value '{value}' not in list."))
                
                elif rule_type == "bic":
                    if not re.match(r'^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$', str(value)):
                        report.add_issue(ValidationIssue(severity, layer, rule_id, _get_line(key), f"{desc} Invalid BIC structure: '{value}'."))
                    elif self.supported_bics and value.upper() not in self.supported_bics:
                        report.add_issue(ValidationIssue("WARNING", layer, "BIC_NOT_FOUND", _get_line(key), f"BIC '{value}' not found in official directory.", "Verify if the BIC is correct or recently decommissioned."))
                
                elif rule_type == "currency_amount":
                    ccy_path = key + "@Ccy"
                    if not ccy_path in data:
                         ccy_path = key.rsplit('.', 1)[0] + ".Ccy"
                    
                    ccy = data.get(ccy_path)
                    allowed_decimals = None
                    
                    if ccy and "currency" in codelists:
                         curr_list = codelists["currency"]
                         if isinstance(curr_list, dict):
                             allowed_decimals = curr_list.get("currencies", {}).get(ccy)
                    
                    if allowed_decimals is not None:
                        val_str = str(value)
                        actual_decimals = len(val_str.split('.')[1]) if '.' in val_str else 0
                        if actual_decimals > allowed_decimals:
                             report.add_issue(ValidationIssue(severity, layer, "INVALID_DECIMAL_PRECISION", _get_line(key), f"Invalid decimal precision for {ccy}. Max {allowed_decimals}, found {actual_decimals}."))

                elif rule_type == "regex":
                    pattern = rule.get("pattern", ".*")
                    if not re.match(pattern, str(value)):
                        report.add_issue(ValidationIssue(severity, layer, rule_id, _get_line(key), f"{desc} Value '{value}' is invalid format."))
                
                elif rule_type == "expression":
                    rule_meta = {"severity": severity, "layer": layer, "rule_id": rule_id, "desc": desc}
                    if not self._evaluate_expression(rule.get("expression", "True"), data, line_map, value, key, rule_meta, codelists, report):
                        report.add_issue(ValidationIssue(severity, layer, rule_id, _get_line(key), desc))

        # 2. Logic Based Rules
        else:
            condition = rule.get("condition", "True")
            if not self._evaluate_expression(condition, data, line_map, codelists=codelists, report=report):
                return

            for field in rule.get("mandatory_fields", []):
                if not self._evaluate_expression(f"exists({field})", data, line_map, codelists=codelists, report=report):
                    report.add_issue(ValidationIssue(severity, layer, rule_id, _get_line(field), desc))

            expr = rule.get("expression")
            if expr:
                rule_meta = {"severity": severity, "layer": layer, "rule_id": rule_id, "desc": desc}
                if not self._evaluate_expression(expr, data, line_map, KEY="", rule_meta=rule_meta, codelists=codelists, report=report):
                     report.add_issue(ValidationIssue(severity, layer, rule_id, "/", desc))

    def _evaluate_expression(self, expr: str, data: Dict[str, Any], line_map: Dict[str, int] = None, VALUE: Any = None, KEY: str = "", rule_meta: Dict[str, Any] = None, codelists: Dict[str, Any] = None, report: ValidationReport = None) -> bool:
        """
        Evaluates dynamic expressions against the canonical data map.
        Supports indexed paths and global VALUE keyword.
        """
        # Ensure codelists is never None
        if codelists is None:
            codelists = {}
        def exists_sub(match):
            path = match.group(1).replace("[", "\\[").replace("]", "\\]")
            return "True" if any(re.match(f"^{path}(\\[\\d+\\])?(\\..*)?$", k) for k in data.keys()) else "False"

        def _gl(key):
             if not line_map: return "/"
             l = line_map.get(key)
             if not l:
                  clean = re.sub(r'\[\d+\]', '', key)
                  l = line_map.get(clean)
             return str(l) if l else "/"

        def check_address(addr_path, data, report, severity, layer, rule_id, desc):
            # ... (Existing address check logic is fine, keeping it concise for this tool call)
            block_content = {k: v for k, v in data.items() if k.startswith(f"{addr_path}.")}
            if not block_content: return True # Empty block is fine

            mandate_date_str = self.config.get("validation_rules", {}).get("cbpr_plus_mandate_date", "2026-11-01T00:00:00")
            try:
                mandate_date = datetime.fromisoformat(mandate_date_str)
            except:
                mandate_date = datetime(2026, 11, 1)
                
            is_after_2026 = datetime.now() > mandate_date
            has_town = any(k.startswith(f"{addr_path}.TownNm") for k in data.keys())
            has_ctry = any(k.startswith(f"{addr_path}.Ctry") for k in data.keys())
            
            issues_found = []
            if not has_town: issues_found.append(".TownNm")
            if not has_ctry: issues_found.append(".Ctry")

            if issues_found:
                for suffix in issues_found:
                    clean_field_path = (addr_path + suffix).split('.')[-4:]
                    field_path = ".".join(clean_field_path)

                    if is_after_2026:
                        report.add_issue(ValidationIssue(severity, layer, rule_id, field_path, f"{desc} (Mandate Active)", "Add this mandatory field to comply with CBPR+ requirements."))
                    else:
                        report.add_issue(ValidationIssue("WARNING", layer, rule_id, field_path, f"ADVISORY: {desc} (Future Mandate Nov 2026)", f"Add {suffix[1:]} now to ensure future compatibility."))
                
                if is_after_2026: return False
            return True
        def check_bic_match(header_role, doc_role):
            # 1. Find Header BIC
            h_key = f"AppHdr.{header_role}.FIId.FinInstnId.BICFI"
            h_val = data.get(h_key)
            
            # 2. Find Document BIC (Search anywhere in message)
            d_val = None
            d_key = None
            suffix = f".{doc_role}.FinInstnId.BICFI"
            
            for k, v in data.items():
                if k.endswith(suffix):
                    d_val = v
                    d_key = k
                    break
            
            # If either is missing, we can't compare
            if not h_val or not d_val:
                return True 
            
            if h_val != d_val:
                 # Add specific issue with correct line number
                 line = _gl(d_key) if d_key else _gl(h_key)
                 msg = f"{rule_meta.get('desc')} (Header: '{h_val}' vs Doc: '{d_val}')"
                 
                 report.add_issue(ValidationIssue(
                     rule_meta.get("severity", "ERROR"), 
                     rule_meta.get("layer", 3), 
                     rule_meta.get("rule_id", "MX_MATCH"), 
                     line, 
                     msg,
                     f"Update {doc_role} to match the Header BIC or vice versa."
                 ))
                 return True # Suppress generic error

            return True

        def check_purpose_limit(purp_key, val, data, report, rule_meta):
            """
            Consolidated Business Validation Decision Tree (Layer 3)
            Step 1: Purpose -> Step 2: Amount Values -> Step 3: Decimal -> Step 4: Limit -> Step 5: High Value
            """
            purpose = str(val).upper()
            
            # --- Step 1: Validate Purpose Code ---
            purpose_data = codelists.get("purpose_code", {})
            supported_purposes = purpose_data.get("codes", []) if isinstance(purpose_data, dict) else []
            
            if purpose not in supported_purposes:
                report.add_issue(ValidationIssue("ERROR", 3, "INVALID_PURPOSE_CODE", _gl(purp_key), 
                    f"Message contains purpose code '{purpose}' which is not in the supported list (SALA, RENT, SUPP).", 
                    "Ensure only approved business purpose codes (SALA/RENT/SUPP) are used."))
                return True # Suppress generic error by returning True after adding specific error
            # Discover Amount Key (climb up from Purp)
            amt_key = None
            current_path = purp_key
            while '.' in current_path:
                current_path = current_path.rsplit('.', 1)[0]
                # Try common amount tags at this level
                for tag in ["IntrBkSttlmAmt", "InstdAmt", "Amt.InstdAmt", "EqvtAmt"]:
                    candidate = f"{current_path}.{tag}"
                    if candidate in data:
                        amt_key = candidate
                        break
                if amt_key: break
            
            if not amt_key:
                return True

            amount_val = data.get(amt_key)
            if amount_val is None: return True
            
            try:
                amount = float(amount_val)
            except:
                return True
                
            ccy_key = f"{amt_key}@Ccy"
            currency = data.get(ccy_key)
            if not currency:
                return True

            # --- Step 2: Validate Amount > 0 ---
            if amount <= 0:
                report.add_issue(ValidationIssue("ERROR", 3, "INVALID_AMOUNT", _gl(amt_key), 
                    f"The payment amount {amount} must be greater than zero.", "Update to a positive value."))
                return True

            # --- Step 3: Validate Decimal Precision ---
            curr_data = codelists.get("currency", {})
            allowed_decimals = curr_data.get("currencies", {}).get(currency)
            if allowed_decimals is not None:
                raw_str = str(amount_val)
                actual_decimals = len(raw_str.split('.')[1]) if '.' in raw_str else 0
                if actual_decimals > allowed_decimals:
                    report.add_issue(ValidationIssue("ERROR", 3, "INVALID_DECIMAL_PRECISION", _gl(amt_key), 
                        f"Currency {currency} does not support {actual_decimals} decimals (Max: {allowed_decimals}). Found '{raw_str}'.", 
                        f"Adjust the value to match {currency} minor units."))
                    return True

            # --- Step 4: Validate Purpose + Currency Limit ---
            limits = self.config.get("validation_rules", {}).get("purpose_amount_limits", {})
            purpose_limits = limits.get(purpose, {})
            limit = purpose_limits.get(currency)
            
            if limit is not None and amount > limit:
                report.add_issue(ValidationIssue("ERROR", 3, "AMOUNT_EXCEEDS_PURPOSE_LIMIT", _gl(amt_key), 
                    f"The {purpose} payout of {amount:,.2f} {currency} exceeds the business cap of {limit:,.2f}.", 
                    "Ensure payment amount is within the approved purpose limits."))
                return True

            # --- Step 5: Validate High-Value Threshold ---
            hv_thresholds = self.config.get("validation_rules", {}).get("high_value_thresholds", {})
            hv_limit = hv_thresholds.get(currency)
            if hv_limit is not None and amount > hv_limit:
                 report.add_issue(ValidationIssue("WARNING", 3, "HIGH_VALUE_TRANSACTION", _gl(amt_key), 
                    f"Notice: This {currency} {amount:,.2f} payment is flagged as HIGH_VALUE_TRANSACTION.", 
                    "Risk monitoring is active for this high-value transfer."))

            return True

        try:
            temp_expr = re.sub(r'exists\(([^)]+)\)', exists_sub, expr)
            
            mandate_date_str = self.config.get("validation_rules", {}).get("cbpr_plus_mandate_date", "2026-11-01T00:00:00")
            try:
                mandate_date = datetime.fromisoformat(mandate_date_str)
            except:
                mandate_date = datetime(2026, 11, 1)

            ctx = {
                "float": float, "int": int, "str": str, "len": len, "datetime": datetime,
                "True": True, "False": False, "None": None,
                "VALUE": VALUE, "KEY": KEY, "DATA": data,
                "check_address": lambda p: check_address(p, data, report, 
                                                        rule_meta.get("severity", "ERROR"), 
                                                        rule_meta.get("layer", 3), 
                                                        rule_meta.get("rule_id", "E001"), 
                                                        rule_meta.get("desc", "")) if rule_meta else True,
                "check_bic_match": check_bic_match,
                "check_purpose_limit": lambda k, v: check_purpose_limit(k, v, data, report, rule_meta),
                "is_after_2026": datetime.now() > mandate_date,
                "exists": lambda x: any(k.startswith(x) for k in data.keys())
            }
            
            reserved = set(["VALUE", "KEY", "DATA", "True", "False", "None", "exists", "check_address", "check_bic_match", "datetime", "len", "float", "int", "str"])
            for key in sorted(data.keys(), key=len, reverse=True):
                pattern = r'\b' + re.escape(key) + r'\b'
                if re.search(pattern, temp_expr) and key not in reserved:
                    val = f"'{data[key]}'" if isinstance(data[key], str) else str(data[key])
                    temp_expr = re.sub(pattern, val, temp_expr)
            
            return eval(temp_expr, {"__builtins__": None}, ctx)
        except Exception as e:
            return False

    def _load_codelists(self) -> Dict[str, Any]:
        """Loads all JSON codelists from the resource directory fully"""
        lists = {}
        if not os.path.exists(self.codelists_path): return lists
        
        for filename in os.listdir(self.codelists_path):
            if filename.endswith(".json"):
                 try:
                    with open(os.path.join(self.codelists_path, filename), "r") as f:
                        lists[filename.replace(".json", "").lower()] = json.load(f)
                 except: pass
        return lists
