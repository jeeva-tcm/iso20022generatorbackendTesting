
import json
from typing import Dict, Any, Optional

def validateSchmeNm(schmeNm: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates ISO 20022 <SchmeNm> element under /OrgId/Othr using reference data.
    
    Args:
        schmeNm: A dictionary representing the element, e.g. {'Cd': 'LEI'} or {'Prtry': 'CUST'}
    """
    config = {
      "schmeNm_validation": {
        "valid_cd_codes": [
          { 
            "code": "LEI", 
            "meaning": "Legal Entity Identifier", 
            "recommended": True,
            "usage": "Best for identifying legal entities globally"
          },
          { 
            "code": "TXID", 
            "meaning": "Tax Identification", 
            "recommended": False,
            "usage": "Used for tax identification numbers" 
          },
          { 
            "code": "BANK", 
            "meaning": "Bank Identifier", 
            "recommended": False,
            "usage": "Used for bank identification"
          },
          { 
            "code": "CUST", 
            "meaning": "Customer ID", 
            "recommended": True,
            "usage": "Safe fallback for customer identifiers"
          },
          { 
            "code": "COID", 
            "meaning": "Company Identifier", 
            "recommended": False,
            "usage": "Used for company identification"
          },
          { 
            "code": "TXNR", 
            "meaning": "Tax Number", 
            "recommended": False,
            "usage": "Used for tax number references"
          },
          { 
            "code": "DUNS", 
            "meaning": "Dun & Bradstreet Number", 
            "recommended": False,
            "usage": "Business credit and identity verification"
          },
          { 
            "code": "GIIN", 
            "meaning": "Global Intermediary Identification Number", 
            "recommended": False,
            "usage": "Used for FATCA compliance identification"
          }
        ],
        "invalid_cd_codes": [
          { "code": "Passport", "reason": "Used for individuals, not organizations", "fix": "Use LEI or CUST instead" },
          { "code": "PAN",      "reason": "Not a standard ISO scheme", "fix": "Use TXID for tax-related identification" },
          { "code": "AADHAR",   "reason": "Not ISO compliant, region-specific individual ID", "fix": "Use LEI for organization identification" },
          { "code": "ID123",    "reason": "Random custom code, not recognized by ISO", "fix": "Use <Prtry> tag instead for custom codes" },
          { "code": "ABC",      "reason": "Not a recognized ISO scheme code", "fix": "Use <Prtry>ABC</Prtry> if custom value is needed" },
          { "code": "TEST",     "reason": "Not valid for production environments", "fix": "Replace with LEI or CUST for production use" },
          { "code": "12345",    "reason": "Numeric only values are not allowed in <Cd>", "fix": "Use alphabetic ISO code like LEI or TXID" },
          { "code": "NAME",     "reason": "NAME is not an ID scheme, it is a data field", "fix": "Use COID or LEI for organization identification" }
        ],
        "prtry_rules": {
          "allowed": True,
          "accepts_any_non_empty_string": True,
          "examples": ["CUST", "INTERNAL", "LOCALID"],
          "note": "Prtry bypasses ISO Cd restrictions — use for custom identifiers"
        },
        "structure_rules": [
          {
            "rule": "mutually_exclusive",
            "description": "Only one of <Cd> or <Prtry> allowed — never both",
            "fix": "Use either <Cd> or <Prtry>, never both"
          },
          {
            "rule": "required_when_othr_present",
            "description": "<SchmeNm> is required whenever <Othr> block is used",
            "fix": "Add <SchmeNm><Cd>LEI</Cd></SchmeNm> inside <Othr>"
          },
          {
            "rule": "cd_must_match_allowlist",
            "description": "<Cd> value must exist in valid_cd_codes list"
          }
        ],
        "errors": {
          "invalid_scheme":       "Invalid scheme code in <Cd>",
          "missing_schmenm":      "<SchmeNm> is required when <Othr> is present",
          "both_cd_and_prtry":    "Mutually exclusive elements conflict",
          "empty_prtry":          "<Prtry> value must not be empty",
          "missing_element":      "<SchmeNm> must contain either <Cd> or <Prtry>"
        }
      }
    }

    rules = config["schmeNm_validation"]
    cd_val = schmeNm.get('Cd')
    prtry_val = schmeNm.get('Prtry')
    
    result = {
        "valid": False,
        "field": "/OrgId/Othr/SchmeNm",
        "value": None,
        "type": None,
        "error": None,
        "reason": None
    }

    # 1. Mutually Exclusive Rule
    if cd_val is not None and prtry_val is not None:
        result["error"] = rules["errors"]["both_cd_and_prtry"]
        result["value"] = f"Cd: {cd_val}, Prtry: {prtry_val}"
        return result

    # 2. Check type and value
    if cd_val is not None:
        result["type"] = "Cd"
        result["value"] = cd_val
        
        # Check against invalid codes first
        for item in rules["invalid_cd_codes"]:
            if item["code"].upper() == str(cd_val).upper():
                result["error"] = rules["errors"]["invalid_scheme"]
                result["reason"] = item["reason"]
                return result
        
        # Check against valid codes
        valid_codes = [c["code"].upper() for c in rules["valid_cd_codes"]]
        if str(cd_val).upper() in valid_codes:
            result["valid"] = True
        else:
            result["error"] = rules["errors"]["invalid_scheme"]
            
    elif prtry_val is not None:
        result["type"] = "Prtry"
        result["value"] = prtry_val
        
        if str(prtry_val).strip():
            result["valid"] = True
        else:
            result["error"] = rules["errors"]["empty_prtry"]
            
    else:
        # Neither Cd nor Prtry present (but function was called with schmeNm dict)
        result["error"] = rules["errors"]["missing_element"]
        result["value"] = str(schmeNm)

    return result

# Simple test script
if __name__ == "__main__":
    test_cases = [
        {"Cd": "LEI"},
        {"Cd": "Passport"},
        {"Prtry": "INTERNAL"},
        {"Cd": "LEI", "Prtry": "INTERNAL"},
        {"Cd": "UNKNOWN"},
        {"Prtry": ""},
        {}
    ]
    
    for tc in test_cases:
        print(f"Testing: {tc} -> {json.dumps(validateSchmeNm(tc), indent=2)}")
