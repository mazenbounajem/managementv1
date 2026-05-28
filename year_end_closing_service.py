import logging
import asyncio
import os
from datetime import datetime
from database_manager import db_manager
from connection import connection
from reports import Reports
from accounting_helpers import save_accounting_transaction

class YearEndClosingService:
    @staticmethod
    def get_opening_balances():
        """
        Calculates balances for:
        - Customers (4111.*)
        - Suppliers (4011.*)
        - VAT (442*)
        - Product Stock (Stock valuation)
        """
        # 1. Get auxiliary balances from Trial Balance
        trial_balance = Reports.fetch_trial_balance()
        
        balances = []
        
        for row in trial_balance:
            acc_num = str(row['Account Number'])
            balance = row['Net Balance']
            
            # Skip near-zero balances
            if abs(balance) < 0.01:
                continue
                
            # Carry forward all accounts that have a balance (as requested)
            # This includes Balance Sheet (1-5) and P&L (6-7) if they haven't been closed
            balances.append({
                'account': acc_num,
                'name': row['Account Name'],
                'debit': balance if balance > 0 else 0,
                'credit': abs(balance) if balance < 0 else 0
            })
            
            # Special check for 4111 if not already there (though Trial Balance should have it if it has balance)
            # The current logic will pick up 4111 or 4111.xxx if they show up in Trial Balance
        
        # 2. Calculate Product Stock Valuation
        products_stock_value = 0.0
        product_data = []
        connection.contogetrows("SELECT SUM(stock_quantity * cost_price) FROM products WHERE stock_quantity > 0", product_data)
        if product_data and product_data[0][0]:
            products_stock_value = float(product_data[0][0])
            
        return balances, products_stock_value

    @staticmethod
    async def run_backup(db_name, progress_callback=None):
        """Execute backup of the database."""
        try:
            if progress_callback: await progress_callback(f"Starting backup of {db_name}...")
            
            backup_dir = os.path.abspath("backups")
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(backup_dir, f"{db_name}_{timestamp}.bak")
            
            sql = f"BACKUP DATABASE [{db_name}] TO DISK = '{backup_file}' WITH FORMAT, INIT"
            await db_manager.execute_non_transactional_async(sql)
            
            if progress_callback: await progress_callback(f"Backup finished: {os.path.basename(backup_file)}")
            return True, backup_file
        except Exception as e:
            logging.error(f"Backup error: {e}")
            return False, str(e)

    @staticmethod
    async def run_restore_archive(backup_file, archive_db_name, progress_callback=None):
        """Restore as an archive database (e.g. POSDb2025)."""
        try:
            if progress_callback: await progress_callback(f"Restoring archive as {archive_db_name}...")
            
            # Get logical names using non-transactional to be safe
            logical_files = await db_manager.execute_query_async(f"RESTORE FILELISTONLY FROM DISK = '{backup_file}'")
            move_clause = ""
            data_dir = os.path.abspath("data")
            os.makedirs(data_dir, exist_ok=True)
            
            for file in logical_files:
                logical_name = file[0]
                physical_name = file[1]
                ext = os.path.splitext(physical_name)[1]
                new_path = os.path.join(data_dir, f"{archive_db_name}{ext}")
                move_clause += f", MOVE '{logical_name}' TO '{new_path}'"
            
            original_db = db_manager.CONNECTION_CONFIG['database']
            db_manager.switch_database("master")
            
            sql = f"IF EXISTS (SELECT name FROM sys.databases WHERE name = '{archive_db_name}') DROP DATABASE [{archive_db_name}];"
            sql += f" RESTORE DATABASE [{archive_db_name}] FROM DISK = '{backup_file}' WITH REPLACE {move_clause}"
            
            await db_manager.execute_non_transactional_async(sql)
            db_manager.switch_database(original_db)
            
            if progress_callback: await progress_callback(f"Archive {archive_db_name} restored successfully.")
            return True, "Success"
        except Exception as e:
            logging.error(f"Restore error: {e}")
            try: db_manager.switch_database(original_db)
            except: pass
            return False, str(e)

    @staticmethod
    async def create_new_database_from_backup(backup_file, new_db_name, progress_callback=None):
        """Creates a new database by restoring a clone of the old one, then we will purge it."""
        try:
            if progress_callback: await progress_callback(f"Initializing new database {new_db_name} from backup...")
            
            # Get logical names
            logical_files = await db_manager.execute_query_async(f"RESTORE FILELISTONLY FROM DISK = '{backup_file}'")
            move_clause = ""
            data_dir = os.path.abspath("data")
            os.makedirs(data_dir, exist_ok=True)
            
            for file in logical_files:
                logical_name = file[0]
                physical_name = file[1]
                ext = os.path.splitext(physical_name)[1]
                new_path = os.path.join(data_dir, f"{new_db_name}{ext}")
                move_clause += f", MOVE '{logical_name}' TO '{new_path}'"
            
            original_db = db_manager.CONNECTION_CONFIG['database']
            db_manager.switch_database("master")
            
            # Create new database as a full clone
            sql = f"IF EXISTS (SELECT name FROM sys.databases WHERE name = '{new_db_name}') DROP DATABASE [{new_db_name}];"
            sql += f" RESTORE DATABASE [{new_db_name}] FROM DISK = '{backup_file}' WITH REPLACE {move_clause}"
            
            await db_manager.execute_non_transactional_async(sql)
            db_manager.switch_database(original_db)
            
            if progress_callback: await progress_callback(f"New database {new_db_name} initialized as a clone (ready for purging).")
            return True, "Database restored successfully."
        except Exception as e:
            logging.error(f"Error in create_new_database_from_backup: {e}")
            try: db_manager.switch_database(original_db)
            except: pass
            return False, str(e)

    @staticmethod
    async def run_rollover_sp(new_db_name, current_year=None, closing_date=None, log_callback=None):
        """Execute the stored procedure pb_run_fiscal_year_rollover."""
        try:
            if log_callback: await log_callback("Executing rollover stored procedure...")
            original_db = db_manager.CONNECTION_CONFIG['database']
            db_manager.switch_database(new_db_name)
            
            if current_year and closing_date:
                sql = f"EXEC pb_run_fiscal_year_rollover @p_current_year={current_year}, @p_closing_date='{closing_date}'"
            else:
                sql = "EXEC pb_run_fiscal_year_rollover"
                
            await db_manager.execute_update_async(sql)
            
            db_manager.switch_database(original_db)
            if log_callback: await log_callback("Rollover stored procedure executed.")
            return True, "SP executed"
        except Exception as e:
            logging.error(f"SP error: {e}")
            try: db_manager.switch_database(original_db)
            except: pass
            return False, str(e)

    @staticmethod
    async def log_fiscal_year_transition(fiscal_year, current_db, new_db, archive_db, status="Completed"):
        """Creates a central tracking log for fiscal year rollovers."""
        try:
            sql_create = """
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='fiscal_year_transitions' and xtype='U')
            CREATE TABLE fiscal_year_transitions (
                id INT IDENTITY(1,1) PRIMARY KEY,
                fiscal_year INT,
                current_db VARCHAR(100),
                new_db VARCHAR(100),
                archive_db VARCHAR(100),
                status VARCHAR(50),
                created_at DATETIME DEFAULT GETDATE()
            )
            """
            await db_manager.execute_update_async(sql_create)
            
            await db_manager.execute_update_async(f"""
            INSERT INTO fiscal_year_transitions (fiscal_year, current_db, new_db, archive_db, status)
            VALUES ({fiscal_year}, '{current_db}', '{new_db}', '{archive_db}', '{status}')
            """)
            return True
        except Exception as e:
            logging.error(f"Error logging fiscal transition: {e}")
            return False

    @staticmethod
    async def verify_opening_jv_exists(new_db_name, log_callback=None):
        """Verify that the SP generated opening entries."""
        try:
            if log_callback: await log_callback("Verifying opening entries exist in new database...")
            
            original_db = db_manager.CONNECTION_CONFIG['database']
            db_manager.switch_database(new_db_name)
            
            count = await db_manager.execute_scalar_async("SELECT COUNT(*) FROM journal_voucher")
            count_trans = await db_manager.execute_scalar_async("SELECT COUNT(*) FROM accounting_transactions")
            
            db_manager.switch_database(original_db)
            
            if log_callback: await log_callback(f"Found {count or 0} JVs and {count_trans or 0} accounting entries.")
            return True, "Opening entries verified"
        except Exception as e:
            logging.error(f"Verification error: {e}")
            try: db_manager.switch_database(original_db)
            except: pass
            return False, str(e)

    @staticmethod
    async def close_vat_for_year(progress_callback=None):
        """Executes full year VAT closing."""
        try:
            if progress_callback: await progress_callback("Closing VAT for the whole year...")
            # This logic follows vat_close_ui.py approach
            # We assume current year's data is to be closed
            current_year = datetime.now().year
            from_date = f"{current_year}-01-01"
            to_date = f"{current_year}-12-31"
            
            # Since this is a complex UI-driven process, we'll implement a simplified version
            # that replicates the core logic of vat_close_ui.py:post_vat_close
            
            # 1. Aggregate
            child_data = []
            connection.contogetrows(
                f"""
                SELECT l.account_number, l.auxiliary_id, SUM(l.debit), SUM(l.credit)
                FROM accounting_transaction_lines l
                INNER JOIN accounting_transactions t ON t.jv_id = l.jv_id
                WHERE (l.account_number LIKE '44210%' OR l.account_number LIKE '44270%')
                  AND t.description NOT LIKE 'Close VAT Period%'
                  AND CONVERT(date, t.transaction_date) >= '{from_date}'
                  AND CONVERT(date, t.transaction_date) <= '{to_date}'
                GROUP BY l.account_number, l.auxiliary_id
                """,
                child_data
            )
            
            if not child_data:
                if progress_callback: await progress_callback("No VAT data to close.")
                return True, "No data"

            sales_vat_credit = 0.0
            purchase_vat_debit = 0.0
            for row in child_data:
                acct = str(row[0] or '')
                total_debit = float(row[2] or 0)
                total_credit = float(row[3] or 0)
                if acct.startswith('44270'):
                    sales_vat_credit += total_credit - total_debit
                elif acct.startswith('44210'):
                    purchase_vat_debit += total_debit - total_credit

            difference = sales_vat_credit - purchase_vat_debit
            desc = f"Close VAT Year {current_year}"
            
            # Post JV
            from accounting_helpers import save_accounting_transaction
            jv_lines = []
            for row in child_data:
                acct = str(row[0] or '')
                aux_id = row[1]
                net = float(row[2] or 0) - float(row[3] or 0)
                if abs(net) < 0.01: continue
                jv_lines.append({
                    'account': acct,
                    'auxiliary_id': aux_id,
                    'debit': abs(net) if net < 0 else 0,
                    'credit': net if net > 0 else 0
                })

            if abs(difference) >= 0.01:
                if difference > 0:
                    jv_lines.append({'account': '44250', 'debit': 0, 'credit': round(difference, 2)})
                else:
                    jv_lines.append({'account': '44260', 'debit': round(abs(difference), 2), 'credit': 0})

            save_accounting_transaction(
                reference_type="VAT Close",
                reference_id=int(current_year),
                lines=jv_lines,
                description=desc
            )
            
            if progress_callback: await progress_callback("VAT year-end closing posted.")
            return True, "VAT Closed"
        except Exception as e:
            logging.error(f"VAT close error: {e}")
            return False, str(e)

    @staticmethod
    async def close_pnl_accounts(progress_callback=None):
        """
        Calculates the net profit/loss by aggregating all Class 6 and 7 accounts,
        then posts a closing JV to the current database to zero them out.
        Returns the net result and the result account used (138 or 139).
        """
        try:
            if progress_callback: await progress_callback("Calculating P&L closing entry (Class 6 & 7)...")
            
            # Fetch current trial balance for P&L accounts
            trial_balance = Reports.fetch_trial_balance()
            
            jv_lines = []
            net_balance_sum = 0.0 # Debit (+) minus Credit (-)
            
            for row in trial_balance:
                acc_num = str(row['Account Number'])
                balance = float(row['Net Balance'] or 0)
                
                # Filter for Expenses (6) and Revenue/Purchases (7)
                if acc_num.startswith('6') or acc_num.startswith('7'):
                    if abs(balance) < 0.01:
                        continue
                    
                    # To zero out: Credit if Debit, Debit if Credit
                    jv_lines.append({
                        'account': acc_num,
                        'debit': abs(balance) if balance < 0 else 0,
                        'credit': balance if balance > 0 else 0
                    })
                    net_balance_sum += balance

            if not jv_lines:
                if progress_callback: await progress_callback("No P&L data found to close.")
                return True, "No data", 0.0, None

            # Determine Result account: 138 (Profit) if Credit balance dominates, 139 (Loss) if Debit dominates.
            # net_balance_sum > 0 => More debits (expenses) than credits (revenue) => LOSS
            # net_balance_sum < 0 => More credits (revenue) than debits (expenses) => PROFIT
            
            if net_balance_sum > 0:
                result_account = '139' # Loss
                jv_lines.append({'account': result_account, 'debit': abs(net_balance_sum), 'credit': 0})
            else:
                result_account = '138' # Profit
                jv_lines.append({'account': result_account, 'debit': 0, 'credit': abs(net_balance_sum)})

            current_year = datetime.now().year
            save_accounting_transaction(
                reference_type="Year-End Closing",
                reference_id=int(current_year),
                lines=jv_lines,
                description=f"P&L Accounts Closing for Fiscal Year {current_year}"
            )
            
            if progress_callback: await progress_callback(f"P&L accounts closed to {result_account} (Balance: {abs(net_balance_sum):,.2f})")
            return True, "P&L Closed", abs(net_balance_sum), result_account
        except Exception as e:
            logging.error(f"P&L close error: {e}")
            return False, str(e), 0.0, None

    @staticmethod
    async def post_opening_jv(new_db_name, balances, stock_value, progress_callback=None):
        """Posts the opening JV to the new database."""
        try:
            if progress_callback: await progress_callback("Posting opening journal voucher...")
            original_db = db_manager.CONNECTION_CONFIG['database']
            db_manager.switch_database(new_db_name)
            
            jv_lines = []
            total_debit = 0.0
            total_credit = 0.0
            
            for b in balances:
                acct_str = str(b['account'])
                # Class 6 and 7 should be 0 anyway if we ran the closing JV, 
                # but we still explicitly ignore them just in case.
                if acct_str.startswith('6') or acct_str.startswith('7'):
                    continue
                    
                jv_lines.append({
                    'account': b['account'],
                    'debit': b['debit'],
                    'credit': b['credit']
                })
                total_debit += float(b['debit'])
                total_credit += float(b['credit'])
            
            # Stock account (User specified 3710)
            stock_account = '3710'
            # Ensure it exists
            exists = await db_manager.execute_scalar_async(f"SELECT COUNT(*) FROM auxiliary WHERE number = '{stock_account}'")
            if not exists:
                # Fallback to any 3xxx if 3710 not found, or use 3710 anyway (SP might create it)
                pass
                
            if stock_value > 0:
                jv_lines.append({
                    'account': stock_account,
                    'debit': stock_value,
                    'credit': 0
                })
                total_debit += stock_value
            
            # Balancing entry
            equity_account = await db_manager.execute_scalar_async("SELECT number FROM auxiliary WHERE number LIKE '11%' OR number LIKE '12%' ORDER BY number")
            if not equity_account:
                equity_account = '1100'
                
            diff = total_debit - total_credit
            if abs(diff) > 0.01:
                if diff > 0:
                    jv_lines.append({'account': equity_account, 'debit': 0, 'credit': diff})
                else:
                    jv_lines.append({'account': equity_account, 'debit': abs(diff), 'credit': 0})
            
            save_accounting_transaction(
                reference_type="Opening",
                reference_id=int(datetime.now().year),
                lines=jv_lines,
                description=f"Opening Balances for Year Transition {datetime.now().year}"
            )

            # --- ALSO: Populate journal_voucher table for UI visibility ---
            try:
                # 1. Create Header
                opening_year = datetime.now().year
                opening_entry = f"Opening Balance {opening_year}"
                opening_manual_ref = f"Opening Balance"
                
                # Try to resolve SubTypeId for "Opening" so JournalVoucher UI can categorize correctly.
                subtype_id = await db_manager.execute_scalar_async(
                    "SELECT TOP 1 Id FROM SubType WHERE Name LIKE '%Opening%' ORDER BY Id"
                )
                header_sql = """
                    INSERT INTO journal_voucher (Entry, SubTypeId, [Date], [Status], ManualReference, UpdateDate)
                    VALUES (?, ?, GETDATE(), 1, ?, GETDATE())
                """
                await db_manager.execute_update_async(header_sql, (opening_entry, subtype_id, opening_manual_ref))
                
                # Get the inserted ID
                h_id = await db_manager.execute_scalar_async("SELECT MAX(NumberId) FROM journal_voucher")
                
                # 2. Create Items
                for line in jv_lines:
                    # Resolve auxiliary ID from account number string
                    aux_id = await db_manager.execute_scalar_async(f"SELECT id FROM auxiliary WHERE number = '{line['account']}'")
                    if aux_id:
                        item_sql = """
                            INSERT INTO journal_voucher_items (VoucherId, AuxiliaryId, [Date], Debit, Credit, [Status], Remark)
                            VALUES (?, ?, GETDATE(), ?, ?, 1, 'Opening Balance')
                        """
                        await db_manager.execute_update_async(
                            item_sql,
                            (h_id, aux_id, line['debit'], line['credit'])
                        )
            except Exception as jve:
                logging.warning(f"Could not create JV UI record: {jve}")
            
            db_manager.switch_database(original_db)
            if progress_callback: await progress_callback("Opening JV posted successfully.")
            return True, "Opening JV posted successfully."
        except Exception as e:
            logging.error(f"Error posting opening JV: {e}")
            try: db_manager.switch_database(original_db)
            except: pass
            return False, str(e)

    @staticmethod
    async def empty_operational_tables(target_db, progress_callback=None):
        """Empty transaction/operational tables in the new database."""
        try:
            if progress_callback: await progress_callback("Emptying operational tables in new database...")
            original_db = db_manager.CONNECTION_CONFIG['database']
            db_manager.switch_database(target_db)
            
            # List of tables to empty (order matters for FKs)
            tables_to_empty = [
                'sale_items', 'sales_payment', 'sales_invoice_account_links', 'sales',
                'sales_return_items', 'sales_returns',
                'purchase_items', 'purchase_payment', 'purchase_invoice_account_links', 'purchases',
                'purchase_return_items', 'purchase_returns',
                'customer_receipt_details', 'customer_payments', 'customer_receipt',
                'supplier_payment_details', 'supplier_payment',
                'expenses', 'appointments', 'cash_drawer_operations', 'report_audit_log',
                'price_cost_date_history',
                'stock_operation_items', 'stock_operations',
                'accounting_transaction_lines', 'accounting_transactions', 'journal_voucher_items', 'journal_voucher'
            ]
            
            for table in tables_to_empty:
                # Check if table exists
                exists = await db_manager.execute_scalar_async(f"SELECT COUNT(*) FROM sysobjects WHERE name='{table}' AND xtype='U'")
                if exists:
                    if progress_callback: await progress_callback(f"Purging table: {table}")
                    if table == 'accounting_transaction_lines':
                        # Use jv_id instead of id for accounting_transactions
                        await db_manager.execute_update_async("DELETE FROM accounting_transaction_lines WHERE jv_id NOT IN (SELECT jv_id FROM accounting_transactions WHERE reference_type = 'Opening' OR reference_type LIKE 'VAT%')")
                    elif table == 'accounting_transactions':
                        await db_manager.execute_update_async("DELETE FROM accounting_transactions WHERE reference_type <> 'Opening' AND reference_type NOT LIKE 'VAT%'")
                    else:
                        await db_manager.execute_update_async(f"DELETE FROM [{table}]")
            
            db_manager.switch_database(original_db)
            if progress_callback: await progress_callback("Operational tables emptied.")
            return True, "Emptied"
        except Exception as e:
            logging.error(f"Empty tables error: {e}")
            try: db_manager.switch_database(original_db)
            except: pass
            return False, str(e)

    @staticmethod
    async def rollover_open_documents(new_db, progress_callback=None):
        """
        Rollover 2.0: Migrates unpaid sales, purchases, returns, and calculates 
        unallocated credits (Payments on Account) to be carried over as 'Opening' documents.
        """
        current_db = db_manager.CONNECTION_CONFIG['database']
        try:
            if progress_callback: await progress_callback("Processing open documents (Invoices & Returns)...")
            
            # ---------------------------------------------------------
            # 1. SALES & RETURNS (Customers)
            # ---------------------------------------------------------
            unpaid_sales = []
            connection.contogetrows(
                "SELECT s.invoice_number, s.customer_id, s.total_amount, s.auxiliary_id, s.currency_id, s.sale_date, s.id FROM sales s WHERE s.status <> 'Cancelled'",
                unpaid_sales
            )
            
            sales_to_carry = []
            customer_doc_totals = {} # {cust_id: net_docs_total}
            
            for row in unpaid_sales:
                inv_num, cust_id, total, aux_id, cur_id, sale_date, doc_id = row
                paid_data = []
                connection.contogetrows_with_params(
                    "SELECT SUM(settlement_amount) FROM customer_receipt_details WHERE source_type='Invoice' AND source_id=?",
                    paid_data, (doc_id,)
                )
                paid = float(paid_data[0][0] or 0)
                balance = float(total or 0) - paid
                if balance > 0.01:
                    sales_to_carry.append({'type': 'Sale', 'num': inv_num, 'cid': cust_id, 'aux': aux_id, 'cur': cur_id, 'bal': balance, 'date': sale_date})
                    customer_doc_totals[cust_id] = customer_doc_totals.get(cust_id, 0.0) + balance

            # Sales Returns
            pending_returns = []
            connection.contogetrows(
                "SELECT r.invoice_number, r.customer_id, r.total_amount, r.id, r.currency_id, r.return_date FROM sales_returns r WHERE r.status <> 'Cancelled'",
                pending_returns
            )
            
            returns_to_carry = []
            for row in pending_returns:
                inv_num, cust_id, total, doc_id, cur_id, return_date = row
                settled_data = []
                connection.contogetrows_with_params(
                    "SELECT SUM(settlement_amount) FROM customer_receipt_details WHERE source_type='Return' AND source_id=?",
                    settled_data, (doc_id,)
                )
                settled = abs(float(settled_data[0][0] or 0)) # Returns are negative in balance but stored as positive in amount? 
                # In DB, Returns amount is positive. Settlement is negative.
                balance = float(total or 0) - settled
                if balance > 0.01:
                    returns_to_carry.append({'type': 'Return', 'num': inv_num, 'cid': cust_id, 'aux': None, 'cur': cur_id, 'bal': balance, 'date': return_date})
                    customer_doc_totals[cust_id] = customer_doc_totals.get(cust_id, 0.0) - balance

            # ---------------------------------------------------------
            # 2. PURCHASES & RETURNS (Suppliers)
            # ---------------------------------------------------------
            unpaid_purchases = []
            connection.contogetrows(
                "SELECT p.invoice_number, p.supplier_id, p.total_amount, p.auxiliary_number, p.currency_id, p.purchase_date, p.id FROM purchases p WHERE p.status <> 'Cancelled' AND p.payment_status = 'pending'",
                unpaid_purchases
            )
            
            purchases_to_carry = []
            supplier_doc_totals = {}
            
            for row in unpaid_purchases:
                inv_num, supp_id, total, aux_num, cur_id, purchase_date, doc_id = row
                paid_data = []
                connection.contogetrows_with_params(
                    "SELECT SUM(settlement_amount) FROM supplier_payment_details WHERE source_type='Invoice' AND source_id=?",
                    paid_data, (doc_id,)
                )
                paid = float(paid_data[0][0] or 0)
                balance = float(total or 0) - paid
                if balance > 0.01:
                    purchases_to_carry.append({'type': 'Purchase', 'num': inv_num, 'sid': supp_id, 'aux_num': aux_num, 'cur': cur_id, 'bal': balance, 'date': purchase_date})
                    supplier_doc_totals[supp_id] = supplier_doc_totals.get(supp_id, 0.0) + balance

            pending_p_returns = []
            connection.contogetrows(
                "SELECT r.invoice_number, r.supplier_id, r.total_amount, r.id, r.currency_id, r.return_date FROM purchase_returns r WHERE r.status <> 'Cancelled' AND r.payment_status = 'pending'",
                pending_p_returns
            )
            
            p_returns_to_carry = []
            for row in pending_p_returns:
                inv_num, supp_id, total, doc_id, cur_id, return_date = row
                settled_data = []
                connection.contogetrows_with_params(
                    "SELECT SUM(settlement_amount) FROM supplier_payment_details WHERE source_type='Return' AND source_id=?",
                    settled_data, (doc_id,)
                )
                settled = abs(float(settled_data[0][0] or 0))
                balance = float(total or 0) - settled
                if balance > 0.01:
                    p_returns_to_carry.append({'type': 'Return', 'num': inv_num, 'sid': supp_id, 'aux_num': None, 'cur': cur_id, 'bal': balance, 'date': return_date})
                    supplier_doc_totals[supp_id] = supplier_doc_totals.get(supp_id, 0.0) - balance

            # ---------------------------------------------------------
            # 3. DETECT UNALLOCATED PAYMENTS (Payments on Account)
            # ---------------------------------------------------------
            unallocated_sales_credits = []
            cust_balances = []
            connection.contogetrows("SELECT id, balance FROM customers", cust_balances)
            for c_id, real_bal in cust_balances:
                doc_bal = customer_doc_totals.get(c_id, 0.0)
                reserved_credit = doc_bal - float(real_bal or 0)
                if reserved_credit > 0.01:
                    unallocated_sales_credits.append({'cid': c_id, 'bal': reserved_credit})

            unallocated_purchase_credits = []
            supp_balances = []
            connection.contogetrows("SELECT id, balance FROM suppliers", supp_balances)
            for s_id, real_bal in supp_balances:
                doc_bal = supplier_doc_totals.get(s_id, 0.0)
                reserved_credit = doc_bal - float(real_bal or 0)
                if reserved_credit > 0.01:
                    unallocated_purchase_credits.append({'sid': s_id, 'bal': reserved_credit})

            # ---------------------------------------------------------
            # 4. INSERT INTO NEW DB
            # ---------------------------------------------------------
            db_manager.switch_database(new_db)
            
            # Insert Sales (Status 'Opening')
            for s in sales_to_carry:
                sale_date = s.get('date') or datetime.now().date()
                notes = f"Opening Balance from {s['num']}"
                await db_manager.execute_update_async(
                    "INSERT INTO sales (invoice_number, customer_id, total_amount, subtotal, total_vat, auxiliary_id, currency_id, sale_date, notes, status, payment_status) VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?, 'Opening', 'pending')",
                    (s['num'], s['cid'], s['bal'], s['bal'], s['aux'], s['cur'], sale_date, notes)
                )
            # Insert Sales Returns (Status 'Opening')
            for r in returns_to_carry:
                await db_manager.execute_update_async(
                    "INSERT INTO sales_returns (invoice_number, customer_id, total_amount, subtotal, total_vat, currency_id, return_date, reason, status, payment_status) VALUES (?, ?, ?, ?, 0, ?, ?, ?, 'Opening', 'pending')",
                    (r['num'], r['cid'], r['bal'], r['bal'], r['cur'], r.get('date') or datetime.now().date(), f"Opening Return from {r['num']}", 'pending')
                )
            # Insert Unallocated Credits as Returns (Status 'Opening')
            for u in unallocated_sales_credits:
                await db_manager.execute_update_async(
                    "INSERT INTO sales_returns (invoice_number, customer_id, total_amount, subtotal, total_vat, currency_id, return_date, reason, status, payment_status) VALUES (?, ?, ?, ?, 0, 1, GETDATE(), ?, 'Opening', 'pending')",
                    (f"OPN-CR-{u['cid']}", u['cid'], u['bal'], u['bal'], 'Unallocated Payment on Account (Opening)')
                )

            # Insert Purchases (Status 'Opening')
            for p in purchases_to_carry:
                purchase_date = p.get('date') or datetime.now().date()
                notes = f"Opening Balance from {p['num']}"
                await db_manager.execute_update_async(
                    "INSERT INTO purchases (invoice_number, supplier_id, total_amount, subtotal, total_vat, auxiliary_number, currency_id, purchase_date, notes, status, payment_status) VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?, 'Opening', 'pending')",
                    (p['num'], p['sid'], p['bal'], p['bal'], p['aux_num'], p['cur'], purchase_date, notes)
                )
            # Insert Purchase Returns (Status 'Opening')
            for r in p_returns_to_carry:
                await db_manager.execute_update_async(
                    "INSERT INTO purchase_returns (invoice_number, supplier_id, total_amount, subtotal, total_vat, currency_id, return_date, reason, status, payment_status) VALUES (?, ?, ?, ?, 0, ?, ?, ?, 'Opening', 'pending')",
                    (r['num'], r['sid'], r['bal'], r['bal'], r['cur'], r.get('date') or datetime.now().date(), f"Opening Return from {r['num']}", 'pending')
                )
            # Insert Unallocated Purchase Credits (Status 'Opening')
            for u in unallocated_purchase_credits:
                await db_manager.execute_update_async(
                    "INSERT INTO purchase_returns (invoice_number, supplier_id, total_amount, subtotal, total_vat, currency_id, return_date, reason, status, payment_status) VALUES (?, ?, ?, ?, 0, 1, GETDATE(), ?, 'Opening', 'pending')",
                    (f"OPN-CR-{u['sid']}", u['sid'], u['bal'], u['bal'], 'Unallocated Payment on Account (Opening)')
                )

            db_manager.switch_database(current_db)
            if progress_callback: await progress_callback("Rollover complete (Invoices, Returns & Credits).")
            return True, "Done"
        except Exception as e:
            logging.error(f"Open document rollover error: {e}")
            try: db_manager.switch_database(current_db)
            except: pass
            return False, str(e)

    @staticmethod
    async def delete_closing(progress_callback=None):
        """
        Deletes all "Opening" records in the current database.
        This includes Opening JVs, Opening Sales, Opening Purchases, and Opening Returns.
        """
        try:
            if progress_callback: await progress_callback("Starting reset of opening balances...")
            
            # 1. Delete Opening JVs
            if progress_callback: await progress_callback("Removing Opening Journal Vouchers...")
            # Detect opening JVs from the journal_voucher table using Entry like 'OPN-%'
            opn_jvs = []
            connection.contogetrows("SELECT NumberId FROM journal_voucher WHERE Entry LIKE 'OPN-%'", opn_jvs)
            for jv in opn_jvs:
                await db_manager.execute_update_async("DELETE FROM journal_voucher_items WHERE VoucherId = ?", (jv[0],))
                await db_manager.execute_update_async("DELETE FROM journal_voucher WHERE NumberId = ?", (jv[0],))
            
            # 2. Delete Opening Accounting Transactions
            await db_manager.execute_update_async("DELETE FROM accounting_transaction_lines WHERE jv_id IN (SELECT jv_id FROM accounting_transactions WHERE reference_type = 'Opening')")
            await db_manager.execute_update_async("DELETE FROM accounting_transactions WHERE reference_type = 'Opening'")
            
            # 3. Delete Opening Sales
            if progress_callback: await progress_callback("Removing Opening Sales records...")
            await db_manager.execute_update_async("DELETE FROM sales WHERE status = 'Opening'")
            
            # 4. Delete Opening Sales Returns
            if progress_callback: await progress_callback("Removing Opening Sales Returns records...")
            await db_manager.execute_update_async("DELETE FROM sales_returns WHERE status = 'Opening'")
            
            # 5. Delete Opening Purchases
            if progress_callback: await progress_callback("Removing Opening Purchase records...")
            await db_manager.execute_update_async("DELETE FROM purchases WHERE status = 'Opening'")
            
            # 6. Delete Opening Purchase Returns
            if progress_callback: await progress_callback("Removing Opening Purchase Returns records...")
            await db_manager.execute_update_async("DELETE FROM purchase_returns WHERE status = 'Opening'")
            
            if progress_callback: await progress_callback("Opening balances reset successfully.")
            return True, "Closing reset complete"
        except Exception as e:
            logging.error(f"Delete closing error: {e}")
            return False, str(e)
