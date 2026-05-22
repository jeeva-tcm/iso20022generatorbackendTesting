import os

search_dir = r"c:\Users\HP\Documents\ISO20022 Validator new\iso20022generatorbackend"
target = "ChrgsInf"

for root, dirs, files in os.walk(search_dir):
    for file in files:
        if file.endswith(".py"):
            path = os.path.join(root, file)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for idx, line in enumerate(f, 1):
                        if target in line or "ChargesInformation" in line or "RtrdInstdAmt" in line:
                            rel = os.path.relpath(path, search_dir)
                            print(f"{rel}:{idx}: {line.strip()}")
            except Exception as e:
                pass
