"""
Bulk ISO 20022 Message Generator
Generates N valid randomized ISO 20022 messages based on selected message type and blocks.
"""
import uuid
import random
import string
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

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
COUNTRIES = ["US", "GB", "DE", "FR", "CH", "JP", "AU", "CA", "NL", "SE", "NO", "DK", "BE", "AT", "IT"]
BIC_BANK_CODES = [
    "AAAA", "BBBB", "CCCC", "DDDD", "EEEE", "FFFF", "GGGG", "HHHH", "IIII", "JJJJ",
    "KKKK", "MMMM", "NNNN", "PPPP", "QQQQ", "RRRR", "SSSS", "TTTT", "UUUU", "VVVV",
    "CITI", "HSBC", "DEUT", "BNPA", "UBSW", "CRED", "BARC", "RBOS", "LLOY", "INGB",
    "ABNA", "RABO", "TRIO", "WEST", "EAST", "NORT", "SOCY", "AGRI", "MUFG", "SMBC",
]
BIC_COUNTRIES = {
    "US": "33", "GB": "2L", "DE": "FF", "FR": "PP", "CH": "SS",
    "JP": "JT", "AU": "SS", "CA": "TT", "NL": "NL", "SE": "SS",
    "NO": "NO", "DK": "KK", "BE": "BB", "AT": "WW", "IT": "MM",
}
CHARGE_BEARERS = ["SLEV", "SHAR", "CRED", "DEBT"]
SETTLEMENT_METHODS = ["INDA", "INGA"]
RETURN_REASONS = ["AC01", "AC04", "AC06", "AG01", "AM04", "CUST", "FF01", "MD01", "MS03", "RR01"]
SERVICE_LEVELS = ["G001", "SDVA", "URGP", "NURG", "SEPA"]
PURPOSE_CODES = ["SALA", "SUPP", "TRAD", "CASH", "COLL", "INTC", "LOAN", "DIVD", "PENS", "OTHR"]
IBAN_COUNTRIES_GB = ["GB", "DE", "FR", "NL", "BE", "AT", "IT", "ES", "PT", "SE", "NO", "DK"]


# ── Random Data Generators ─────────────────────────────────────────────────────

def rng_bic(country_code: Optional[str] = None) -> str:
    """Generate a random valid BIC (11 chars: BANKCCLLXXX)."""
    bank = random.choice(BIC_BANK_CODES)
    if country_code and country_code in BIC_COUNTRIES:
        cc = country_code
        loc = BIC_COUNTRIES[country_code]
    else:
        cc = random.choice(list(BIC_COUNTRIES.keys()))
        loc = BIC_COUNTRIES[cc]
    return f"{bank}{cc}{loc}XXX"


def rng_iban(country: Optional[str] = None) -> str:
    """Generate a random IBAN."""
    c = country or random.choice(IBAN_COUNTRIES_GB)
    check = random.randint(10, 99)
    if c == "GB":
        bank = ''.join(random.choices(string.ascii_uppercase, k=4))
        sort = ''.join(random.choices(string.digits, k=6))
        acct = ''.join(random.choices(string.digits, k=8))
        return f"GB{check}{bank}{sort}{acct}"
    elif c == "DE":
        return f"DE{check}{''.join(random.choices(string.digits, k=18))}"
    elif c == "FR":
        return f"FR{check}{''.join(random.choices(string.digits, k=23))}"
    elif c == "NL":
        bank = ''.join(random.choices(string.ascii_uppercase, k=4))
        acct = ''.join(random.choices(string.digits, k=10))
        return f"NL{check}{bank}{acct}"
    else:
        return f"{c}{check}{''.join(random.choices(string.ascii_uppercase + string.digits, k=18))}"


def rng_amount(currency: str = "USD") -> str:
    """Generate a random valid amount string."""
    if currency == "JPY":
        return str(random.randint(10000, 9999999))
    base = random.uniform(100.0, 500000.0)
    return f"{base:.2f}"


def rng_date(offset_days: int = 0) -> str:
    d = datetime.now(timezone.utc) + timedelta(days=offset_days)
    return d.strftime("%Y-%m-%d")


def rng_datetime() -> str:
    d = datetime.now(timezone.utc)
    return d.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def rng_id(prefix: str = "", length: int = 16) -> str:
    chars = string.ascii_uppercase + string.digits
    return f"{prefix}{''.join(random.choices(chars, k=length))}"


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


def agent_xml(tag: str, bic: str, indent: int = 4) -> str:
    t = tabs(indent)
    t1 = tabs(indent + 1)
    t2 = tabs(indent + 2)
    return f"{t}<{tag}>\n{t1}<FinInstnId>\n{t2}<BICFI>{xe(bic)}</BICFI>\n{t1}</FinInstnId>\n{t}</{tag}>\n"


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
    t2 = tabs(indent + 2)
    content = f"{t1}<Nm>{xe(name)}</Nm>\n"
    content += f"{t1}<PstlAdr>\n{t2}<Ctry>{xe(country)}</Ctry>\n{t1}</PstlAdr>\n"
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
        {"id": "debtor",                     "label": "Debtor",                      "mandatory": False},
        {"id": "debtor_account",             "label": "Debtor Account",              "mandatory": False, "requires": ["debtor"]},
        {"id": "debtor_agent",               "label": "Debtor Agent",                "mandatory": False},
        {"id": "debtor_agent_account",       "label": "Debtor Agent Account",        "mandatory": False, "requires": ["debtor_agent"]},
        {"id": "creditor_agent",             "label": "Creditor Agent",              "mandatory": False},
        {"id": "creditor_agent_account",     "label": "Creditor Agent Account",      "mandatory": False, "requires": ["creditor_agent"]},
        {"id": "creditor",                   "label": "Creditor",                    "mandatory": False},
        {"id": "creditor_account",           "label": "Creditor Account",            "mandatory": False, "requires": ["creditor"]},
        {"id": "previous_instructing_agent_1","label": "Previous Instructing Agent 1","mandatory": False},
        {"id": "previous_instructing_agent_2","label": "Previous Instructing Agent 2","mandatory": False, "requires": ["previous_instructing_agent_1"]},
        {"id": "previous_instructing_agent_3","label": "Previous Instructing Agent 3","mandatory": False, "requires": ["previous_instructing_agent_2"]},
        {"id": "intermediary_agent_1",       "label": "Intermediary Agent 1",        "mandatory": False},
        {"id": "intermediary_agent_1_account","label": "Intermediary Agent 1 Account","mandatory": False, "requires": ["intermediary_agent_1"]},
        {"id": "intermediary_agent_2",       "label": "Intermediary Agent 2",        "mandatory": False, "requires": ["intermediary_agent_1"]},
        {"id": "intermediary_agent_2_account","label": "Intermediary Agent 2 Account","mandatory": False, "requires": ["intermediary_agent_2"]},
        {"id": "intermediary_agent_3",       "label": "Intermediary Agent 3",        "mandatory": False, "requires": ["intermediary_agent_2"]},
        {"id": "intermediary_agent_3_account","label": "Intermediary Agent 3 Account","mandatory": False, "requires": ["intermediary_agent_3"]},
        {"id": "ultimate_debtor",            "label": "Ultimate Debtor",             "mandatory": False},
        {"id": "ultimate_creditor",          "label": "Ultimate Creditor",           "mandatory": False},
        {"id": "payment_type_information",   "label": "Payment Type Information",    "mandatory": False},
        {"id": "remittance_information",     "label": "Remittance Information",      "mandatory": False},
        {"id": "charges_information",        "label": "Charges Information",         "mandatory": False},
        {"id": "settlement_time_request",    "label": "Settlement Time Request",     "mandatory": False},
    ],
    "pacs.009.cov": [
        {"id": "instructing_agent",          "label": "Instructing Agent",           "mandatory": True},
        {"id": "instructed_agent",           "label": "Instructed Agent",            "mandatory": True},
        {"id": "debtor",                     "label": "Debtor",                      "mandatory": False},
        {"id": "debtor_account",             "label": "Debtor Account",              "mandatory": False, "requires": ["debtor"]},
        {"id": "debtor_agent",               "label": "Debtor Agent",                "mandatory": False},
        {"id": "debtor_agent_account",       "label": "Debtor Agent Account",        "mandatory": False, "requires": ["debtor_agent"]},
        {"id": "creditor_agent",             "label": "Creditor Agent",              "mandatory": False},
        {"id": "creditor_agent_account",     "label": "Creditor Agent Account",      "mandatory": False, "requires": ["creditor_agent"]},
        {"id": "creditor",                   "label": "Creditor",                    "mandatory": False},
        {"id": "creditor_account",           "label": "Creditor Account",            "mandatory": False, "requires": ["creditor"]},
        {"id": "previous_instructing_agent_1","label": "Previous Instructing Agent 1","mandatory": False},
        {"id": "intermediary_agent_1",       "label": "Intermediary Agent 1",        "mandatory": False},
        {"id": "intermediary_agent_1_account","label": "Intermediary Agent 1 Account","mandatory": False, "requires": ["intermediary_agent_1"]},
        {"id": "intermediary_agent_2",       "label": "Intermediary Agent 2",        "mandatory": False, "requires": ["intermediary_agent_1"]},
        {"id": "intermediary_agent_2_account","label": "Intermediary Agent 2 Account","mandatory": False, "requires": ["intermediary_agent_2"]},
        {"id": "intermediary_agent_3",       "label": "Intermediary Agent 3",        "mandatory": False, "requires": ["intermediary_agent_2"]},
        {"id": "ultimate_debtor",            "label": "Ultimate Debtor",             "mandatory": False},
        {"id": "ultimate_creditor",          "label": "Ultimate Creditor",           "mandatory": False},
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
}


def get_blocks_for_message(msg_type: str) -> List[Dict]:
    key = msg_type.lower().replace(" ", ".").replace("pacs.009.001.08 cov", "pacs.009.cov").replace("pacs.009cov", "pacs.009.cov")
    # Normalise
    if "pacs.008" in key:
        return MESSAGE_BLOCKS["pacs.008"]
    if "pacs.009" in key and "cov" in key:
        return MESSAGE_BLOCKS["pacs.009.cov"]
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
    return MESSAGE_BLOCKS.get("pacs.008", [])


# ── Pacs.008 Generator ─────────────────────────────────────────────────────────

def _gen_pacs008(selected: set, idx: int) -> str:
    ccy = rng_currency()
    from_bic = rng_bic("US")
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
    debtor_ctry = rng_country()
    creditor_ctry = rng_country()
    debtor_bic = rng_bic()
    creditor_bic = rng_bic()
    instg_bic = from_bic
    instd_bic = to_bic
    debtor_iban = rng_iban()
    creditor_iban = rng_iban()

    # Transaction XML
    tx = ""

    # PmtTpInf
    if "payment_type_information" in selected:
        svc = random.choice(SERVICE_LEVELS)
        tx += f"\t\t\t\t<PmtTpInf>\n\t\t\t\t\t<SvcLvl>\n\t\t\t\t\t\t<Cd>{svc}</Cd>\n\t\t\t\t\t</SvcLvl>\n\t\t\t\t</PmtTpInf>\n"

    tx += f"\t\t\t\t<IntrBkSttlmAmt Ccy=\"{xe(ccy)}\">{amount}</IntrBkSttlmAmt>\n"
    tx += el("IntrBkSttlmDt", sttlm_dt, 4)
    tx += el("ChrgBr", charge_br, 4)

    # ChrgsInf
    if "charges_information" in selected:
        chg_ccy = ccy
        chg_amt = rng_amount(chg_ccy)
        chg_bic = rng_bic()
        tx += (f"\t\t\t\t<ChrgsInf>\n"
               f"\t\t\t\t\t<Amt Ccy=\"{xe(chg_ccy)}\">{chg_amt}</Amt>\n"
               f"\t\t\t\t\t<Agt>\n\t\t\t\t\t\t<FinInstnId>\n\t\t\t\t\t\t\t<BICFI>{xe(chg_bic)}</BICFI>\n"
               f"\t\t\t\t\t\t</FinInstnId>\n\t\t\t\t\t</Agt>\n\t\t\t\t</ChrgsInf>\n")

    # PrvsInstgAgt1/2/3
    if "previous_instructing_agent_1" in selected:
        tx += agent_xml("PrvsInstgAgt1", rng_bic(), 4)
    if "previous_instructing_agent_2" in selected:
        tx += agent_xml("PrvsInstgAgt2", rng_bic(), 4)
    if "previous_instructing_agent_3" in selected:
        tx += agent_xml("PrvsInstgAgt3", rng_bic(), 4)

    # InstgAgt / InstdAgt at txn level
    if "instructing_agent" in selected:
        tx += agent_xml("InstgAgt", instg_bic, 4)
    if "instructed_agent" in selected:
        tx += agent_xml("InstdAgt", instd_bic, 4)

    # IntrmyAgts
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

    # SttlmTmReq
    if "settlement_time_request" in selected:
        tx += f"\t\t\t\t<SttlmTmReq>\n\t\t\t\t\t<CLSTm>14:00:00.000Z</CLSTm>\n\t\t\t\t</SttlmTmReq>\n"

    # UltmtDbtr
    if "ultimate_debtor" in selected:
        tx += party_xml("UltmtDbtr", rng_name(), rng_country(), 4)

    # Dbtr, DbtrAcct, DbtrAgt, DbtrAgtAcct
    if "debtor" in selected:
        tx += party_xml("Dbtr", debtor_name, debtor_ctry, 4)
    if "debtor_account" in selected:
        tx += account_xml("DbtrAcct", debtor_iban, 4)
    if "debtor_agent" in selected:
        tx += agent_xml("DbtrAgt", debtor_bic, 4)
    if "debtor_agent_account" in selected:
        tx += account_othr_xml("DbtrAgtAcct", rng_id("ACCT", 10), 4)

    # CdtrAgt, CdtrAgtAcct, Cdtr, CdtrAcct, UltmtCdtr
    if "creditor_agent" in selected:
        tx += agent_xml("CdtrAgt", creditor_bic, 4)
    if "creditor_agent_account" in selected:
        tx += account_othr_xml("CdtrAgtAcct", rng_id("ACCT", 10), 4)
    if "creditor" in selected:
        tx += party_xml("Cdtr", creditor_name, creditor_ctry, 4)
    if "creditor_account" in selected:
        tx += account_xml("CdtrAcct", creditor_iban, 4)
    if "ultimate_creditor" in selected:
        tx += party_xml("UltmtCdtr", rng_name(), rng_country(), 4)

    # RmtInf
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

def _gen_pacs009(selected: set, idx: int, is_cov: bool = False) -> str:
    ccy = rng_currency()
    from_bic = rng_bic("US")
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

    tx = ""

    if "payment_type_information" in selected:
        svc = random.choice(SERVICE_LEVELS)
        tx += f"\t\t\t\t<PmtTpInf>\n\t\t\t\t\t<SvcLvl>\n\t\t\t\t\t\t<Cd>{svc}</Cd>\n\t\t\t\t\t</SvcLvl>\n\t\t\t\t</PmtTpInf>\n"

    tx += f"\t\t\t\t<IntrBkSttlmAmt Ccy=\"{xe(ccy)}\">{amount}</IntrBkSttlmAmt>\n"
    tx += el("IntrBkSttlmDt", sttlm_dt, 4)

    if "charges_information" in selected:
        chg_amt = rng_amount(ccy)
        chg_bic = rng_bic()
        tx += (f"\t\t\t\t<ChrgsInf>\n"
               f"\t\t\t\t\t<Amt Ccy=\"{xe(ccy)}\">{chg_amt}</Amt>\n"
               f"\t\t\t\t\t<Agt>\n\t\t\t\t\t\t<FinInstnId>\n\t\t\t\t\t\t\t<BICFI>{xe(chg_bic)}</BICFI>\n"
               f"\t\t\t\t\t\t</FinInstnId>\n\t\t\t\t\t</Agt>\n\t\t\t\t</ChrgsInf>\n")

    if "previous_instructing_agent_1" in selected:
        tx += agent_xml("PrvsInstgAgt1", rng_bic(), 4)
    if "previous_instructing_agent_2" in selected:
        tx += agent_xml("PrvsInstgAgt2", rng_bic(), 4)
    if "previous_instructing_agent_3" in selected:
        tx += agent_xml("PrvsInstgAgt3", rng_bic(), 4)

    if "instructing_agent" in selected:
        tx += agent_xml("InstgAgt", instg_bic, 4)
    if "instructed_agent" in selected:
        tx += agent_xml("InstdAgt", instd_bic, 4)

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

    if "settlement_time_request" in selected:
        tx += f"\t\t\t\t<SttlmTmReq>\n\t\t\t\t\t<CLSTm>14:00:00.000Z</CLSTm>\n\t\t\t\t</SttlmTmReq>\n"

    if "ultimate_debtor" in selected:
        tx += party_xml("UltmtDbtr", rng_name(), rng_country(), 4)
    if "debtor" in selected:
        tx += party_xml("Dbtr", rng_name(), rng_country(), 4)
    if "debtor_account" in selected:
        tx += account_xml("DbtrAcct", rng_iban(), 4)
    if "debtor_agent" in selected:
        tx += agent_xml("DbtrAgt", rng_bic(), 4)
    if "debtor_agent_account" in selected:
        tx += account_othr_xml("DbtrAgtAcct", rng_id("ACCT", 10), 4)

    if "creditor_agent" in selected:
        tx += agent_xml("CdtrAgt", rng_bic(), 4)
    if "creditor_agent_account" in selected:
        tx += account_othr_xml("CdtrAgtAcct", rng_id("ACCT", 10), 4)
    if "creditor" in selected:
        tx += party_xml("Cdtr", rng_name(), rng_country(), 4)
    if "creditor_account" in selected:
        tx += account_xml("CdtrAcct", rng_iban(), 4)
    if "ultimate_creditor" in selected:
        tx += party_xml("UltmtCdtr", rng_name(), rng_country(), 4)

    if "remittance_information" in selected:
        tx += f"\t\t\t\t<RmtInf>\n\t\t\t\t\t<Ustrd>{xe(rng_id('REF', 16))}</Ustrd>\n\t\t\t\t</RmtInf>\n"

    # COV: add underlying customer credit transfer
    if is_cov and "underlying_customer_credit_transfer" in selected:
        cov_e2e = rng_id("COVE2E", 10)
        cov_tx = rng_id("COVTX", 10)
        cov_amt = rng_amount(ccy)
        cov_dbtr = rng_name()
        cov_cdtr = rng_name()
        cov_dbtr_iban = rng_iban()
        cov_cdtr_iban = rng_iban()
        cov_dbtr_bic = rng_bic()
        cov_cdtr_bic = rng_bic()
        tx += f"""\t\t\t\t<UndrlygCstmrCdtTrf>
\t\t\t\t\t<InitgPty><Nm>{xe(cov_dbtr)}</Nm></InitgPty>
\t\t\t\t\t<Dbtr><Nm>{xe(cov_dbtr)}</Nm><PstlAdr><Ctry>{rng_country()}</Ctry></PstlAdr></Dbtr>
\t\t\t\t\t<DbtrAcct><Id><IBAN>{xe(cov_dbtr_iban)}</IBAN></Id></DbtrAcct>
\t\t\t\t\t<DbtrAgt><FinInstnId><BICFI>{xe(cov_dbtr_bic)}</BICFI></FinInstnId></DbtrAgt>
\t\t\t\t\t<CdtrAgt><FinInstnId><BICFI>{xe(cov_cdtr_bic)}</BICFI></FinInstnId></CdtrAgt>
\t\t\t\t\t<Cdtr><Nm>{xe(cov_cdtr)}</Nm><PstlAdr><Ctry>{rng_country()}</Ctry></PstlAdr></Cdtr>
\t\t\t\t\t<CdtrAcct><Id><IBAN>{xe(cov_cdtr_iban)}</IBAN></Id></CdtrAcct>
\t\t\t\t\t<RmtInf><Ustrd>{xe(rng_id('COVREF', 10))}</Ustrd></RmtInf>
\t\t\t\t</UndrlygCstmrCdtTrf>
"""

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
\t\t<FinInstnCdtTrf>
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
\t\t</FinInstnCdtTrf>
\t</Document>
</BusMsgEnvlp>"""
    return xml


# ── Pacs.004 Generator ─────────────────────────────────────────────────────────

def _gen_pacs004(selected: set, idx: int) -> str:
    ccy = rng_currency()
    from_bic = rng_bic()
    to_bic = rng_bic()
    biz_msg_id = rng_id("BIZ", 16)
    msg_id = rng_id("MSG", 16)
    rtr_id = rng_id("RTR", 16)
    orig_e2e = rng_id("ORIE2E", 10)
    orig_tx = rng_id("ORITX", 10)
    orig_uetr = rng_uetr()
    uetr = rng_uetr()
    cre_dt = rng_datetime()
    sttlm_dt = rng_date(1)
    amount = rng_amount(ccy)
    rtr_reason = random.choice(RETURN_REASONS)

    tx = ""

    if "instructing_agent" in selected:
        tx += agent_xml("InstgAgt", from_bic, 4)
    if "instructed_agent" in selected:
        tx += agent_xml("InstdAgt", to_bic, 4)
    if "ultimate_debtor" in selected:
        tx += party_xml("UltmtDbtr", rng_name(), rng_country(), 4)

    # RtrChain
    chain = ""
    if "debtor_agent" in selected:
        chain += agent_xml("DbtrAgt", rng_bic(), 5)
    if "debtor" in selected:
        chain += party_xml("Dbtr", rng_name(), rng_country(), 5)
    if "debtor_account" in selected:
        chain += account_xml("DbtrAcct", rng_iban(), 5)
    if "creditor_agent" in selected:
        chain += agent_xml("CdtrAgt", rng_bic(), 5)
    if "creditor" in selected:
        chain += party_xml("Cdtr", rng_name(), rng_country(), 5)
    if "creditor_account" in selected:
        chain += account_xml("CdtrAcct", rng_iban(), 5)
    if chain:
        tx += f"\t\t\t\t<RtrChain>\n{chain}\t\t\t\t</RtrChain>\n"

    if "ultimate_creditor" in selected:
        tx += party_xml("UltmtCdtr", rng_name(), rng_country(), 4)

    tx += f"\t\t\t\t<RtrRsnInf>\n\t\t\t\t\t<Rsn>\n\t\t\t\t\t\t<Cd>{xe(rtr_reason)}</Cd>\n\t\t\t\t\t</Rsn>\n\t\t\t\t</RtrRsnInf>\n"

    if "charges_information" in selected:
        chg_amt = rng_amount(ccy)
        chg_bic = rng_bic()
        tx += (f"\t\t\t\t<ChrgsInf>\n"
               f"\t\t\t\t\t<Amt Ccy=\"{xe(ccy)}\">{chg_amt}</Amt>\n"
               f"\t\t\t\t\t<Agt>\n\t\t\t\t\t\t<FinInstnId>\n\t\t\t\t\t\t\t<BICFI>{xe(chg_bic)}</BICFI>\n"
               f"\t\t\t\t\t\t</FinInstnId>\n\t\t\t\t\t</Agt>\n\t\t\t\t</ChrgsInf>\n")

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
\t\t\t\t<OrgnlEndToEndId>{xe(orig_e2e)}</OrgnlEndToEndId>
\t\t\t\t<OrgnlTxId>{xe(orig_tx)}</OrgnlTxId>
\t\t\t\t<OrgnlUETR>{xe(orig_uetr)}</OrgnlUETR>
\t\t\t\t<RtrdIntrBkSttlmAmt Ccy="{xe(ccy)}">{amount}</RtrdIntrBkSttlmAmt>
\t\t\t\t<IntrBkSttlmDt>{xe(sttlm_dt)}</IntrBkSttlmDt>
{tx}\t\t\t</TxInf>
\t\t</PmtRtr>
\t</Document>
</BusMsgEnvlp>"""
    return xml


# ── Pacs.003 Generator ─────────────────────────────────────────────────────────

def _gen_pacs003(selected: set, idx: int) -> str:
    ccy = rng_currency()
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
    tx += el("ChrgBr", random.choice(CHARGE_BEARERS), 4)

    if "charges_information" in selected:
        chg_amt = rng_amount(ccy)
        chg_bic = rng_bic()
        tx += (f"\t\t\t\t<ChrgsInf>\n"
               f"\t\t\t\t\t<Amt Ccy=\"{xe(ccy)}\">{chg_amt}</Amt>\n"
               f"\t\t\t\t\t<Agt>\n\t\t\t\t\t\t<FinInstnId>\n\t\t\t\t\t\t\t<BICFI>{xe(chg_bic)}</BICFI>\n"
               f"\t\t\t\t\t\t</FinInstnId>\n\t\t\t\t\t</Agt>\n\t\t\t\t</ChrgsInf>\n")

    if "instructing_agent" in selected:
        tx += agent_xml("InstgAgt", from_bic, 4)
    if "instructed_agent" in selected:
        tx += agent_xml("InstdAgt", to_bic, 4)

    if "ultimate_debtor" in selected:
        tx += party_xml("UltmtDbtr", rng_name(), rng_country(), 4)
    if "debtor" in selected:
        tx += party_xml("Dbtr", rng_name(), rng_country(), 4)
    if "debtor_account" in selected:
        tx += account_xml("DbtrAcct", rng_iban(), 4)
    if "debtor_agent" in selected:
        tx += agent_xml("DbtrAgt", rng_bic(), 4)
    if "creditor_agent" in selected:
        cdtr_agt_bic = rng_bic()
        tx += agent_xml("CdtrAgt", cdtr_agt_bic, 4)
        if "creditor_agent_account" in selected:
            tx += account_othr_xml("CdtrAgtAcct", rng_id("ACCT", 10), 4)
    if "creditor" in selected:
        tx += party_xml("Cdtr", rng_name(), rng_country(), 4)
    if "creditor_account" in selected:
        tx += account_xml("CdtrAcct", rng_iban(), 4)
    if "ultimate_creditor" in selected:
        tx += party_xml("UltmtCdtr", rng_name(), rng_country(), 4)

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
\t\t\t\t<DrctDbtTx>
\t\t\t\t\t<MndtRltdInf>
\t\t\t\t\t\t<MndtId>{xe(mndt_id)}</MndtId>
\t\t\t\t\t\t<DtOfSgntr>{rng_date(-30)}</DtOfSgntr>
\t\t\t\t\t</MndtRltdInf>
\t\t\t\t</DrctDbtTx>
{tx}\t\t\t</DrctDbtTxInf>
\t\t</FIToFICstmrDrctDbt>
\t</Document>
</BusMsgEnvlp>"""
    return xml


# ── Pacs.002 Generator ─────────────────────────────────────────────────────────

def _gen_pacs002(selected: set, idx: int) -> str:
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

    tx = ""
    if "instructing_agent" in selected:
        tx += agent_xml("InstgAgt", from_bic, 4)
    if "instructed_agent" in selected:
        tx += agent_xml("InstdAgt", to_bic, 4)
    if "debtor" in selected:
        tx += party_xml("OrgnlDbtr", rng_name(), rng_country(), 4)
    if "creditor" in selected:
        tx += party_xml("OrgnlCdtr", rng_name(), rng_country(), 4)

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
{tx}\t\t\t</GrpHdr>
\t\t\t<TxInfAndSts>
\t\t\t\t<OrgnlGrpInf>
\t\t\t\t\t<OrgnlMsgId>{xe(orig_msg_id)}</OrgnlMsgId>
\t\t\t\t\t<OrgnlMsgNmId>pacs.008.001.08</OrgnlMsgNmId>
\t\t\t\t</OrgnlGrpInf>
\t\t\t\t<OrgnlEndToEndId>{xe(orig_e2e)}</OrgnlEndToEndId>
\t\t\t\t<OrgnlTxId>{xe(orig_tx)}</OrgnlTxId>
\t\t\t\t<OrgnlUETR>{xe(orig_uetr)}</OrgnlUETR>
\t\t\t\t<TxSts>{xe(status)}</TxSts>
{reject_reason}\t\t\t</TxInfAndSts>
\t\t</FIToFIPmtStsRpt>
\t</Document>
</BusMsgEnvlp>"""
    return xml


# ── Pacs.010 Generator ─────────────────────────────────────────────────────────

def _gen_pacs010(selected: set, idx: int, v3: bool = False) -> str:
    ccy = rng_currency()
    from_bic = rng_bic()
    to_bic = rng_bic()
    biz_msg_id = rng_id("BIZ", 16)
    msg_id = rng_id("MSG", 16)
    instr_id = rng_id("INSTR", 11)
    e2e_id = rng_id("E2E", 16)
    tx_id = rng_id("TX", 16)
    uetr = rng_uetr()
    cre_dt = rng_datetime()
    sttlm_dt = rng_date(1)
    amount = rng_amount(ccy)

    ns = "urn:iso:std:iso:20022:tech:xsd:pacs.010.001.03" if v3 else "urn:iso:std:iso:20022:tech:xsd:pacs.010.001.10"
    msg_def = "pacs.010.001.03" if v3 else "pacs.010.001.10"

    tx = ""

    if "payment_type_information" in selected:
        svc = random.choice(SERVICE_LEVELS)
        tx += f"\t\t\t\t<PmtTpInf>\n\t\t\t\t\t<SvcLvl>\n\t\t\t\t\t\t<Cd>{svc}</Cd>\n\t\t\t\t\t</SvcLvl>\n\t\t\t\t</PmtTpInf>\n"

    tx += f"\t\t\t\t<IntrBkSttlmAmt Ccy=\"{xe(ccy)}\">{amount}</IntrBkSttlmAmt>\n"
    tx += el("IntrBkSttlmDt", sttlm_dt, 4)

    if "instructing_agent" in selected:
        tx += agent_xml("InstgAgt", from_bic, 4)
    if "instructed_agent" in selected:
        tx += agent_xml("InstdAgt", to_bic, 4)
    if "debtor_agent" in selected:
        tx += agent_xml("DbtrAgt", rng_bic(), 4)
    if "debtor" in selected:
        tx += party_xml("Dbtr", rng_name(), rng_country(), 4)
    if "debtor_account" in selected:
        tx += account_xml("DbtrAcct", rng_iban(), 4)
    if "creditor_agent" in selected:
        tx += agent_xml("CdtrAgt", rng_bic(), 4)
    if "creditor" in selected:
        tx += party_xml("Cdtr", rng_name(), rng_country(), 4)
    if "creditor_account" in selected:
        tx += account_xml("CdtrAcct", rng_iban(), 4)

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
\t\t<MsgDefIdr>{msg_def}</MsgDefIdr>
\t\t<BizSvc>swift.cbprplus.02</BizSvc>
\t\t<CreDt>{cre_dt}</CreDt>
\t</AppHdr>
\t<Document xmlns="{ns}">
\t\t<FIToFIFincInstrFwd>
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
\t\t</FIToFIFincInstrFwd>
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
    msg_lower = message_type.lower()
    if "pacs.008" in msg_lower:
        return _gen_pacs008(selected, idx)
    elif "pacs.009" in msg_lower and "cov" in msg_lower:
        return _gen_pacs009(selected, idx, is_cov=True)
    elif "pacs.009" in msg_lower:
        return _gen_pacs009(selected, idx, is_cov=False)
    elif "pacs.004" in msg_lower:
        return _gen_pacs004(selected, idx)
    elif "pacs.003" in msg_lower:
        return _gen_pacs003(selected, idx)
    elif "pacs.002" in msg_lower:
        return _gen_pacs002(selected, idx)
    elif "pacs.010" in msg_lower and ("001.03" in msg_lower or "v3" in msg_lower):
        return _gen_pacs010(selected, idx, v3=True)
    elif "pacs.010" in msg_lower:
        return _gen_pacs010(selected, idx, v3=False)
    else:
        return _gen_pacs008(selected, idx)


# ── Main Generator ─────────────────────────────────────────────────────────────

def generate_bulk_messages(
    message_type: str,
    count: int,
    selected_blocks: List[str]
) -> List[Dict[str, Any]]:
    """
    Generate `count` ISO 20022 messages of the given type with selected optional blocks.
    Returns list of dicts: {index, xml, biz_msg_id, uetr}.
    """
    selected = set(b.lower() for b in selected_blocks)
    results = []
    msg_lower = message_type.lower()

    for i in range(1, count + 1):
        try:
            if "pacs.008" in msg_lower:
                xml = _gen_pacs008(selected, i)
            elif "pacs.009" in msg_lower and "cov" in msg_lower:
                xml = _gen_pacs009(selected, i, is_cov=True)
            elif "pacs.009" in msg_lower:
                xml = _gen_pacs009(selected, i, is_cov=False)
            elif "pacs.004" in msg_lower:
                xml = _gen_pacs004(selected, i)
            elif "pacs.003" in msg_lower:
                xml = _gen_pacs003(selected, i)
            elif "pacs.002" in msg_lower:
                xml = _gen_pacs002(selected, i)
            elif "pacs.010" in msg_lower and ("001.03" in msg_lower or "v3" in msg_lower):
                xml = _gen_pacs010(selected, i, v3=True)
            elif "pacs.010" in msg_lower:
                xml = _gen_pacs010(selected, i, v3=False)
            else:
                xml = _gen_pacs008(selected, i)

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
