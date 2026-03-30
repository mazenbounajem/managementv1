"""
SQL Server Script - Run in SSMS on POSDB
"""

SQL = """
-- Add remaining_balance to sales if missing
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('sales') AND name = 'remaining_balance')
BEGIN
    ALTER TABLE sales ADD remaining_balance DECIMAL(15,2) DEFAULT 0
    UPDATE sales SET remaining_balance = total_amount WHERE remaining_balance IS NULL
    PRINT '✅ remaining_balance added to sales'
END

-- Add to purchases if missing  
IF EXISTS (SELECT * FROM sys.tables WHERE name = 'purchases')
BEGIN
    IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = OBJECT_ID('purchases') AND name = 'remaining_balance')
    BEGIN
        ALTER TABLE purchases ADD remaining_balance DECIMAL(15,2) DEFAULT 0
        UPDATE purchases SET remaining_balance = total_amount WHERE remaining_balance IS NULL
        PRINT '✅ remaining_balance added to purchases'
    END
END
ELSE
    PRINT '⚠️  purchases table not found (supplier credits use suppliers.balance)'

-- Verify
SELECT 'sales' as TableName, COUNT(*) as PendingInvoices FROM sales WHERE payment_status = 'pending'
UNION ALL
SELECT 'purchases' as TableName, COUNT(*) as PendingInvoices FROM purchases WHERE payment_status = 'pending'
"""

print("✅ Copy below SQL to SSMS → POSDB → Execute")
print("="*80)
print(SQL)
print("="*80)
print("\nRun: python main.py → Test /customerreceipt & /supplierpayment")

