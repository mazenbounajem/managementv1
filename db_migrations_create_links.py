from database_manager import db_manager

def main():
    stmts = [
        """
        IF OBJECT_ID('purchase_invoice_account_links','U') IS NULL
        CREATE TABLE purchase_invoice_account_links (
            id INT IDENTITY(1,1) PRIMARY KEY,
            purchase_invoice_number NVARCHAR(50) NOT NULL,
            purchase_id INT NOT NULL,
            expense_aux_number NVARCHAR(50) NULL,
            discount_aux_number NVARCHAR(50) NULL,
            vat_aux_number NVARCHAR(50) NULL,
            created_at DATETIME DEFAULT GETDATE()
        );
        """,
        """
        IF OBJECT_ID('sales_invoice_account_links','U') IS NULL
        CREATE TABLE sales_invoice_account_links (
            id INT IDENTITY(1,1) PRIMARY KEY,
            sales_invoice_number NVARCHAR(50) NOT NULL,
            sale_id INT NOT NULL,
            revenue_aux_number NVARCHAR(50) NULL,
            discount_aux_number NVARCHAR(50) NULL,
            vat_aux_number NVARCHAR(50) NULL,
            created_at DATETIME DEFAULT GETDATE()
        );
        """
    ]

    for s in stmts:
        db_manager.execute_update(s)
    print("links_tables_created_or_exist")

if __name__ == "__main__":
    main()
