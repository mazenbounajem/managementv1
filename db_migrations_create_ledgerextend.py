from database_manager import db_manager

def main():
    # NOTE:
    # ledgerextend is used as a backend reporting index for extended ledger accounts
    # (e.g. 6011.<suffix>, 6019.<suffix>, 7011.<suffix>, 7090.<suffix>)
    # It must store debit/credit so reports can be generated directly from ledgerextend.

    stmts = [
        """
        IF OBJECT_ID('ledgerextend','U') IS NULL
        CREATE TABLE ledgerextend (
            id INT IDENTITY(1,1) PRIMARY KEY,
            ledger_root NVARCHAR(50) NOT NULL,
            extended_ledger_account NVARCHAR(50) NOT NULL,
            invoice_number NVARCHAR(50) NOT NULL,
            purchase_id INT NULL,
            sale_id INT NULL,
            suffix NVARCHAR(50) NULL,
            extended_account_number NVARCHAR(50) NULL,
            created_at DATETIME DEFAULT GETDATE(),

            -- Debit/Credit (for reporting drilldowns)
            debit DECIMAL(18,4) NOT NULL DEFAULT(0),
            credit DECIMAL(18,4) NOT NULL DEFAULT(0)
        );
        """,

        -- Add columns if the table already exists but missing debit/credit / extended_account_number / suffix.
        """
        IF OBJECT_ID('ledgerextend','U') IS NOT NULL
        BEGIN
            IF COL_LENGTH('ledgerextend','debit') IS NULL
                ALTER TABLE ledgerextend ADD debit DECIMAL(18,4) NOT NULL DEFAULT(0);

            IF COL_LENGTH('ledgerextend','credit') IS NULL
                ALTER TABLE ledgerextend ADD credit DECIMAL(18,4) NOT NULL DEFAULT(0);

            IF COL_LENGTH('ledgerextend','extended_account_number') IS NULL
                ALTER TABLE ledgerextend ADD extended_account_number NVARCHAR(50) NULL;

            IF COL_LENGTH('ledgerextend','suffix') IS NULL
                ALTER TABLE ledgerextend ADD suffix NVARCHAR(50) NULL;
        END
        """
    ]

    for s in stmts:
        db_manager.execute_update(s)

    print("ledgerextend_table_created_or_altered")

if __name__ == "__main__":
    main()
