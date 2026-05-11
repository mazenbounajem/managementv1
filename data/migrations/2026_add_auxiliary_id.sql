BEGIN TRY
    BEGIN TRAN;

    DECLARE @auxiliaryTable NVARCHAR(256) = N'dbo.auxiliary';

    -- Helper pattern: add column if missing
    -- dbo.customers
    IF COL_LENGTH('dbo.customers', 'auxiliary_id') IS NULL
    BEGIN
        ALTER TABLE dbo.customers ADD auxiliary_id INT NULL;
    END;

    IF NOT EXISTS (
        SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_customers_auxiliary'
    ) AND EXISTS (
        SELECT 1 FROM sys.tables WHERE name = 'customers' AND schema_id = SCHEMA_ID('dbo')
    )
    BEGIN
        IF EXISTS (
            SELECT 1 FROM sys.tables WHERE name = 'auxiliary' AND schema_id = SCHEMA_ID('dbo')
        )
        BEGIN
            ALTER TABLE dbo.customers
            ADD CONSTRAINT FK_customers_auxiliary
            FOREIGN KEY (auxiliary_id) REFERENCES dbo.auxiliary(id);
        END
    END;

    -- dbo.suppliers
    IF COL_LENGTH('dbo.suppliers', 'auxiliary_id') IS NULL
    BEGIN
        ALTER TABLE dbo.suppliers ADD auxiliary_id INT NULL;
    END;

    IF NOT EXISTS (
        SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_suppliers_auxiliary'
    ) AND EXISTS (
        SELECT 1 FROM sys.tables WHERE name = 'suppliers' AND schema_id = SCHEMA_ID('dbo')
    )
    BEGIN
        IF EXISTS (
            SELECT 1 FROM sys.tables WHERE name = 'auxiliary' AND schema_id = SCHEMA_ID('dbo')
        )
        BEGIN
            ALTER TABLE dbo.suppliers
            ADD CONSTRAINT FK_suppliers_auxiliary
            FOREIGN KEY (auxiliary_id) REFERENCES dbo.auxiliary(id);
        END
    END;

    -- dbo.customer_receipt
    IF COL_LENGTH('dbo.customer_receipt', 'auxiliary_id') IS NULL
    BEGIN
        ALTER TABLE dbo.customer_receipt ADD auxiliary_id INT NULL;
    END;

    IF NOT EXISTS (
        SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_customer_receipt_auxiliary'
    ) AND EXISTS (
        SELECT 1 FROM sys.tables WHERE name = 'customer_receipt' AND schema_id = SCHEMA_ID('dbo')
    )
    BEGIN
        IF EXISTS (
            SELECT 1 FROM sys.tables WHERE name = 'auxiliary' AND schema_id = SCHEMA_ID('dbo')
        )
        BEGIN
            ALTER TABLE dbo.customer_receipt
            ADD CONSTRAINT FK_customer_receipt_auxiliary
            FOREIGN KEY (auxiliary_id) REFERENCES dbo.auxiliary(id);
        END
    END;

    -- dbo.supplier_payment
    IF COL_LENGTH('dbo.supplier_payment', 'auxiliary_id') IS NULL
    BEGIN
        ALTER TABLE dbo.supplier_payment ADD auxiliary_id INT NULL;
    END;

    IF NOT EXISTS (
        SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_supplier_payment_auxiliary'
    ) AND EXISTS (
        SELECT 1 FROM sys.tables WHERE name = 'supplier_payment' AND schema_id = SCHEMA_ID('dbo')
    )
    BEGIN
        IF EXISTS (
            SELECT 1 FROM sys.tables WHERE name = 'auxiliary' AND schema_id = SCHEMA_ID('dbo')
        )
        BEGIN
            ALTER TABLE dbo.supplier_payment
            ADD CONSTRAINT FK_supplier_payment_auxiliary
            FOREIGN KEY (auxiliary_id) REFERENCES dbo.auxiliary(id);
        END
    END;

    -- dbo.products
    IF COL_LENGTH('dbo.products', 'auxiliary_id') IS NULL
    BEGIN
        ALTER TABLE dbo.products ADD auxiliary_id INT NULL;
    END;

    IF NOT EXISTS (
        SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_products_auxiliary'
    ) AND EXISTS (
        SELECT 1 FROM sys.tables WHERE name = 'products' AND schema_id = SCHEMA_ID('dbo')
    )
    BEGIN
        IF EXISTS (
            SELECT 1 FROM sys.tables WHERE name = 'auxiliary' AND schema_id = SCHEMA_ID('dbo')
        )
        BEGIN
            ALTER TABLE dbo.products
            ADD CONSTRAINT FK_products_auxiliary
            FOREIGN KEY (auxiliary_id) REFERENCES dbo.auxiliary(id);
        END
    END;

    -- dbo.cash_drawer
    IF COL_LENGTH('dbo.cash_drawer', 'auxiliary_id') IS NULL
    BEGIN
        ALTER TABLE dbo.cash_drawer ADD auxiliary_id INT NULL;
    END;

    IF NOT EXISTS (
        SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_cash_drawer_auxiliary'
    ) AND EXISTS (
        SELECT 1 FROM sys.tables WHERE name = 'cash_drawer' AND schema_id = SCHEMA_ID('dbo')
    )
    BEGIN
        IF EXISTS (
            SELECT 1 FROM sys.tables WHERE name = 'auxiliary' AND schema_id = SCHEMA_ID('dbo')
        )
        BEGIN
            ALTER TABLE dbo.cash_drawer
            ADD CONSTRAINT FK_cash_drawer_auxiliary
            FOREIGN KEY (auxiliary_id) REFERENCES dbo.auxiliary(id);
        END
    END;

    -- dbo.accounting_transaction
    IF COL_LENGTH('dbo.accounting_transaction', 'auxiliary_id') IS NULL
    BEGIN
        ALTER TABLE dbo.accounting_transaction ADD auxiliary_id INT NULL;
    END;

    IF NOT EXISTS (
        SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_accounting_transaction_auxiliary'
    ) AND EXISTS (
        SELECT 1 FROM sys.tables WHERE name = 'accounting_transaction' AND schema_id = SCHEMA_ID('dbo')
    )
    BEGIN
        IF EXISTS (
            SELECT 1 FROM sys.tables WHERE name = 'auxiliary' AND schema_id = SCHEMA_ID('dbo')
        )
        BEGIN
            ALTER TABLE dbo.accounting_transaction
            ADD CONSTRAINT FK_accounting_transaction_auxiliary
            FOREIGN KEY (auxiliary_id) REFERENCES dbo.auxiliary(id);
        END
    END;

    -- dbo.accounting_transaction_lines
    IF COL_LENGTH('dbo.accounting_transaction_lines', 'auxiliary_id') IS NULL
    BEGIN
        ALTER TABLE dbo.accounting_transaction_lines ADD auxiliary_id INT NULL;
    END;

    IF NOT EXISTS (
        SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_accounting_transaction_lines_auxiliary'
    ) AND EXISTS (
        SELECT 1 FROM sys.tables WHERE name = 'accounting_transaction_lines' AND schema_id = SCHEMA_ID('dbo')
    )
    BEGIN
        IF EXISTS (
            SELECT 1 FROM sys.tables WHERE name = 'auxiliary' AND schema_id = SCHEMA_ID('dbo')
        )
        BEGIN
            ALTER TABLE dbo.accounting_transaction_lines
            ADD CONSTRAINT FK_accounting_transaction_lines_auxiliary
            FOREIGN KEY (auxiliary_id) REFERENCES dbo.auxiliary(id);
        END
    END;

    COMMIT;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK;
    THROW;
END CATCH;
