import os
path = r"e:\managementv1\journal_voucher_ui.py"
with open(path, "r", encoding="utf-8", errors="ignore") as f:
    content = f.read()
# Clean the content: keep only ASCII and some symbols
clean_content = "".join(c for c in content if ord(c) < 128 or c in "\n\r\t")
print(f"Cleaned content length: {len(clean_content)}")
print(clean_content[2000:4000]) # Print a chunk around create_ui
