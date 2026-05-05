from connection import connection
from connection_cashdrawer import connection_cashdrawer

class PurchaseRepository:
    def get_user_permissions(self, role_id):
        return connection.get_user_permissions(role_id)

    def get_max_purchase_id(self):
        try:
            max_id_result = []
            connection.contogetrows("SELECT MAX(id) FROM purchases", max_id_result)
            return max_id_result[0][0] if max_id_result and max_id_result[0][0] else 0
        except Exception:
            return 0

    def get_purchase_header_data(self, purchase_id):
        purchase_header_data = []
        connection.contogetrows(
            "SELECT s.name, s.phone, p.payment_status, p.invoice_number, p.purchase_date, p.currency_id FROM purchases p "
            "INNER JOIN suppliers s ON s.id = p.supplier_id WHERE p.id = ?",
            purchase_header_data, params=[purchase_id]
        )
        return purchase_header_data

    def get_purchase_items(self, purchase_id):
        purchase_items_data = []
        query = (
            "SELECT pr.barcode, pr.product_name, pi.quantity, ISNULL(pi.discount_amount, 0), "
            "pi.unit_cost, pi.total_cost, pi.unit_price, pi.profit, ISNULL(pi.vat_amount, 0), ISNULL(pi.vat_percentage, 0) FROM purchase_items pi "
            "INNER JOIN products pr ON pr.id = pi.product_id WHERE pi.purchase_id = ?"
        )
        connection.contogetrows(query, purchase_items_data, params=[purchase_id])
        return purchase_items_data

    def get_all_purchases(self):
        raw_purchases_data = []
        connection.contogetrows(
            "SELECT p.id, p.purchase_date, s.name, p.total_amount, p.invoice_number, p.payment_status, p.account_code, p.auxiliary_number, c.currency_name FROM purchases p INNER JOIN suppliers s ON s.id = p.supplier_id LEFT JOIN currencies c ON c.id = p.currency_id ORDER BY p.id DESC",
            raw_purchases_data
        )
        return raw_purchases_data

    def get_product_by_barcode(self, barcode):
        product_data = []
        connection.contogetrows(
            "SELECT barcode, product_name, cost_price, price, currency_id, local_price, is_vat_subjected, vat_percentage FROM products WHERE barcode = ?",
            product_data,
            params=[barcode]
        )
        return product_data

    def get_all_products(self):
        headers = []
        connection.contogetheaders("SELECT barcode, product_name, stock_quantity, cost_price, price FROM products", headers)
        data = []
        connection.contogetrows("SELECT barcode, product_name, stock_quantity, cost_price, price FROM products", data)
        return headers, data

    def get_all_suppliers(self):
        headers = []
        connection.contogetheaders("SELECT id, name, phone FROM suppliers", headers)
        data = []
        connection.contogetrows("SELECT id, name, phone FROM suppliers", data)
        return headers, data

    def get_purchase_details_for_deletion(self, purchase_id):
        purchase_data = []
        connection.contogetrows(
            "SELECT total_amount, payment_status, supplier_id FROM purchases WHERE id = ?",
            purchase_data, params=[purchase_id]
        )
        return purchase_data

    def delete_purchase_items(self, purchase_id):
        connection.deleterow("DELETE FROM purchase_items WHERE purchase_id = ?", [purchase_id])

    def delete_purchase(self, purchase_id):
        connection.deleterow("DELETE FROM purchases WHERE id = ?", [purchase_id])

    def update_supplier_balance(self, amount, supplier_id):
        
        connection.update_supplierbalance("UPDATE suppliers SET balance = balance - ? WHERE id = ?", (amount, supplier_id))

    def insert_price_cost_history(self, product_id, old_price, new_price, old_cost, new_cost, change_date, changed_by):
        history_sql = """
            INSERT INTO price_cost_date_history
            (product_id, old_price, new_price, old_cost_price, new_cost_price, change_date, changed_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        history_values = (
            product_id, old_price, new_price, old_cost, new_cost, change_date, changed_by
        )
        connection.insertingtodatabase(history_sql, history_values)

    def get_product_id_by_name(self, product_name):
        return connection.getid('select id from products where product_name = ?', [product_name])

    def get_product_id_by_barcode(self, barcode):
        return connection.getid('select id from products where barcode = ?', [barcode])

    def insert_purchase_item(self, purchase_id, barcode, product_id, quantity, cost, subtotal, price, profit, discount, vat_amount=0, vat_percentage=0):
        purchase_item_sql = """
            INSERT INTO purchase_items (purchase_id, barcode, product_id, quantity, unit_cost, total_cost, unit_price, profit, discount_amount, vat_amount, vat_percentage)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        purchase_item_values = (
            purchase_id, barcode, product_id, quantity, cost,
            subtotal, price, profit, discount, vat_amount, vat_percentage
        )
        connection.insertingtodatabase(purchase_item_sql, purchase_item_values)

    def update_product_stock_and_price(self, cost, price, quantity, updated_at, product_id):
        update_product_sql = """
            UPDATE products
            SET cost_price = ?, price = ?, stock_quantity = stock_quantity + ?, updated_at=?
            WHERE id = ?
        """
        update_product_values = (
            cost, price, quantity, updated_at, product_id
        )
        connection.update_product(update_product_sql, update_product_values)

    def get_old_purchase_items(self, purchase_id):
        old_items = []
        connection.contogetrows("SELECT product_id, quantity FROM purchase_items WHERE purchase_id = ?", old_items, params=[purchase_id])
        return old_items

    def revert_product_stock(self, quantity, product_id):
        connection.update_product("UPDATE products SET stock_quantity = stock_quantity - ? WHERE id = ?", (quantity, product_id))

    def get_previous_purchase_financials(self, purchase_id):
        previous_data = []
        connection.contogetrows("SELECT payment_status, total_amount, supplier_id FROM purchases WHERE id = ?", previous_data, params=[purchase_id])
        return previous_data

    def add_cash_drawer_operation(self, amount, operation_type, user_id, notes):
        return connection_cashdrawer.add_cash_drawer_operation(amount, operation_type, user_id, notes)

    def revert_supplier_balance(self, amount, supplier_id):
        connection.update_supplierbalance("UPDATE suppliers SET balance = balance - ? WHERE id = ?", (amount, supplier_id))

    def delete_purchase_payment_records(self, purchase_id):
        connection.deleterow("DELETE FROM purchase_payment WHERE purchase_id = ?", [purchase_id])

    def get_invoice_number(self, purchase_id):
        return connection.getid("SELECT invoice_number FROM purchases WHERE id = ?", [purchase_id])

    def delete_supplier_payment_by_invoice(self, invoice_number):
        connection.deleterow("DELETE FROM supplier_payment WHERE manual_reference = ?", [invoice_number])

    def update_supplier_balance_on_account(self, amount, supplier_id, currency_id):
        symbol = self.get_currency_symbol_by_id(currency_id)
        if symbol == '$':  # USD
            connection.update_supplierbalance("UPDATE suppliers SET balance_usd = balance_usd + ? WHERE id = ?", (amount, supplier_id))
        else:  # LL or other
            connection.update_supplierbalance("UPDATE suppliers SET balance = balance + ? WHERE id = ?", (amount, supplier_id))

    def insert_purchase_payment_on_account(self, purchase_id, invoice_number, total_amount, purchase_date, created_date, supplier_id, notes):
        purchase_payment_sql = """
            INSERT INTO purchase_payment (purchase_id, purchase_invoice_number, total_amount, purchase_date, created_date, supplier_id, status, amount_paid, payment_method, debit, credit, notes)
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?)
        """
        purchase_payment_values = (purchase_id, invoice_number, total_amount, purchase_date, created_date, supplier_id, 0, 'On Account', total_amount, 0, notes)
        connection.insertingtodatabase(purchase_payment_sql, purchase_payment_values)

    def insert_supplier_payment_cash(self, invoice_number, purchase_date, supplier_id, total_amount, notes, created_at):
        supplier_payment_sql = """
            INSERT INTO supplier_payment (manual_reference, payment_date, supplier_id, amount, payment_method, status, notes, created_at)
            VALUES (?, ?, ?, ?, ?, 'completed', ?, ?)
        """
        supplier_payment_values = (invoice_number, purchase_date, supplier_id, total_amount, 'Cash', notes, created_at)
        connection.insertingtodatabase(supplier_payment_sql, supplier_payment_values)

    def insert_purchase_payment_cash(self, purchase_id, invoice_number, total_amount, purchase_date, created_date, supplier_id, notes):
        purchase_payment_sql = """
            INSERT INTO purchase_payment (purchase_id, purchase_invoice_number, total_amount, purchase_date, created_date, supplier_id, status, amount_paid, payment_method, debit, credit, notes)
            VALUES (?, ?, ?, ?, ?, ?, 'completed', ?, ?, ?, ?, ?)
        """
        purchase_payment_values = (purchase_id, invoice_number, total_amount, purchase_date, created_date, supplier_id, total_amount, 'Cash', total_amount, total_amount, notes)
        connection.insertingtodatabase(purchase_payment_sql, purchase_payment_values)

    def create_purchase(self, purchase_date, supplier_id, subtotal, discount_amount, final_total, invoice_number, created_at, payment_status, currency_id=1, total_vat=0, payment_method='Cash'):
        purchase_sql = """
            INSERT INTO purchases (purchase_date, supplier_id, subtotal, discount_amount, total_amount, invoice_number, created_at, payment_status, currency_id, total_vat)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        purchase_values = (
            purchase_date, supplier_id, subtotal, discount_amount,
            final_total, invoice_number, created_at, payment_status, currency_id, total_vat
        )
        connection.insertingtodatabase(purchase_sql, purchase_values)
        last_id = connection.getid("SELECT MAX(id) FROM purchases", [])
        
        try:
            import accounting_helpers
            import business_track_settings
            if supplier_id:
                supplier_aux = []
                connection.contogetrows(f"SELECT auxiliary_number FROM suppliers WHERE id={supplier_id}", supplier_aux)
                credit_account = supplier_aux[0][0] if (supplier_aux and supplier_aux[0][0]) else "4011.000001"
            else:
                credit_account = "4011.000001"

            has_vat = total_vat > 0
            purchase_account = business_track_settings.get_purchase_account(has_vat)
                
            jv_lines = [
                {'account': purchase_account, 'debit': subtotal, 'credit': 0}
            ]
            if total_vat > 0:
                supplier_name = ""
                if supplier_id:
                    name_res = []
                    connection.contogetrows(f"SELECT name FROM suppliers WHERE id={supplier_id}", name_res)
                    supplier_name = name_res[0][0] if name_res else "Unknown"
                    
                vat_account = accounting_helpers.ensure_vat_auxiliary('Supplier', supplier_id, supplier_name, credit_account)
                jv_lines.append({'account': vat_account, 'debit': total_vat, 'credit': 0})
                
            if discount_amount > 0:
                jv_lines.append({'account': '6019.000001', 'debit': 0, 'credit': discount_amount})
                
            jv_lines.append({'account': credit_account, 'debit': 0, 'credit': final_total})
            
            if payment_status != 'pending':
                payment_aux = business_track_settings.get_payment_account(payment_method)
                # Cash payment logic
                jv_lines.append({'account': credit_account, 'debit': final_total, 'credit': 0})
                jv_lines.append({'account': payment_aux, 'debit': 0, 'credit': final_total})

                # Record cash drawer operation
                try:
                    from session_storage import session_storage
                    user = session_storage.get('user')
                    user_id = user.get('user_id') if user else None
                    self.add_cash_drawer_operation(final_total, 'Out', user_id, f"Purchase Invoice {invoice_number}")
                except Exception as ex:
                    print(f"Cash Drawer Error: {ex}")
                
            accounting_helpers.save_accounting_transaction(
                reference_type='Purchase',
                reference_id=last_id,
                lines=jv_lines,
                description=f"Purchase Invoice {invoice_number}"
            )
        except Exception as e:
            print(f"Accounting Error: {e}")
            
        return last_id

    def update_purchase(self, purchase_date, supplier_id, subtotal, discount_amount, final_total, created_at, payment_status, purchase_id, currency_id=1, total_vat=0, payment_method='Cash'):
        purchase_sql = """
            UPDATE purchases
            SET purchase_date = ?, supplier_id = ?, subtotal = ?, discount_amount = ?,
                total_amount = ?, created_at = ?, payment_status = ?, currency_id = ?, total_vat = ?
            WHERE id = ?
        """
        purchase_values = (
            purchase_date, supplier_id, subtotal, discount_amount,
            final_total, created_at, payment_status, currency_id, total_vat, purchase_id
        )
        connection.insertingtodatabase(purchase_sql, purchase_values)

        try:
            import accounting_helpers
            import business_track_settings
            connection.insertingtodatabase("DELETE FROM accounting_transaction_lines WHERE jv_id IN (SELECT jv_id FROM accounting_transactions WHERE reference_type='Purchase' AND reference_id=?)", [purchase_id])
            connection.insertingtodatabase("DELETE FROM accounting_transactions WHERE reference_type='Purchase' AND reference_id=?", [purchase_id])
            
            if supplier_id:
                supplier_aux = []
                connection.contogetrows(f"SELECT auxiliary_number FROM suppliers WHERE id={supplier_id}", supplier_aux)
                credit_account = supplier_aux[0][0] if (supplier_aux and supplier_aux[0][0]) else "4011.000001"
            else:
                credit_account = "4011.000001"
                
            inv_data = []
            connection.contogetrows(f"SELECT invoice_number FROM purchases WHERE id={purchase_id}", inv_data)
            inv_num = inv_data[0][0] if inv_data else str(purchase_id)

            has_vat = total_vat > 0
            purchase_account = business_track_settings.get_purchase_account(has_vat)
            
            jv_lines = [
                {'account': purchase_account, 'debit': subtotal, 'credit': 0}
            ]
            if total_vat > 0:
                supplier_name = ""
                if supplier_id:
                    name_res = []
                    connection.contogetrows(f"SELECT name FROM suppliers WHERE id={supplier_id}", name_res)
                    supplier_name = name_res[0][0] if name_res else "Unknown"
                
                vat_account = accounting_helpers.ensure_vat_auxiliary('Supplier', supplier_id, supplier_name, credit_account)
                jv_lines.append({'account': vat_account, 'debit': total_vat, 'credit': 0})
                
            if discount_amount > 0:
                jv_lines.append({'account': '6019.000001', 'debit': 0, 'credit': discount_amount})
                
            jv_lines.append({'account': credit_account, 'debit': 0, 'credit': final_total})
            
            if payment_status != 'pending':
                # Reversal logic for cash updates
                prev_data = []
                connection.contogetrows("SELECT total_amount, payment_status FROM purchases WHERE id=?", prev_data, [purchase_id])
                if prev_data and prev_data[0][1] != 'pending':
                    prev_total = prev_data[0][0]
                    try:
                        from session_storage import session_storage
                        user = session_storage.get('user')
                        user_id = user.get('user_id') if user else None
                        self.add_cash_drawer_operation(prev_total, 'In', user_id, f"Reversal for update Invoice {inv_num}")
                    except Exception as ex:
                        print(f"Cash Drawer Reversal Error: {ex}")

                payment_aux = business_track_settings.get_payment_account(payment_method)
                jv_lines.append({'account': credit_account, 'debit': final_total, 'credit': 0})
                jv_lines.append({'account': payment_aux, 'debit': 0, 'credit': final_total})

                # Record new cash drawer operation
                try:
                    from session_storage import session_storage
                    user = session_storage.get('user')
                    user_id = user.get('user_id') if user else None
                    self.add_cash_drawer_operation(final_total, 'Out', user_id, f"Update Purchase Invoice {inv_num}")
                except Exception as ex:
                    print(f"Cash Drawer Error: {ex}")
            
            accounting_helpers.save_accounting_transaction(
                reference_type='Purchase',
                reference_id=purchase_id,
                lines=jv_lines,
                description=f"Updated Purchase Invoice {inv_num}"
            )
        except Exception as e:
            print(f"Accounting Error: {e}")

    def get_supplier_id(self, supplier_name):
        return connection.getid('select id from suppliers where name = ?', [supplier_name])

    def get_existing_invoices(self):
        existing_invoices = connection.contogetrows(
            "SELECT invoice_number FROM purchases WHERE invoice_number IS NOT NULL", []
        )
        return {row[0] for row in existing_invoices}
        
    def get_purchase_data_for_invoice(self, purchase_id):
        purchase_data = []
        connection.contogetrows(
            "SELECT p.invoice_number, p.purchase_date, s.name, s.phone, p.total_amount, p.subtotal, p.currency_id, ISNULL(p.total_vat, 0) FROM purchases p INNER JOIN suppliers s ON s.id = p.supplier_id WHERE p.id = ?",
            purchase_data, params=[purchase_id]
        )
        return purchase_data

    def get_purchase_items_for_invoice(self, purchase_id):
        purchase_items_data = []
        connection.contogetrows(
            "SELECT pr.product_name, pi.quantity, pi.unit_cost, pi.discount_amount, pi.total_cost, ISNULL(pi.vat_amount, 0) FROM purchase_items pi INNER JOIN products pr ON pr.id = pi.product_id WHERE pi.purchase_id = ?",
            purchase_items_data, params=[purchase_id]
        )
        return purchase_items_data

    def get_ledger_id_by_account(self, account_number):
        ledger_data = []
        connection.contogetrows("SELECT Id FROM Ledger WHERE AccountNumber = ?", ledger_data, (account_number,))
        return ledger_data

    def get_auxiliary_count_by_ledger(self, ledger_id):
        count_data = []
        connection.contogetrows("SELECT COUNT(*) FROM Auxiliary WHERE ledger_id = ?", count_data, (ledger_id,))
        return count_data if count_data else [[0]]

    def create_auxiliary(self, ledger_id, account_number, name):
        aux_sql = "INSERT INTO Auxiliary (ledger_id, number, account_name, status) VALUES (?, ?, ?, 1)"
        connection.insertingtodatabase(aux_sql, (ledger_id, account_number, name))

    def get_last_auxiliary_id(self):
        aux_id_data = []
        connection.contogetrows("SELECT MAX(id) FROM Auxiliary", aux_id_data)
        return aux_id_data if aux_id_data else [[None]]

    def update_purchase_auxiliary_id(self, purchase_id, auxiliary_id):
        connection.insertingtodatabase("UPDATE purchases SET auxiliary_id = ? WHERE id = ?", (auxiliary_id, purchase_id))

    def update_purchase_auxiliary_number(self, purchase_id, auxiliary_number):
        connection.insertingtodatabase("UPDATE purchases SET auxiliary_number = ? WHERE id = ?", (auxiliary_number, purchase_id))

    def get_all_currencies(self):
        headers = []
        connection.contogetheaders("SELECT id, currency_code, currency_name, symbol, exchange_rate FROM currencies WHERE is_active = 1", headers)
        data = []
        connection.contogetrows("SELECT id, currency_code, currency_name, symbol, exchange_rate FROM currencies WHERE is_active = 1", data)
        return headers, data

    def get_currency_symbol(self, currency_id):
        currency_data = []
        connection.contogetrows("SELECT symbol FROM currencies WHERE id = ?", currency_data, params=[currency_id])
        return currency_data

    def get_currency_symbol_by_id(self, currency_id):
        currency_data = []
        connection.contogetrows("SELECT symbol FROM currencies WHERE id = ?", currency_data, params=[currency_id])
        return currency_data[0][0] if currency_data else '$'

    def get_product_currency(self, product_id):
        currency_data = []
        connection.contogetrows("SELECT currency_id FROM products WHERE id = ?", currency_data, params=[product_id])
        return currency_data[0][0] if currency_data and currency_data[0][0] else None

    def get_exchange_rate(self, currency_id):
        rate_data = []
        connection.contogetrows("SELECT exchange_rate FROM currencies WHERE id = ?", rate_data, params=[currency_id])
        return float(rate_data[0][0]) if rate_data and rate_data[0][0] else None

    def add_cash_drawer_operation(self, amount, operation_type, user_id, notes=None):
        """Helper to update cash drawer via connection"""
        return connection.update_cash_drawer_balance(amount, operation_type, user_id, notes)
