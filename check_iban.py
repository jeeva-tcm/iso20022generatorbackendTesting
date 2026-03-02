iban = 'GB98765432109876543210'
print(f'IBAN: {iban}')
print(f'Length: {len(iban)} (GB requires 22) -> {"OK" if len(iban)==22 else "FAIL"}')

# MOD-97 verification
rearranged = iban[4:] + iban[:4]
numeric = ''.join(str(ord(c)-55) if c.isalpha() else c for c in rearranged)
remainder = int(numeric) % 97
print(f'MOD-97 remainder: {remainder} (must be 1 to pass -> {"PASS" if remainder==1 else "FAIL"})')
print()

# Calculate what the correct check digits SHOULD be for BBAN 765432109876543210
bban = iban[4:]
candidate = bban + 'GB00'
numeric2 = ''.join(str(ord(c)-55) if c.isalpha() else c for c in candidate)
check = 98 - (int(numeric2) % 97)
check_str = str(check).zfill(2)
correct_iban = 'GB' + check_str + bban
print(f'=> To fix this IBAN, the correct check digits for BBAN "{bban}" would make:')
print(f'   {correct_iban}')
print()

# Note the structural issue with GB BBAN
print(f'NOTE: GB BBAN structure is: 4 ALPHA (bank code) + 6 NUMERIC (sort code) + 8 NUMERIC (account)')
print(f'  First 4 of this BBAN: "{bban[:4]}" are all DIGITS, should be letters like NWBK, BARC, HSBC')
print(f'  So this BBAN is not a structurally valid UK bank account either.')
print()

# Verify a known-good test IBAN
good = 'GB29NWBK60161331926819'
r2 = good[4:] + good[:4]
n2 = ''.join(str(ord(c)-55) if c.isalpha() else c for c in r2)
r_good = int(n2) % 97
print(f'Known-good test IBAN: {good}')
print(f'  MOD-97 = {r_good} -> {"VALID" if r_good==1 else "INVALID"}')
