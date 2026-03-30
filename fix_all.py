import re
import os

files = [
    "customer_payment_ui.py",
    "supplier_payment_ui_fixed_v2.py",
    "expenses.py",
    "expensestype.py",
    "currencies.py",
    "accounting_finance.py",
    "cashdrawer_ui.py",
    "ledgerui.py",
    "auxiliaryui.py",
    "journal_voucher_ui.py",
    "voucher_subtype_ui.py",
    "roles.py",
    "appointments_ui.py",
    "services_ui.py"
]

def process_file(file):
    with open(file, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Remove manual creation of navigation
    # Example: 
    # navigation = EnhancedNavigation(...)
    # navigation.create_navigation_drawer()
    # navigation.create_navigation_header()
    content = re.sub(r'[ \t]*navigation\s*=\s*EnhancedNavigation\(permissions,\s*user\)\n[ \t]*navigation\.create_navigation_drawer\(\)\n[ \t]*navigation\.create_navigation_header\(\)\n', '', content)

    # 2. Fix the standalone parameter in the route function
    # def roles_page_route(): -> def roles_page_route(standalone=False):
    # Only replace if it doesn't already have standalone
    content = re.sub(r'(def [a-zA-Z0-9_]+_page[a-zA-Z0-9_]*)\(\):', r'\1(standalone=False):', content)

    # 3. Pass standalone to ModernPageLayout
    # with ModernPageLayout("..."): -> with ModernPageLayout("...", standalone=standalone):
    content = re.sub(r'(with ModernPageLayout\("[^"]+"\))(:\s*\n)', r'\1, standalone=standalone\2', content)

    # 4. Remove duplicate decorators that just call the function.
    # Ex: @ui.page('/expenses')\ndef expenses_page_route():\n    expenses_page()
    # Let's just fix it if it exists.
    duplicate_pattern = re.compile(r'@ui\.page\(\'[^\']+\'\)\n+def [a-zA-Z0-9_]+_route\(\):\n+ {4}[a-zA-Z0-9_]+_page\(\)\n?')
    content = duplicate_pattern.sub('', content)

    with open(file, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Processed {file}")

for f in files:
    try:
        process_file(f)
    except Exception as e:
        print(f"Error {f}: {e}")
