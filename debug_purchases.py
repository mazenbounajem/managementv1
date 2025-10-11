from connection import connection
from purchase_service import PurchaseService

service = PurchaseService()

try:
    purchases_data = service.get_all_purchases()
    print(f"Service returned {len(purchases_data)} purchases")
    for p in purchases_data[:3]:
        print(f"  {p}")
except Exception as e:
    print(f"Error in get_all_purchases: {e}")

# Check if purchases table has data
purchases_count = []
connection.contogetrows("SELECT COUNT(*) FROM purchases", purchases_count)
print(f"Total purchases: {purchases_count[0][0] if purchases_count else 0}")

# Check suppliers
suppliers_count = []
connection.contogetrows("SELECT COUNT(*) FROM suppliers", suppliers_count)
print(f"Total suppliers: {suppliers_count[0][0] if suppliers_count else 0}")

# Check purchases with invalid supplier_id
invalid_suppliers = []
connection.contogetrows("SELECT p.id, p.supplier_id FROM purchases p LEFT JOIN suppliers s ON s.id = p.supplier_id WHERE s.id IS NULL", invalid_suppliers)
print(f"Purchases with invalid supplier_id: {len(invalid_suppliers)}")
for row in invalid_suppliers:
    print(f"  Purchase ID: {row[0]}, Supplier ID: {row[1]}")

# Get all purchases with join
all_purchases = []
connection.contogetrows("SELECT p.id, p.purchase_date, s.name, p.total_amount, p.invoice_number, p.payment_status FROM purchases p INNER JOIN suppliers s ON s.id = p.supplier_id ORDER BY p.id DESC", all_purchases)
print(f"Purchases with valid suppliers: {len(all_purchases)}")
for row in all_purchases[:5]:  # First 5
    print(f"  ID: {row[0]}, Date: {row[1]}, Supplier: {row[2]}, Total: {row[3]}, Invoice: {row[4]}, Status: {row[5]}")
