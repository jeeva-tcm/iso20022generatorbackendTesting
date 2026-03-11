import json
import re
import time
import os
from datetime import datetime
from typing import Dict, Any, List
from .models import ValidationIssue, ValidationReport

class Layer3Mixin:

    def _load_generic_config(self):
        """Loads the new global algorithms and field library."""
        config = {"algorithms": {}, "fields": {}, "messages": {}}
        try:
            for name in ["algorithms", "fields", "message_definitions"]:
                path = os.path.join(self.rules_path, f"{name}.json")
                if os.path.exists(path):
                    with open(path, "r", encoding='utf-8-sig') as f:
                        data = json.load(f)
                        if name == "message_definitions":
                            config["messages"] = data.get("messages", {})
                        else:
                            config[name] = data.get(name, {})
        except Exception as e:
            print(f"Error loading generic config: {e}")
        return config

    def _load_all_rules(self, message_type: str) -> List[Dict[str, Any]]:
        """
        Loads global rules + family rules + message-specific rules.
        """
        rules = []
        
        # 1. Load Global
        global_file = os.path.join(self.rules_path, "global.json")
        if os.path.exists(global_file):
            try:
                with open(global_file, "r", encoding='utf-8-sig') as f:
                    rules.extend(json.load(f))
            except Exception as e: 
                print(f"Error loading global rules: {e}")

        parts = message_type.split(".")
        
        # 2. Load Family Level (e.g., pacs.json)
        if len(parts) >= 1:
            family = parts[0]
            family_file = os.path.join(self.rules_path, f"{family}.json")
            if os.path.exists(family_file):
                try:
                    with open(family_file, "r", encoding='utf-8-sig') as f:
                        rules.extend(json.load(f))
                except Exception as e: 
                    print(f"Error loading family rules: {e}")

        # 3. Load Message Specific (e.g., pacs.008.json)
        # Try pacs.008 first
        specific_name = ".".join(parts[:2]) if len(parts) >= 2 else message_type
        specific_file = os.path.join(self.rules_path, f"{specific_name}.json")
        
        # If not found, try full name just in case (e.g. pacs.008.001.08.json - rare but possible)
        if not os.path.exists(specific_file):
             specific_file = os.path.join(self.rules_path, f"{message_type}.json")

        if os.path.exists(specific_file):
            try:
                with open(specific_file, "r", encoding='utf-8-sig') as f:
                    rules.extend(json.load(f))
            except Exception as e: 
                print(f"Error loading specific rules: {e}")
            
        return rules

    def _run_dynamic_layer(self, layer_id: int, rules: List[Dict[str, Any]], data: Dict[str, Any], line_map: Dict[str, int], report: ValidationReport):
        """
        Executes all rules assigned to a specific layer.
        """
        start = time.time()
        
        # Filter rules for the current layer
        layer_rules = [r for r in rules if r.get("layer") == layer_id]
        
        # Use cached codelists (Layer 3 always needs them)
        codelists = self.codelists

        for rule in layer_rules:
            self._execute_rule_logic(rule, data, line_map, codelists, report)
        
        # Assessment for layer dashboard
        success = not any(i['layer'] == layer_id and i['severity'] == "ERROR" for i in report.issues)
        report.layer_status[str(layer_id)] = {
            "status": "✅" if success else "❌", 
            "time": round((time.time() - start) * 1000, 2)
        }

    def _run_generic_field_validation(self, message_type: str, data: Dict[str, Any], line_map: Dict[str, int], report: ValidationReport):
        """
        Executes validation based on the Generic Field Library and Global Algorithms.
        This acts as Layer 2.5 (Syntax + Semantic).
        """
        start = time.time()
        config = self._load_generic_config()
        algorithms = config.get("algorithms", {})
        fields_lib = config.get("fields", {})
        message_defs = config.get("messages", {})

        # 1. Identify which message definition to use
        # Normalize message_type (e.g. pacs.008.001.08 -> pacs.008)
        parts = message_type.split(".")
        short_type = ".".join(parts[:2]) if len(parts) >= 2 else message_type
        
        # Try finding the exact or short version (pacs.008.cov vs pacs.008)
        msg_def = message_defs.get(message_type)
        if not msg_def:
            msg_def = message_defs.get(short_type)
            
        if not msg_def:
            # If no definition for this message type, skip this validation layer
            return

        # 2. Iterate through sections of the message (AppHdr, GrpHdr, etc.)
        for section, expected_fields in msg_def.items():
            # Find elements in data that belong to this section
            # We look for keys starting with [section] or ending with [section].[field]
            for field_name in expected_fields:
                field_cfg = fields_lib.get(field_name)
                if not field_cfg:
                    continue

                # Find all occurrences of this field in the current section
                # Use regex to find keys like Document.CdtTrfTxInf.InstrId or AppHdr.CreDtTm
                pattern = rf"(^|\.){section}(\.\w+)*\.{field_name}$"
                matching_keys = [k for k in data.keys() if re.search(pattern, k)]
                
                # Removed redundant mandatory check (XSD Layer 2 handles existence)
                # This fixes the issue where optional fields were being reported as missing
                
                for key in matching_keys:
                    # Apply regex ONLY for mandatory fields as requested by USER
                    # Generic Layer focuses on core identifiers defined as min: 1 in fields.json
                    if field_cfg.get("min", 0) <= 0:
                        continue
                        
                    value = data[key]
                    algo_name = field_cfg.get("regex")
                    regex_pattern = algorithms.get(algo_name, algo_name) # Fallback if it's a literal regex

                    # 1. Regex Validation
                    if regex_pattern and not re.match(regex_pattern, str(value)):
                        report.add_issue(ValidationIssue(
                            "ERROR", 3, "INVALID_FIELD_FORMAT", str(line_map.get(key, "/")),
                            f"Field '{field_name}' has invalid format: '{value}'.",
                            f"Value must match pattern for '{algo_name}': {regex_pattern}"
                        ))

                    # 2. Attributes Validation (e.g. Ccy)
                    attrs_cfg = field_cfg.get("attributes", {})
                    for attr_name, attr_algo in attrs_cfg.items():
                        attr_key = f"{key}@{attr_name}"
                        attr_val = data.get(attr_key)
                        attr_regex = algorithms.get(attr_algo, attr_algo)
                        
                        if not attr_val:
                             report.add_issue(ValidationIssue(
                                "ERROR", 3, "MISSING_ATTRIBUTE", str(line_map.get(key, "/")),
                                f"Mandatory attribute '{attr_name}' is missing for field '{field_name}'.",
                                f"Add {attr_name}=\"...\" to the <{field_name}> tag."
                            ))
                        elif attr_regex and not re.match(attr_regex, str(attr_val)):
                             report.add_issue(ValidationIssue(
                                "ERROR", 3, "INVALID_ATTRIBUTE_FORMAT", str(line_map.get(attr_key, "/")),
                                f"Attribute '{attr_name}' for '{field_name}' has invalid format: '{attr_val}'.",
                                f"Value must match pattern for '{attr_algo}': {attr_regex}"
                            ))

        # No longer assigning to report.layer_status["Global Algorithms"] as requested.
        pass

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
                            # Build context-aware message and fix suggestion
                            field_name = key.split('.')[-1]
                            if list_name == "country":
                                msg = f"Invalid country code '{value}' in field '{field_name}'."
                                fix = (f"'{value}' is not a valid ISO 3166-1 Alpha-2 country code. "
                                       f"Use a 2-letter code like 'US', 'GB', 'DE', 'FR', 'IN', 'SG', etc.")
                            elif list_name == "charge_bearer":
                                msg = f"Invalid Charge Bearer code '{value}'."
                                fix = (f"'{value}' is not allowed. Valid Charge Bearer codes are: "
                                       f"SLEV (Shared, as agreed), SHAR (Shared), CRED (Borne by Creditor), DEBT (Borne by Debtor).")
                            elif list_name == "purpose_code":
                                msg = f"Invalid Purpose Code '{value}'."
                                fix = (f"'{value}' is not a valid ISO 20022 Purpose Code. "
                                       f"Use a standard code such as SALA, RENT, SUPP, CORT, PENS, BONU, TRAD, LOAN, TAXS, etc.")
                            else:
                                msg = f"Field '{field_name}' contains invalid code '{value}'."
                                fix = f"Value '{value}' is not a valid code for this field. Please check the ISO 20022 standard for permitted values."
                            
                            report.add_issue(ValidationIssue(severity, layer, rule_id, _get_line(key), msg, fix))
                
                elif rule_type == "bic":
                    if not re.match(r'^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$', str(value)):
                        report.add_issue(ValidationIssue(severity, layer, rule_id, _get_line(key), f"{desc} Invalid BIC structure: '{value}'.", "BIC must be 8 or 11 characters: 4-char bank code + 2-letter country + 2-char location + optional 3-char branch (e.g., BNKGB2LXXX)."))
                    elif self.supported_bics and value.upper() not in self.supported_bics:
                        report.add_issue(ValidationIssue("WARNING", layer, "BIC_NOT_FOUND", _get_line(key), f"BIC '{value}' not found in official directory.", "Verify if the BIC is correct or recently decommissioned."))
                
                elif rule_type == "currency_amount":
                    ccy_path = key + "@Ccy"
                    if not ccy_path in data:
                        ccy_path = key.rsplit('.', 1)[0] + ".Ccy"
                    
                    ccy = data.get(ccy_path)
                    allowed_decimals = None
                    
                    if ccy:
                        if "currency" in codelists:
                            curr_list = codelists["currency"]
                            if isinstance(curr_list, dict):
                                currencies = curr_list.get("currencies", {})
                                if ccy in currencies:
                                    allowed_decimals = currencies.get(ccy)
                                else:
                                    report.add_issue(ValidationIssue(
                                        severity, layer, "INVALID_CURRENCY_CODE", _get_line(ccy_path),
                                        f"Unrecognised Currency Code '{ccy}'.",
                                        f"The code '{ccy}' is not a valid ISO 4217 currency. Use standard codes like USD, EUR, GBP, JPY, etc."
                                    ))
                                    continue
                        
                        if allowed_decimals is not None:
                            val_str = str(value)
                            actual_decimals = len(val_str.split('.')[1]) if '.' in val_str else 0
                            if actual_decimals > allowed_decimals:
                                report.add_issue(ValidationIssue(
                                    severity, layer, "INVALID_DECIMAL_PRECISION", _get_line(key),
                                    f"Incorrect decimal precision for {ccy} amount '{value}'. {ccy} allows max {allowed_decimals} decimal place(s), but {actual_decimals} were provided.",
                                    f"Adjust the fractional part: {ccy} supports {allowed_decimals} decimal place(s) (e.g., {'10.00' if allowed_decimals == 2 else '10' if allowed_decimals == 0 else '10.000'})."
                                ))

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
                    f"Invalid purpose code '{purpose}'. This code is not a recognised ISO 20022 ExternalPurpose1Code value.", 
                    f"Replace '{purpose}' with a valid ISO 20022 purpose code (e.g., SALA, CORT, PENS, BONU, TRAD, LOAN, RENT, SUPP, TAXS, etc.)."))
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
                "check_iban_currency": lambda k, v: self._check_iban_currency(k, v, data, report, _gl, codelists),
                "is_after_2026": datetime.now() > mandate_date,
                "exists": lambda x: any(k.startswith(x) for k in data.keys())
            }
            
            reserved = set(["VALUE", "KEY", "DATA", "True", "False", "None", "exists", "check_address", "check_bic_match", "datetime", "len", "float", "int", "str"])
            for key in sorted(data.keys(), key=len, reverse=True):
                pattern = r'\b' + re.escape(key) + r'\b'
                if re.search(pattern, temp_expr) and key not in reserved:
                    val = data[key]
                    if isinstance(val, str):
                        escaped_val = val.replace("'", "\\'")
                        val_str = f"'{escaped_val}'"
                    else:
                        val_str = str(val)
                    
                    # Use lambda to avoid backslash issues in re.sub
                    temp_expr = re.sub(pattern, lambda m: val_str, temp_expr)
            
            return eval(temp_expr, {"__builtins__": None}, ctx)
        except Exception as e:
            return False

    def _check_iban_currency(self, iban_key, iban_val, data, report, _gl, codelists):
        """
        Business Rule: Validate if the transaction currency matches the local currency 
        of the country where the Debtor's IBAN is registered.
        """
        # Rule is configurable via flag
        if not self.config.get("validation_rules", {}).get("enable_iban_currency_check", True):
            return True

        # Extract currency - searching relative or anywhere
        # User example: <InstdAmt Ccy="XXX">
        currency = None
        ccy_key = None
        
        # 1. Search for currency in common locations (InstdAmt, IntrBkSttlmAmt)
        # We prioritize tags in the same transaction block if possible
        tx_path = iban_key.rsplit('.DbtrAcct', 1)[0] if '.DbtrAcct' in iban_key else None
        
        if tx_path:
             for tag in ["InstdAmt", "IntrBkSttlmAmt", "Amt.InstdAmt"]:
                  k = f"{tx_path}.{tag}@Ccy"
                  if k in data:
                       currency = data[k]
                       ccy_key = k
                       break
        
        # Fallback: Search anywhere
        if not currency:
            for k, v in data.items():
                if k.endswith("@Ccy") and ("InstdAmt" in k or "IntrBkSttlmAmt" in k):
                    currency = v
                    ccy_key = k
                    break
        
        if not currency:
            return True # Cannot validate if currency attribute is missing from standard tags

        # IBAN basic validation (Min 15 characters as per requirement)
        if not iban_val or not isinstance(iban_val, str) or len(iban_val) < 15:
            report.add_issue(ValidationIssue("ERROR", 3, "INVALID_IBAN", _gl(iban_key), "Invalid or Missing Debtor IBAN", "Ensure the IBAN is at least 15 characters long and follows the correct structure."))
            return True

        country_code = iban_val[:2].upper()
        if not country_code.isalpha():
             report.add_issue(ValidationIssue("ERROR", 3, "INVALID_IBAN_CTRY", _gl(iban_key), "Invalid or Missing Debtor IBAN", "The first two characters of the IBAN must be a valid country code."))
             return True

        # Map country to currency
        iban_map = codelists.get("iban_currency_map", {})
        expected_currency = iban_map.get(country_code)
        
        if not expected_currency:
            report.add_issue(ValidationIssue("ERROR", 3, "UNSUPPORTED_IBAN_CTRY", _gl(iban_key), "Unsupported IBAN Country Code", f"The country code '{country_code}' extracted from the IBAN is not supported in the currency mapping."))
            return True

        # Currency must follow ISO 4217 format (3 uppercase letters) and be case-sensitive
        if currency != expected_currency:
            report.add_issue(ValidationIssue(
                "ERROR", 3, "CURR_IBAN_MISMATCH", _gl(ccy_key or iban_key),
                f"Currency {currency} does not match expected currency {expected_currency} for IBAN country {country_code}",
                f"Update the transaction currency to {expected_currency} for the account based in {country_code}."
            ))
            return True # Suppress generic error

        return True

