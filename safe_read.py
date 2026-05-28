import os
path = r"e:\managementv1\journal_voucher_ui.py"
with open(path, "rb") as f:
    content = f.read()
print(f"File size: {len(content)}")
print(f"First 500 bytes: {content[:500]}")
# Replace \r\n with \n and \r with \n for printing
safe_content = content.decode('utf-8', errors='ignore').replace('\r\n', '\n').replace('\r', '\n')
lines = safe_content.split('\n')
for i, line in enumerate(lines[:100]):
    print(f"{i+1}: {line}")
