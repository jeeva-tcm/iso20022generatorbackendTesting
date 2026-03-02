import sys
sys.stdout.reconfigure(encoding='utf-8')
import re

IBAN_LENGTHS = {
    'AD':24,'AE':23,'AL':28,'AT':20,'AZ':28,'BA':20,'BE':16,'BF':28,
    'BG':22,'BH':22,'BI':27,'BJ':28,'BR':29,'BY':28,'CF':27,'CG':27,
    'CH':21,'CI':28,'CM':27,'CR':22,'CV':25,'CY':28,'CZ':24,'DE':22,
    'DJ':27,'DK':18,'DO':28,'DZ':26,'EE':20,'EG':29,'ES':24,'FI':18,
    'FK':18,'FO':18,'FR':27,'GA':27,'GB':22,'GE':22,'GI':23,'GL':18,
    'GN':26,'GQ':27,'GR':27,'GT':28,'GW':25,'HN':28,'HR':21,'HU':28,
    'IE':22,'IL':23,'IQ':23,'IR':26,'IS':26,'IT':27,'JO':30,'KM':27,
    'KW':30,'KZ':20,'LB':28,'LC':32,'LI':21,'LT':20,'LU':20,'LV':21,
    'LY':25,'MA':28,'MC':27,'MD':24,'ME':22,'MG':27,'MK':19,'ML':28,
    'MN':20,'MR':27,'MT':31,'MU':30,'MZ':25,'NE':28,'NI':32,'NL':18,
    'NO':15,'NZ':16,'PK':24,'PL':28,'PS':29,'PT':25,'QA':29,'RO':24,
    'RS':22,'RU':33,'SA':24,'SC':31,'SD':18,'SE':24,'SI':19,'SK':24,
    'SM':27,'SN':28,'SO':23,'ST':25,'SV':28,'TD':27,'TG':28,'TL':23,
    'TN':24,'TR':26,'UA':29,'VA':22,'VG':24,'XK':20,'YE':30,
}
IBAN_PATTERN = re.compile(r'^[A-Z]{2}[0-9]{2}[A-Z0-9]{1,30}$')

def m97(iban):
    r = iban[4:]+iban[:4]
    n = ''.join(str(ord(c)-55) if c.isalpha() else c for c in r)
    return int(n) % 97 == 1

def chk(v):
    v = v.strip().replace(' ', '').upper()
    if not IBAN_PATTERN.match(v): return 'FAIL:pattern'
    c = v[:2]
    if c not in IBAN_LENGTHS: return 'FAIL:unknown-country'
    e = IBAN_LENGTHS[c]
    if len(v) != e: return f'FAIL:len={len(v)},need={e}'
    if not m97(v): return 'FAIL:mod97'
    return 'PASS'

tests = [
    ('GB29NWBK60161331926819', 'PASS', 'Valid GB IBAN'),
    ('DE89370400440532013000', 'PASS', 'Valid DE IBAN'),
    ('NL91ABNA0417164300',     'PASS', 'Valid NL IBAN (18 chars)'),
    ('FR7630006000011234567890189', 'PASS', 'Valid FR IBAN (27 chars)'),
    ('DE755121080012451261998789798798789797097097097097970970709', 'FAIL', 'Too long - user DbtrAcct'),
    ('DE75512108001245126199', 'PASS', 'User CdtrAcct - valid 22-char DE IBAN'),
    ('GB29NWBK60161331926818', 'FAIL', 'Bad MOD-97 (last digit wrong)'),
    ('XX12345678901234',       'FAIL', 'Unknown country XX'),
    ('DE00370400440532013000', 'FAIL', 'MOD-97 fails (00 check digits)'),
    ('gb29nwbk60161331926819', 'FAIL', 'Lowercase -> pattern fail'),
    ('GB29 NWBK 6016 1331 9268 19', 'PASS', 'With spaces stripped -> valid'),
]

all_ok = True
print(f'Country table: {len(IBAN_LENGTHS)} countries loaded\n')
for v, exp, desc in tests:
    got = chk(v)
    actual = 'PASS' if got == 'PASS' else 'FAIL'
    ok = actual == exp
    if not ok:
        all_ok = False
    label = 'OK  ' if ok else 'FAIL'
    print(f'  [{label}] {desc}: {got}')

print()
print('RESULT: ALL PASS' if all_ok else 'RESULT: SOME TESTS FAILED')
