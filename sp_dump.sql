
CREATE PROCEDURE [dbo].[pb_run_fiscal_year_rollover]
    @p_current_year INT,
    @p_closing_date DATE
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @v_next_year INT = @p_current_year + 1;
    DECLARE @v_opening_date DATE = DATEADD(day, 1, @p_closing_date);
    DECLARE @v_jv_header_id_close INT;
    DECLARE @v_jv_header_id_open INT;
    DECLARE @v_net_profit_lbp DECIMAL(18,2) = 0.00;
    DECLARE @v_net_profit_usd DECIMAL(18,2) = 0.00;

    BEGIN TRANSACTION;
    BEGIN TRY

        -- PHASE 1: Calculate current year's net financial profit/loss (Class 7 - Class 6)
        SELECT 
            @v_net_profit_lbp = COALESCE(SUM(CASE WHEN account_code LIKE '7%' AND currency_code = 'LBP' THEN balance_credit - balance_debit ELSE 0 END), 0.00),
            @v_net_profit_usd = COALESCE(SUM(CASE WHEN account_code LIKE '7%' AND currency_code = 'USD' THEN balance_credit - balance_debit ELSE 0 END), 0.00)
        FROM (
            SELECT account_code, currency_code,
                   SUM(debit_amount) AS balance_debit, 
                   SUM(credit_amount) AS balance_credit
            FROM journal_lines
            WHERE fiscal_year = @p_current_year
            GROUP BY account_code, currency_code
        ) t;

        -- Create Year-End Closing Voucher Header
        INSERT INTO journal_headers (voucher_number, voucher_date, fiscal_year, description, status)
        VALUES ('JV-CLOSE-' + CAST(@p_current_year AS VARCHAR), @p_closing_date, @p_current_year, 'Year-End Closing Entry - Class 6 & 7', 'POSTED');
        
        SET @v_jv_header_id_close = SCOPE_IDENTITY();

        -- Clear Income Statement Accounts (Class 6 & 7) to Zero
        INSERT INTO journal_lines (header_id, fiscal_year, account_code, currency_code, debit_amount, credit_amount, line_description)
        SELECT 
            @v_jv_header_id_close,
            @p_current_year,
            account_code,
            currency_code,
            CASE WHEN account_code LIKE '7%' THEN (SUM(credit_amount) - SUM(debit_amount)) ELSE 0.00 END AS debit_amount,
            CASE WHEN account_code LIKE '6%' THEN (SUM(debit_amount) - SUM(credit_amount)) ELSE 0.00 END AS credit_amount,
            'Closing balance entry'
        FROM journal_lines
        WHERE fiscal_year = @p_current_year AND (account_code LIKE '6%' OR account_code LIKE '7%')
        GROUP BY account_code, currency_code
        HAVING (SUM(debit_amount) - SUM(credit_amount)) <> 0 OR (SUM(credit_amount) - SUM(debit_amount)) <> 0;

        -- Route net profit to Retained Earnings (Account 11100)
        IF @v_net_profit_lbp <> 0
        BEGIN
            INSERT INTO journal_lines (header_id, fiscal_year, account_code, currency_code, debit_amount, credit_amount, line_description)
            VALUES (@v_jv_header_id_close, @p_current_year, '11100', 'LBP', CASE WHEN @v_net_profit_lbp < 0 THEN ABS(@v_net_profit_lbp) ELSE 0.00 END, CASE WHEN @v_net_profit_lbp > 0 THEN @v_net_profit_lbp ELSE 0.00 END, 'Allocation of Net Profit/Loss LBP');
        END

        IF @v_net_profit_usd <> 0
        BEGIN
            INSERT INTO journal_lines (header_id, fiscal_year, account_code, currency_code, debit_amount, credit_amount, line_description)
            VALUES (@v_jv_header_id_close, @p_current_year, '11100', 'USD', CASE WHEN @v_net_profit_usd < 0 THEN ABS(@v_net_profit_usd) ELSE 0.00 END, CASE WHEN @v_net_profit_usd > 0 THEN @v_net_profit_usd ELSE 0.00 END, 'Allocation of Net Profit/Loss USD');
        END

        -- =========================================================================
        -- PHASE 2: Roll Over Permanent Balance Sheet Accounts (Class 1, 2, 3, 4, 5)
        -- =========================================================================
        INSERT INTO journal_headers (voucher_number, voucher_date, fiscal_year, description, status)
        VALUES ('JV-OPEN-' + CAST(@v_next_year AS VARCHAR), @v_opening_date, @v_next_year, 'Opening Balances Fiscal Year ' + CAST(@v_next_year AS VARCHAR), 'POSTED');
        
        SET @v_jv_header_id_open = SCOPE_IDENTITY();

        -- Migrate final active positions as the next year's opening markers
        INSERT INTO journal_lines (header_id, fiscal_year, account_code, sub_ledger_code, currency_code, debit_amount, credit_amount, line_description)
        SELECT 
            @v_jv_header_id_open,
            @v_next_year,
            account_code,
            sub_ledger_code,
            currency_code,
            CASE WHEN (SUM(debit_amount) - SUM(credit_amount)) > 0 THEN (SUM(debit_amount) - SUM(credit_amount)) ELSE 0.00 END,
            CASE WHEN (SUM(credit_amount) - SUM(debit_amount)) > 0 THEN (SUM(credit_amount) - SUM(debit_amount)) ELSE 0.00 END,
            'Opening Balance'
        FROM journal_lines
        WHERE fiscal_year = @p_current_year AND (account_code NOT LIKE '6%' AND account_code NOT LIKE '7%')
        GROUP BY account_code, sub_ledger_code, currency_code
        HAVING SUM(debit_amount) <> SUM(credit_amount); -- FIXED: Absolute safety for credit accounts

        -- Double Entry Validation Check
        DECLARE @v_check_debits DECIMAL(18,2);
        DECLARE @v_check_credits DECIMAL(18,2);

        SELECT @v_check_debits = COALESCE(SUM(debit_amount), 0.00), @v_check_credits = COALESCE(SUM(credit_amount), 0.00)
        FROM journal_lines WHERE header_id = @v_jv_header_id_open;

        IF @v_check_debits <> @v_check_credits
        BEGIN
            THROW 50001, 'CRITICAL CLOSING FAILURE: New Year Opening balances do not match.', 1;
        END

        COMMIT TRANSACTION;
        PRINT 'Fiscal Year successfully rolled over.';

    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW; 
    END CATCH
END;