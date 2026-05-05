
import pyodbc

conn = pyodbc.connect('Driver={SQL Server Native Client 11.0};Server=DESKTOP-Q7U1STD\\SQLEXPRESS02;Database=POSDB;Trusted_Connection=yes', autocommit=True)
cursor = conn.cursor()

pages = [
    'dashboard', 'timespend', 'sales', 'sales-returns', 'products', 'purchase', 
    'purchase-returns', 'stockoperations', 'category', 
    'customers', 'customerreceipt', 'suppliers', 'supplierpayment', 'expenses', 
    'expensestype', 'currencies', 'accounting', 'cash-drawer', 'ledger', 
    'auxiliary', 'journal_voucher', 'voucher_subtype', 'accounting-transactions', 
    'employees', 'company', 'roles', 'appointments', 'services', 'business-track', 
    'reports', 'statistical-reports', 'backup'
]

# Ensure we have these for role_id = 1 (typically Admin)
print("Restoring permissions for role_id = 1...")

for page in pages:
    cursor.execute("SELECT id FROM role_permissions WHERE role_id = 1 AND page_name = ?", (page,))
    result = cursor.fetchone()
    if not result:
        print(f"Missing permission for {page}, inserting...")
        cursor.execute("INSERT INTO role_permissions (role_id, page_name, can_access) VALUES (1, ?, 1)", (page,))
        
print("Permission restoration complete.")

cursor.close()
conn.close()
