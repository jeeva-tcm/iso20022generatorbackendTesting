import re
from datetime import datetime

today_date = datetime.now().date()
print(f'Today: {today_date}')

xml = """<BusMsgEnvlp>
<AppHdr>
<CreDt>2026-02-01T10:35:00+00:00</CreDt>
</AppHdr>
<Document>
<CreDtTm>2026-02-01T10:35:00+00:00</CreDtTm>
<IntrBkSttlmDt>2026-02-01</IntrBkSttlmDt>
<SomeFutureDt>2026-12-31</SomeFutureDt>
<Amount>1500.00</Amount>
<BIC>BBBBUS33XXX</BIC>
</Document>
</BusMsgEnvlp>"""

xml_date_patt = re.compile(
    r'<([A-Za-z][A-Za-z0-9]*)>'
    r'\s*'
    r'(\d{4}-\d{2}-\d{2}'
    r'(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)?)'
    r'\s*'
    r'</\1>'
)

seen = set()
print()
errors = 0
for m in xml_date_patt.finditer(xml):
    tag = m.group(1)
    val = m.group(2).strip()
    if (tag, val) in seen:
        continue
    seen.add((tag, val))
    parsed = datetime.strptime(val[:10], '%Y-%m-%d').date()
    is_past = parsed < today_date
    line_num = xml.count('\n', 0, m.start()) + 1
    if is_past:
        errors += 1
        print(f'ERROR  Line {line_num:2d}  <{tag}> = {val!r}  -> PAST DATE (must be >= {today_date})')
    else:
        print(f'OK     Line {line_num:2d}  <{tag}> = {val!r}  -> future/today')

print()
print(f'Non-date fields (Amount, BIC) were correctly skipped (no match in pattern).')
print(f'Total past-date errors found: {errors}')
