import os

directory = r'c:\Users\HP\Desktop\iso final\iso20022generatorfrontend\src'
for root, _, files in os.walk(directory):
    for file in files:
        if file.endswith(('.ts', '.html', '.json', '.scss')):
            path = os.path.join(root, file)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if "BankToCustomerDebitCreditNotification" in content or "The document's namespace" in content or "is not valid. It should be" in content:
                        print(f"FOUND IN FRONTEND: {path}")
            except Exception as e:
                pass
print("Frontend search complete.")
