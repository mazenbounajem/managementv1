BEGIN TRY
    BEGIN TRAN;

    -- Add cash_drawer_auxiliary_id column to customer_receipt if missing
    IF COL_LENGTH('dbo.customer_receipt', 'cash_drawer_auxiliary_id') IS NULL
    BEGIN
        ALTER TABLE dbo.customer_receipt ADD cash_drawer_auxiliary_id INT NULL;
    END;

    -- Add FK to auxiliary(id) if missing
    IF NOT EXISTS (
        SELECT 1 FROM sys.foreign_keys WHERE name = 'FK_customer_receipt_cash_drawer_auxiliary'
    ) AND EXISTS (
        SELECT 1 FROM sys.tables WHERE name = 'customer_receipt' AND schema_id = SCHEMA_ID('dbo')
    )
    BEGIN
        IF EXISTS (
            SELECT 1 FROM sys.tables WHERE name = 'auxiliary' AND schema_id = SCHEMA_ID('dbo')
        )
        BEGIN
            ALTER TABLE dbo.customer_receipt
            ADD CONSTRAINT FK_customer_receipt_cash_drawer_auxiliary
            FOREIGN KEY (cash_drawer_auxiliary_id) REFERENCES dbo.auxiliary(id);
        END
    END;

    COMMIT;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK;
    THROW;
END CATCH;
