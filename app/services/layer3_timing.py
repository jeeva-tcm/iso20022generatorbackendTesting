import json
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo
from typing import Dict, Any, List, Optional

class ValidationIssue:
    def __init__(self, rule_id: str, severity: str, field: Optional[str], message: str, details: Dict):
        self.rule_id = rule_id
        self.severity = severity
        self.field = field
        self.message = message
        self.details = details

    def to_dict(self):
        res = {
            "ruleId": self.rule_id,
            "severity": self.severity,
            "message": self.message,
            "details": self.details
        }
        if self.field:
            res["field"] = self.field
        return res

class ValidationResult:
    def __init__(self):
        self.layer = 3
        self.status = "PASS"
        self.summary = []
        self.recommended_value_date = None
        self.issues = []

    def add_issue(self, issue: ValidationIssue):
        self.issues.append(issue)
        if issue.severity == "FAIL":
            self.status = "FAIL"
        elif issue.severity == "WARN" and self.status != "FAIL":
            self.status = "WARN"
            
    def set_recommended_value_date(self, dt: str):
        self.recommended_value_date = dt

    def to_dict(self):
        res = {
            "layer": self.layer,
            "status": self.status,
            "summary": " ".join(self.summary) if self.summary else "Timing validation passed.",
            "issues": [i.to_dict() for i in self.issues]
        }
        if self.recommended_value_date:
            res["recommendedValueDate"] = self.recommended_value_date
        return res

def is_holiday(country_code: str, dt: date) -> bool:
    """Stub: Can integrate with a holiday API here."""
    return False

def get_system_config(country: str, system_key: str, cutoff_config: Dict) -> Optional[Dict]:
    countries_conf = cutoff_config.get("timings", {})
    if country not in countries_conf:
        return None
    systems_conf = countries_conf[country].get("paymentSystems", {})
    if system_key not in systems_conf:
        return None
    sys_conf = systems_conf[system_key].copy()
    sys_conf["country"] = country
    return sys_conf

def parse_time(time_str: str) -> time:
    return datetime.strptime(time_str, "%H:%M").time()

def to_zoned_datetime(dt_str: str, target_tz: str) -> datetime:
    if not dt_str:
        return None
    dt_str = dt_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(dt_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(ZoneInfo(target_tz))

def is_business_day(system_config: Dict, dt: date, country: str) -> bool:
    day_abbr = dt.strftime("%a").upper()
    if day_abbr not in system_config.get("days", []):
        return False
    if is_holiday(country, dt):
        return False
    return True

def next_business_day(system_config: Dict, start_date: date, country: str) -> date:
    next_day = start_date + timedelta(days=1)
    while not is_business_day(system_config, next_day, country):
        next_day += timedelta(days=1)
    return next_day

def build_details(debtor_c, debtor_s, d_cutoff, d_tz, d_eval, d_bus_day,
                  cred_c, cred_s, c_cutoff, c_tz, c_eval, c_bus_day, computed=None):
    details = {
        "debtor": {
            "country": debtor_c, "system": debtor_s, "cutoffTime": d_cutoff,
            "timezone": d_tz, "evaluatedTime": d_eval, "businessDay": d_bus_day
        },
        "creditor": {
            "country": cred_c, "system": cred_s, "cutoffTime": c_cutoff,
            "timezone": c_tz, "evaluatedTime": c_eval, "businessDay": c_bus_day
        }
    }
    if computed:
        details["computed"] = computed
    return details

def validateLayer3Timing(payload: Dict, context: Dict, cutoffConfig: Dict) -> Dict:
    result = ValidationResult()

    debtor_country = context.get("debtorCountry")
    debtor_system_key = context.get("debtorPaymentSystem")
    creditor_country = context.get("creditorCountry")
    creditor_system_key = context.get("creditorPaymentSystem")
    validation_mode = context.get("validationMode", "STRICT")
    sub_timestamp_str = context.get("submissionTimestamp")

    if not all([debtor_country, debtor_system_key, creditor_country, creditor_system_key, sub_timestamp_str]):
        result.add_issue(ValidationIssue("CONFIG_NOT_FOUND", "FAIL", None, "Missing required context parameters.", {}))
        result.summary.append("Context missing parameters.")
        return result.to_dict()

    debtor_config = get_system_config(debtor_country, debtor_system_key, cutoffConfig)
    creditor_config = get_system_config(creditor_country, creditor_system_key, cutoffConfig)

    if not debtor_config:
        result.add_issue(ValidationIssue("CONFIG_NOT_FOUND", "FAIL", None, 
            f"Debtor configuration not found for {debtor_country} - {debtor_system_key}.", {}))
        result.summary.append("Debtor system not configured.")
        return result.to_dict()
    
    if not creditor_config:
        result.add_issue(ValidationIssue("CONFIG_NOT_FOUND", "FAIL", None, 
            f"Creditor configuration not found for {creditor_country} - {creditor_system_key}.", {}))
        result.summary.append("Creditor system not configured.")
        return result.to_dict()

    try:
        sub_d_dt = to_zoned_datetime(sub_timestamp_str, debtor_config["timezone"])
        sub_c_dt = to_zoned_datetime(sub_timestamp_str, creditor_config["timezone"])
    except ValueError as e:
        result.add_issue(ValidationIssue("TIME_PARSE", "FAIL", None, f"Invalid submission timestamp format: {e}", {}))
        return result.to_dict()

    # Base detail block
    def mkt_details(comp=None):
        return build_details(
            debtor_country, debtor_system_key, debtor_config["cutoffTime"], debtor_config["timezone"],
            sub_d_dt.isoformat(), is_business_day(debtor_config, sub_d_dt.date(), debtor_country),
            creditor_country, creditor_system_key, creditor_config["cutoffTime"], creditor_config["timezone"],
            sub_c_dt.isoformat(), is_business_day(creditor_config, sub_c_dt.date(), creditor_country),
            comp
        )

    # Re-use payload extraction
    cre_dt_tm = payload.get("CreDtTm") or sub_timestamp_str
    try:
        cre_d_dt = to_zoned_datetime(cre_dt_tm, debtor_config["timezone"])
        cre_c_dt = to_zoned_datetime(cre_dt_tm, creditor_config["timezone"])
    except ValueError:
        cre_d_dt = sub_d_dt
        cre_c_dt = sub_c_dt

    reqd_exctn_dt_str = payload.get("ReqdExctnDt")
    intr_bk_sttlm_dt_str = payload.get("IntrBkSttlmDt")

    # CUT001: Creation date-time must be before cut-off
    d_cutoff_time = parse_time(debtor_config["cutoffTime"])
    c_cutoff_time = parse_time(creditor_config["cutoffTime"])
    
    is_d_after_cutoff = cre_d_dt.time() >= d_cutoff_time
    is_c_after_cutoff = cre_c_dt.time() >= c_cutoff_time
    
    if is_d_after_cutoff:
        stat = "FAIL" if validation_mode == "STRICT" else "WARN"
        result.add_issue(ValidationIssue("CUT001", stat, "CreDtTm", 
            "Creation date-time is after the cut-off for the debtor payment system.", mkt_details()))
    elif is_c_after_cutoff:
        stat = "WARN"
        result.add_issue(ValidationIssue("CUT001", stat, "CreDtTm", 
            "Creation date-time is after the cut-off for the creditor payment system. Credit may be delayed.", mkt_details()))

    # CUT004 Base Setup
    computed = {}
    is_d_bus_day = is_business_day(debtor_config, sub_d_dt.date(), debtor_country)
    
    computed_next_d = next_business_day(debtor_config, sub_d_dt.date(), debtor_country).isoformat()
    computed_next_c = next_business_day(creditor_config, sub_c_dt.date(), creditor_country).isoformat()
    
    rec_val_date = None
    if is_d_after_cutoff or not is_d_bus_day:
        base_rec_d = next_business_day(debtor_config, sub_d_dt.date(), debtor_country)
        # Check against creditor availability on base_rec_d
        # Convert base_rec_d to creditor date roughly
        is_c_bus_day = is_business_day(creditor_config, base_rec_d, creditor_country)
        if not is_c_bus_day:
            rec_val_date = next_business_day(creditor_config, base_rec_d, creditor_country)
        else:
            rec_val_date = base_rec_d
            
        rec_str = rec_val_date.isoformat()
        computed = {
            "recommendedValueDate": rec_str,
            "nextBusinessDayDebtor": computed_next_d,
            "nextBusinessDayCreditor": computed_next_c
        }
        result.set_recommended_value_date(rec_str)

    # CUT002: ReqdExctnDt must be a valid business day
    if reqd_exctn_dt_str:
        req_dt = date.fromisoformat(reqd_exctn_dt_str)
        req_d_bus = is_business_day(debtor_config, req_dt, debtor_country)
        req_c_bus = is_business_day(creditor_config, req_dt, creditor_country)

        if not req_d_bus or not req_c_bus:
            stat = "FAIL" if validation_mode == "STRICT" else "WARN"
            msg = f"Requested execution date {reqd_exctn_dt_str} is not a valid business day for both parties."
            result.add_issue(ValidationIssue("CUT002", stat, "ReqdExctnDt", msg, mkt_details(computed)))
        elif rec_val_date and req_dt < rec_val_date:
            stat = "FAIL" if validation_mode == "STRICT" else "WARN"
            msg = f"Requested execution date {reqd_exctn_dt_str} is earlier than recommended value date {rec_val_date.isoformat()}."
            result.add_issue(ValidationIssue("CUT004", stat, "ReqdExctnDt", msg, mkt_details(computed)))

    # CUT003: IntrBkSttlmDt must align with the settlement system
    if intr_bk_sttlm_dt_str:
        intr_dt = date.fromisoformat(intr_bk_sttlm_dt_str)
        intr_c_bus = is_business_day(creditor_config, intr_dt, creditor_country)
        
        if not intr_c_bus:
            stat = "FAIL" if validation_mode == "STRICT" else "WARN"
            msg = f"Interbank settlement date {intr_bk_sttlm_dt_str} is not a valid business day for creditor."
            result.add_issue(ValidationIssue("CUT003", stat, "IntrBkSttlmDt", msg, mkt_details(computed)))
        elif rec_val_date and intr_dt < rec_val_date:
            stat = "FAIL" if validation_mode == "STRICT" else "WARN"
            msg = f"Interbank settlement date {intr_bk_sttlm_dt_str} is earlier than recommended value date {rec_val_date.isoformat()}."
            result.add_issue(ValidationIssue("CUT004", stat, "IntrBkSttlmDt", msg, mkt_details(computed)))

    if not result.issues:
        result.summary.append("All timing rules passed successfully.")
    else:
        # Just summarizing how many failed/warn
        fails = sum(1 for i in result.issues if i.severity == "FAIL")
        warns = sum(1 for i in result.issues if i.severity == "WARN")
        if fails:
            result.summary.append(f"Validation failed with {fails} error(s).")
        if warns:
            result.summary.append(f"Validation completed with {warns} warning(s).")
            
    return result.to_dict()

# =========================================================================
# Unit Tests
# =========================================================================
if __name__ == "__main__":
    cutoff_config = {
      "timings": {
        "US": {
          "paymentSystems": {
            "FEDWIRE": {
              "cutoffTime": "18:00",
              "timezone": "America/New_York",
              "days": ["MON", "TUE", "WED", "THU", "FRI"]
            }
          }
        },
        "GB": {
          "paymentSystems": {
            "CHAPS": {
              "cutoffTime": "16:00",
              "timezone": "Europe/London",
              "days": ["MON", "TUE", "WED", "THU", "FRI"]
            }
          }
        }
      }
    }

    # Format output helper
    def pp(res):
        print(json.dumps(res, indent=2))

    print("--- Test 1: Happy Path ---")
    payload = {
        "CreDtTm": "2023-10-10T10:00:00Z",
        "ReqdExctnDt": "2023-10-10",
        "IntrBkSttlmDt": "2023-10-10"
    } # 10 AM UTC = 6 AM NY = 11 AM London -> Tuesday
    context = {
        "debtorCountry": "US", "debtorPaymentSystem": "FEDWIRE",
        "creditorCountry": "GB", "creditorPaymentSystem": "CHAPS",
        "submissionTimestamp": "2023-10-10T10:00:00Z",
        "validationMode": "STRICT"
    }
    pp(validateLayer3Timing(payload, context, cutoff_config))

    print("\n--- Test 2: After debtor cutoff (STRICT) ---")
    # 2023-10-10T23:00:00Z -> 19:00 NY (After 18:00 cutoff)
    payload = {"CreDtTm": "2023-10-10T23:00:00Z", "ReqdExctnDt": "2023-10-10"}
    context["submissionTimestamp"] = "2023-10-10T23:00:00Z"
    pp(validateLayer3Timing(payload, context, cutoff_config))

    print("\n--- Test 3: After debtor cutoff (LENIENT) ---")
    context["validationMode"] = "LENIENT"
    pp(validateLayer3Timing(payload, context, cutoff_config))

    print("\n--- Test 4: Weekend / Non-business day ---")
    # 2023-10-14 is Saturday
    payload = {"CreDtTm": "2023-10-14T10:00:00Z"}
    context["submissionTimestamp"] = "2023-10-14T10:00:00Z"
    context["validationMode"] = "STRICT"
    pp(validateLayer3Timing(payload, context, cutoff_config))

    print("\n--- Test 5: Missing Config ---")
    context["debtorCountry"] = "XX"
    pp(validateLayer3Timing(payload, context, cutoff_config))

