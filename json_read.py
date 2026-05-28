import json
path = r"e:\managementv1\journal_voucher_ui.py"
with open(path, "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()
    for i in range(50, 150):
        if i < len(lines):
            print(f"{i+1}: {json.dumps(lines[i])}")
