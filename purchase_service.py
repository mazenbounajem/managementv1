from datetime import datetime
from purchase_repository import PurchaseRepository

class PurchaseService:
    def __init__(self):
        self.repository = PurchaseRepository()

    def get_user_permissions(self, role_id):
        return self.repository.get_user_permissions(role_id)

    def get_max_purchase_id(self):
        return self.repository.get_max_purchase_id()

    def get_purchase_details(self, purchase_id):
        purchase_header = self.repository.get_purchase_header_data(purchase_id)
        if not purchase_header:
            raise ValueError(f'Purchase with ID {purchase_id} not found.')

        supplier_name, phone, payment_status, invoice_number, purchase_date, currency_id = purchase_header[0]
        purchase_items = self.repository.get_purchase_items(purchase_id)
        
        # Get exchange rate for denormalization
        exchange_rate = 1.0
        if currency_id:
            exchange_rate = float(self.repository.get_exchange_rate(currency_id) or 1.0)

        rows = []
        for item in purchase_items:
            rows.append({
                'barcode': str(item[0]) if item[0] else '',
                'product': str(item[1]) if item[1] else 'Unknown Product',
                'quantity': int(item[2]) if item[2] else 0,
                'discount': float(item[3]) * exchange_rate if item[3] else 0.0,
                'cost': float(item[4]) * exchange_rate if item[4] else 0.0,
                'subtotal': float(item[5]) * exchange_rate if item[5] else 0.0,
                'price': float(item[6]) * exchange_rate if item[6] else 0.0,
                'profit': float(item[7]) * exchange_rate if item[7] else 0.0,
                'vat_amount': float(item[8]) * exchange_rate if len(item) > 8 else 0.0,
                'vat_percentage': float(item[9]) if len(item) > 9 else 0.0,
                'old_cost_price': float(item[4]) * exchange_rate if item[4] else None,
                'old_price': float(item[6]) * exchange_rate if item[6] else None,
                'highlighted': False,
            })

        return {
            'supplier_name': supplier_name,
            'phone': phone,
            'payment_status': payment_status,
            'invoice_number': invoice_number,
            'purchase_date': purchase_date,
            'currency_id': currency_id,
            'rows': rows
        }

    def get_all_purchases(self):
        raw_data = self.repository.get_all_purchases()
        purchases_data = []
        for row in raw_data:
            purchases_data.append({
                'id': row[0],
                'purchase_date': str(row[1]),
                'supplier_name': str(row[2]),
                'total_amount': float(row[3]),
                'invoice_number': str(row[4]),
                'payment_status': str(row[5]),
                'account_code': str(row[6]) if row[6] else '',
                'auxiliary_number': str(row[7]) if row[7] else '',
                'currency_name': str(row[8]) if row[8] else '',
                'highlighted': False
            })
        return purchases_data

    def get_product_by_barcode(self, barcode):
        data = self.repository.get_product_by_barcode(barcode)
        if data:
            r = data[0]
            return {
                'barcode': r[0],
                'product_name': r[1],
                'cost_price': float(r[2] or 0),
                'price': float(r[3] or 0),
                'currency_id': r[4],
                'local_price': float(r[5] or 0),
                'is_vat_subjected': bool(r[6]),
                'vat_percentage': float(r[7] or 0)
            }
        return None

    def get_all_products(self):
        headers, data = self.repository.get_all_products()
        rows = []
        for row in data:
            row_dict = {}
            for i, header in enumerate(headers):
                row_dict[header] = row[i]
            rows.append(row_dict)
        return headers, rows

    def get_all_suppliers(self):
        headers, data = self.repository.get_all_suppliers()
        rows = []
        for row in data:
            row_dict = {}
            for i, header in enumerate(headers):
                row_dict[header] = row[i]
            rows.append(row_dict)
        return headers, rows

    def delete_purchase(self, purchase_id, user_id):
        purchase_data = self.repository.get_purchase_details_for_deletion(purchase_id)
        if not purchase_data:
            return f'Purchase {purchase_id} not found'

        purchase_total, payment_status, supplier_id = purchase_data[0]

        # Revert stock quantities
        self._revert_previous_stock(purchase_id)

        # Handle financial reversals
        if payment_status == 'completed':
            # Reverse cash drawer operation: add money back
            notes = f"Reversal for purchase deletion {purchase_id}"
            if not self.repository.add_cash_drawer_operation(purchase_total, 'In', user_id, notes):
                raise Exception('Failed to reverse cash drawer operation')
        elif payment_status == 'pending' and supplier_id:
            # Deduct from supplier balance (reverse the on-account addition)
            self.repository.update_supplier_balance(purchase_total, supplier_id)

        # Delete related payment records
        self.repository.delete_purchase_payment_records(purchase_id)
        invoice_number = self.repository.get_invoice_number(purchase_id)
        if invoice_number:
            self.repository.delete_supplier_payment_by_invoice(invoice_number)

        # Delete purchase items and purchase header
        self.repository.delete_purchase_items(purchase_id)
        self.repository.delete_purchase(purchase_id)

        return f'Purchase {purchase_id} deleted successfully'

    def generate_invoice_number(self):
        try:
            existing_set = self.repository.get_existing_invoices()
            max_num = 0
            for invoice in existing_set:
                if invoice.startswith('PUR-'):
                    try:
                        num = int(invoice.split('-')[1])
                        max_num = max(max_num, num)
                    except (ValueError, IndexError):
                        continue
            next_num = max_num + 1
            while f"PUR-{next_num:06d}" in existing_set:
                next_num += 1
            return f"PUR-{next_num:06d}"
        except Exception:
            import time
            return f"PUR-{int(time.time())}"

    def save_purchase(self, purchase_data, rows, current_purchase_id=None):
        if not rows:
            raise ValueError('No items to save!')

        is_update = current_purchase_id is not None
        
        if is_update:
            self._update_existing_purchase(purchase_data, rows, current_purchase_id)
        else:
            self._create_new_purchase(purchase_data, rows)

    def _create_new_purchase(self, data, rows):
        invoice_number = data.get('invoice_number') or self.generate_invoice_number()
        currency_id = data.get('currency_id', 1)
        exchange_rate = float(self.repository.get_exchange_rate(currency_id) or 1.0)

        last_purchase_id = self.repository.create_purchase(
            data['purchase_date'], data['supplier_id'], 
            data['subtotal'] / exchange_rate, 
            data['discount_amount'] / exchange_rate,
            data['final_total'] / exchange_rate, 
            invoice_number, data['created_at'], data['payment_status'], currency_id,
            data.get('total_vat', 0) / exchange_rate,
            data.get('payment_method', 'Cash')
        )

        # Get ledger id for purchases (6011)
        ledger_data = self.repository.get_ledger_id_by_account('6011')
        if ledger_data:
            ledger_id = ledger_data[0][0]

            # Get next subnumber for auxiliary
            next_sub = last_purchase_id
            account_number = f"6011.{next_sub:05d}"

            # Create auxiliary
            self.repository.create_auxiliary(ledger_id, account_number, invoice_number)

            # Get auxiliary id
            aux_id_data = self.repository.get_last_auxiliary_id()
            aux_id = aux_id_data[0][0]

            # Update purchase with auxiliary_number
            self.repository.update_purchase_auxiliary_number(last_purchase_id, f"{next_sub:05d}")

        self._process_purchase_items(last_purchase_id, data['created_at'], data['user'], data['session_id'], rows, currency_id, exchange_rate)

        self._handle_payment_logic(
            purchase_id=last_purchase_id,
            is_update=False,
            **data
        )

    def _update_existing_purchase(self, data, rows, purchase_id):
        self._revert_previous_financials(purchase_id, data['user']['user_id'])
        self._revert_previous_stock(purchase_id)

        currency_id = data.get('currency_id', 1)
        exchange_rate = float(self.repository.get_exchange_rate(currency_id) or 1.0)

        self.repository.update_purchase(
            data['purchase_date'], data['supplier_id'], 
            data['subtotal'] / exchange_rate, 
            data['discount_amount'] / exchange_rate,
            data['final_total'] / exchange_rate, 
            data['created_at'], data['payment_status'], purchase_id, currency_id,
            data.get('total_vat', 0) / exchange_rate,
            data.get('payment_method', 'Cash')
        )
        
        self.repository.delete_purchase_items(purchase_id)
        
        self._process_purchase_items(purchase_id, data['created_at'], data['user'], data['session_id'], rows, currency_id, exchange_rate)
        
        invoice_number = self.repository.get_invoice_number(purchase_id)
        self._handle_payment_logic(
            purchase_id=purchase_id,
            is_update=True,
            **data
        )

    def _process_purchase_items(self, purchase_id, created_at, user, session_id, rows, purchase_currency_id, exchange_rate):
        for row in rows:
            product_id = self.repository.get_product_id_by_name(row['product'])
            barcode = row['barcode']
            product_id_from_barcode = self.repository.get_product_id_by_barcode(barcode)
            final_product_id = product_id_from_barcode or product_id

            self.repository.insert_purchase_item(
                purchase_id, row['barcode'], final_product_id, row['quantity'], 
                row['cost'] / exchange_rate,
                row['subtotal'] / exchange_rate, 
                row['price'] / exchange_rate, 
                row['profit'] / exchange_rate, 
                row['discount'] / exchange_rate,
                row.get('vat_amount', 0) / exchange_rate,
                row.get('vat_percentage', 0)
            )

            old_price = row.get('old_price')
            old_cost_price = row.get('old_cost_price')
            new_price = float(row['price'])
            new_cost_price = float(row['cost'])
            changed_by = f"{session_id} - {user.get('username') if user else 'System'}"

            # Convert prices back to product's currency if purchase currency differs
            product_currency_id = self.repository.get_product_currency(final_product_id)
            if purchase_currency_id and product_currency_id and purchase_currency_id != product_currency_id:
                # Get exchange rates
                product_rate = self.repository.get_exchange_rate(product_currency_id)

                if exchange_rate and product_rate and exchange_rate > 0 and product_rate > 0:
                    # Convert from purchase currency to product currency
                    conversion_factor = exchange_rate / product_rate
                    new_price = new_price / conversion_factor
                    new_cost_price = new_cost_price / conversion_factor

            if old_price != new_price or old_cost_price != new_cost_price:
                self.repository.insert_price_cost_history(
                    final_product_id, old_price, new_price, old_cost_price, new_cost_price, created_at, changed_by
                )

            self.repository.update_product_stock_and_price(
                new_cost_price, new_price, row['quantity'], created_at, final_product_id
            )

    def _revert_previous_stock(self, purchase_id):
        old_items = self.repository.get_old_purchase_items(purchase_id)
        for product_id, quantity in old_items:
            self.repository.revert_product_stock(quantity, product_id)

    def _revert_previous_financials(self, purchase_id, user_id):
        previous_data = self.repository.get_previous_purchase_financials(purchase_id)
        if not previous_data:
            return

        previous_payment_status, previous_total, supplier_id = previous_data[0]
        previous_total = float(previous_total)

        if previous_payment_status == 'completed':
            # Cash drawer reversal is now handled in repository update_purchase
            pass
        
        elif previous_payment_status == 'pending' and supplier_id:
            self.repository.revert_supplier_balance(previous_total, supplier_id)
        
        self.repository.delete_purchase_payment_records(purchase_id)
        invoice_number = self.repository.get_invoice_number(purchase_id)
        if invoice_number:
            self.repository.delete_supplier_payment_by_invoice(invoice_number)

    def _handle_payment_logic(self, purchase_id, invoice_number, is_update, **data):
        final_total = data['final_total']
        supplier_id = data['supplier_id']
        payment_status = data['payment_status']
        payment_method = data['payment_method']
        purchase_date = data['purchase_date']
        created_at = data['created_at']

        if supplier_id and payment_status == 'pending':
            self.repository.update_supplier_balance_on_account(final_total, supplier_id, data.get('currency_id', 1))
            self.repository.insert_purchase_payment_on_account(
                purchase_id, invoice_number, final_total, purchase_date, created_at, supplier_id, 'Payment pending - On Account'
            )
        else:
            # Cash drawer update is now handled in repository create_purchase/update_purchase
            pass

            self.repository.insert_supplier_payment_cash(
                invoice_number, purchase_date, supplier_id, final_total, 'Payment processed for selected invoices', created_at
            )
            self.repository.insert_purchase_payment_cash(
                purchase_id, invoice_number, final_total, purchase_date, created_at, supplier_id, 'Payment processed'
            )

    def get_supplier_id(self, supplier_name):
        return self.repository.get_supplier_id(supplier_name)

    def get_all_currencies(self):
        headers, data = self.repository.get_all_currencies()
        rows = []
        for row in data:
            row_dict = {}
            for i, header in enumerate(headers):
                row_dict[header] = row[i]
            rows.append(row_dict)
        return headers, rows

    def get_invoice_data(self, purchase_id):
        purchase_data = self.repository.get_purchase_data_for_invoice(purchase_id)
        if not purchase_data:
            raise ValueError('Purchase data not found')

        invoice_number, purchase_date, supplier_name, supplier_phone, total_amount, subtotal, currency_id = purchase_data[0]

        # Get currency symbol
        currency_symbol = '$'
        if currency_id:
            currency_data = self.repository.get_currency_symbol(currency_id)
            if currency_data:
                currency_symbol = currency_data[0][0]

        purchase_items_data = self.repository.get_purchase_items_for_invoice(purchase_id)
        if not purchase_items_data:
            raise ValueError('No purchase items found to print')

        rows = []
        for item in purchase_items_data:
            product_name, quantity, unit_cost, discount_amount, total_cost = item
            discount_percent = (discount_amount / (quantity * unit_cost)) * 100 if quantity * unit_cost > 0 else 0
            rows.append({
                'product': product_name,
                'quantity': quantity,
                'price': unit_cost,
                'discount': discount_percent,
                'subtotal': total_cost,
                'currency_symbol': currency_symbol
            })

        return {
            'rows': rows,
            'supplier_name': supplier_name,
            'invoice_number': invoice_number,
            'total_amount': total_amount,
            'subtotal': subtotal,
            'supplier_phone': supplier_phone,
            'purchase_date': purchase_date,
            'currency_symbol': currency_symbol
        }
