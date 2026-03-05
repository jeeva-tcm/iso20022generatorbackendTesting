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
    r = iban[4:] + iban[:4]
    n = ''.join(str(ord(c) - 55) if c.isalpha() else c for c in r)
    return int(n) % 97 == 1

def chk(raw):
    v = raw.strip().replace(' ', '').upper()
    if not IBAN_PATTERN.match(v): return 'FAIL:pattern'
    country = v[:2]
    if country not in IBAN_LENGTHS: return 'FAIL:unknown-country-' + country
    expected = IBAN_LENGTHS[country]
    if len(v) != expected: return 'FAIL:len=' + str(len(v)) + ',need=' + str(expected)
    if not m97(v): return 'FAIL:mod97'
    return 'PASS'

# (value, expected_result, description)
tests = [
    ('GB29NWBK60161331926819',   'PASS', 'Valid GB IBAN (22)'),
    ('DE89370400440532013000',   'PASS', 'Valid DE IBAN (22)'),
    ('NL91ABNA0417164300',       'PASS', 'Valid NL IBAN (18)'),
    ('FR7630006000011234567890189', 'PASS', 'Valid FR IBAN (27)'),
    ('DE75512108001245126199',   'PASS', 'User CdtrAcct - valid DE IBAN MOD97 OK'),
    ('DE755121080012451261998789798798789797097097097097970970709',
                                 'FAIL', 'User DbtrAcct - too long, fails pattern'),
    ('GB29NWBK60161331926818',   'FAIL', 'Bad check digit - MOD97 fails'),
    ('XX12345678901234',          'FAIL', 'Unknown country XX'),
    ('DE00370400440532013000',   'FAIL', 'DE IBAN with bad check digits 00'),
    ('gb29nwbk60161331926819',   'FAIL', 'Lowercase - fails pattern'),
    ('GB29 NWBK 6016 1331 9268 19', 'PASS', 'Spaces stripped then valid'),
]

all_ok = True
fail_count = 0
results = []

for val, exp, desc in tests:
    got = chk(val)
    actual = 'PASS' if got == 'PASS' else 'FAIL'
    ok = actual == exp
    if not ok:
        all_ok = False
        fail_count += 1
    results.append((ok, desc, got))

for ok, desc, got in results:
    label = '[PASS]' if ok else '[FAIL]'
    print(label + ' ' + desc + ' -> ' + got)

print('')
print('COUNTRIES LOADED: ' + str(len(IBAN_LENGTHS)))
print('RESULT: ALL PASS' if all_ok else 'RESULT: ' + str(fail_count) + ' FAILED')
