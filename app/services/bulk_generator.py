"""
Bulk ISO 20022 Message Generator
Generates N valid randomized ISO 20022 messages based on selected message type and blocks.
"""
import uuid
import random
import string
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import contextvars

# Context variable to hold selected blocks for deep XML generators
selected_blocks_ctx = contextvars.ContextVar('selected_blocks', default=set())

# ── Random Data Pools ──────────────────────────────────────────────────────────
FIRST_NAMES = ["James", "Emma", "Oliver", "Sophia", "Liam", "Ava", "Noah", "Isabella",
               "Ethan", "Mia", "William", "Charlotte", "Benjamin", "Amelia", "Lucas",
               "Harper", "Mason", "Evelyn", "Logan", "Abigail", "Alexander", "Emily"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
              "Davis", "Wilson", "Martinez", "Anderson", "Taylor", "Thomas", "Jackson",
              "White", "Harris", "Martin", "Lewis", "Walker", "Hall", "Allen", "Young"]
COMPANY_NAMES = [
    "Global Trade Corp", "Alpha Finance Ltd", "Pacific Investments SA",
    "Atlantic Capital Group", "Euro Commerce AG", "Northern Bank Holdings",
    "Southern Assets Ltd", "Eastern Capital Management", "Western Finance Corp",
    "Premier Financial Services", "International Trade Solutions", "Apex Capital SA",
    "Summit Bank Holdings", "Meridian Financial Group", "Horizon Investments Ltd",
    "Pinnacle Capital Partners", "Stellar Finance Corp", "Quantum Trading AG",
]
CURRENCIES = ["USD", "EUR", "GBP", "CHF", "CAD", "AUD", "SEK", "NOK", "DKK", "JPY"]
# Countries used for PstlAdr/Ctry (any ISO country)
COUNTRIES = ["GB", "DE", "FR", "CH", "NL", "SE", "NO", "DK", "BE", "AT", "IT", "ES", "PT"]
BIC_BANK_CODES = [
    "AAAA", "BBBB", "CCCC", "DDDD", "EEEE", "FFFF", "GGGG", "HHHH", "IIII", "JJJJ",
    "KKKK", "MMMM", "NNNN", "PPPP", "QQQQ", "RRRR", "SSSS", "TTTT", "UUUU", "VVVV",
    "CITI", "HSBC", "DEUT", "BNPA", "UBSW", "CRED", "BARC", "RBOS", "LLOY", "INGB",
    "ABNA", "RABO", "TRIO", "WEST", "EAST", "NORT", "SOCY", "AGRI", "MUFG", "SMBC",
]
BIC_COUNTRIES = {
    "GB": "2L", "DE": "FF", "FR": "PP", "CH": "SS",
    "NL": "NL", "SE": "SS",
    "NO": "NO", "DK": "KK", "BE": "BB", "AT": "WW", "IT": "MM",
}
CHARGE_BEARERS = ["SHAR", "CRED", "DEBT"]
SETTLEMENT_METHODS = ["INDA", "INGA"]
RETURN_REASONS = ["AC01", "AC04", "AC06", "AG01", "AM04", "CUST", "FF01", "MD01", "MS03", "RR01"]
SERVICE_LEVELS = ["G001", "SDVA", "URGP", "NURG"]
PURPOSE_CODES = ["SALA", "SUPP", "TRAD", "CASH", "COLL", "INTC", "LOAN", "DIVD", "PENS", "OTHR"]
# Only countries that participate in IBAN scheme (ISO 13616) — US, CA, AU, JP do NOT use IBAN
IBAN_COUNTRIES_GB = ["GB", "DE", "FR", "NL", "BE", "AT", "IT", "ES", "PT", "SE", "NO", "DK"]


# ── Random Data Generators ─────────────────────────────────────────────────────

def rng_bic(country_code: Optional[str] = None) -> str:
    """Generate a random valid BIC (11 chars: BANKCCLLXXX)."""
    bank = random.choice(BIC_BANK_CODES)
    # Only use countries that exist in BIC_COUNTRIES map
    if country_code and country_code in BIC_COUNTRIES:
        cc = country_code
        loc = BIC_COUNTRIES[country_code]
    else:
        cc = random.choice(list(BIC_COUNTRIES.keys()))
        loc = BIC_COUNTRIES[cc]
    return f"{bank}{cc}{loc}XXX"


def _iban_check_digits(country: str, bban: str) -> str:
    """Compute valid IBAN check digits using ISO 13616 MOD-97-10 algorithm."""
    # Rearrange: BBAN + country + "00"
    raw = bban + country + "00"
    # Convert letters to numbers (A=10, B=11, ..., Z=35)
    numeric = ''.join(str(ord(c) - 55) if c.isalpha() else c for c in raw)
    # MOD 97 calculation
    remainder = int(numeric) % 97
    check = 98 - remainder
    return f"{check:02d}"


def rng_iban(country: Optional[str] = None) -> str:
    """Generate a random IBAN with valid MOD-97 check digits."""
    c = country or random.choice(IBAN_COUNTRIES_GB)
    # Generate country-specific BBAN, then compute valid check digits
    if c == "GB":
        bank = ''.join(random.choices(string.ascii_uppercase, k=4))
        sort = ''.join(random.choices(string.digits, k=6))
        acct = ''.join(random.choices(string.digits, k=8))
        bban = f"{bank}{sort}{acct}"
    elif c == "DE":
        bban = ''.join(random.choices(string.digits, k=18))
    elif c == "FR":
        bban = ''.join(random.choices(string.digits, k=23))
    elif c == "NL":
        bank = ''.join(random.choices(string.ascii_uppercase, k=4))
        acct = ''.join(random.choices(string.digits, k=10))
        bban = f"{bank}{acct}"
    elif c == "BE":
        bban = ''.join(random.choices(string.digits, k=12))
    elif c == "AT":
        bban = ''.join(random.choices(string.digits, k=16))
    elif c == "IT":
        check_char = random.choice(string.ascii_uppercase)
        bank = ''.join(random.choices(string.digits, k=5))
        branch = ''.join(random.choices(string.digits, k=5))
        acct = ''.join(random.choices(string.digits, k=12))
        bban = f"{check_char}{bank}{branch}{acct}"
    elif c == "ES":
        bban = ''.join(random.choices(string.digits, k=20))
    elif c == "PT":
        bban = ''.join(random.choices(string.digits, k=21))
    elif c == "SE":
        bban = ''.join(random.choices(string.digits, k=20))
    elif c == "NO":
        bban = ''.join(random.choices(string.digits, k=11))
    elif c == "DK":
        bban = ''.join(random.choices(string.digits, k=14))
    else:
        # Fallback: use GB format
        c = "GB"
        bank = ''.join(random.choices(string.ascii_uppercase, k=4))
        sort = ''.join(random.choices(string.digits, k=6))
        acct = ''.join(random.choices(string.digits, k=8))
        bban = f"{bank}{sort}{acct}"
    check = _iban_check_digits(c, bban)
    return f"{c}{check}{bban}"


def rng_amount(currency: str = "USD") -> str:
    """Generate a random valid amount string."""
    if currency == "JPY":
        return str(random.randint(10000, 9999999))
    base = random.uniform(100.0, 500000.0)
    return f"{base:.2f}"


def rng_date(offset_days: int = 0) -> str:
    """Generate a date string. Default is today; use offset_days >= 1 for future dates."""
    # For settlement dates use offset_days=1 to avoid past-date errors
    d = datetime.now(timezone.utc) + timedelta(days=max(offset_days, 0))
    return d.strftime("%Y-%m-%d")


def rng_datetime() -> str:
    """Generate a CBPR+ compliant datetime string.
    CBPR+ rules:
      - No 'Z' UTC indicator (FORBIDDEN)
      - No milliseconds (FORBIDDEN)
      - Must have explicit timezone offset like +00:00
    """
    d = datetime.now(timezone.utc)
    # Use a safe business time (e.g., 10 AM) to avoid daily cutoff errors (CUT001) during generation
    return d.strftime("%Y-%m-%dT10:00:00+00:00")


def rng_currency_and_country() -> tuple[str, str]:
    """Returns a valid (currency, country_code) pair that will pass business rules."""
    curr_map = {
        "GB": "GBP", "DE": "EUR", "FR": "EUR", "NL": "EUR", "BE": "EUR",
        "AT": "EUR", "IT": "EUR", "ES": "EUR", "PT": "EUR", "SE": "SEK",
        "NO": "NOK", "DK": "DKK", "CH": "CHF", "US": "USD", "CA": "CAD"
    }
    country = random.choice(list(curr_map.keys()))
    return curr_map[country], country


def rng_id(prefix: str = "", length: int = 16, max_total: int = 35) -> str:
    """Generate a random ID with prefix. Total length capped at max_total (default 35 for ISO 20022)."""
    chars = string.ascii_uppercase + string.digits
    # Ensure total length does not exceed max_total
    available = max(1, max_total - len(prefix))
    actual_len = min(length, available)
    return f"{prefix}{''.join(random.choices(chars, k=actual_len))}"


def rng_uetr() -> str:
    return str(uuid.uuid4())


def rng_name() -> str:
    if random.random() > 0.4:
        return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
    return random.choice(COMPANY_NAMES)


def rng_currency() -> str:
    return random.choice(CURRENCIES)


def rng_country() -> str:
    return random.choice(COUNTRIES)


# ── XML Helpers ────────────────────────────────────────────────────────────────

def xe(val: str) -> str:
    """XML-escape a string."""
    return (val or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def tabs(n: int) -> str:
    return '\t' * n


def el(tag: str, val: str, indent: int = 3) -> str:
    if not val or not str(val).strip():
        return ''
    return f"{tabs(indent)}<{tag}>{xe(str(val))}</{tag}>\n"


def tag_wrap(tag: str, content: str, indent: int = 3) -> str:
    if not content or not content.strip():
        return ''
    return f"{tabs(indent)}<{tag}>\n{content}{tabs(indent)}</{tag}>\n"


def _rng_pstl_adr(indent: int, country: str = None) -> str:
    t2 = tabs(indent)
    t3 = tabs(indent + 1)
    c = country or rng_country()
    
    xml = f"{t2}<PstlAdr>\n"
    # Include all requested fields with randomized data IN STRICT XSD ORDER:
    # StrtNm, BldgNb, BldgNm, PstCd, TwnNm, Ctry, AdrLine
    xml += f"{t3}<StrtNm>{xe(random.choice(LAST_NAMES))} Street</StrtNm>\n"
    xml += f"{t3}<BldgNb>{random.randint(1, 999)}</BldgNb>\n"
    if random.random() > 0.3:
        xml += f"{t3}<BldgNm>{xe(random.choice(COMPANY_NAMES))} Tower</BldgNm>\n"
    xml += f"{t3}<PstCd>{random.randint(10000, 99999)}</PstCd>\n"
    xml += f"{t3}<TwnNm>{xe(random.choice(LAST_NAMES))} City</TwnNm>\n"
    xml += f"{t3}<Ctry>{xe(c)}</Ctry>\n"
    xml += f"{t3}<AdrLine>{random.randint(1, 999)} {xe(random.choice(LAST_NAMES))} Ave</AdrLine>\n"
    xml += f"{t3}<AdrLine>Suite {random.randint(1, 100)}</AdrLine>\n"
    xml += f"{t2}</PstlAdr>\n"
    return xml


def agent_xml(tag: str, bic: str, indent: int = 4) -> str:
    t = tabs(indent)
    t1 = tabs(indent + 1)
    t2 = tabs(indent + 2)
    
    xml = f"{t}<{tag}>\n{t1}<FinInstnId>\n{t2}<BICFI>{xe(bic)}</BICFI>\n"
    
    # Exclude InstgAgt and InstdAgt from getting the address
    exclude_tags = {"InstgAgt", "InstdAgt"}
    
    # Randomly include Name and Address (must coexist per CBPR+)
    if tag not in exclude_tags and random.random() < 0.5:
        xml += f"{t2}<Nm>{xe(random.choice(COMPANY_NAMES))} Bank</Nm>\n"
        xml += _rng_pstl_adr(indent + 2)
        
    xml += f"{t1}</FinInstnId>\n{t}</{tag}>\n"
    return xml


def account_xml(tag: str, iban: str, indent: int = 4) -> str:
    t = tabs(indent)
    t1 = tabs(indent + 1)
    t2 = tabs(indent + 2)
    return f"{t}<{tag}>\n{t1}<Id>\n{t2}<IBAN>{xe(iban)}</IBAN>\n{t1}</Id>\n{t}</{tag}>\n"


def account_othr_xml(tag: str, acct_id: str, indent: int = 4) -> str:
    t = tabs(indent)
    t1 = tabs(indent + 1)
    t2 = tabs(indent + 2)
    t3 = tabs(indent + 3)
    return f"{t}<{tag}>\n{t1}<Id>\n{t2}<Othr>\n{t3}<Id>{xe(acct_id)}</Id>\n{t2}</Othr>\n{t1}</Id>\n{t}</{tag}>\n"


def party_xml(tag: str, name: str, country: str, indent: int = 4) -> str:
    t = tabs(indent)
    t1 = tabs(indent + 1)
    
    content = f"{t1}<Nm>{xe(name)}</Nm>\n"
    
    # Always include full address (StrtNm, BldgNb, PstCd, TwnNm, Ctry, AdrLine)
    # CBPR+ rule: If PstlAdr is used and AdrLine is absent, TwnNm + Ctry are mandatory
    content += _rng_pstl_adr(indent + 1, country)
        
    return f"{t}<{tag}>\n{content}{t}</{tag}>\n"


def apphdr_fi(bic: str) -> str:
    return f"\t\t\t<FIId>\n\t\t\t\t<FinInstnId>\n\t\t\t\t\t<BICFI>{xe(bic)}</BICFI>\n\t\t\t\t</FinInstnId>\n\t\t\t</FIId>\n"


# ── Message Block Definitions ──────────────────────────────────────────────────

MESSAGE_BLOCKS: Dict[str, List[Dict]] = {
    "pacs.008": [
        {"id": "instructing_agent",          "label": "Instructing Agent",           "mandatory": True},
        {"id": "instructed_agent",           "label": "Instructed Agent",            "mandatory": True},
        {"id": "debtor_agent",               "label": "Debtor Agent",                "mandatory": True},
        {"id": "debtor",                     "label": "Debtor",                      "mandatory": True},
        {"id": "debtor_account",             "label": "Debtor Account",              "mandatory": True,  "requires": ["debtor"]},
        {"id": "creditor_agent",             "label": "Creditor Agent",              "mandatory": True},
        {"id": "creditor",                   "label": "Creditor",                    "mandatory": True},
        {"id": "creditor_account",           "label": "Creditor Account",            "mandatory": True,  "requires": ["creditor"]},
        {"id": "previous_instructing_agent_1","label": "Previous Instructing Agent 1","mandatory": False},
        {"id": "previous_instructing_agent_2","label": "Previous Instructing Agent 2","mandatory": False, "requires": ["previous_instructing_agent_1"]},
        {"id": "previous_instructing_agent_3","label": "Previous Instructing Agent 3","mandatory": False, "requires": ["previous_instructing_agent_2"]},
        {"id": "intermediary_agent_1",       "label": "Intermediary Agent 1",        "mandatory": False},
        {"id": "intermediary_agent_1_account","label": "Intermediary Agent 1 Account","mandatory": False, "requires": ["intermediary_agent_1"]},
        {"id": "intermediary_agent_2",       "label": "Intermediary Agent 2",        "mandatory": False, "requires": ["intermediary_agent_1"]},
        {"id": "intermediary_agent_2_account","label": "Intermediary Agent 2 Account","mandatory": False, "requires": ["intermediary_agent_2"]},
        {"id": "intermediary_agent_3",       "label": "Intermediary Agent 3",        "mandatory": False, "requires": ["intermediary_agent_2"]},
        {"id": "intermediary_agent_3_account","label": "Intermediary Agent 3 Account","mandatory": False, "requires": ["intermediary_agent_3"]},
        {"id": "debtor_agent_account",       "label": "Debtor Agent Account",        "mandatory": False, "requires": ["debtor_agent"]},
        {"id": "creditor_agent_account",     "label": "Creditor Agent Account",      "mandatory": False, "requires": ["creditor_agent"]},
        {"id": "ultimate_debtor",            "label": "Ultimate Debtor",             "mandatory": False},
        {"id": "ultimate_creditor",          "label": "Ultimate Creditor",           "mandatory": False},
        {"id": "payment_type_information",   "label": "Payment Type Information",    "mandatory": False},
        {"id": "remittance_information",     "label": "Remittance Information",      "mandatory": False},
        {"id": "charges_information",        "label": "Charges Information",         "mandatory": False},
        {"id": "settlement_time_request",    "label": "Settlement Time Request",     "mandatory": False},
    ],
    "pacs.009": [
        {"id": "instructing_agent",          "label": "Instructing Agent",           "mandatory": True},
        {"id": "instructed_agent",           "label": "Instructed Agent",            "mandatory": True},
        {"id": "debtor",                     "label": "Debtor (FI)",                 "mandatory": True},
        {"id": "debtor_account",             "label": "Debtor Account",              "mandatory": False},
        {"id": "debtor_agent",               "label": "Debtor Agent",                "mandatory": False},
        {"id": "debtor_agent_account",       "label": "Debtor Agent Account",        "mandatory": False, "requires": ["debtor_agent"]},
        {"id": "creditor_agent",             "label": "Creditor Agent",              "mandatory": False},
        {"id": "creditor_agent_account",     "label": "Creditor Agent Account",      "mandatory": False, "requires": ["creditor_agent"]},
        {"id": "creditor",                   "label": "Creditor (FI)",               "mandatory": True},
        {"id": "creditor_account",           "label": "Creditor Account",            "mandatory": False},
        {"id": "previous_instructing_agent_1","label": "Previous Instructing Agent 1","mandatory": False},
        {"id": "previous_instructing_agent_2","label": "Previous Instructing Agent 2","mandatory": False, "requires": ["previous_instructing_agent_1"]},
        {"id": "previous_instructing_agent_3","label": "Previous Instructing Agent 3","mandatory": False, "requires": ["previous_instructing_agent_2"]},
        {"id": "intermediary_agent_1",       "label": "Intermediary Agent 1",        "mandatory": False},
        {"id": "intermediary_agent_1_account","label": "Intermediary Agent 1 Account","mandatory": False, "requires": ["intermediary_agent_1"]},
        {"id": "intermediary_agent_2",       "label": "Intermediary Agent 2",        "mandatory": False, "requires": ["intermediary_agent_1"]},
        {"id": "intermediary_agent_2_account","label": "Intermediary Agent 2 Account","mandatory": False, "requires": ["intermediary_agent_2"]},
        {"id": "intermediary_agent_3",       "label": "Intermediary Agent 3",        "mandatory": False, "requires": ["intermediary_agent_2"]},
        {"id": "intermediary_agent_3_account","label": "Intermediary Agent 3 Account","mandatory": False, "requires": ["intermediary_agent_3"]},
        {"id": "payment_type_information",   "label": "Payment Type Information",    "mandatory": False},
        {"id": "remittance_information",     "label": "Remittance Information",      "mandatory": False},
        {"id": "settlement_time_request",    "label": "Settlement Time Request",     "mandatory": False},
    ],
    "pacs.009.adv": [
        {"id": "instructing_agent",          "label": "Instructing Agent",           "mandatory": True},
        {"id": "instructed_agent",           "label": "Instructed Agent",            "mandatory": True},
        {"id": "debtor",                     "label": "Debtor (FI)",                 "mandatory": True},
        {"id": "debtor_account",             "label": "Debtor Account",              "mandatory": False},
        {"id": "debtor_agent",               "label": "Debtor Agent",                "mandatory": False},
        {"id": "debtor_agent_account",       "label": "Debtor Agent Account",        "mandatory": False, "requires": ["debtor_agent"]},
        {"id": "creditor_agent",             "label": "Creditor Agent",              "mandatory": False},
        {"id": "creditor_agent_account",     "label": "Creditor Agent Account",      "mandatory": False, "requires": ["creditor_agent"]},
        {"id": "creditor",                   "label": "Creditor (FI)",               "mandatory": True},
        {"id": "creditor_account",           "label": "Creditor Account",            "mandatory": False},
        {"id": "previous_instructing_agent_1","label": "Previous Instructing Agent 1","mandatory": False},
        {"id": "previous_instructing_agent_2","label": "Previous Instructing Agent 2","mandatory": False, "requires": ["previous_instructing_agent_1"]},
        {"id": "previous_instructing_agent_3","label": "Previous Instructing Agent 3","mandatory": False, "requires": ["previous_instructing_agent_2"]},
        {"id": "intermediary_agent_1",       "label": "Intermediary Agent 1",        "mandatory": False},
        {"id": "intermediary_agent_1_account","label": "Intermediary Agent 1 Account","mandatory": False, "requires": ["intermediary_agent_1"]},
        {"id": "intermediary_agent_2",       "label": "Intermediary Agent 2",        "mandatory": False, "requires": ["intermediary_agent_1"]},
        {"id": "intermediary_agent_2_account","label": "Intermediary Agent 2 Account","mandatory": False, "requires": ["intermediary_agent_2"]},
        {"id": "intermediary_agent_3",       "label": "Intermediary Agent 3",        "mandatory": False, "requires": ["intermediary_agent_2"]},
        {"id": "intermediary_agent_3_account","label": "Intermediary Agent 3 Account","mandatory": False, "requires": ["intermediary_agent_3"]},
        {"id": "payment_type_information",   "label": "Payment Type Information",    "mandatory": False},
        {"id": "remittance_information",     "label": "Remittance Information",      "mandatory": False},
        {"id": "settlement_time_request",    "label": "Settlement Time Request",     "mandatory": False},
    ],
    "pacs.009.cov": [
        {"id": "instructing_agent",          "label": "Instructing Agent",           "mandatory": True},
        {"id": "instructed_agent",           "label": "Instructed Agent",            "mandatory": True},
        {"id": "debtor",                     "label": "Debtor (FI)",                 "mandatory": True},
        {"id": "debtor_account",             "label": "Debtor Account",              "mandatory": False},
        {"id": "debtor_agent",               "label": "Debtor Agent",                "mandatory": False},
        {"id": "debtor_agent_account",       "label": "Debtor Agent Account",        "mandatory": False, "requires": ["debtor_agent"]},
        {"id": "creditor_agent",             "label": "Creditor Agent",              "mandatory": False},
        {"id": "creditor_agent_account",     "label": "Creditor Agent Account",      "mandatory": False, "requires": ["creditor_agent"]},
        {"id": "creditor",                   "label": "Creditor (FI)",               "mandatory": True},
        {"id": "creditor_account",           "label": "Creditor Account",            "mandatory": False},
        {"id": "previous_instructing_agent_1","label": "Previous Instructing Agent 1","mandatory": False},
        {"id": "intermediary_agent_1",       "label": "Intermediary Agent 1",        "mandatory": False},
        {"id": "intermediary_agent_1_account","label": "Intermediary Agent 1 Account","mandatory": False, "requires": ["intermediary_agent_1"]},
        {"id": "intermediary_agent_2",       "label": "Intermediary Agent 2",        "mandatory": False, "requires": ["intermediary_agent_1"]},
        {"id": "intermediary_agent_2_account","label": "Intermediary Agent 2 Account","mandatory": False, "requires": ["intermediary_agent_2"]},
        {"id": "intermediary_agent_3",       "label": "Intermediary Agent 3",        "mandatory": False, "requires": ["intermediary_agent_2"]},
        {"id": "underlying_customer_credit_transfer", "label": "Underlying Customer Credit Transfer (COV)", "mandatory": True},
        {"id": "payment_type_information",   "label": "Payment Type Information",    "mandatory": False},
        {"id": "remittance_information",     "label": "Remittance Information",      "mandatory": False},
    ],
    "pacs.004": [
        {"id": "instructing_agent",          "label": "Instructing Agent",           "mandatory": True},
        {"id": "instructed_agent",           "label": "Instructed Agent",            "mandatory": True},
        {"id": "debtor_agent",               "label": "Return Debtor Agent",         "mandatory": True},
        {"id": "debtor",                     "label": "Return Debtor",               "mandatory": True},
        {"id": "debtor_account",             "label": "Return Debtor Account",       "mandatory": False, "requires": ["debtor"]},
        {"id": "creditor_agent",             "label": "Return Creditor Agent",       "mandatory": True},
        {"id": "creditor",                   "label": "Return Creditor",             "mandatory": True},
        {"id": "creditor_account",           "label": "Return Creditor Account",     "mandatory": False, "requires": ["creditor"]},
        {"id": "intermediary_agent_1",       "label": "Intermediary Agent 1",        "mandatory": False},
        {"id": "ultimate_debtor",            "label": "Ultimate Debtor",             "mandatory": False},
        {"id": "ultimate_creditor",          "label": "Ultimate Creditor",           "mandatory": False},
        {"id": "charges_information",        "label": "Charges Information",         "mandatory": False},
        {"id": "remittance_information",     "label": "Remittance Information",      "mandatory": False},
    ],
    "pacs.003": [
        {"id": "instructing_agent",          "label": "Instructing Agent",           "mandatory": True},
        {"id": "instructed_agent",           "label": "Instructed Agent",            "mandatory": True},
        {"id": "debtor_agent",               "label": "Debtor Agent",                "mandatory": True},
        {"id": "debtor",                     "label": "Debtor",                      "mandatory": True},
        {"id": "debtor_account",             "label": "Debtor Account",              "mandatory": True,  "requires": ["debtor"]},
        {"id": "creditor_agent",             "label": "Creditor Agent",              "mandatory": True},
        {"id": "creditor",                   "label": "Creditor",                    "mandatory": True},
        {"id": "creditor_account",           "label": "Creditor Account",            "mandatory": True,  "requires": ["creditor"]},
        {"id": "creditor_agent_account",     "label": "Creditor Agent Account",      "mandatory": False, "requires": ["creditor_agent"]},
        {"id": "ultimate_debtor",            "label": "Ultimate Debtor",             "mandatory": False},
        {"id": "ultimate_creditor",          "label": "Ultimate Creditor",           "mandatory": False},
        {"id": "payment_type_information",   "label": "Payment Type Information",    "mandatory": False},
        {"id": "remittance_information",     "label": "Remittance Information",      "mandatory": False},
        {"id": "charges_information",        "label": "Charges Information",         "mandatory": False},
    ],
    "pacs.002": [
        {"id": "instructing_agent",          "label": "Instructing Agent",           "mandatory": True},
        {"id": "instructed_agent",           "label": "Instructed Agent",            "mandatory": True},
        {"id": "debtor",                     "label": "Debtor",                      "mandatory": False},
        {"id": "creditor",                   "label": "Creditor",                    "mandatory": False},
        {"id": "charges_information",        "label": "Charges Information",         "mandatory": False},
    ],
    "pacs.010": [
        {"id": "instructing_agent",          "label": "Instructing Agent",           "mandatory": True},
        {"id": "instructed_agent",           "label": "Instructed Agent",            "mandatory": True},
        {"id": "debtor_agent",               "label": "Debtor Agent",                "mandatory": True},
        {"id": "debtor",                     "label": "Debtor",                      "mandatory": True},
        {"id": "debtor_account",             "label": "Debtor Account",              "mandatory": True,  "requires": ["debtor"]},
        {"id": "creditor_agent",             "label": "Creditor Agent",              "mandatory": False},
        {"id": "creditor",                   "label": "Creditor",                    "mandatory": False},
        {"id": "creditor_account",           "label": "Creditor Account",            "mandatory": False, "requires": ["creditor"]},
        {"id": "payment_type_information",   "label": "Payment Type Information",    "mandatory": False},
        {"id": "remittance_information",     "label": "Remittance Information",      "mandatory": False},
    ],
    "pacs.010.v3": [
        {"id": "instructing_agent",          "label": "Instructing Agent",           "mandatory": True},
        {"id": "instructed_agent",           "label": "Instructed Agent",            "mandatory": True},
        {"id": "debtor_agent",               "label": "Debtor Agent",                "mandatory": True},
        {"id": "debtor",                     "label": "Debtor",                      "mandatory": True},
        {"id": "debtor_account",             "label": "Debtor Account",              "mandatory": True,  "requires": ["debtor"]},
        {"id": "creditor_agent",             "label": "Creditor Agent",              "mandatory": False},
        {"id": "creditor",                   "label": "Creditor",                    "mandatory": False},
        {"id": "creditor_account",           "label": "Creditor Account",            "mandatory": False, "requires": ["creditor"]},
        {"id": "remittance_information",     "label": "Remittance Information",      "mandatory": False},
    ],

    # ── CAMT Messages ──────────────────────────────────────────────────────────
    "camt.057": [
        {"id": "group_header",              "label": "Group Header",                "mandatory": True},
        {"id": "debtor",                    "label": "Debtor",                      "mandatory": True},
        {"id": "debtor_account",            "label": "Debtor Account",              "mandatory": True,  "requires": ["debtor"]},
        {"id": "debtor_agent",              "label": "Debtor Agent",                "mandatory": True},
        {"id": "creditor",                  "label": "Creditor",                    "mandatory": False},
        {"id": "creditor_account",          "label": "Creditor Account",            "mandatory": False, "requires": ["creditor"]},
        {"id": "creditor_agent",            "label": "Creditor Agent",              "mandatory": False},
        {"id": "intermediary_agent_1",      "label": "Intermediary Agent 1",        "mandatory": False},
    ],
    "camt.052": [
        {"id": "group_header",              "label": "Group Header",                "mandatory": True},
        {"id": "account_identification",    "label": "Account Identification",      "mandatory": True},
        {"id": "account_owner",             "label": "Account Owner",               "mandatory": False},
        {"id": "account_servicer",          "label": "Account Servicer",            "mandatory": False},
        {"id": "balance",                   "label": "Balance",                     "mandatory": True},
        {"id": "transaction_summary",       "label": "Transaction Summary",         "mandatory": False},
        {"id": "entry",                     "label": "Entry Details",               "mandatory": False},
    ],
    "camt.053": [
        {"id": "group_header",              "label": "Group Header",                "mandatory": True},
        {"id": "account_identification",    "label": "Account Identification",      "mandatory": True},
        {"id": "account_owner",             "label": "Account Owner",               "mandatory": False},
        {"id": "account_servicer",          "label": "Account Servicer",            "mandatory": False},
        {"id": "balance",                   "label": "Balance",                     "mandatory": True},
        {"id": "transaction_summary",       "label": "Transaction Summary",         "mandatory": False},
        {"id": "entry",                     "label": "Entry Details",               "mandatory": False},
    ],
    "camt.054": [
        {"id": "group_header",              "label": "Group Header",                "mandatory": True},
        {"id": "account_identification",    "label": "Account Identification",      "mandatory": True},
        {"id": "account_owner",             "label": "Account Owner",               "mandatory": False},
        {"id": "account_servicer",          "label": "Account Servicer",            "mandatory": False},
        {"id": "entry",                     "label": "Entry Details",               "mandatory": True},
    ],
    "camt.055": [
        {"id": "group_header",              "label": "Group Header (Assignment)",   "mandatory": True},
        {"id": "original_group_information","label": "Original Group Information",  "mandatory": True},
        {"id": "original_payment_information","label": "Original Payment Info",     "mandatory": True},
        {"id": "cancellation_reason",       "label": "Cancellation Reason",         "mandatory": False},
        {"id": "original_transaction",      "label": "Original Transaction Info",   "mandatory": False},
    ],
    "camt.056": [
        {"id": "group_header",              "label": "Group Header (Assignment)",   "mandatory": True},
        {"id": "original_group_information","label": "Original Group Information",  "mandatory": True},
        {"id": "transaction_information",   "label": "Transaction Information",     "mandatory": True},
        {"id": "cancellation_reason",       "label": "Cancellation Reason",         "mandatory": False},
        {"id": "original_transaction",      "label": "Original Transaction Info",   "mandatory": False},
    ],

    # ── PAIN Messages ──────────────────────────────────────────────────────────
    "pain.001": [
        {"id": "group_header",              "label": "Group Header",                "mandatory": True},
        {"id": "initiating_party",          "label": "Initiating Party",            "mandatory": True},
        {"id": "debtor",                    "label": "Debtor",                      "mandatory": True},
        {"id": "debtor_account",            "label": "Debtor Account",              "mandatory": True,  "requires": ["debtor"]},
        {"id": "debtor_agent",              "label": "Debtor Agent",                "mandatory": True},
        {"id": "creditor",                  "label": "Creditor",                    "mandatory": True},
        {"id": "creditor_account",          "label": "Creditor Account",            "mandatory": True,  "requires": ["creditor"]},
        {"id": "creditor_agent",            "label": "Creditor Agent",              "mandatory": False},
        {"id": "ultimate_debtor",           "label": "Ultimate Debtor",             "mandatory": False},
        {"id": "ultimate_creditor",         "label": "Ultimate Creditor",           "mandatory": False},
        {"id": "payment_type_information",  "label": "Payment Type Information",    "mandatory": False},
        {"id": "remittance_information",    "label": "Remittance Information",      "mandatory": False},
    ],
    "pain.002": [
        {"id": "group_header",              "label": "Group Header",                "mandatory": True},
        {"id": "original_group_information","label": "Original Group Information",  "mandatory": True},
        {"id": "original_payment_information","label": "Original Payment Info",     "mandatory": False},
        {"id": "status_reason",             "label": "Status Reason Information",   "mandatory": False},
        {"id": "original_transaction",      "label": "Original Transaction Info",   "mandatory": False},
    ],
    "pain.008": [
        {"id": "group_header",              "label": "Group Header",                "mandatory": True},
        {"id": "initiating_party",          "label": "Initiating Party",            "mandatory": True},
        {"id": "creditor",                  "label": "Creditor",                    "mandatory": True},
        {"id": "creditor_account",          "label": "Creditor Account",            "mandatory": True,  "requires": ["creditor"]},
        {"id": "creditor_agent",            "label": "Creditor Agent",              "mandatory": True},
        {"id": "debtor",                    "label": "Debtor",                      "mandatory": True},
        {"id": "debtor_account",            "label": "Debtor Account",              "mandatory": True,  "requires": ["debtor"]},
        {"id": "debtor_agent",              "label": "Debtor Agent",                "mandatory": False},
        {"id": "ultimate_creditor",         "label": "Ultimate Creditor",           "mandatory": False},
        {"id": "ultimate_debtor",           "label": "Ultimate Debtor",             "mandatory": False},
        {"id": "payment_type_information",  "label": "Payment Type Information",    "mandatory": False},
        {"id": "remittance_information",    "label": "Remittance Information",      "mandatory": False},
    ],
}


def get_blocks_for_message(msg_type: str) -> List[Dict]:
    key = msg_type.lower().replace(" ", ".").replace("pacs.009.001.08 cov", "pacs.009.cov").replace("pacs.009cov", "pacs.009.cov")
    # Normalise
    if "pacs.008" in key:
        return MESSAGE_BLOCKS["pacs.008"]
    if "pacs.009" in key and "cov" in key:
        return MESSAGE_BLOCKS["pacs.009.cov"]
    if "pacs.009" in key and "adv" in key:
        return MESSAGE_BLOCKS["pacs.009.adv"]
    if "pacs.009" in key:
        return MESSAGE_BLOCKS["pacs.009"]
    if "pacs.004" in key:
        return MESSAGE_BLOCKS["pacs.004"]
    if "pacs.003" in key:
        return MESSAGE_BLOCKS["pacs.003"]
    if "pacs.002" in key:
        return MESSAGE_BLOCKS["pacs.002"]
    if "pacs.010" in key and ("001.03" in key or "v3" in key):
        return MESSAGE_BLOCKS["pacs.010.v3"]
    if "pacs.010" in key:
        return MESSAGE_BLOCKS["pacs.010"]
    # CAMT messages
    if "camt.057" in key:
        return MESSAGE_BLOCKS["camt.057"]
    if "camt.052" in key:
        return MESSAGE_BLOCKS["camt.052"]
    if "camt.053" in key:
        return MESSAGE_BLOCKS["camt.053"]
    if "camt.054" in key:
        return MESSAGE_BLOCKS["camt.054"]
    if "camt.055" in key:
        return MESSAGE_BLOCKS["camt.055"]
    if "camt.056" in key:
        return MESSAGE_BLOCKS["camt.056"]
    # PAIN messages
    if "pain.001" in key:
        return MESSAGE_BLOCKS["pain.001"]
    if "pain.002" in key:
        return MESSAGE_BLOCKS["pain.002"]
    if "pain.008" in key:
        return MESSAGE_BLOCKS["pain.008"]
    return MESSAGE_BLOCKS.get("pacs.008", [])


# ── Pacs.008 Generator ─────────────────────────────────────────────────────────

def _gen_pacs008(selected: set, idx: int) -> str:
    ccy, iban_country = rng_currency_and_country()
    from_bic = rng_bic("GB")
    to_bic = rng_bic("GB")
    biz_msg_id = rng_id("BIZ", 16)
    msg_id = rng_id("MSG", 16)
    instr_id = rng_id("INSTR", 11)
    e2e_id = rng_id("E2E", 16)
    tx_id = rng_id("TX", 16)
    uetr = rng_uetr()
    cre_dt = rng_datetime()
    sttlm_dt = rng_date(1)
    sttlm_mtd = random.choice(SETTLEMENT_METHODS)
    charge_br = random.choice(CHARGE_BEARERS)
    amount = rng_amount(ccy)

    # Party data
    debtor_name = rng_name()
    creditor_name = rng_name()
    debtor_ctry = iban_country
    creditor_ctry = iban_country
    debtor_iban = rng_iban(iban_country)
    creditor_iban = rng_iban(iban_country)
    debtor_bic = rng_bic(iban_country)
    creditor_bic = rng_bic(iban_country)
    instg_bic = from_bic
    instd_bic = to_bic

    # Transaction XML — elements MUST follow strict XSD CreditTransferTransaction39 sequence
    tx = ""

    # 1. PmtTpInf (optional)
    if "payment_type_information" in selected:
        svc = random.choice(SERVICE_LEVELS)
        tx += f"\t\t\t\t<PmtTpInf>\n\t\t\t\t\t<SvcLvl>\n\t\t\t\t\t\t<Cd>{svc}</Cd>\n\t\t\t\t\t</SvcLvl>\n\t\t\t\t</PmtTpInf>\n"

    # 2. IntrBkSttlmAmt (mandatory)
    tx += f"\t\t\t\t<IntrBkSttlmAmt Ccy=\"{xe(ccy)}\">{amount}</IntrBkSttlmAmt>\n"

    # 3. IntrBkSttlmDt
    tx += el("IntrBkSttlmDt", sttlm_dt, 4)

    # 4. SttlmTmReq (optional) — must come BEFORE InstdAmt per XSD
    if "settlement_time_request" in selected:
        tx += f"\t\t\t\t<SttlmTmReq>\n\t\t\t\t\t<CLSTm>14:00:00+00:00</CLSTm>\n\t\t\t\t</SttlmTmReq>\n"

    # 4b. InstdAmt — MANDATORY when ChrgsInf is present (CBPR+ rule)
    if "charges_information" in selected:
        instd_amt = rng_amount(ccy)
        tx += f"\t\t\t\t<InstdAmt Ccy=\"{xe(ccy)}\">{instd_amt}</InstdAmt>\n"

    # 5. ChrgBr (MANDATORY in pacs.008) — exclude SHAR/SLEV per business rules
    charge_br = random.choice(["CRED", "DEBT"])
    tx += el("ChrgBr", charge_br, 4)

    # 6. ChrgsInf (optional)
    if "charges_information" in selected:
        chg_ccy = ccy
        chg_amt = rng_amount(chg_ccy)
        chg_bic = rng_bic()
        tx += (f"\t\t\t\t<ChrgsInf>\n"
               f"\t\t\t\t\t<Amt Ccy=\"{xe(chg_ccy)}\">{chg_amt}</Amt>\n"
               f"\t\t\t\t\t<Agt>\n\t\t\t\t\t\t<FinInstnId>\n\t\t\t\t\t\t\t<BICFI>{xe(chg_bic)}</BICFI>\n"
               f"\t\t\t\t\t\t</FinInstnId>\n\t\t\t\t\t</Agt>\n\t\t\t\t</ChrgsInf>\n")

    # 7. PrvsInstgAgt1/2/3 (optional)
    if "previous_instructing_agent_1" in selected:
        tx += agent_xml("PrvsInstgAgt1", rng_bic(), 4)
    if "previous_instructing_agent_2" in selected:
        tx += agent_xml("PrvsInstgAgt2", rng_bic(), 4)
    if "previous_instructing_agent_3" in selected:
        tx += agent_xml("PrvsInstgAgt3", rng_bic(), 4)

    # 8. InstgAgt / InstdAgt (in CdtTrfTxInf per XSD v13 CreditTransferTransaction70)
    if "instructing_agent" in selected:
        tx += agent_xml("InstgAgt", instg_bic, 4)
    if "instructed_agent" in selected:
        tx += agent_xml("InstdAgt", instd_bic, 4)

    # 9. IntrmyAgt1/2/3 (optional)
    if "intermediary_agent_1" in selected:
        intr1_bic = rng_bic()
        tx += agent_xml("IntrmyAgt1", intr1_bic, 4)
        if "intermediary_agent_1_account" in selected:
            tx += account_othr_xml("IntrmyAgt1Acct", rng_id("ACCT", 10), 4)
    if "intermediary_agent_2" in selected:
        intr2_bic = rng_bic()
        tx += agent_xml("IntrmyAgt2", intr2_bic, 4)
        if "intermediary_agent_2_account" in selected:
            tx += account_othr_xml("IntrmyAgt2Acct", rng_id("ACCT", 10), 4)
    if "intermediary_agent_3" in selected:
        intr3_bic = rng_bic()
        tx += agent_xml("IntrmyAgt3", intr3_bic, 4)
        if "intermediary_agent_3_account" in selected:
            tx += account_othr_xml("IntrmyAgt3Acct", rng_id("ACCT", 10), 4)

    # 10. UltmtDbtr (optional)
    if "ultimate_debtor" in selected:
        tx += party_xml("UltmtDbtr", rng_name(), rng_country(), 4)

    # 11. Dbtr (mandatory)
    tx += party_xml("Dbtr", debtor_name, debtor_ctry, 4)

    # 12. DbtrAcct (mandatory)
    tx += account_xml("DbtrAcct", debtor_iban, 4)

    # 13. DbtrAgt (mandatory)
    tx += agent_xml("DbtrAgt", debtor_bic, 4)
    if "debtor_agent_account" in selected:
        tx += account_othr_xml("DbtrAgtAcct", rng_id("ACCT", 10), 4)

    # 14. CdtrAgt (mandatory)
    tx += agent_xml("CdtrAgt", creditor_bic, 4)
    if "creditor_agent_account" in selected:
        tx += account_othr_xml("CdtrAgtAcct", rng_id("ACCT", 10), 4)

    # 15. Cdtr (mandatory)
    tx += party_xml("Cdtr", creditor_name, creditor_ctry, 4)

    # 16. CdtrAcct (mandatory)
    tx += account_xml("CdtrAcct", creditor_iban, 4)

    # 17. UltmtCdtr (optional)
    if "ultimate_creditor" in selected:
        tx += party_xml("UltmtCdtr", rng_name(), rng_country(), 4)

    # 18. RmtInf (optional)
    if "remittance_information" in selected:
        rmt_ref = rng_id("REF", 16)
        tx += f"\t\t\t\t<RmtInf>\n\t\t\t\t\t<Ustrd>{xe(rmt_ref)}</Ustrd>\n\t\t\t\t</RmtInf>\n"

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<BusMsgEnvlp xmlns="urn:swift:xsd:envelope">
\t<AppHdr xmlns="urn:iso:std:iso:20022:tech:xsd:head.001.001.02">
\t\t<Fr>
{apphdr_fi(from_bic)}\t\t</Fr>
\t\t<To>
{apphdr_fi(to_bic)}\t\t</To>
\t\t<BizMsgIdr>{xe(biz_msg_id)}</BizMsgIdr>
\t\t<MsgDefIdr>pacs.008.001.08</MsgDefIdr>
\t\t<BizSvc>swift.cbprplus.02</BizSvc>
\t\t<CreDt>{cre_dt}</CreDt>
\t</AppHdr>
\t<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
\t\t<FIToFICstmrCdtTrf>
\t\t\t<GrpHdr>
\t\t\t\t<MsgId>{xe(msg_id)}</MsgId>
\t\t\t\t<CreDtTm>{cre_dt}</CreDtTm>
\t\t\t\t<NbOfTxs>1</NbOfTxs>
\t\t\t\t<SttlmInf>
\t\t\t\t\t<SttlmMtd>{xe(sttlm_mtd)}</SttlmMtd>
\t\t\t\t</SttlmInf>
\t\t\t</GrpHdr>
\t\t\t<CdtTrfTxInf>
\t\t\t\t<PmtId>
\t\t\t\t\t<InstrId>{xe(instr_id)}</InstrId>
\t\t\t\t\t<EndToEndId>{xe(e2e_id)}</EndToEndId>
\t\t\t\t\t<TxId>{xe(tx_id)}</TxId>
\t\t\t\t\t<UETR>{xe(uetr)}</UETR>
\t\t\t\t</PmtId>
{tx}\t\t\t</CdtTrfTxInf>
\t\t</FIToFICstmrCdtTrf>
\t</Document>
</BusMsgEnvlp>"""
    return xml


# ── Pacs.009 Generator ─────────────────────────────────────────────────────────

def _gen_pacs009(selected: set, idx: int, is_cov: bool = False, is_adv: bool = False) -> str:
    """Generate pacs.009.001.08 (FI Credit Transfer).

    v12 schema differences vs v08:
      - Root element: FICdtTrf  (was FinInstnCdtTrf)
      - Namespace:    pacs.009.001.08
      - Dbtr / Cdtr:  MANDATORY, type BranchAndFinancialInstitutionIdentification8
      - UltmtDbtr / UltmtCdtr: also BranchAndFinancialInstitutionIdentification8
      - ChrgsInf:     does NOT exist in CreditTransferTransaction67
    """
    ccy, country = rng_currency_and_country()
    from_bic = rng_bic("GB")
    to_bic = rng_bic("GB")
    biz_msg_id = rng_id("BIZ", 16)
    msg_id = rng_id("MSG", 16)
    instr_id = rng_id("INSTR", 11)
    e2e_id = rng_id("E2E", 16)
    tx_id = rng_id("TX", 16)
    uetr = rng_uetr()
    cre_dt = rng_datetime()
    sttlm_dt = rng_date(1)
    sttlm_mtd = random.choice(SETTLEMENT_METHODS)
    amount = rng_amount(ccy)

    instg_bic = from_bic
    instd_bic = to_bic

    # Generate BICs for mandatory Dbtr and Cdtr (FI-type in v12)
    debtor_bic = rng_bic()
    creditor_bic = rng_bic()

    tx = ""

    # ── Element order must match XSD CreditTransferTransaction67 sequence ──

    # 1. PmtTpInf (optional)
    if "payment_type_information" in selected or is_adv:
        svc = random.choice(SERVICE_LEVELS)
        tx += "\t\t\t\t<PmtTpInf>\n"
        if "payment_type_information" in selected:
            tx += f"\t\t\t\t\t<SvcLvl>\n\t\t\t\t\t\t<Cd>{svc}</Cd>\n\t\t\t\t\t</SvcLvl>\n"
        if is_adv:
            tx += "\t\t\t\t\t<LclInstrm>\n\t\t\t\t\t\t<Prtry>ADV</Prtry>\n\t\t\t\t\t</LclInstrm>\n"
        tx += "\t\t\t\t</PmtTpInf>\n"

    # 2. IntrBkSttlmAmt (mandatory)
    tx += f"\t\t\t\t<IntrBkSttlmAmt Ccy=\"{xe(ccy)}\">{amount}</IntrBkSttlmAmt>\n"
    # 3. IntrBkSttlmDt (optional)
    tx += el("IntrBkSttlmDt", sttlm_dt, 4)

    # 4. SttlmTmReq (optional)
    if "settlement_time_request" in selected:
        tx += f"\t\t\t\t<SttlmTmReq>\n\t\t\t\t\t<CLSTm>14:00:00+00:00</CLSTm>\n\t\t\t\t</SttlmTmReq>\n"

    # 5. PrvsInstgAgt1/2/3 (optional)
    if "previous_instructing_agent_1" in selected:
        tx += agent_xml("PrvsInstgAgt1", rng_bic(), 4)
    if "previous_instructing_agent_2" in selected:
        tx += agent_xml("PrvsInstgAgt2", rng_bic(), 4)
    if "previous_instructing_agent_3" in selected:
        tx += agent_xml("PrvsInstgAgt3", rng_bic(), 4)

    # 6. InstgAgt / InstdAgt (optional)
    if "instructing_agent" in selected:
        tx += agent_xml("InstgAgt", instg_bic, 4)
    if "instructed_agent" in selected:
        tx += agent_xml("InstdAgt", instd_bic, 4)

    # 7. IntrmyAgt1/2/3 (optional)
    if "intermediary_agent_1" in selected:
        tx += agent_xml("IntrmyAgt1", rng_bic(), 4)
        if "intermediary_agent_1_account" in selected:
            tx += account_othr_xml("IntrmyAgt1Acct", rng_id("ACCT", 10), 4)
    if "intermediary_agent_2" in selected:
        tx += agent_xml("IntrmyAgt2", rng_bic(), 4)
        if "intermediary_agent_2_account" in selected:
            tx += account_othr_xml("IntrmyAgt2Acct", rng_id("ACCT", 10), 4)
    if "intermediary_agent_3" in selected:
        tx += agent_xml("IntrmyAgt3", rng_bic(), 4)
        if "intermediary_agent_3_account" in selected:
            tx += account_othr_xml("IntrmyAgt3Acct", rng_id("ACCT", 10), 4)

    # 9. Dbtr — MANDATORY in v12, FI type (BranchAndFinancialInstitutionIdentification8)
    tx += agent_xml("Dbtr", debtor_bic, 4)

    # 10. DbtrAcct (optional)
    if "debtor_account" in selected:
        tx += account_xml("DbtrAcct", rng_iban(country), 4)
    # 11. DbtrAgt (optional)
    if "debtor_agent" in selected:
        tx += agent_xml("DbtrAgt", rng_bic(), 4)
    if "debtor_agent_account" in selected:
        tx += account_othr_xml("DbtrAgtAcct", rng_id("ACCT", 10), 4)

    # 12. CdtrAgt (optional)
    if "creditor_agent" in selected:
        tx += agent_xml("CdtrAgt", rng_bic(), 4)
    if "creditor_agent_account" in selected:
        tx += account_othr_xml("CdtrAgtAcct", rng_id("ACCT", 10), 4)

    # 13. Cdtr — MANDATORY in v12, FI type (BranchAndFinancialInstitutionIdentification8)
    tx += agent_xml("Cdtr", creditor_bic, 4)

    # 14. CdtrAcct (optional)
    if "creditor_account" in selected:
        tx += account_xml("CdtrAcct", rng_iban(country), 4)

    # 16. RmtInf (optional)
    if "remittance_information" in selected:
        tx += f"\t\t\t\t<RmtInf>\n\t\t\t\t\t<Ustrd>{xe(rng_id('REF', 16))}</Ustrd>\n\t\t\t\t</RmtInf>\n"

    # 17. UndrlygCstmrCdtTrf — COV only
    if is_cov and "underlying_customer_credit_transfer" in selected:
        cov_dbtr = rng_name()
        cov_cdtr = rng_name()
        cov_dbtr_iban = rng_iban()
        cov_cdtr_iban = rng_iban()
        cov_dbtr_bic = rng_bic()
        cov_cdtr_bic = rng_bic()
        tx += f"""\t\t\t\t<UndrlygCstmrCdtTrf>
\t\t\t\t\t<Dbtr><Nm>{xe(cov_dbtr)}</Nm><PstlAdr><Ctry>{rng_country()}</Ctry></PstlAdr></Dbtr>
\t\t\t\t\t<DbtrAcct><Id><IBAN>{xe(cov_dbtr_iban)}</IBAN></Id></DbtrAcct>
\t\t\t\t\t<DbtrAgt><FinInstnId><BICFI>{xe(cov_dbtr_bic)}</BICFI></FinInstnId></DbtrAgt>
\t\t\t\t\t<CdtrAgt><FinInstnId><BICFI>{xe(cov_cdtr_bic)}</BICFI></FinInstnId></CdtrAgt>
\t\t\t\t\t<Cdtr><Nm>{xe(cov_cdtr)}</Nm><PstlAdr><Ctry>{rng_country()}</Ctry></PstlAdr></Cdtr>
\t\t\t\t\t<CdtrAcct><Id><IBAN>{xe(cov_cdtr_iban)}</IBAN></Id></CdtrAcct>
\t\t\t\t\t<RmtInf><Ustrd>{xe(rng_id('COVREF', 10))}</Ustrd></RmtInf>
\t\t\t\t</UndrlygCstmrCdtTrf>
"""

    # ── v12 namespace and root element ──
    ns = "urn:iso:std:iso:20022:tech:xsd:pacs.009.001.08"
    msg_def = "pacs.009.001.08"

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<BusMsgEnvlp xmlns="urn:swift:xsd:envelope">
\t<AppHdr xmlns="urn:iso:std:iso:20022:tech:xsd:head.001.001.02">
\t\t<Fr>
{apphdr_fi(from_bic)}\t\t</Fr>
\t\t<To>
{apphdr_fi(to_bic)}\t\t</To>
\t\t<BizMsgIdr>{xe(biz_msg_id)}</BizMsgIdr>
\t\t<MsgDefIdr>{msg_def}</MsgDefIdr>
\t\t<BizSvc>swift.cbprplus.02</BizSvc>
\t\t<CreDt>{cre_dt}</CreDt>
\t</AppHdr>
\t<Document xmlns="{ns}">
\t\t<FICdtTrf>
\t\t\t<GrpHdr>
\t\t\t\t<MsgId>{xe(msg_id)}</MsgId>
\t\t\t\t<CreDtTm>{cre_dt}</CreDtTm>
\t\t\t\t<NbOfTxs>1</NbOfTxs>
\t\t\t\t<SttlmInf>
\t\t\t\t\t<SttlmMtd>{xe(sttlm_mtd)}</SttlmMtd>
\t\t\t\t</SttlmInf>
\t\t\t</GrpHdr>
\t\t\t<CdtTrfTxInf>
\t\t\t\t<PmtId>
\t\t\t\t\t<InstrId>{xe(instr_id)}</InstrId>
\t\t\t\t\t<EndToEndId>{xe(e2e_id)}</EndToEndId>
\t\t\t\t\t<TxId>{xe(tx_id)}</TxId>
\t\t\t\t\t<UETR>{xe(uetr)}</UETR>
\t\t\t\t</PmtId>
{tx}\t\t\t</CdtTrfTxInf>
\t\t</FICdtTrf>
\t</Document>
</BusMsgEnvlp>"""
    return xml


# ── Pacs.004 Generator ─────────────────────────────────────────────────────────

def _gen_pacs004(selected: set, idx: int) -> str:
    ccy, country = rng_currency_and_country()
    iban_country = country
    from_bic = rng_bic()
    to_bic = rng_bic()
    biz_msg_id = rng_id("BIZ", 16)
    msg_id = rng_id("MSG", 16)
    rtr_id = rng_id("RTR", 16)
    orig_instr_id = rng_id("ORGINSTR", 11)
    orig_e2e = rng_id("ORIE2E", 10)
    orig_tx = rng_id("ORITX", 10)
    orig_uetr = rng_uetr()
    uetr = rng_uetr()
    cre_dt = rng_datetime()
    sttlm_dt = rng_date(1)
    amount = rng_amount(ccy)
    rtr_reason = random.choice(RETURN_REASONS)
    # pacs.004 usually allows CRED, SHAR but may reject DEBT/SLEV in some rules
    charge_br = random.choice(["SHAR", "CRED"])

    tx = ""

    # -- ChrgsInf (optional) -- XSD pos after IntrBkSttlmDt
    if "charges_information" in selected:
        chg_amt = rng_amount(ccy)
        chg_bic = rng_bic()
        tx += (f"\t\t\t\t<ChrgsInf>\n"
               f"\t\t\t\t\t<Amt Ccy=\"{xe(ccy)}\">{chg_amt}</Amt>\n"
               f"\t\t\t\t\t<Agt>\n\t\t\t\t\t\t<FinInstnId>\n\t\t\t\t\t\t\t<BICFI>{xe(chg_bic)}</BICFI>\n"
               f"\t\t\t\t\t\t</FinInstnId>\n\t\t\t\t\t</Agt>\n\t\t\t\t</ChrgsInf>\n")

    # -- InstgAgt / InstdAgt -- XSD pos after ChrgsInf
    if "instructing_agent" in selected:
        tx += agent_xml("InstgAgt", from_bic, 4)
    if "instructed_agent" in selected:
        tx += agent_xml("InstdAgt", to_bic, 4)

    # -- RtrChain (TransactionParties11) -- XSD pos after InstdAgt
    # XSD sequence inside RtrChain: UltmtDbtr → Dbtr → DbtrAcct → ... → DbtrAgt → ... → CdtrAgt → ... → Cdtr → CdtrAcct → UltmtCdtr
    chain = ""
    if "ultimate_debtor" in selected:
        chain += f"\t\t\t\t\t<UltmtDbtr>\n\t\t\t\t\t\t<Pty>\n{party_xml('_unused', rng_name(), country, 7).replace('<_unused>','').replace('</_unused>','')}\t\t\t\t\t\t</Pty>\n\t\t\t\t\t</UltmtDbtr>\n"
    
    # Dbtr is Mandatory in pacs.004 TransactionParties11
    chain += f"\t\t\t\t\t<Dbtr>\n\t\t\t\t\t\t<Pty>\n{party_xml('_unused', rng_name(), country, 7).replace('<_unused>','').replace('</_unused>','')}\t\t\t\t\t\t</Pty>\n\t\t\t\t\t</Dbtr>\n"
    
    if "debtor_account" in selected:
        chain += account_xml("DbtrAcct", rng_iban(iban_country), 5)
    if "debtor_agent" in selected:
        chain += agent_xml("DbtrAgt", rng_bic(), 5)
    if "creditor_agent" in selected:
        chain += agent_xml("CdtrAgt", rng_bic(), 5)

    # Cdtr is ALSO Mandatory in TransactionParties11
    chain += f"\t\t\t\t\t<Cdtr>\n\t\t\t\t\t\t<Pty>\n{party_xml('_unused', rng_name(), country, 7).replace('<_unused>','').replace('</_unused>','')}\t\t\t\t\t\t</Pty>\n\t\t\t\t\t</Cdtr>\n"

    if "creditor_account" in selected:
        chain += account_xml("CdtrAcct", rng_iban(iban_country), 5)
    if "ultimate_creditor" in selected:
        chain += f"\t\t\t\t\t<UltmtCdtr>\n\t\t\t\t\t\t<Pty>\n{party_xml('_unused', rng_name(), rng_country(), 7).replace('<_unused>','').replace('</_unused>','')}\t\t\t\t\t\t</Pty>\n\t\t\t\t\t</UltmtCdtr>\n"
    if chain:
        tx += f"\t\t\t\t<RtrChain>\n{chain}\t\t\t\t</RtrChain>\n"

    # -- RtrRsnInf -- XSD pos after RtrChain
    tx += f"\t\t\t\t<RtrRsnInf>\n\t\t\t\t\t<Rsn>\n\t\t\t\t\t\t<Cd>{xe(rtr_reason)}</Cd>\n\t\t\t\t\t</Rsn>\n\t\t\t\t</RtrRsnInf>\n"

    # -- RmtInf -- not a direct child per XSD, skip for now
    if "remittance_information" in selected:
        pass  # RmtInf is inside OrgnlTxRef, not directly in TxInf for pacs.004

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<BusMsgEnvlp xmlns="urn:swift:xsd:envelope">
\t<AppHdr xmlns="urn:iso:std:iso:20022:tech:xsd:head.001.001.02">
\t\t<Fr>
{apphdr_fi(from_bic)}\t\t</Fr>
\t\t<To>
{apphdr_fi(to_bic)}\t\t</To>
\t\t<BizMsgIdr>{xe(biz_msg_id)}</BizMsgIdr>
\t\t<MsgDefIdr>pacs.004.001.09</MsgDefIdr>
\t\t<BizSvc>swift.cbprplus.02</BizSvc>
\t\t<CreDt>{cre_dt}</CreDt>
\t</AppHdr>
\t<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.004.001.09">
\t\t<PmtRtr>
\t\t\t<GrpHdr>
\t\t\t\t<MsgId>{xe(msg_id)}</MsgId>
\t\t\t\t<CreDtTm>{cre_dt}</CreDtTm>
\t\t\t\t<NbOfTxs>1</NbOfTxs>
\t\t\t\t<SttlmInf>
\t\t\t\t\t<SttlmMtd>INDA</SttlmMtd>
\t\t\t\t</SttlmInf>
\t\t\t</GrpHdr>
\t\t\t<TxInf>
\t\t\t\t<RtrId>{xe(rtr_id)}</RtrId>
\t\t\t\t<OrgnlGrpInf>
\t\t\t\t\t<OrgnlMsgId>{xe(rng_id("ORIGMSG", 10))}</OrgnlMsgId>
\t\t\t\t\t<OrgnlMsgNmId>pacs.008.001.08</OrgnlMsgNmId>
\t\t\t\t</OrgnlGrpInf>
\t\t\t\t<OrgnlInstrId>{xe(orig_instr_id)}</OrgnlInstrId>
\t\t\t\t<OrgnlEndToEndId>{xe(orig_e2e)}</OrgnlEndToEndId>
\t\t\t\t<OrgnlTxId>{xe(orig_tx)}</OrgnlTxId>
\t\t\t\t<OrgnlUETR>{xe(orig_uetr)}</OrgnlUETR>
\t\t\t\t<RtrdIntrBkSttlmAmt Ccy="{xe(ccy)}">{amount}</RtrdIntrBkSttlmAmt>
\t\t\t\t<IntrBkSttlmDt>{xe(sttlm_dt)}</IntrBkSttlmDt>
\t\t\t\t<ChrgBr>{xe(charge_br)}</ChrgBr>
{tx}\t\t\t</TxInf>
\t\t</PmtRtr>
\t</Document>
</BusMsgEnvlp>"""
    return xml


# ── Pacs.003 Generator ─────────────────────────────────────────────────────────

def _gen_pacs003(selected: set, idx: int) -> str:
    ccy, country = rng_currency_and_country()
    iban_country = country
    from_bic = rng_bic()
    to_bic = rng_bic()
    biz_msg_id = rng_id("BIZ", 16)
    msg_id = rng_id("MSG", 16)
    instr_id = rng_id("INSTR", 11)
    e2e_id = rng_id("E2E", 16)
    tx_id = rng_id("TX", 16)
    uetr = rng_uetr()
    mndt_id = rng_id("MNDT", 10)
    cre_dt = rng_datetime()
    sttlm_dt = rng_date(1)
    amount = rng_amount(ccy)

    tx = ""

    if "payment_type_information" in selected:
        svc = random.choice(SERVICE_LEVELS)
        tx += f"\t\t\t\t<PmtTpInf>\n\t\t\t\t\t<SvcLvl>\n\t\t\t\t\t\t<Cd>{svc}</Cd>\n\t\t\t\t\t</SvcLvl>\n\t\t\t\t</PmtTpInf>\n"

    tx += f"\t\t\t\t<IntrBkSttlmAmt Ccy=\"{xe(ccy)}\">{amount}</IntrBkSttlmAmt>\n"
    tx += el("IntrBkSttlmDt", sttlm_dt, 4)

    # -- ChrgBr (mandatory per XSD) --
    charge_br = random.choice(["SHAR", "CRED", "DEBT"])
    tx += el("ChrgBr", charge_br, 4)

    # -- ChrgsInf (optional) --
    if "charges_information" in selected:
        chg_amt = rng_amount(ccy)
        chg_bic = rng_bic()
        tx += (f"\t\t\t\t<ChrgsInf>\n"
               f"\t\t\t\t\t<Amt Ccy=\"{xe(ccy)}\">{chg_amt}</Amt>\n"
               f"\t\t\t\t\t<Agt>\n\t\t\t\t\t\t<FinInstnId>\n\t\t\t\t\t\t\t<BICFI>{xe(chg_bic)}</BICFI>\n"
               f"\t\t\t\t\t\t</FinInstnId>\n\t\t\t\t\t</Agt>\n\t\t\t\t</ChrgsInf>\n")

    # -- ReqdColltnDt (pos 11) --
    tx += el("ReqdColltnDt", rng_date(2), 4)

    # -- DrctDbtTx (optional, after ReqdColltnDt per XSD) --
    if "direct_debit_transaction" in selected:
        tx += (f"\t\t\t\t<DrctDbtTx>\n"
               f"\t\t\t\t\t<MndtRltdInf>\n"
               f"\t\t\t\t\t\t<MndtId>{xe(mndt_id)}</MndtId>\n"
               f"\t\t\t\t\t\t<DtOfSgntr>{rng_date(-30)}</DtOfSgntr>\n"
               f"\t\t\t\t\t</MndtRltdInf>\n"
               f"\t\t\t\t</DrctDbtTx>\n")

    # -- Cdtr (Mandatory) --
    tx += party_xml("Cdtr", rng_name(), rng_country(), 4)
    # CdtrAcct (Mandatory)
    tx += account_xml("CdtrAcct", rng_iban(), 4)

    # -- CdtrAgt (Mandatory) --
    tx += agent_xml("CdtrAgt", rng_bic(), 4)
    if "creditor_agent_account" in selected:
        tx += account_othr_xml("CdtrAgtAcct", rng_id("ACCT", 10), 4)

    # -- UltmtCdtr --
    if "ultimate_creditor" in selected:
        tx += party_xml("UltmtCdtr", rng_name(), rng_country(), 4)

    # -- InstgAgt / InstdAgt --
    if "instructing_agent" in selected:
        tx += agent_xml("InstgAgt", from_bic, 4)
    if "instructed_agent" in selected:
        tx += agent_xml("InstdAgt", to_bic, 4)

    # -- IntrmyAgt1/2/3 --
    if "intermediary_agent_1" in selected:
        tx += agent_xml("IntrmyAgt1", rng_bic(), 4)
    if "intermediary_agent_2" in selected:
        tx += agent_xml("IntrmyAgt2", rng_bic(), 4)
    if "intermediary_agent_3" in selected:
        tx += agent_xml("IntrmyAgt3", rng_bic(), 4)

    # -- Dbtr (Mandatory) --
    tx += party_xml("Dbtr", rng_name(), rng_country(), 4)
    # DbtrAcct (Mandatory)
    tx += account_xml("DbtrAcct", rng_iban(iban_country), 4)
    # DbtrAgt (Mandatory)
    tx += agent_xml("DbtrAgt", rng_bic(), 4)

    # -- UltmtDbtr --
    if "ultimate_debtor" in selected:
        tx += party_xml("UltmtDbtr", rng_name(), rng_country(), 4)

    # -- RmtInf --
    if "remittance_information" in selected:
        tx += f"\t\t\t\t<RmtInf>\n\t\t\t\t\t<Ustrd>{xe(rng_id('REF', 16))}</Ustrd>\n\t\t\t\t</RmtInf>\n"

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<BusMsgEnvlp xmlns="urn:swift:xsd:envelope">
\t<AppHdr xmlns="urn:iso:std:iso:20022:tech:xsd:head.001.001.02">
\t\t<Fr>
{apphdr_fi(from_bic)}\t\t</Fr>
\t\t<To>
{apphdr_fi(to_bic)}\t\t</To>
\t\t<BizMsgIdr>{xe(biz_msg_id)}</BizMsgIdr>
\t\t<MsgDefIdr>pacs.003.001.08</MsgDefIdr>
\t\t<BizSvc>swift.cbprplus.02</BizSvc>
\t\t<CreDt>{cre_dt}</CreDt>
\t</AppHdr>
\t<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.003.001.08">
\t\t<FIToFICstmrDrctDbt>
\t\t\t<GrpHdr>
\t\t\t\t<MsgId>{xe(msg_id)}</MsgId>
\t\t\t\t<CreDtTm>{cre_dt}</CreDtTm>
\t\t\t\t<NbOfTxs>1</NbOfTxs>
\t\t\t\t<SttlmInf>
\t\t\t\t\t<SttlmMtd>INDA</SttlmMtd>
\t\t\t\t</SttlmInf>
\t\t\t</GrpHdr>
\t\t\t<DrctDbtTxInf>
\t\t\t\t<PmtId>
\t\t\t\t\t<InstrId>{xe(instr_id)}</InstrId>
\t\t\t\t\t<EndToEndId>{xe(e2e_id)}</EndToEndId>
\t\t\t\t\t<TxId>{xe(tx_id)}</TxId>
\t\t\t\t\t<UETR>{xe(uetr)}</UETR>
\t\t\t\t</PmtId>
{tx}\t\t\t</DrctDbtTxInf>
\t\t</FIToFICstmrDrctDbt>
\t</Document>
</BusMsgEnvlp>"""
    return xml


# ── Pacs.002 Generator ─────────────────────────────────────────────────────────

def _gen_pacs002(selected: set, idx: int) -> str:
    ccy, country = rng_currency_and_country()
    iban_country = country
    from_bic = rng_bic()
    to_bic = rng_bic()
    biz_msg_id = rng_id("BIZ", 16)
    msg_id = rng_id("MSG", 16)
    cre_dt = rng_datetime()
    orig_msg_id = rng_id("ORIGMSG", 10)
    orig_e2e = rng_id("ORIE2E", 10)
    orig_tx = rng_id("ORITX", 10)
    orig_uetr = rng_uetr()
    status_codes = ["ACSC", "ACCP", "ACSP", "RJCT", "PDNG"]
    status = random.choice(status_codes)

    grphdr_tx = ""
    if "instructing_agent" in selected:
        grphdr_tx += agent_xml("InstgAgt", from_bic, 4)
    if "instructed_agent" in selected:
        grphdr_tx += agent_xml("InstdAgt", to_bic, 4)

    # Original parties belong in OrgnlTxRef (pos 16 in TxInfAndSts)
    orgnl_tx_ref = ""
    if "debtor" in selected:
        orgnl_tx_ref += f"\t\t\t\t\t<Dbtr>\n{party_xml('Pty', rng_name(), country, 6)}\t\t\t\t\t</Dbtr>\n"
    if "creditor" in selected:
        orgnl_tx_ref += f"\t\t\t\t\t<Cdtr>\n{party_xml('Pty', rng_name(), country, 6)}\t\t\t\t\t</Cdtr>\n"

    reject_reason = ""
    if status == "RJCT":
        reasons = ["AM04", "AC01", "FF01", "AG01"]
        reject_reason = f"\t\t\t\t<StsRsnInf>\n\t\t\t\t\t<Rsn>\n\t\t\t\t\t\t<Cd>{random.choice(reasons)}</Cd>\n\t\t\t\t\t</Rsn>\n\t\t\t\t</StsRsnInf>\n"

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<BusMsgEnvlp xmlns="urn:swift:xsd:envelope">
\t<AppHdr xmlns="urn:iso:std:iso:20022:tech:xsd:head.001.001.02">
\t\t<Fr>
{apphdr_fi(from_bic)}\t\t</Fr>
\t\t<To>
{apphdr_fi(to_bic)}\t\t</To>
\t\t<BizMsgIdr>{xe(biz_msg_id)}</BizMsgIdr>
\t\t<MsgDefIdr>pacs.002.001.10</MsgDefIdr>
\t\t<BizSvc>swift.cbprplus.02</BizSvc>
\t\t<CreDt>{cre_dt}</CreDt>
\t</AppHdr>
\t<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.002.001.10">
\t\t<FIToFIPmtStsRpt>
\t\t\t<GrpHdr>
\t\t\t\t<MsgId>{xe(msg_id)}</MsgId>
\t\t\t\t<CreDtTm>{cre_dt}</CreDtTm>
{grphdr_tx}\t\t\t</GrpHdr>
\t\t\t<TxInfAndSts>
\t\t\t\t<OrgnlGrpInf>
\t\t\t\t\t<OrgnlMsgId>{xe(orig_msg_id)}</OrgnlMsgId>
\t\t\t\t\t<OrgnlMsgNmId>pacs.008.001.08</OrgnlMsgNmId>
\t\t\t\t</OrgnlGrpInf>
\t\t\t\t<OrgnlEndToEndId>{xe(orig_e2e)}</OrgnlEndToEndId>
\t\t\t\t<OrgnlTxId>{xe(orig_tx)}</OrgnlTxId>
\t\t\t\t<OrgnlUETR>{xe(orig_uetr)}</OrgnlUETR>
\t\t\t\t<TxSts>{xe(status)}</TxSts>
{reject_reason}\t\t\t\t<OrgnlTxRef>
{orgnl_tx_ref}\t\t\t\t</OrgnlTxRef>
\t\t\t</TxInfAndSts>
\t\t</FIToFIPmtStsRpt>
\t</Document>
</BusMsgEnvlp>"""
    return xml


# ── Pacs.010 Generator ─────────────────────────────────────────────────────────

def _gen_pacs010(selected: set, idx: int) -> str:
    ccy, country = rng_currency_and_country()
    iban_country = country
    from_bic = rng_bic()
    to_bic = rng_bic()
    biz_msg_id = rng_id("BIZ", 16)
    msg_id = rng_id("MSG", 16)
    cdt_id = rng_id("CDT", 16)
    instr_id = rng_id("INSTR", 11)
    e2e_id = rng_id("E2E", 16)
    tx_id = rng_id("TX", 16)
    uetr = rng_uetr()
    cre_dt = rng_datetime()
    sttlm_dt = rng_date(1)
    amount = rng_amount(ccy)

    # Both pacs.010 variants (main and v3 / Margin Collection) use the same
    # CBPR+ namespace; the v3 flag only changes the XML body structure.
    ns = "urn:iso:std:iso:20022:tech:xsd:pacs.010.001.03"
    msg_def = "pacs.010.001.03"

    # DrctDbtTxInf body: PmtId → PmtTpInf → IntrBkSttlmAmt → IntrBkSttlmDt → UltmtDbtr → Dbtr → DbtrAcct → DbtrAgt → RmtInf
    dd_tx = ""
    if "payment_type_information" in selected:
        svc = random.choice(SERVICE_LEVELS)
        dd_tx += f"\t\t\t\t\t<PmtTpInf>\n\t\t\t\t\t\t<SvcLvl>\n\t\t\t\t\t\t\t<Cd>{svc}</Cd>\n\t\t\t\t\t\t</SvcLvl>\n\t\t\t\t\t</PmtTpInf>\n"

    dd_tx += f"\t\t\t\t\t<IntrBkSttlmAmt Ccy=\"{xe(ccy)}\">{amount}</IntrBkSttlmAmt>\n"
    dd_tx += el("IntrBkSttlmDt", sttlm_dt, 5)

    # Dbtr mandatory (BranchAndFinancialInstitutionIdentification8)
    dd_tx += agent_xml("Dbtr", rng_bic(), 5)
    if "debtor_account" in selected:
        dd_tx += account_xml("DbtrAcct", rng_iban(iban_country), 5)
    if "debtor_agent" in selected:
        dd_tx += agent_xml("DbtrAgt", rng_bic(), 5)

    if "remittance_information" in selected:
        dd_tx += f"\t\t\t\t\t<RmtInf>\n\t\t\t\t\t\t<Ustrd>{xe(rng_id('REF', 16))}</Ustrd>\n\t\t\t\t\t</RmtInf>\n"

    # CdtInstr body: CdtId → IntrBkSttlmDt → InstgAgt → InstdAgt → CdtrAgt → Cdtr → CdtrAcct → DrctDbtTxInf
    cdt_body = ""
    if "instructing_agent" in selected:
        cdt_body += agent_xml("InstgAgt", from_bic, 4)
    if "instructed_agent" in selected:
        cdt_body += agent_xml("InstdAgt", to_bic, 4)
    if "creditor_agent" in selected:
        cdt_body += agent_xml("CdtrAgt", rng_bic(), 4)
    # Cdtr mandatory (BranchAndFinancialInstitutionIdentification8)
    cdt_body += agent_xml("Cdtr", rng_bic(), 4)
    if "creditor_account" in selected:
        cdt_body += account_xml("CdtrAcct", rng_iban(iban_country), 4)

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<BusMsgEnvlp xmlns="urn:swift:xsd:envelope">
\t<AppHdr xmlns="urn:iso:std:iso:20022:tech:xsd:head.001.001.02">
\t\t<Fr>
{apphdr_fi(from_bic)}\t\t</Fr>
\t\t<To>
{apphdr_fi(to_bic)}\t\t</To>
\t\t<BizMsgIdr>{xe(biz_msg_id)}</BizMsgIdr>
\t\t<MsgDefIdr>{msg_def}</MsgDefIdr>
\t\t<BizSvc>swift.cbprplus.02</BizSvc>
\t\t<CreDt>{cre_dt}</CreDt>
\t</AppHdr>
\t<Document xmlns="{ns}">
\t\t<FIDrctDbt>
\t\t\t<GrpHdr>
\t\t\t\t<MsgId>{xe(msg_id)}</MsgId>
\t\t\t\t<CreDtTm>{cre_dt}</CreDtTm>
\t\t\t\t<NbOfTxs>1</NbOfTxs>
\t\t\t</GrpHdr>
\t\t\t<CdtInstr>
\t\t\t\t<CdtId>{xe(cdt_id)}</CdtId>
\t\t\t\t<IntrBkSttlmDt>{sttlm_dt}</IntrBkSttlmDt>
{cdt_body}\t\t\t\t<DrctDbtTxInf>
\t\t\t\t\t<PmtId>
\t\t\t\t\t\t<InstrId>{xe(instr_id)}</InstrId>
\t\t\t\t\t\t<EndToEndId>{xe(e2e_id)}</EndToEndId>
\t\t\t\t\t\t<TxId>{xe(tx_id)}</TxId>
\t\t\t\t\t\t<UETR>{xe(uetr)}</UETR>
\t\t\t\t\t</PmtId>
{dd_tx}\t\t\t\t</DrctDbtTxInf>
\t\t\t</CdtInstr>
\t\t</FIDrctDbt>
\t</Document>
</BusMsgEnvlp>"""
    return xml


# ── CAMT.057 Generator ─────────────────────────────────────────────────────────

def _gen_camt057(selected: set, idx: int) -> str:
    ccy, country = rng_currency_and_country()
    iban_country = country
    from_bic = rng_bic()
    to_bic = rng_bic()
    biz_msg_id = rng_id("BIZ", 16)
    msg_id = rng_id("MSG", 16)
    notif_id = rng_id("NTFN", 10)
    cre_dt = rng_datetime()
    amount = rng_amount(ccy)
    e2e_id = rng_id("E2E", 16)

    items = ""
    if "debtor" in selected:
        items += f"\t\t\t\t\t<Dbtr>\n\t\t\t\t\t\t<Pty>\n{party_xml('_unused', rng_name(), country, 6).replace('<_unused>','').replace('</_unused>','')}\t\t\t\t\t\t</Pty>\n\t\t\t\t\t</Dbtr>\n"
    if "debtor_agent" in selected:
        items += agent_xml("DbtrAgt", rng_bic(), 5)
    if "intermediary_agent_1" in selected:
        items += agent_xml("IntrmyAgt", rng_bic(), 5)

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<BusMsgEnvlp xmlns="urn:swift:xsd:envelope">
\t<AppHdr xmlns="urn:iso:std:iso:20022:tech:xsd:head.001.001.02">
\t\t<Fr>
{apphdr_fi(from_bic)}\t\t</Fr>
\t\t<To>
{apphdr_fi(to_bic)}\t\t</To>
\t\t<BizMsgIdr>{xe(biz_msg_id)}</BizMsgIdr>
\t\t<MsgDefIdr>camt.057.001.06</MsgDefIdr>
\t\t<BizSvc>swift.cbprplus.02</BizSvc>
\t\t<CreDt>{cre_dt}</CreDt>
\t</AppHdr>
\t<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.057.001.06">
\t\t<NtfctnToRcv>
\t\t\t<GrpHdr>
\t\t\t\t<MsgId>{xe(msg_id)}</MsgId>
\t\t\t\t<CreDtTm>{cre_dt}</CreDtTm>
\t\t\t</GrpHdr>
\t\t\t<Ntfctn>
\t\t\t\t<Id>{xe(notif_id)}</Id>
\t\t\t\t<Acct><Id><IBAN>{xe(rng_iban(country))}</IBAN></Id></Acct>
\t\t\t\t<XpctdValDt>{rng_date(2)}</XpctdValDt>
\t\t\t\t<Itm>
\t\t\t\t\t<Id>{xe(rng_id("ITM", 10))}</Id>
\t\t\t\t\t<EndToEndId>{xe(e2e_id)}</EndToEndId>
\t\t\t\t\t<Amt Ccy="{xe(ccy)}">{amount}</Amt>
{items}\t\t\t\t</Itm>
\t\t\t</Ntfctn>
\t\t</NtfctnToRcv>
\t</Document>
</BusMsgEnvlp>"""
    return xml


# ── CAMT.052 Generator ─────────────────────────────────────────────────────────

def _gen_camt052(selected: set, idx: int) -> str:
    from_bic = rng_bic()
    to_bic = rng_bic()
    biz_msg_id = rng_id("BIZ", 16)
    msg_id = rng_id("MSG", 16)
    cre_dt = rng_datetime()
    ccy = rng_currency()
    acct_iban = rng_iban()

    rpt = ""
    # Account block with nested Ownr/Svcr and mandatory Ccy
    rpt += f"\t\t\t\t<Acct>\n\t\t\t\t\t<Id><IBAN>{xe(acct_iban)}</IBAN></Id>\n"
    rpt += f"\t\t\t\t\t<Ccy>{xe(ccy)}</Ccy>\n"
    if "account_owner" in selected:
        rpt += f"\t\t\t\t\t<Ownr>\n{party_xml('_unused', rng_name(), rng_country(), 7).replace('<_unused>','').replace('</_unused>','')}\t\t\t\t\t</Ownr>\n"
    if "account_servicer" in selected:
        rpt += f"\t\t\t\t\t<Svcr>\n{agent_xml('_unused', rng_bic(), 7).replace('<_unused>','').replace('</_unused>','')}\t\t\t\t\t</Svcr>\n"
    rpt += "\t\t\t\t</Acct>\n"
    if "balance" in selected:
        bal_amt = rng_amount(ccy)
        rpt += f"""\t\t\t\t<Bal>
\t\t\t\t\t<Tp><CdOrPrtry><Cd>OPBD</Cd></CdOrPrtry></Tp>
\t\t\t\t\t<Amt Ccy="{xe(ccy)}">{bal_amt}</Amt>
\t\t\t\t\t<CdtDbtInd>CRDT</CdtDbtInd>
\t\t\t\t\t<Dt><Dt>{rng_date(0)}</Dt></Dt>
\t\t\t\t</Bal>
"""
    if "transaction_summary" in selected:
        rpt += f"""\t\t\t\t<TxsSummry>
\t\t\t\t\t<TtlNtries><NbOfNtries>1</NbOfNtries></TtlNtries>
\t\t\t\t</TxsSummry>
"""
    if "entry" in selected:
        entry_amt = rng_amount(ccy)
        rpt += f"""\t\t\t\t<Ntry>
\t\t\t\t\t<Amt Ccy="{xe(ccy)}">{entry_amt}</Amt>
\t\t\t\t\t<CdtDbtInd>CRDT</CdtDbtInd>
\t\t\t\t\t<Sts><Cd>BOOK</Cd></Sts>
\t\t\t\t\t<BookgDt><Dt>{rng_date(0)}</Dt></BookgDt>
\t\t\t\t\t<ValDt><Dt>{rng_date(0)}</Dt></ValDt>
\t\t\t\t\t<BkTxCd><Prtry><Cd>VALL</Cd><Issr>CBPR</Issr></Prtry></BkTxCd>
\t\t\t\t</Ntry>
"""

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<BusMsgEnvlp xmlns="urn:swift:xsd:envelope">
\t<AppHdr xmlns="urn:iso:std:iso:20022:tech:xsd:head.001.001.02">
\t\t<Fr>
{apphdr_fi(from_bic)}\t\t</Fr>
\t\t<To>
{apphdr_fi(to_bic)}\t\t</To>
\t\t<BizMsgIdr>{xe(biz_msg_id)}</BizMsgIdr>
\t\t<MsgDefIdr>camt.052.001.08</MsgDefIdr>
\t\t<BizSvc>swift.cbprplus.02</BizSvc>
\t\t<CreDt>{cre_dt}</CreDt>
\t</AppHdr>
\t<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.052.001.08">
\t\t<BkToCstmrAcctRpt>
\t\t\t<GrpHdr>
\t\t\t\t<MsgId>{xe(msg_id)}</MsgId>
\t\t\t\t<CreDtTm>{cre_dt}</CreDtTm>
\t\t\t</GrpHdr>
\t\t\t<Rpt>
\t\t\t\t<Id>{xe(rng_id("RPT", 10))}</Id>
\t\t\t\t<RptPgntn>
\t\t\t\t\t<PgNb>1</PgNb>
\t\t\t\t\t<LastPgInd>true</LastPgInd>
\t\t\t\t</RptPgntn>
\t\t\t\t<CreDtTm>{cre_dt}</CreDtTm>
{rpt}\t\t\t</Rpt>
\t\t</BkToCstmrAcctRpt>
\t</Document>
</BusMsgEnvlp>"""
    return xml


# ── CAMT.053 Generator ─────────────────────────────────────────────────────────

def _gen_camt053(selected: set, idx: int) -> str:
    from_bic = rng_bic()
    to_bic = rng_bic()
    biz_msg_id = rng_id("BIZ", 16)
    msg_id = rng_id("MSG", 16)
    cre_dt = rng_datetime()
    ccy, iban_country = rng_currency_and_country()
    acct_iban = rng_iban(iban_country)

    stmt = ""
    # Account block with nested Ownr/Svcr in v13
    stmt += f"\t\t\t\t<Acct>\n\t\t\t\t\t<Id><IBAN>{xe(acct_iban)}</IBAN></Id>\n"
    if "account_owner" in selected:
        stmt += f"\t\t\t\t\t<Ownr>\n{party_xml('_unused', rng_name(), rng_country(), 7).replace('<_unused>','').replace('</_unused>','')}\t\t\t\t\t</Ownr>\n"
    if "account_servicer" in selected:
        stmt += f"\t\t\t\t\t<Svcr>\n{agent_xml('_unused', rng_bic(), 7).replace('<_unused>','').replace('</_unused>','')}\t\t\t\t\t</Svcr>\n"
    stmt += "\t\t\t\t</Acct>\n"
    
    # Balance is Mandatory in camt.053 AccountStatement
    bal_amt = rng_amount(ccy)
    stmt += f"""\t\t\t\t<Bal>
\t\t\t\t\t<Tp><CdOrPrtry><Cd>OPBD</Cd></CdOrPrtry></Tp>
\t\t\t\t\t<Amt Ccy="{xe(ccy)}">{bal_amt}</Amt>
\t\t\t\t\t<CdtDbtInd>CRDT</CdtDbtInd>
\t\t\t\t\t<Dt><Dt>{rng_date(0)}</Dt></Dt>
\t\t\t\t</Bal>
"""
    if "transaction_summary" in selected:
        stmt += f"""\t\t\t\t<TxsSummry>
\t\t\t\t\t<TtlNtries><NbOfNtries>1</NbOfNtries></TtlNtries>
\t\t\t\t</TxsSummry>
"""
    if "entry" in selected:
        entry_amt = rng_amount(ccy)
        stmt += f"""\t\t\t\t<Ntry>
\t\t\t\t\t<Amt Ccy="{xe(ccy)}">{entry_amt}</Amt>
\t\t\t\t\t<CdtDbtInd>DBIT</CdtDbtInd>
\t\t\t\t\t<Sts><Cd>BOOK</Cd></Sts>
\t\t\t\t\t<BookgDt><Dt>{rng_date(0)}</Dt></BookgDt>
\t\t\t\t\t<ValDt><Dt>{rng_date(0)}</Dt></ValDt>
\t\t\t\t\t<BkTxCd><Prtry><Cd>VALL</Cd></Prtry></BkTxCd>
\t\t\t\t</Ntry>
"""

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<BusMsgEnvlp xmlns="urn:swift:xsd:envelope">
\t<AppHdr xmlns="urn:iso:std:iso:20022:tech:xsd:head.001.001.02">
\t\t<Fr>
{apphdr_fi(from_bic)}\t\t</Fr>
\t\t<To>
{apphdr_fi(to_bic)}\t\t</To>
\t\t<BizMsgIdr>{xe(biz_msg_id)}</BizMsgIdr>
\t\t<MsgDefIdr>camt.053.001.08</MsgDefIdr>
\t\t<BizSvc>swift.cbprplus.02</BizSvc>
\t\t<CreDt>{cre_dt}</CreDt>
\t</AppHdr>
\t<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.08">
\t\t<BkToCstmrStmt>
\t\t\t<GrpHdr>
\t\t\t\t<MsgId>{xe(msg_id)}</MsgId>
\t\t\t\t<CreDtTm>{cre_dt}</CreDtTm>
\t\t\t</GrpHdr>
\t\t\t<Stmt>
\t\t\t\t<Id>{xe(rng_id("STMT", 10))}</Id>
\t\t\t\t<CreDtTm>{cre_dt}</CreDtTm>
\t\t\t\t<FrToDt>
\t\t\t\t\t<FrDtTm>{rng_date(-1)}T00:00:00.000Z</FrDtTm>
\t\t\t\t\t<ToDtTm>{rng_date(0)}T23:59:59.000Z</ToDtTm>
\t\t\t\t</FrToDt>
{stmt}\t\t\t</Stmt>
\t\t</BkToCstmrStmt>
\t</Document>
</BusMsgEnvlp>"""
    return xml


# ── CAMT.054 Generator ─────────────────────────────────────────────────────────

def _gen_camt054(selected: set, idx: int) -> str:
    from_bic = rng_bic()
    to_bic = rng_bic()
    biz_msg_id = rng_id("BIZ", 16)
    msg_id = rng_id("MSG", 16)
    cre_dt = rng_datetime()
    ccy = rng_currency()

    ntfctn = ""
    # Account block with nested Ownr/Svcr in v13
    ntfctn += f"\t\t\t\t<Acct>\n\t\t\t\t\t<Id><IBAN>{xe(rng_iban())}</IBAN></Id>\n"
    if "account_owner" in selected:
        ntfctn += f"\t\t\t\t\t<Ownr>\n{party_xml('_unused', rng_name(), rng_country(), 7).replace('<_unused>','').replace('</_unused>','')}\t\t\t\t\t</Ownr>\n"
    if "account_servicer" in selected:
        ntfctn += f"\t\t\t\t\t<Svcr>\n{agent_xml('_unused', rng_bic(), 7).replace('<_unused>','').replace('</_unused>','')}\t\t\t\t\t</Svcr>\n"
    ntfctn += "\t\t\t\t</Acct>\n"
    if "entry" in selected:
        entry_amt = rng_amount(ccy)
        cdt_dbt = random.choice(["CRDT", "DBIT"])
        ntfctn += f"""\t\t\t\t<Ntry>
\t\t\t\t\t<Amt Ccy="{xe(ccy)}">{entry_amt}</Amt>
\t\t\t\t\t<CdtDbtInd>{cdt_dbt}</CdtDbtInd>
\t\t\t\t\t<Sts><Cd>BOOK</Cd></Sts>
\t\t\t\t\t<BookgDt><Dt>{rng_date(0)}</Dt></BookgDt>
\t\t\t\t\t<ValDt><Dt>{rng_date(0)}</Dt></ValDt>
\t\t\t\t\t<BkTxCd><Prtry><Cd>VALL</Cd></Prtry></BkTxCd>
\t\t\t\t</Ntry>
"""

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<BusMsgEnvlp xmlns="urn:swift:xsd:envelope">
\t<AppHdr xmlns="urn:iso:std:iso:20022:tech:xsd:head.001.001.02">
\t\t<Fr>
{apphdr_fi(from_bic)}\t\t</Fr>
\t\t<To>
{apphdr_fi(to_bic)}\t\t</To>
\t\t<BizMsgIdr>{xe(biz_msg_id)}</BizMsgIdr>
\t\t<MsgDefIdr>camt.054.001.08</MsgDefIdr>
\t\t<BizSvc>swift.cbprplus.02</BizSvc>
\t\t<CreDt>{cre_dt}</CreDt>
\t</AppHdr>
\t<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.054.001.08">
\t\t<BkToCstmrDbtCdtNtfctn>
\t\t\t<GrpHdr>
\t\t\t\t<MsgId>{xe(msg_id)}</MsgId>
\t\t\t\t<CreDtTm>{cre_dt}</CreDtTm>
\t\t\t</GrpHdr>
\t\t\t<Ntfctn>
\t\t\t\t<Id>{xe(rng_id("NTFN", 10))}</Id>
\t\t\t\t<CreDtTm>{cre_dt}</CreDtTm>
{ntfctn}\t\t\t</Ntfctn>
\t\t</BkToCstmrDbtCdtNtfctn>
\t</Document>
</BusMsgEnvlp>"""
    return xml


# ── CAMT.055 Generator ─────────────────────────────────────────────────────────

def _gen_camt055(selected: set, idx: int) -> str:
    from_bic = rng_bic()
    to_bic = rng_bic()
    biz_msg_id = rng_id("BIZ", 16)
    msg_id = rng_id("MSG", 16)
    cre_dt = rng_datetime()

    body = ""
    # In v12, Underlying is: OrgnlGrpInfAndCxl, then OrgnlPmtInfAndCxl
    if "original_group_information" in selected:
        body += f"""\t\t\t\t<OrgnlGrpInfAndCxl>
\t\t\t\t\t<OrgnlMsgId>{xe(rng_id("ORIGMSG", 10))}</OrgnlMsgId>
\t\t\t\t\t<OrgnlMsgNmId>pacs.008.001.08</OrgnlMsgNmId>
\t\t\t\t</OrgnlGrpInfAndCxl>
"""
    
    
    orgnl_tx_ref = ""
    if "original_transaction" in selected:
        orgnl_tx_ref = f"""\n\t\t\t\t\t\t<OrgnlTxRef>
\t\t\t\t\t\t\t<IntrBkSttlmAmt Ccy="{xe(rng_currency())}">{rng_amount("USD")}</IntrBkSttlmAmt>
\t\t\t\t\t\t</OrgnlTxRef>"""

    # Tx details must be inside OrgnlPmtInfAndCxl -> TxInf
    body += f"""\t\t\t\t<OrgnlPmtInfAndCxl>
\t\t\t\t\t<OrgnlPmtInfId>{xe(rng_id("ORIGPMT", 10))}</OrgnlPmtInfId>
\t\t\t\t\t<TxInf>
\t\t\t\t\t\t<CxlId>{xe(rng_id("CXLID", 10))}</CxlId>
\t\t\t\t\t\t<OrgnlEndToEndId>{xe(rng_id("ORIE2E", 10))}</OrgnlEndToEndId>
\t\t\t\t\t\t<OrgnlUETR>{rng_uetr()}</OrgnlUETR>
\t\t\t\t\t\t<CxlRsnInf>
\t\t\t\t\t\t\t<Rsn><Cd>CUST</Cd></Rsn>
\t\t\t\t\t\t</CxlRsnInf>{orgnl_tx_ref}
\t\t\t\t\t</TxInf>
\t\t\t\t</OrgnlPmtInfAndCxl>
"""

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<BusMsgEnvlp xmlns="urn:swift:xsd:envelope">
\t<AppHdr xmlns="urn:iso:std:iso:20022:tech:xsd:head.001.001.02">
\t\t<Fr>
{apphdr_fi(from_bic)}\t\t</Fr>
\t\t<To>
{apphdr_fi(to_bic)}\t\t</To>
\t\t<BizMsgIdr>{xe(biz_msg_id)}</BizMsgIdr>
\t\t<MsgDefIdr>camt.055.001.08</MsgDefIdr>
\t\t<BizSvc>swift.cbprplus.02</BizSvc>
\t\t<CreDt>{cre_dt}</CreDt>
\t</AppHdr>
\t<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.055.001.08">
\t\t<CstmrPmtCxlReq>
\t\t\t<Assgnmt>
\t\t\t\t<Id>{xe(rng_id("ASSGNMT", 10))}</Id>
\t\t\t\t<Assgnr><Agt><FinInstnId><BICFI>{xe(from_bic)}</BICFI></FinInstnId></Agt></Assgnr>
\t\t\t\t<Assgne><Agt><FinInstnId><BICFI>{xe(to_bic)}</BICFI></FinInstnId></Agt></Assgne>
\t\t\t\t<CreDtTm>{cre_dt}</CreDtTm>
\t\t\t</Assgnmt>
\t\t\t<Undrlyg>
{body}\t\t\t</Undrlyg>
\t\t</CstmrPmtCxlReq>
\t</Document>
</BusMsgEnvlp>"""
    return xml


# ── CAMT.056 Generator ─────────────────────────────────────────────────────────

def _gen_camt056(selected: set, idx: int) -> str:
    from_bic = rng_bic()
    to_bic = rng_bic()
    biz_msg_id = rng_id("BIZ", 16)
    cre_dt = rng_datetime()
    ccy = rng_currency()

    cxl_id = rng_id("CXLID", 10)
    case_id = rng_id("CASE", 10)
    org_msg_id = rng_id("ORIGMSG", 10)
    e2e_id = rng_id("ORIE2E", 10)
    uetr = rng_uetr()
    amt = rng_amount(ccy)
    settle_dt = rng_date(-1)

    reasons = ["DUPL", "CUST", "AGNT", "CURR", "UPAY", "FRAD"]
    reason_cd = random.choice(reasons)

    body = f"""\t\t\t\t<TxInf>
\t\t\t\t\t<CxlId>{xe(cxl_id)}</CxlId>
\t\t\t\t\t<Case>
\t\t\t\t\t\t<Id>{xe(case_id)}</Id>
\t\t\t\t\t\t<Cretr>
\t\t\t\t\t\t\t<Agt>
\t\t\t\t\t\t\t\t<FinInstnId>
\t\t\t\t\t\t\t\t\t<BICFI>{xe(from_bic)}</BICFI>
\t\t\t\t\t\t\t\t</FinInstnId>
\t\t\t\t\t\t\t</Agt>
\t\t\t\t\t\t</Cretr>
\t\t\t\t\t</Case>
\t\t\t\t\t<OrgnlGrpInf>
\t\t\t\t\t\t<OrgnlMsgId>{xe(org_msg_id)}</OrgnlMsgId>
\t\t\t\t\t\t<OrgnlMsgNmId>pacs.008.001.08</OrgnlMsgNmId>
\t\t\t\t\t</OrgnlGrpInf>
\t\t\t\t\t<OrgnlEndToEndId>{xe(e2e_id)}</OrgnlEndToEndId>
\t\t\t\t\t<OrgnlUETR>{xe(uetr)}</OrgnlUETR>
\t\t\t\t\t<OrgnlIntrBkSttlmAmt Ccy="{xe(ccy)}">{amt}</OrgnlIntrBkSttlmAmt>
\t\t\t\t\t<OrgnlIntrBkSttlmDt>{settle_dt}</OrgnlIntrBkSttlmDt>
\t\t\t\t\t<CxlRsnInf>
\t\t\t\t\t\t<Rsn>
\t\t\t\t\t\t\t<Cd>{reason_cd}</Cd>
\t\t\t\t\t\t</Rsn>
\t\t\t\t\t\t<AddtlInf>FI cancellation requested</AddtlInf>
\t\t\t\t\t</CxlRsnInf>
\t\t\t\t</TxInf>
"""

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<BusMsgEnvlp xmlns="urn:swift:xsd:envelope">
\t<AppHdr xmlns="urn:iso:std:iso:20022:tech:xsd:head.001.001.02">
\t\t<Fr>
{apphdr_fi(from_bic)}\t\t</Fr>
\t\t<To>
{apphdr_fi(to_bic)}\t\t</To>
\t\t<BizMsgIdr>{xe(biz_msg_id)}</BizMsgIdr>
\t\t<MsgDefIdr>camt.056.001.08</MsgDefIdr>
\t\t<BizSvc>swift.cbprplus.02</BizSvc>
\t\t<CreDt>{cre_dt}</CreDt>
\t</AppHdr>
\t<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.056.001.08">
\t\t<FIToFIPmtCxlReq>
\t\t\t<Assgnmt>
\t\t\t\t<Id>{xe(rng_id("ASSGNMT", 10))}</Id>
\t\t\t\t<Assgnr><Agt><FinInstnId><BICFI>{xe(from_bic)}</BICFI></FinInstnId></Agt></Assgnr>
\t\t\t\t<Assgne><Agt><FinInstnId><BICFI>{xe(to_bic)}</BICFI></FinInstnId></Agt></Assgne>
\t\t\t\t<CreDtTm>{cre_dt}</CreDtTm>
\t\t\t</Assgnmt>
\t\t\t<Undrlyg>
{body}\t\t\t</Undrlyg>
\t\t</FIToFIPmtCxlReq>
\t</Document>
</BusMsgEnvlp>"""
    return xml


# ── PAIN.001 Generator ─────────────────────────────────────────────────────────

def _gen_pain001(selected: set, idx: int) -> str:
    from_bic = rng_bic("GB")
    to_bic = rng_bic("GB")
    biz_msg_id = rng_id("BIZ", 16)
    msg_id = rng_id("MSG", 16)
    pmt_inf_id = rng_id("PMTINF", 10)
    e2e_id = rng_id("E2E", 16)
    instr_id = rng_id("INSTR", 11)
    cre_dt = rng_datetime()
    curr_map = {
        "GB": "GBP", "DE": "EUR", "FR": "EUR", "NL": "EUR", "BE": "EUR",
        "AT": "EUR", "IT": "EUR", "ES": "EUR", "PT": "EUR", "SE": "SEK",
        "NO": "NOK", "DK": "DKK"
    }
    iban_country = random.choice(list(curr_map.keys()))
    ccy = curr_map[iban_country]
    amount = rng_amount(ccy)

    # InitgPty is mandatory in pain.001
    initg = party_xml("InitgPty", rng_name(), rng_country(), 4)

    pmt_tp = ""
    if "payment_type_information" in selected:
        svc = random.choice(SERVICE_LEVELS)
        pmt_tp = f"\t\t\t\t<PmtTpInf><SvcLvl><Cd>{svc}</Cd></SvcLvl></PmtTpInf>\n"

    # Debtor, DebtorAccount, DebtorAgent are MANDATORY in pain.001
    dbtr_info = party_xml("Dbtr", rng_name(), rng_country(), 4)
    dbtr_info += account_xml("DbtrAcct", rng_iban(iban_country), 4)
    dbtr_info += agent_xml("DbtrAgt", rng_bic(), 4)
    if "ultimate_debtor" in selected:
        dbtr_info += party_xml("UltmtDbtr", rng_name(), rng_country(), 4)

    cdt_tf = ""
    # CdtrAgt, Cdtr, CdtrAcct are MANDATORY in pain.001
    cdt_tf += agent_xml("CdtrAgt", rng_bic(), 5)
    cdt_tf += party_xml("Cdtr", rng_name(), rng_country(), 5)
    cdt_tf += account_xml("CdtrAcct", rng_iban(iban_country), 5)
    
    if "ultimate_creditor" in selected:
        cdt_tf += party_xml("UltmtCdtr", rng_name(), rng_country(), 5)
    if "remittance_information" in selected:
        cdt_tf += f"\t\t\t\t\t<RmtInf><Ustrd>{xe(rng_id('REF', 16))}</Ustrd></RmtInf>\n"

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<BusMsgEnvlp xmlns="urn:swift:xsd:envelope">
\t<AppHdr xmlns="urn:iso:std:iso:20022:tech:xsd:head.001.001.02">
\t\t<Fr>
{apphdr_fi(from_bic)}\t\t</Fr>
\t\t<To>
{apphdr_fi(to_bic)}\t\t</To>
\t\t<BizMsgIdr>{xe(biz_msg_id)}</BizMsgIdr>
\t\t<MsgDefIdr>pain.001.001.09</MsgDefIdr>
\t\t<BizSvc>swift.cbprplus.02</BizSvc>
\t\t<CreDt>{cre_dt}</CreDt>
\t</AppHdr>
\t<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.09">
\t\t<CstmrCdtTrfInitn>
\t\t\t<GrpHdr>
\t\t\t\t<MsgId>{xe(msg_id)}</MsgId>
\t\t\t\t<CreDtTm>{cre_dt}</CreDtTm>
\t\t\t\t<NbOfTxs>1</NbOfTxs>
{initg}\t\t\t</GrpHdr>
\t\t\t<PmtInf>
\t\t\t\t<PmtInfId>{xe(pmt_inf_id)}</PmtInfId>
\t\t\t\t<PmtMtd>TRF</PmtMtd>
\t\t\t\t<NbOfTxs>1</NbOfTxs>
{pmt_tp}\t\t\t\t<ReqdExctnDt><Dt>{rng_date(1)}</Dt></ReqdExctnDt>
{dbtr_info}\t\t\t\t<CdtTrfTxInf>
\t\t\t\t\t<PmtId>
\t\t\t\t\t\t<InstrId>{xe(instr_id)}</InstrId>
\t\t\t\t\t\t<EndToEndId>{xe(e2e_id)}</EndToEndId>
\t\t\t\t\t</PmtId>
\t\t\t\t\t<Amt><InstdAmt Ccy="{xe(ccy)}">{amount}</InstdAmt></Amt>
{cdt_tf}\t\t\t\t</CdtTrfTxInf>
\t\t\t</PmtInf>
\t\t</CstmrCdtTrfInitn>
\t</Document>
</BusMsgEnvlp>"""
    return xml


# ── PAIN.002 Generator ─────────────────────────────────────────────────────────

def _gen_pain002(selected: set, idx: int) -> str:
    from_bic = rng_bic()
    to_bic = rng_bic()
    biz_msg_id = rng_id("BIZ", 16)
    msg_id = rng_id("MSG", 16)
    cre_dt = rng_datetime()
    status_codes = ["ACSC", "ACCP", "ACSP", "RJCT", "PDNG"]
    status = random.choice(status_codes)

    body = f"""\t\t\t\t<OrgnlGrpInfAndSts>
\t\t\t\t\t<OrgnlMsgId>{xe(rng_id("ORIGMSG", 10))}</OrgnlMsgId>
\t\t\t\t\t<OrgnlMsgNmId>pain.001.001.09</OrgnlMsgNmId>
\t\t\t\t\t<GrpSts>{status}</GrpSts>
\t\t\t\t</OrgnlGrpInfAndSts>
"""
    if "original_payment_information" in selected:
        body += f"""\t\t\t\t<OrgnlPmtInfAndSts>
\t\t\t\t\t<OrgnlPmtInfId>{xe(rng_id("ORIGPMT", 10))}</OrgnlPmtInfId>
\t\t\t\t\t<PmtInfSts>{status}</PmtInfSts>
"""
        if "status_reason" in selected and status == "RJCT":
            reasons = ["AM04", "AC01", "FF01", "AG01"]
            body += f"""\t\t\t\t\t<StsRsnInf>
\t\t\t\t\t\t<Rsn><Cd>{random.choice(reasons)}</Cd></Rsn>
\t\t\t\t\t</StsRsnInf>
"""
        if "original_transaction" in selected:
            body += f"""\t\t\t\t\t<TxInfAndSts>
\t\t\t\t\t\t<OrgnlEndToEndId>{xe(rng_id("ORIE2E", 10))}</OrgnlEndToEndId>
\t\t\t\t\t\t<TxSts>{status}</TxSts>
\t\t\t\t\t</TxInfAndSts>
"""
        body += "\t\t\t\t</OrgnlPmtInfAndSts>\n"

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<BusMsgEnvlp xmlns="urn:swift:xsd:envelope">
\t<AppHdr xmlns="urn:iso:std:iso:20022:tech:xsd:head.001.001.02">
\t\t<Fr>
{apphdr_fi(from_bic)}\t\t</Fr>
\t\t<To>
{apphdr_fi(to_bic)}\t\t</To>
\t\t<BizMsgIdr>{xe(biz_msg_id)}</BizMsgIdr>
\t\t<MsgDefIdr>pain.002.001.10</MsgDefIdr>
\t\t<BizSvc>swift.cbprplus.02</BizSvc>
\t\t<CreDt>{cre_dt}</CreDt>
\t</AppHdr>
\t<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.002.001.10">
\t\t<CstmrPmtStsRpt>
\t\t\t<GrpHdr>
\t\t\t\t<MsgId>{xe(msg_id)}</MsgId>
\t\t\t\t<CreDtTm>{cre_dt}</CreDtTm>
\t\t\t</GrpHdr>
{body}\t\t</CstmrPmtStsRpt>
\t</Document>
</BusMsgEnvlp>"""
    return xml


# ── PAIN.008 Generator ─────────────────────────────────────────────────────────

def _gen_pain008(selected: set, idx: int) -> str:
    from_bic = rng_bic("GB")
    to_bic = rng_bic("GB")
    biz_msg_id = rng_id("BIZ", 16)
    msg_id = rng_id("MSG", 16)
    pmt_inf_id = rng_id("PMTINF", 10)
    e2e_id = rng_id("E2E", 16)
    instr_id = rng_id("INSTR", 11)
    mndt_id = rng_id("MNDT", 10)
    cre_dt = rng_datetime()
    curr_map = {
        "GB": "GBP", "DE": "EUR", "FR": "EUR", "NL": "EUR", "BE": "EUR",
        "AT": "EUR", "IT": "EUR", "ES": "EUR", "PT": "EUR", "SE": "SEK",
        "NO": "NOK", "DK": "DKK"
    }
    iban_country = random.choice(list(curr_map.keys()))
    ccy = curr_map[iban_country]
    amount = rng_amount(ccy)

    # InitgPty is mandatory in pain.008
    initg = party_xml("InitgPty", rng_name(), rng_country(), 4)

    pmt_tp = ""
    if "payment_type_information" in selected:
        svc = random.choice(SERVICE_LEVELS)
        pmt_tp += f"\t\t\t\t<PmtTpInf><SvcLvl><Cd>{svc}</Cd></SvcLvl></PmtTpInf>\n"

    pmt_body = ""
    # Cdtr, CdtrAcct, CdtrAgt are MANDATORY in pain.008
    pmt_body += party_xml("Cdtr", rng_name(), rng_country(), 4)
    pmt_body += account_xml("CdtrAcct", rng_iban(iban_country), 4)
    pmt_body += agent_xml("CdtrAgt", rng_bic(), 4)
    if "ultimate_creditor" in selected:
        pmt_body += party_xml("UltmtCdtr", rng_name(), rng_country(), 4)

    dd_tx = ""
    # DbtrAgt, Dbtr, DbtrAcct are MANDATORY in pain.008
    dd_tx += agent_xml("DbtrAgt", rng_bic(), 5)
    dd_tx += party_xml("Dbtr", rng_name(), rng_country(), 5)
    dd_tx += account_xml("DbtrAcct", rng_iban(iban_country), 5)
    
    if "ultimate_debtor" in selected:
        dd_tx += party_xml("UltmtDbtr", rng_name(), rng_country(), 5)
    if "remittance_information" in selected:
        dd_tx += f"\t\t\t\t\t<RmtInf><Ustrd>{xe(rng_id('REF', 16))}</Ustrd></RmtInf>\n"

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<BusMsgEnvlp xmlns="urn:swift:xsd:envelope">
\t<AppHdr xmlns="urn:iso:std:iso:20022:tech:xsd:head.001.001.02">
\t\t<Fr>
{apphdr_fi(from_bic)}\t\t</Fr>
\t\t<To>
{apphdr_fi(to_bic)}\t\t</To>
\t\t<BizMsgIdr>{xe(biz_msg_id)}</BizMsgIdr>
\t\t<MsgDefIdr>pain.008.001.08</MsgDefIdr>
\t\t<BizSvc>swift.cbprplus.02</BizSvc>
\t\t<CreDt>{cre_dt}</CreDt>
\t</AppHdr>
\t<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.008.001.08">
\t\t<CstmrDrctDbtInitn>
\t\t\t<GrpHdr>
\t\t\t\t<MsgId>{xe(msg_id)}</MsgId>
\t\t\t\t<CreDtTm>{cre_dt}</CreDtTm>
\t\t\t\t<NbOfTxs>1</NbOfTxs>
{initg}\t\t\t</GrpHdr>
\t\t\t<PmtInf>
\t\t\t\t<PmtInfId>{xe(pmt_inf_id)}</PmtInfId>
\t\t\t\t<PmtMtd>DD</PmtMtd>
\t\t\t\t<NbOfTxs>1</NbOfTxs>
{pmt_tp}\t\t\t\t<ReqdColltnDt>{rng_date(2)}</ReqdColltnDt>
{pmt_body}\t\t\t\t<DrctDbtTxInf>
\t\t\t\t\t<PmtId>
\t\t\t\t\t\t<InstrId>{xe(instr_id)}</InstrId>
\t\t\t\t\t\t<EndToEndId>{xe(e2e_id)}</EndToEndId>
\t\t\t\t\t</PmtId>
\t\t\t\t\t<InstdAmt Ccy="{xe(ccy)}">{amount}</InstdAmt>
\t\t\t\t\t<DrctDbtTx>
\t\t\t\t\t\t<MndtRltdInf>
\t\t\t\t\t\t\t<MndtId>{xe(mndt_id)}</MndtId>
\t\t\t\t\t\t\t<DtOfSgntr>{rng_date(-30)}</DtOfSgntr>
\t\t\t\t\t\t</MndtRltdInf>
\t\t\t\t\t</DrctDbtTx>
{dd_tx}\t\t\t\t</DrctDbtTxInf>
\t\t\t</PmtInf>
\t\t</CstmrDrctDbtInitn>
\t</Document>
</BusMsgEnvlp>"""
    return xml


# ── Single Message Generator ───────────────────────────────────────────────────

def generate_single_xml(
    message_type: str,
    selected_blocks: List[str],
    idx: int
) -> str:
    """Generate one ISO 20022 XML message for the given type and return raw XML."""
    selected = set(b.lower() for b in selected_blocks)
    selected_blocks_ctx.set(selected)
    msg_lower = message_type.lower()
    if "pacs.008" in msg_lower:
        return _gen_pacs008(selected, idx)
    elif "pacs.009" in msg_lower and "cov" in msg_lower:
        return _gen_pacs009(selected, idx, is_cov=True)
    elif "pacs.009" in msg_lower and "adv" in msg_lower:
        return _gen_pacs009(selected, idx, is_cov=False, is_adv=True)
    elif "pacs.009" in msg_lower:
        return _gen_pacs009(selected, idx, is_cov=False)
    elif "pacs.004" in msg_lower:
        return _gen_pacs004(selected, idx)
    elif "pacs.003" in msg_lower:
        return _gen_pacs003(selected, idx)
    elif "pacs.002" in msg_lower:
        return _gen_pacs002(selected, idx)
    elif "pacs.010" in msg_lower:
        # Both pacs.010 variants (Interbank Direct Debit and Margin Collection / v3)
        # share the CBPR+ pacs.010.001.03 namespace and the same generator.
        return _gen_pacs010(selected, idx)
    # CAMT generators
    elif "camt.057" in msg_lower:
        return _gen_camt057(selected, idx)
    elif "camt.052" in msg_lower:
        return _gen_camt052(selected, idx)
    elif "camt.053" in msg_lower:
        return _gen_camt053(selected, idx)
    elif "camt.054" in msg_lower:
        return _gen_camt054(selected, idx)
    elif "camt.055" in msg_lower:
        return _gen_camt055(selected, idx)
    elif "camt.056" in msg_lower:
        return _gen_camt056(selected, idx)
    # PAIN generators
    elif "pain.001" in msg_lower:
        return _gen_pain001(selected, idx)
    elif "pain.002" in msg_lower:
        return _gen_pain002(selected, idx)
    elif "pain.008" in msg_lower:
        return _gen_pain008(selected, idx)
    else:
        return _gen_pacs008(selected, idx)


# ── Main Generator ─────────────────────────────────────────────────────────────

def generate_bulk_messages(
    message_type: str,
    count: int,
    selected_blocks: List[str]
) -> List[Dict[str, Any]]:
    
    results = []
    for i in range(1, count + 1):
        try:
            xml = generate_single_xml(message_type, selected_blocks, i)
            results.append({
                "index": i,
                "xml": xml,
                "message_type": message_type,
                "status": "generated"
            })
        except Exception as e:
            results.append({
                "index": i,
                "xml": f"<!-- Generation error: {str(e)} -->",
                "message_type": message_type,
                "status": "error",
                "error": str(e)
            })

    return results
