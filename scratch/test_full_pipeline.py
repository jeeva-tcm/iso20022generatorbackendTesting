"""Run the FULL validate() pipeline end-to-end on both XMLs.
Confirms no rule crashes the engine and the original user XML still fails."""
import sys, os, asyncio
THIS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(THIS, ".."))
sys.path.insert(0, ROOT)

from app.services.validator import ISOValidator

async def main():
    v = ISOValidator()

    # User's XML
    user_xml = open(os.path.join(THIS, "user_sample.xml"), encoding="utf-8").read()
    rep = await v.validate(user_xml, mode="Full 1-3", message_type="Auto-detect")
    d = rep.to_dict()
    print(f"USER XML: status={d['status']}  errors={d['errors']}  warnings={d['warnings']}")
    print("  first 5 errors:")
    for issue in d.get("details", [])[:5]:
        if issue.get("severity") == "ERROR":
            print(f"   - {issue['code']}: {issue['message'][:90]}")
    assert d["status"] == "FAIL", "User XML must still FAIL"

    # Valid pacs.008 should pass our new rules (XSD might still complain about
    # cross-version edge cases, that's OK — we only assert no crash)
    good_xml = open(os.path.join(THIS, "valid_pacs008.xml"), encoding="utf-8").read()
    rep2 = await v.validate(good_xml, mode="Full 1-3", message_type="Auto-detect")
    d2 = rep2.to_dict()
    print(f"\nVALID pacs.008: status={d2['status']}  errors={d2['errors']}  warnings={d2['warnings']}")
    new_rule_ids = {
        'EMPTY_REQUIRED_CONTAINER', 'EMPTY_PARTY_CONTAINER', 'EMPTY_ACCOUNT_CONTAINER',
        'HEAD001_MSGDEFIDR_MISMATCH', 'HEAD001_BIZSVC_FORMAT', 'HEAD001_TZ_DRIFT',
        'PACS008_UETR_REQUIRED', 'PACS008_DBTRACCT_REQUIRED', 'PACS008_CDTRACCT_REQUIRED',
        'PACS008_CHRGBR_REQUIRED', 'PACS008_NO_LOOPBACK_BIC',
    }
    falsies = [i for i in d2.get("details", [])
               if i.get("code") in new_rule_ids and i.get("severity") == "ERROR"]
    if falsies:
        print("  UNEXPECTED ERRORS from new rules on valid XML:")
        for i in falsies:
            print(f"   - {i['code']}: {i['message'][:90]}")
    else:
        print("  No false-positive errors from new rules.")
    assert not falsies, "New rules false-positive on valid XML"

    print("\nFull pipeline smoke OK.")

asyncio.run(main())
