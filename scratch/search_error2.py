import os

directory = r'c:\Users\HP\Desktop\iso final'
for root, _, files in os.walk(directory):
    if '.venv' in root or '.git' in root or 'node_modules' in root:
        continue
    for file in files:
        if file.endswith(('.py', '.json', '.txt', '.ts', '.html', '.md')):
            path = os.path.join(root, file)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read().lower()
                    if "is not valid" in content and "it should be" in content:
                        print(f"FOUND IN: {path}")
            except Exception as e:
                pass
print("Search complete.")
