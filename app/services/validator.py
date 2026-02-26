import time
import uuid
import re
import os
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set
import zipfile
from lxml import etree

from .models import ValidationIssue, ValidationReport
from .layer1_validator import Layer1Mixin
from .layer2_validator import Layer2Mixin
from .layer3_validator import Layer3Mixin


class ISOValidator(Layer1Mixin, Layer2Mixin, Layer3Mixin):

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
        """Loads all JSON codelists from the resource directory (Lowercased keys)"""
        lists = {}
        if not os.path.exists(self.codelists_path):
            return lists
        
        for filename in os.listdir(self.codelists_path):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(self.codelists_path, filename), 'r') as f:
                        lists[filename.replace(".json", "").lower()] = json.load(f)
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
                # Note: skip non-element nodes (Comments, PIs) whose .tag is a function
                element_children = [c for c in element if isinstance(c.tag, str)]
                tag_counts = {}
                for child in element_children:
                    tag = get_clean_tag(child.tag)
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
                
                current_counts = {}
                for child in element_children:
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

    def _get_xsd_path(self, message_type: str) -> Optional[str]:
        """
        Locates the XSD file for the given message type.
        1. Exact Match (e.g. pacs.008.001.08.xsd)
        2. Family Fallback (e.g. pacs.008.xsd)
        3. Version Fallback (Look for highest available version e.g. .13)
        """
        if not message_type or message_type == "Unknown":
            return None

        # 1. Exact Match
        exact_xsd = f"{message_type}.xsd"
        exact_path = os.path.join(self.xsd_path, exact_xsd)
        if os.path.exists(exact_path):
            return exact_path

        # 2. Family Match (User's specific preference for short names)
        parts = message_type.split('.')
        family_prefix = ".".join(parts[:3]) if len(parts) >= 3 else message_type
        family_short = parts[0] + "." + parts[1] if len(parts) >= 2 else message_type
        
        family_xsd = f"{family_short}.xsd"
        family_path = os.path.join(self.xsd_path, family_xsd)
        if os.path.exists(family_path):
            return family_path

        # 3. Version-Blind Fallback (Highest available version in family)
        try:
            candidates = []
            for f in os.listdir(self.xsd_path):
                if f.startswith(family_prefix) and f.endswith(".xsd"):
                    candidates.append(f)
            
            if candidates:
                best_match = sorted(candidates, reverse=True)[0]
                fallback_path = os.path.join(self.xsd_path, best_match)
                print(f"XSD: Exact version '{message_type}' not found. Falling back to '{best_match}'.")
                return fallback_path
        except:
            pass

        return None

