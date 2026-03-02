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
from .layer3_timing import validateLayer3Timing


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
        
        self.cutoff_config_path = os.path.join(backend_root, "app", "resources", "cutoff_timings.json")
        self.cutoff_config = {}
        if os.path.exists(self.cutoff_config_path):
            try:
                with open(self.cutoff_config_path, 'r') as f:
                    self.cutoff_config = json.load(f)
            except Exception as e:
                print(f"Error loading cutoff config: {e}")
        
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

            # STEP 4.5: DATE VALIDATION — runs on raw XML before Layer 2
            # so past-date errors are ALWAYS reported even when XSD also fails.
            self._validate_dates_in_xml(xml_content, report, start_time)

            # STEP 4.6: ID FIELD MAX-LENGTH VALIDATION — runs on raw XML before Layer 2
            self._validate_id_lengths_in_xml(xml_content, report)

            # STEP 4.7: UETR UUID v4 FORMAT VALIDATION — runs on raw XML before Layer 2
            self._validate_uetr_in_xml(xml_content, report)

            # STEP 4.8: IBAN / BBAN ACCOUNT IDENTIFIER VALIDATION
            self._validate_account_identifiers_in_xml(xml_content, report)

            if mode != "Layer 1 only":
                try:
                    layer2_success = await self._run_layer_2(xml_content, report, detected_type)
                    if not layer2_success:
                         # ⛔ Rejection: If XSD fails, stop here after collecting all errors.
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

            # (Date validation already ran in Step 4.5 above, before Layer 2)


            # STEP 5.1: FAIL-FAST SANCTIONS SCREENING (Dynamic)
            sanctions_config = self.config.get("sanctions", {})
            sanctioned_codes = set(sanctions_config.get("codes", []))
            sanctioned_names = set(sanctions_config.get("names", []))
            
            # Use defaults if config is empty for fallback safety
            if not sanctioned_codes: sanctioned_codes = {'AF', 'RU', 'KP'}
            if not sanctioned_names: sanctioned_names = {'russia', 'iran', 'north korea'}
            
            for path, value in canonical_data.items():
                # Check fields associated with parties (Debtor, Creditor, Agents)
                if any(x in path for x in ['Dbtr', 'Cdtr', 'InstgAgt', 'InstdAgt', 'InitgPty', 'Pty']):
                    str_val = str(value).strip().lower()
                    # Check ISO code (in Ctry tags)
                    if 'Ctry' in path and value in sanctioned_codes:
                        report.add_issue(ValidationIssue("ERROR", 3, "SANCTIONS_BLOCKED", path, f"Fail-fast: Party from sanctioned country code '{value}' detected.", "Transaction rejected due to sanctions compliance."))
                        break
                    # Check names in address/name fields
                    if any(name in str_val for name in sanctioned_names):
                        # Simple keyword hit
                        hit = next(name for name in sanctioned_names if name in str_val)
                        report.add_issue(ValidationIssue("ERROR", 3, "SANCTIONS_BLOCKED", path, f"Fail-fast: Party from sanctioned country '{hit.title()}' detected.", "Transaction rejected due to sanctions compliance."))
                        break
            
            if any(i['code'] == 'SANCTIONS_BLOCKED' for i in report.issues):
                 # Fail fast, skip further L3 rules
                 report.layer_status['3'] = {"status": "❌", "time": round((time.time() - start_time) * 1000, 2)}
                 return self._finalize_report(report, start_time)

            # STEP 6-9: Dynamic Rule Engine (Layers 1-3)
            # Load all rules once
            try:
                all_rules = self._load_all_rules(detected_type)
                
                if mode == "Full 1-3":
                    for layer_id in [3]:
                        self._run_dynamic_layer(layer_id, all_rules, canonical_data, line_map, report)
                        
                        # --- Apply Layer 3 Timing Validation ---
                        try:
                            if self.cutoff_config:
                                # Dynamic Defaults
                                t_conf = self.config.get("timing_defaults", {})
                                debtor_country = t_conf.get("debtor_country", "US")
                                creditor_country = t_conf.get("creditor_country", "GB")
                                debtor_sys = t_conf.get("debtor_system", "FEDWIRE")
                                creditor_sys = t_conf.get("creditor_system", "CHAPS")
                                
                                for k, v in canonical_data.items():
                                    if k.endswith('.Dbtr.PstlAdr.Ctry') or k.endswith('.InitgPty.PstlAdr.Ctry'):
                                        debtor_country = v
                                    if k.endswith('.Cdtr.PstlAdr.Ctry'):
                                        creditor_country = v
                                        
                                d_sys_conf = self.cutoff_config.get("timings", {}).get(debtor_country, {}).get("paymentSystems", {})
                                if d_sys_conf: debtor_sys = list(d_sys_conf.keys())[0]
                                c_sys_conf = self.cutoff_config.get("timings", {}).get(creditor_country, {}).get("paymentSystems", {})
                                if c_sys_conf: creditor_sys = list(c_sys_conf.keys())[0]

                                ctx = {
                                    "debtorCountry": debtor_country,
                                    "debtorPaymentSystem": debtor_sys,
                                    "creditorCountry": creditor_country,
                                    "creditorPaymentSystem": creditor_sys,
                                    "submissionTimestamp": datetime.now(timezone.utc).isoformat(),
                                    "validationMode": "STRICT"
                                }
                                
                                # Extract specific timing fields into payload
                                t_payload = {}
                                t_paths = {} # FieldName in payload -> Canonical Path in message
                                for k, v in canonical_data.items():
                                    # Fallback country detection from BIC
                                    if k.endswith('.BICFI') or k == 'BICFI':
                                        bic_val = str(v).strip().upper()
                                        if len(bic_val) >= 6:
                                            extracted_ctry = bic_val[4:6]
                                            if 'Dbtr' in k or 'InstgAgt' in k:
                                                ctx["debtorCountry"] = extracted_ctry
                                            if 'Cdtr' in k or 'InstdAgt' in k:
                                                ctx["creditorCountry"] = extracted_ctry

                                    if k.endswith('.CreDtTm') or k.endswith('.CreDt') or k in ['CreDtTm', 'CreDt']:
                                        t_payload['CreDtTm'] = v
                                        t_paths['CreDtTm'] = k
                                    elif k.endswith('.ReqdExctnDt') or k == 'ReqdExctnDt':
                                        t_payload['ReqdExctnDt'] = v
                                        t_paths['ReqdExctnDt'] = k
                                    elif k.endswith('.IntrBkSttlmDt') or k == 'IntrBkSttlmDt':
                                        t_payload['IntrBkSttlmDt'] = v
                                        t_paths['IntrBkSttlmDt'] = k
                                    elif 'MsgDefIdr' in k:
                                        t_payload['MsgDefIdr'] = v
                                        
                                timing_result = validateLayer3Timing(t_payload, ctx, self.cutoff_config)
                                for iss_dict in timing_result.get("issues", []):
                                    field_key = iss_dict.get("field", "CreDtTm") # Default to creation time if missing
                                    matched_path = t_paths.get(field_key, "/")
                                             
                                    # Fallback search if path is still /
                                    if matched_path == "/":
                                        for k in canonical_data.keys():
                                            if k.endswith(f".{field_key}") or k == field_key:
                                                matched_path = k
                                                break
                                                
                                    line = str(line_map.get(matched_path, "/"))
                                    severity = "ERROR" if iss_dict["severity"] == "FAIL" else iss_dict["severity"]
                                    
                                    details_str = ""
                                    if "computed" in iss_dict.get("details", {}):
                                         details_str = f"Recommended Value Date: {iss_dict['details']['computed'].get('recommendedValueDate', '')}"
                                    
                                    full_msg = f"{iss_dict['message']} {details_str}".strip()
                                    report.add_issue(ValidationIssue(severity, 3, iss_dict["ruleId"], line, full_msg, details_str))
                                    
                                if timing_result.get("status") == "FAIL":
                                    report.layer_status['3'] = {"status": "❌", "time": round((time.time() - start_time) * 1000, 2)}
                        except Exception as e:
                            print(f"DEBUG Timing Validation Error: {e}")

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

    def _validate_dates_in_xml(self, xml_content: str, report: ValidationReport, start_time: float) -> None:
        """
        Step 4.5 — Past Date Validation
        Scans the raw XML string directly for ALL date and datetime values.
        This runs BEFORE Layer 2 so past-date errors are always reported,
        even when the XSD also finds other errors (e.g. invalid amount/IBAN).

        Supported formats:
          2026-03-02                       (XML date)
          2026-03-02T10:35:00              (XML dateTime, no tz)
          2026-03-02T10:35:00Z             (XML dateTime, UTC)
          2026-03-02T10:35:00+05:30        (XML dateTime, offset)
          2026-03-02T10:35:00.123+00:00    (XML dateTime, ms + offset)
        """
        today_date = datetime.now().date()

        # Matches tag + value pairs: <TagName>2026-02-01T10:35:00+00:00</TagName>
        # Captures: (1) tag name  (2) date/datetime value  (3) optional time+tz part
        xml_date_patt = re.compile(
            r'<([A-Za-z][A-Za-z0-9]*)>'           # opening tag
            r'\s*'
            r'(\d{4}-\d{2}-\d{2}'                  # date part  (group 2)
            r'(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)?)'  # optional time+tz
            r'\s*'
            r'</\1>'                               # matching closing tag
        )

        seen = set()  # avoid duplicate errors for the same tag+value
        for m in xml_date_patt.finditer(xml_content):
            tag_name  = m.group(1)
            raw_value = m.group(2).strip()
            key = (tag_name, raw_value)
            if key in seen:
                continue
            seen.add(key)

            try:
                date_part  = raw_value[:10]          # always YYYY-MM-DD
                parsed_date = datetime.strptime(date_part, "%Y-%m-%d").date()
            except ValueError:
                continue  # not a real calendar date

            if parsed_date < today_date:
                # Find the line number in the raw XML
                try:
                    line_num = xml_content.count('\n', 0, m.start()) + 1
                except Exception:
                    line_num = "Unknown"

                report.add_issue(ValidationIssue(
                    "ERROR",
                    3,
                    "PAST_DATE_ERROR",
                    str(line_num),
                    f"Date cannot be in the past. "
                    f"Field <{tag_name}> contains '{raw_value}', "
                    f"which is before today ({today_date}).",
                    f"Update <{tag_name}> to today ({today_date}) or a future date. "
                    f"(Line: {line_num})"
                ))

    def _validate_id_lengths_in_xml(self, xml_content: str, report: ValidationReport) -> None:
        """
        Step 4.6 — ID Field Maximum Length Validation
        Scans the raw XML string for known identifier fields and checks that
        their values do not exceed their ISO 20022-defined maximum lengths.

        This runs BEFORE Layer 2 so violations are always reported alongside
        any XSD errors (e.g. invalid amounts, IBANs, UETRs).

        Field limits enforced:
          InstrId      → max 35 chars
          EndToEndId   → max 35 chars
          BizMsgIdr    → max 35 chars
          MsgId        → max 35 chars
          TxId         → max 35 chars
          UETR         → max 36 chars
        """
        # UETR is handled by the dedicated _validate_uetr_in_xml validator (Step 4.7)
        # which checks UUID v4 format fully, so it is excluded here to avoid
        # double-reporting.
        ID_MAX_LENGTHS = {
            "InstrId":    35,
            "EndToEndId": 35,
            "BizMsgIdr":  35,
            "MsgId":      35,
            "TxId":       35,
        }

        # Build one combined pattern that matches any of the tracked tags
        tag_alternation = "|".join(re.escape(t) for t in ID_MAX_LENGTHS)
        id_patt = re.compile(
            r'<(' + tag_alternation + r')>'   # opening tag  (group 1)
            r'\s*([^<]+?)\s*'                  # value        (group 2)
            r'</\1>'                           # matching closing tag
        )

        for m in id_patt.finditer(xml_content):
            tag_name   = m.group(1)
            raw_value  = m.group(2).strip()
            max_len    = ID_MAX_LENGTHS[tag_name]
            actual_len = len(raw_value)

            if actual_len > max_len:
                try:
                    line_num = xml_content.count('\n', 0, m.start()) + 1
                except Exception:
                    line_num = "Unknown"

                report.add_issue(ValidationIssue(
                    "ERROR",
                    3,
                    "ID_LENGTH_ERROR",
                    str(line_num),
                    f"Invalid length in element <{tag_name}> at line {line_num}: "
                    f"Length {actual_len} exceeds maximum allowed {max_len}.",
                    f"Shorten the value of <{tag_name}> to at most {max_len} characters. "
                    f"Current value has {actual_len} characters."
                ))

    def _validate_uetr_in_xml(self, xml_content: str, report: ValidationReport) -> None:
        """
        Step 4.7 — UETR UUID v4 Format Validation
        Finds every <UETR> element in the raw XML and validates it against
        the full UUID v4 specification:

          Format : 8-4-4-4-12  (total 36 chars including hyphens)
          Chars  : lowercase hexadecimal (0-9, a-f) and hyphens only
          Version: third group must start with '4'  (UUID version 4)
          Variant: fourth group must start with 8, 9, a, or b

        Example valid UETR: 550e8400-e29b-41d4-a716-446655440000

        This runs BEFORE Layer 2 so UETR errors are always reported even
        when other XSD errors are present.
        """
        # Strict UUID v4 pattern: lowercase only, version=4, variant=[89ab]
        UUID_V4 = re.compile(
            r'^[0-9a-f]{8}-'      # 8 hex
            r'[0-9a-f]{4}-'       # 4 hex
            r'4[0-9a-f]{3}-'      # version 4 + 3 hex
            r'[89ab][0-9a-f]{3}-' # variant + 3 hex
            r'[0-9a-f]{12}$'      # 12 hex
        )

        # Match all <UETR>...</UETR> elements
        uetr_patt = re.compile(
            r'<(UETR)>'           # opening tag (group 1)
            r'\s*([^<]+?)\s*'     # value        (group 2)
            r'</\1>'              # matching closing tag
        )

        for m in uetr_patt.finditer(xml_content):
            tag_name  = m.group(1)
            raw_value = m.group(2).strip()

            if not UUID_V4.match(raw_value):
                try:
                    line_num = xml_content.count('\n', 0, m.start()) + 1
                except Exception:
                    line_num = "Unknown"

                # Give a specific hint about what exactly is wrong
                if len(raw_value) != 36:
                    hint = f"Value has {len(raw_value)} characters; must be exactly 36."
                elif raw_value != raw_value.lower():
                    hint = "Value must use only lowercase characters."
                elif not re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
                                  raw_value.lower()):
                    hint = "Value does not follow 8-4-4-4-12 hex grouping with hyphens."
                elif raw_value[14] != '4':
                    hint = f"Third group must start with '4' (UUID v4). Found '{raw_value[14]}'."
                else:
                    hint = (f"Fourth group must start with 8, 9, a, or b (UUID v4 variant). "
                            f"Found '{raw_value[19]}'.")

                report.add_issue(ValidationIssue(
                    "ERROR",
                    3,
                    "UETR_FORMAT_ERROR",
                    str(line_num),
                    f"Invalid UETR in element <{tag_name}> at line {line_num}: "
                    f"Must be a valid UUID v4 (36-character format). "
                    f"Value: '{raw_value}'.",
                    f"{hint} "
                    f"Example of a valid UETR: 550e8400-e29b-41d4-a716-446655440000"
                ))

    def _validate_account_identifiers_in_xml(self, xml_content: str, report: ValidationReport) -> None:
        """
        Step 4.8 — IBAN / BBAN Account Identifier Validation

        For every account container element (DbtrAcct, CdtrAcct, etc.) found in
        the XML, validates the <Id> child against ISO 20022 account rules:

          1. IBAN validation  — format, country length, MOD-97 check digit, overall length (15-34)
          2. BBAN validation  — length, alphanumeric, country-specific structure (FR, ES)
          3. Mutual exclusivity — exactly one of <IBAN> or <Othr> must be present
          4. SEPA rule        — BBAN not permitted when SvcLvl/Cd = SEPA
          5. Amount validation - checks for strictly positive amounts
        """
        # ── Country-specific IBAN lengths (SWIFT IBAN Registry, Edition 2024) ─
        # ⚠️  IMPORTANT: Countries like US, CA, AU, IN, CN, JP do NOT use IBAN.
        #     The US banking system uses ABA routing numbers + account numbers.
        #     An IBAN starting with 'US' is ALWAYS INVALID — the US is not a
        #     participant in the IBAN scheme (ISO 13616 / SWIFT Registry).
        IBAN_LENGTHS = {
            # A
            'AD':24,  # Andorra
            'AE':23,  # United Arab Emirates
            'AL':28,  # Albania
            'AT':20,  # Austria
            'AZ':28,  # Azerbaijan
            # B
            'BA':20,  # Bosnia and Herzegovina
            'BE':16,  # Belgium
            'BF':28,  # Burkina Faso
            'BG':22,  # Bulgaria
            'BH':22,  # Bahrain
            'BI':27,  # Burundi
            'BJ':28,  # Benin
            'BR':29,  # Brazil
            'BY':28,  # Belarus
            # C
            'CF':27,  # Central African Republic
            'CG':27,  # Congo
            'CH':21,  # Switzerland
            'CI':28,  # Ivory Coast (Côte d'Ivoire)
            'CM':27,  # Cameroon
            'CR':22,  # Costa Rica
            'CV':25,  # Cape Verde
            'CY':28,  # Cyprus
            'CZ':24,  # Czech Republic
            # D
            'DE':22,  # Germany
            'DJ':27,  # Djibouti
            'DK':18,  # Denmark
            'DO':28,  # Dominican Republic
            'DZ':26,  # Algeria
            # E
            'EE':20,  # Estonia
            'EG':29,  # Egypt
            'ES':24,  # Spain
            # F
            'FI':18,  # Finland
            'FK':18,  # Falkland Islands
            'FO':18,  # Faroe Islands
            'FR':27,  # France
            # G
            'GA':27,  # Gabon
            'GB':22,  # United Kingdom
            'GE':22,  # Georgia
            'GI':23,  # Gibraltar
            'GL':18,  # Greenland
            'GN':26,  # Guinea
            'GQ':27,  # Equatorial Guinea
            'GR':27,  # Greece
            'GT':28,  # Guatemala
            'GW':25,  # Guinea-Bissau
            # H
            'HN':28,  # Honduras
            'HR':21,  # Croatia
            'HU':28,  # Hungary
            # I
            'IE':22,  # Ireland
            'IL':23,  # Israel
            'IQ':23,  # Iraq
            'IR':26,  # Iran
            'IS':26,  # Iceland
            'IT':27,  # Italy
            # J
            'JO':30,  # Jordan
            # K
            'KM':27,  # Comoros
            'KW':30,  # Kuwait
            'KZ':20,  # Kazakhstan
            # L
            'LB':28,  # Lebanon
            'LC':32,  # Saint Lucia
            'LI':21,  # Liechtenstein
            'LT':20,  # Lithuania
            'LU':20,  # Luxembourg
            'LV':21,  # Latvia
            'LY':25,  # Libya
            # M
            'MA':28,  # Morocco
            'MC':27,  # Monaco
            'MD':24,  # Moldova
            'ME':22,  # Montenegro
            'MG':27,  # Madagascar
            'MK':19,  # North Macedonia
            'ML':28,  # Mali
            'MN':20,  # Mongolia
            'MR':27,  # Mauritania
            'MT':31,  # Malta
            'MU':30,  # Mauritius
            'MZ':25,  # Mozambique
            # N
            'NE':28,  # Niger
            'NI':32,  # Nicaragua
            'NL':18,  # Netherlands
            'NO':15,  # Norway
            'NZ':16,  # New Zealand
            # O
            'OM':23,  # Oman
            # P
            'PK':24,  # Pakistan
            'PL':28,  # Poland
            'PS':29,  # Palestinian Territory
            'PT':25,  # Portugal
            # Q
            'QA':29,  # Qatar
            # R
            'RO':24,  # Romania
            'RS':22,  # Serbia
            'RU':33,  # Russia
            # S
            'SA':24,  # Saudi Arabia
            'SC':31,  # Seychelles
            'SD':18,  # Sudan
            'SE':24,  # Sweden
            'SI':19,  # Slovenia
            'SK':24,  # Slovakia
            'SM':27,  # San Marino
            'SN':28,  # Senegal
            'SO':23,  # Somalia
            'ST':25,  # Sao Tome and Principe
            'SV':28,  # El Salvador
            # T
            'TD':27,  # Chad
            'TG':28,  # Togo
            'TL':23,  # Timor-Leste
            'TN':24,  # Tunisia
            'TR':26,  # Turkey
            # U
            'UA':29,  # Ukraine
            # V
            'VA':22,  # Vatican City
            'VG':24,  # British Virgin Islands
            # X
            'XK':20,  # Kosovo
            # Y
            'YE':30,  # Yemen
        }
        IBAN_PATTERN = re.compile(r'^[A-Z]{2}[0-9]{2}[A-Z0-9]{1,30}$')

        # Account container tags to scan
        ACCOUNT_TAGS = [
            'DbtrAcct','CdtrAcct','IntrmyAgtAcct','InstgAgtAcct','InstdAgtAcct',
            'CdtrAgtAcct','DbtrAgtAcct','SttlmAcct','RcvgAgtAcct','DlvrgAgtAcct',
        ]

        # Amount tags to scan for positive value (simple local tag names only)
        AMOUNT_TAGS = {
            'InstdAmt', 'IntrBkSttlmAmt', 'ChrgAmt', 'Amt', 'EqvtAmt', 'TtlIntrBkSttlmAmt',
        }

        # ── Country-specific BBAN structures (SWIFT IBAN Registry / ISO 13616) ─
        # Each entry: (total_bban_length, [(segment_length, type), ...])
        # type: 'n'=numeric only, 'a'=alphabetic only, 'c'=alphanumeric
        BBAN_STRUCTURES = {
            'AL': (28, [(8,'n'),(16,'c')]),
            'AD': (20, [(4,'n'),(4,'n'),(12,'c')]),
            'AT': (16, [(5,'n'),(11,'n')]),
            'AZ': (24, [(4,'a'),(20,'c')]),
            'BH': (18, [(4,'a'),(14,'c')]),
            'BE': (12, [(3,'n'),(7,'n'),(2,'n')]),
            'BA': (16, [(3,'n'),(3,'n'),(8,'n'),(2,'n')]),
            'BR': (25, [(8,'n'),(5,'n'),(10,'n'),(1,'a'),(1,'c')]),
            'BG': (18, [(4,'a'),(4,'n'),(2,'n'),(8,'c')]),
            'CR': (18, [(4,'n'),(14,'n')]),
            'HR': (17, [(7,'n'),(10,'n')]),
            'CY': (24, [(3,'n'),(5,'n'),(16,'c')]),
            'CZ': (20, [(4,'n'),(6,'n'),(10,'n')]),
            'DK': (14, [(4,'n'),(9,'n'),(1,'n')]),
            'DO': (24, [(4,'a'),(20,'n')]),
            'EE': (16, [(2,'n'),(2,'n'),(11,'n'),(1,'n')]),
            'FI': (14, [(6,'n'),(7,'n'),(1,'n')]),
            'FO': (14, [(4,'n'),(9,'n'),(1,'n')]),
            'FR': (23, [(5,'n'),(5,'n'),(11,'c'),(2,'n')]),   # bank+branch+acct+rib_key
            'GE': (18, [(2,'a'),(16,'n')]),
            'DE': (18, [(8,'n'),(10,'n')]),
            'GI': (19, [(4,'a'),(15,'c')]),
            'GL': (14, [(4,'n'),(9,'n'),(1,'n')]),
            'GR': (23, [(3,'n'),(4,'n'),(16,'c')]),
            'GT': (24, [(4,'c'),(20,'c')]),
            'HU': (24, [(3,'n'),(4,'n'),(1,'n'),(15,'n'),(1,'n')]),
            'IS': (22, [(4,'n'),(2,'n'),(6,'n'),(10,'n')]),
            'IE': (18, [(4,'a'),(6,'n'),(8,'n')]),
            'IL': (19, [(3,'n'),(3,'n'),(13,'n')]),
            'IT': (23, [(1,'a'),(5,'n'),(5,'n'),(12,'c')]),
            'JO': (26, [(4,'a'),(4,'n'),(18,'c')]),
            'KZ': (16, [(3,'n'),(13,'c')]),
            'KW': (26, [(4,'a'),(22,'c')]),
            'LV': (17, [(4,'a'),(13,'c')]),
            'LB': (24, [(4,'n'),(20,'c')]),
            'LI': (17, [(5,'n'),(12,'c')]),
            'LT': (16, [(5,'n'),(11,'n')]),
            'LU': (16, [(3,'n'),(13,'c')]),
            'MK': (15, [(3,'n'),(10,'c'),(2,'n')]),
            'MT': (27, [(4,'a'),(5,'n'),(18,'c')]),
            'MR': (23, [(5,'n'),(5,'n'),(11,'n'),(2,'n')]),
            'MU': (26, [(4,'a'),(2,'n'),(2,'n'),(12,'n'),(3,'n'),(3,'a')]),
            'MD': (20, [(2,'c'),(18,'n')]),
            'MC': (23, [(5,'n'),(5,'n'),(11,'c'),(2,'n')]),   # same as FR
            'ME': (18, [(3,'n'),(13,'n'),(2,'n')]),
            'NL': (14, [(4,'a'),(10,'n')]),
            'NO': (11, [(4,'n'),(6,'n'),(1,'n')]),
            'PK': (20, [(4,'a'),(16,'n')]),
            'PS': (25, [(4,'a'),(21,'n')]),
            'PL': (24, [(8,'n'),(16,'n')]),
            'PT': (21, [(4,'n'),(4,'n'),(11,'n'),(2,'n')]),
            'QA': (25, [(4,'a'),(21,'c')]),
            'RO': (20, [(4,'a'),(16,'c')]),
            'SM': (23, [(1,'a'),(5,'n'),(5,'n'),(12,'c')]),
            'SA': (20, [(2,'n'),(18,'c')]),
            'RS': (18, [(3,'n'),(13,'n'),(2,'n')]),
            'SK': (20, [(4,'n'),(6,'n'),(10,'n')]),
            'SI': (15, [(5,'n'),(8,'n'),(2,'n')]),
            'ES': (20, [(4,'n'),(4,'n'),(2,'n'),(10,'n')]),   # bank+branch+ctrl+acct
            'SE': (20, [(3,'n'),(16,'n'),(1,'n')]),
            'CH': (17, [(5,'n'),(12,'c')]),
            'TN': (20, [(2,'n'),(3,'n'),(13,'n'),(2,'n')]),
            'TR': (22, [(5,'n'),(1,'n'),(16,'c')]),
            'AE': (19, [(3,'n'),(16,'n')]),
            'GB': (18, [(4,'a'),(6,'n'),(8,'n')]),
            'VG': (20, [(4,'a'),(16,'n')]),
        }

        # ── Helper: MOD 97-10 check digit verification ───────────────────────
        def _iban_mod97(iban: str) -> bool:
            rearranged = iban[4:] + iban[:4]
            numeric = ''.join(
                str(ord(c) - 55) if c.isalpha() else c
                for c in rearranged
            )
            try:
                return int(numeric) % 97 == 1
            except ValueError:
                return False

        # ── Helper: French / Monaco RIB key check ───────────────────────────
        def _fr_rib_check(bban: str) -> bool:
            """
            French BBAN = 5n(bank) + 5n(branch) + 11c(account) + 2n(rib_key)
            Standard letter → digit substitution table used by French banks.
            Expectation: 97 - ((89*bank + 15*branch + 3*acct_numeric) % 97) == rib_key
            Edge case: result of 97 maps to 0.
            """
            if len(bban) != 23:
                return True  # length already checked in segment validator
            try:
                # Letter substitution: A-Z → values per French RIB spec
                _LETTER_MAP = {
                    'A':1,'B':2,'C':3,'D':4,'E':5,'F':6,'G':7,'H':8,'I':9,
                    'J':1,'K':2,'L':3,'M':4,'N':5,'O':6,'P':7,'Q':8,'R':9,
                    'S':2,'T':3,'U':4,'V':5,'W':6,'X':7,'Y':8,'Z':9,
                }
                def to_num(s: str) -> str:
                    return ''.join(str(_LETTER_MAP[c]) if c.isalpha() else c for c in s.upper())

                bank_n   = int(to_num(bban[0:5]))
                branch_n = int(to_num(bban[5:10]))
                acct_n   = int(to_num(bban[10:21]))
                rib_key  = int(bban[21:23])

                expected = (97 - ((89 * bank_n + 15 * branch_n + 3 * acct_n) % 97)) % 97
                return expected == rib_key
            except Exception:
                return True  # don't falsely reject on unexpected parsing errors

        # ── Helper: Spanish CCC control digit check ──────────────────────────
        def _es_check_digit(bban: str) -> bool:
            """
            Spanish CCC: 4n(bank)+4n(branch)+2n(ctrl)+10n(account) = 20 chars
            ctrl[0] = check digit for bank+branch (left-padded to 10 with leading '00')
            ctrl[1] = check digit for account (10 digits)
            Algorithm: weighted sum mod 11, weights = [1,2,4,8,5,10,9,7,3,6]
            """
            if len(bban) != 20:
                return True  # length already checked in segment validator
            try:
                if not bban.isdigit():
                    return True  # character type already checked
                weights = [1, 2, 4, 8, 5, 10, 9, 7, 3, 6]

                def _cd(ten_digits: str) -> int:
                    total = sum(int(d) * w for d, w in zip(ten_digits, weights))
                    rem = total % 11
                    result = 11 - rem
                    return 0 if result == 11 else (1 if result == 10 else result)

                # Bank+branch padded to 10 chars with leading '00'
                bank_branch_10 = '00' + bban[0:4] + bban[4:8]
                ctrl           = bban[8:10]
                account_10     = bban[10:20]

                exp0 = _cd(bank_branch_10)
                exp1 = _cd(account_10)
                return ctrl == f"{exp0}{exp1}"
            except Exception:
                return True

        # ── Helper: validate a single IBAN value ─────────────────────────────
        def _validate_iban(value: str, container: str, line_num) -> list:
            errors = []
            # Strip surrounding whitespace, then remove embedded spaces (per spec: trim spaces)
            trimmed = value.strip()
            v_no_spaces = trimmed.replace(' ', '')

            # 0. Overall length check (ISO 13616 specifies 15-34 characters)
            # Use the space-stripped value for length counting
            if not (15 <= len(v_no_spaces) <= 34):
                errors.append((
                    f"Invalid account identifier in element <{container}> at line {line_num}: "
                    f"Failed IBAN/BBAN validation. "
                    f"IBAN '{value}' has length {len(v_no_spaces)} (after removing spaces), "
                    f"which is outside the valid range of 15–34 characters.",
                    f"An IBAN must be between 15 and 34 characters long (excluding spaces). "
                    f"Check for missing or extra characters."
                ))
                return errors  # Further checks are meaningless

            # 1. Uppercase + no special characters check
            # The spec requires: uppercase A-Z and digits 0-9 only (no lowercase, no specials).
            # We check on the space-stripped raw value (NOT yet uppercased) so that lowercase
            # letters are correctly rejected rather than silently accepted.
            if not IBAN_PATTERN.match(v_no_spaces):
                # Give a more specific hint for the most common violation: lowercase
                if v_no_spaces != v_no_spaces.upper():
                    hint = (
                        f"IBAN must use only UPPERCASE letters (A–Z) and digits (0–9). "
                        f"Lowercase letters are not permitted. "
                        f"Found: '{v_no_spaces}'."
                    )
                else:
                    hint = (
                        f"Correct the IBAN format. Expected: 2-letter country code, "
                        f"2 check digits, then up to 30 uppercase alphanumeric characters."
                    )
                errors.append((
                    f"Invalid account identifier in element <{container}> at line {line_num}: "
                    f"Failed IBAN/BBAN validation. "
                    f"IBAN '{value}' does not match the required pattern "
                    f"^[A-Z]{{2}}[0-9]{{2}}[A-Z0-9]{{1,30}}$ (uppercase alphanumeric only, "
                    f"no spaces or special characters).",
                    hint
                ))
                return errors  # Further checks are meaningless

            # From here on use the normalised (uppercased, space-free) value
            v = v_no_spaces.upper()

            # 2. Country code known in IBAN registry
            country = v[:2]
            if country not in IBAN_LENGTHS:
                errors.append((
                    f"Invalid account identifier in element <{container}> at line {line_num}: "
                    f"Failed IBAN/BBAN validation. "
                    f"IBAN country code '{country}' is not a recognised IBAN-issuing country.",
                    f"Use a recognised 2-letter ISO country code that participates in the IBAN scheme."
                ))
                return errors

            # 3. Exact length for country
            expected_len = IBAN_LENGTHS[country]
            if len(v) != expected_len:
                errors.append((
                    f"Invalid account identifier in element <{container}> at line {line_num}: "
                    f"Failed IBAN/BBAN validation. "
                    f"IBAN '{value}' has length {len(v)}, but {country} IBANs must be "
                    f"exactly {expected_len} characters.",
                    f"Check the IBAN for missing or extra characters. "
                    f"{country} IBANs are always {expected_len} characters long."
                ))
                return errors

            # 4. MOD 97-10 check digit verification
            if not _iban_mod97(v):
                errors.append((
                    f"Invalid account identifier in element <{container}> at line {line_num}: "
                    f"Failed IBAN/BBAN validation. "
                    f"IBAN '{value}' failed the MOD-97 check digit verification.",
                    f"The IBAN check digits (positions 3–4) are incorrect. "
                    f"Move the first 4 characters to the end, convert letters to numbers "
                    f"(A=10…Z=35), then verify the result mod 97 equals 1."
                ))
            return errors

        # ── Helper: validate BBAN value ──────────────────────────────────────
        def _validate_bban(value: str, container: str, line_num, country_code: str = '') -> list:
            """
            Validates a BBAN value against:
              - Non-empty check
              - Maximum 30-character length
              - Alphanumeric characters
              - Country-specific length & character-type structure (if country known)
              - Embedded national check digits: France RIB key, Spain CCC
            """
            errors = []
            v = value.strip()
            cc = (country_code or '').strip().upper()

            # Rule 1: must not be empty
            if not v:
                errors.append((
                    f"Invalid account identifier in element <{container}> at line {line_num}: "
                    f"Failed IBAN/BBAN validation. BBAN value is empty.",
                    "Provide a valid BBAN (domestic account number)."
                ))
                return errors

            # Rule 2: must not exceed 30 characters
            if len(v) > 30:
                errors.append((
                    f"Invalid account identifier in element <{container}> at line {line_num}: "
                    f"Failed IBAN/BBAN validation. BBAN '{v}' exceeds the maximum length of 30 characters "
                    f"(actual: {len(v)}).",
                    "Shorten the BBAN to at most 30 characters."
                ))

            # Country-specific structure validation (takes priority over generic check)
            if cc and cc in BBAN_STRUCTURES:
                bban_len, segments = BBAN_STRUCTURES[cc]

                # Exact domestic length required
                if len(v) != bban_len:
                    errors.append((
                        f"Invalid account identifier in element <{container}> at line {line_num}: "
                        f"Failed IBAN/BBAN validation. BBAN '{v}' has length {len(v)}, "
                        f"but {cc} domestic BBANs must be exactly {bban_len} characters.",
                        f"The BBAN for country {cc} must be exactly {bban_len} characters. "
                        f"Structure: " + ', '.join(f"{l}x{'numeric' if t=='n' else 'alpha' if t=='a' else 'alphanumeric'}" for l, t in segments) + '.'
                    ))
                else:
                    # Validate each segment character type
                    pos = 0
                    seg_errors = []
                    for seg_len, seg_type in segments:
                        seg = v[pos:pos + seg_len]
                        pos += seg_len
                        if seg_type == 'n' and not seg.isdigit():
                            seg_errors.append(
                                f"chars {pos - seg_len + 1}–{pos} ('{seg}') must be numeric only"
                            )
                        elif seg_type == 'a' and not seg.isalpha():
                            seg_errors.append(
                                f"chars {pos - seg_len + 1}–{pos} ('{seg}') must be alphabetic only"
                            )
                        elif seg_type == 'c' and not re.match(r'^[A-Za-z0-9]+$', seg):
                            seg_errors.append(
                                f"chars {pos - seg_len + 1}–{pos} ('{seg}') must be alphanumeric"
                            )
                    if seg_errors:
                        seg_structure = ', '.join(
                            f"{l}x{'n' if t=='n' else 'a' if t=='a' else 'c'}" for l, t in segments
                        )
                        errors.append((
                            f"Invalid account identifier in element <{container}> at line {line_num}: "
                            f"Failed IBAN/BBAN validation. BBAN '{v}' has invalid character types for country {cc}: "
                            + '; '.join(seg_errors) + '.',
                            f"{cc} BBAN structure is {bban_len} chars = [{seg_structure}] "
                            f"where n=numeric, a=alpha, c=alphanumeric."
                        ))

                    # National check digit validation (only when structure passed)
                    if not seg_errors:
                        if cc in ('FR', 'MC') and not _fr_rib_check(v):
                            errors.append((
                                f"Invalid account identifier in element <{container}> at line {line_num}: "
                                f"Failed IBAN/BBAN validation. BBAN '{v}' failed the French RIB key check "
                                f"(2-digit RIB key at positions 22–23).",
                                "Recalculate the RIB key using: 97 - ((89×bank + 15×branch + 3×account) mod 97). "
                                "Apply the French letter substitution table (A=1, B=2 … S=2, T=3 … wrapping at 9)."
                            ))
                        elif cc == 'ES' and not _es_check_digit(v):
                            errors.append((
                                f"Invalid account identifier in element <{container}> at line {line_num}: "
                                f"Failed IBAN/BBAN validation. BBAN '{v}' failed the Spanish CCC control digit check "
                                f"(digits 9–10 of the 20-digit CCC).",
                                "Recalculate the 2 control digits using the Spanish weighted-sum MOD-11 algorithm "
                                "(weights 1,2,4,8,5,10,9,7,3,6) applied to the bank/branch code and account number."
                            ))
            else:
                # Fallback: general alphanumeric check for unknown countries
                if not re.match(r'^[A-Za-z0-9]+$', v):
                    errors.append((
                        f"Invalid account identifier in element <{container}> at line {line_num}: "
                        f"Failed IBAN/BBAN validation. BBAN '{v}' contains invalid characters. "
                        f"Only alphanumeric characters (A–Z, a–z, 0–9) are allowed.",
                        "Remove spaces, hyphens, and any special characters from the BBAN value."
                    ))
            return errors

        # ── Helper: validate amount is strictly positive ─────────────────────
        def _validate_positive_amount(value: str, tag_name: str, line_num) -> list:
            errors = []
            try:
                amount = float(value)
                if amount <= 0:
                    errors.append((
                        f"Invalid amount in element <{tag_name}> at line {line_num}: "
                        f"Amount '{value}' must be strictly positive.",
                        "Ensure the amount is greater than zero."
                    ))
            except ValueError:
                # This case should ideally be caught by XSD validation (Layer 1)
                # but we add a safeguard here.
                errors.append((
                    f"Invalid amount format in element <{tag_name}> at line {line_num}: "
                    f"Value '{value}' is not a valid number.",
                    "Provide a valid numeric amount."
                ))
            return errors

        # ── Parse XML with lxml to walk elements ─────────────────────────────
        try:
            parser = etree.XMLParser(recover=True, remove_blank_text=True)
            root   = etree.fromstring(xml_content.encode('utf-8'), parser)
        except Exception:
            return  # XML parsing handled by Layer 1

        def local(tag):
            return tag.split('}')[-1] if '}' in tag else tag

        def get_text(elem, *tags):
            """Traverse child tags and return stripped text, or None."""
            node = elem
            for t in tags:
                node = next((c for c in node if local(c.tag) == t), None)
                if node is None:
                    return None
            return (node.text or '').strip() or None

        # Detect SEPA context (SvcLvl/Cd = 'SEPA' anywhere in document)
        is_sepa = any(
            (e.text or '').strip().upper() == 'SEPA'
            for e in root.iter()
            if local(e.tag) == 'Cd'
        )

        # Store country codes for BBAN validation if available
        debtor_country = None
        creditor_country = None
        for e in root.iter():
            tag = local(e.tag)
            if tag == 'Ctry':
                parent_tag = local(e.getparent().tag) if e.getparent() is not None else ''
                grandparent_tag = local(e.getparent().getparent().tag) if e.getparent() is not None and e.getparent().getparent() is not None else ''
                if 'Dbtr' in grandparent_tag or 'InitgPty' in grandparent_tag:
                    debtor_country = (e.text or '').strip().upper()
                if 'Cdtr' in grandparent_tag:
                    creditor_country = (e.text or '').strip().upper()

        # Walk all relevant elements
        for elem in root.iter():
            tag_name = local(elem.tag)
            line_num = getattr(elem, 'sourceline', 'Unknown') or 'Unknown'

            # ── Account Identifier Validation ────────────────────────────────
            if tag_name in ACCOUNT_TAGS:
                container = tag_name
                # Find <Id> child
                id_elem = next((c for c in elem if local(c.tag) == 'Id'), None)
                if id_elem is None:
                    continue

                iban_elem = next((c for c in id_elem if local(c.tag) == 'IBAN'), None)
                othr_elem = next((c for c in id_elem if local(c.tag) == 'Othr'), None)

                # ── Rule 3: Mutual exclusivity ───────────────────────────────────
                if iban_elem is not None and othr_elem is not None:
                    report.add_issue(ValidationIssue(
                        "ERROR", 3, "ACCT_MUTUAL_EXCLUSIVITY", str(line_num),
                        f"Invalid account identifier in element <{container}> at line {line_num}: "
                        f"Failed IBAN/BBAN validation. "
                        f"Both <IBAN> and <Othr> are present simultaneously. Exactly one must be used.",
                        "Remove either <IBAN> or <Othr>. ISO 20022 requires exactly one account identification method."
                    ))
                    continue

                if iban_elem is None and othr_elem is None:
                    report.add_issue(ValidationIssue(
                        "ERROR", 3, "ACCT_MISSING_ID", str(line_num),
                        f"Invalid account identifier in element <{container}> at line {line_num}: "
                        f"Failed IBAN/BBAN validation. "
                        f"Neither <IBAN> nor <Othr> is present inside <Id>. "
                        f"Exactly one account identification method must be provided.",
                        "Provide an account identification: either <IBAN> for international accounts, "
                        "or <Othr><SchmeNm><Cd>BBAN</Cd></SchmeNm></Othr> for domestic accounts."
                    ))
                    continue

                # ── IBAN path ─────────────────────────────────────────────────────
                if iban_elem is not None:
                    iban_val = (iban_elem.text or '').strip()
                    for msg, fix in _validate_iban(iban_val, container, line_num):
                        report.add_issue(ValidationIssue(
                            "ERROR", 3, "IBAN_VALIDATION_ERROR", str(line_num), msg, fix
                        ))

                # ── BBAN / Othr path ──────────────────────────────────────────────
                if othr_elem is not None:
                    othr_id  = get_text(othr_elem, 'Id')
                    scheme_cd = get_text(othr_elem, 'SchmeNm', 'Cd')

                    if scheme_cd and scheme_cd.upper() == 'BBAN':
                        # Rule 6: SEPA — BBAN not allowed
                        if is_sepa:
                            report.add_issue(ValidationIssue(
                                "ERROR", 3, "SEPA_BBAN_NOT_ALLOWED", str(line_num),
                                f"Invalid account identifier in element <{container}> at line {line_num}: "
                                f"BBAN account identification is not permitted in SEPA payments. IBAN is mandatory.",
                                "Replace the <Othr><Id>BBAN</Id> block with a valid <IBAN> element for SEPA transactions."
                            ))
                        else:
                            # Determine country for BBAN validation
                            bban_country = None
                            if 'Dbtr' in container or 'InitgPty' in container:
                                bban_country = debtor_country
                            elif 'Cdtr' in container:
                                bban_country = creditor_country

                            for msg, fix in _validate_bban(othr_id or '', container, line_num, bban_country):
                                report.add_issue(ValidationIssue(
                                    "ERROR", 3, "BBAN_VALIDATION_ERROR", str(line_num), msg, fix
                                ))

            # ── Amount Validation (strictly positive) ────────────────────────
            if tag_name in AMOUNT_TAGS:
                amount_val = (elem.text or '').strip()
                if amount_val:
                    for msg, fix in _validate_positive_amount(amount_val, tag_name, line_num):
                        report.add_issue(ValidationIssue(
                            "ERROR", 3, "NON_POSITIVE_AMOUNT", str(line_num), msg, fix
                        ))

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

