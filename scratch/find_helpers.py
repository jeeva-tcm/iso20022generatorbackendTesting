with open('app/services/bulk_generator.py', 'r') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'def party_xml' in l or 'def account_xml' in l or 'def agent_xml' in l:
        print(f"Line {i+1}: {l.strip()}")
        # print next 20 lines
        for j in range(i+1, min(i+35, len(lines))):
            print(f"  {j+1}: {lines[j]}", end='')
