from nicegui import ui
from pathlib import Path
from datetime import date as dt
from connection import connection
from datetime import datetime
from decimal import Decimal
from uiaggridtheme import uiAggridTheme

class PurchaseUI:
    
    def __init__(self):
        self.invoicenumber = ''
        with ui.header().classes('items-center justify-between'):
            ui.label('Purchase Management').classes('text-2xl font-bold')
            ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard')).props('flat color=white')
            self.max_purchase_id = self.get_max_purchase_id()

        # --- Global Variables ---
        self.columns = [
            {'headerName': 'Barcode', 'field': 'barcode', 'width': 100, 'headerClass': 'blue-header'},
            {'headerName': 'Product', 'field': 'product', 'width': 150, 'headerClass': 'blue-header'},
            {'headerName': 'Qty', 'field': 'quantity', 'width': 60,  'headerClass': 'blue-header'},
            {'headerName': 'Discount', 'field': 'discount', 'width': 80,  'headerClass': 'blue-header'},
            {'headerName': 'Cost', 'field': 'cost', 'width': 80,  'headerClass': 'blue-header'},
            {'headerName': 'Price', 'field': 'price', 'width': 80,  'headerClass': 'blue-header'},
            {'headerName': 'Profit', 'field': 'profit', 'width': 80,  'headerClass': 'blue-header'},
            {'headerName': 'Subtotal', 'field': 'subtotal', 'width': 100,  'headerClass': 'blue-header'}
        ]
        self.rows = []
        self.total_amount = 0
        self.total_quantity = 0
        self.total_items = 0
        self.grid_readonly = False
        self.new_mode = False

        # Initialize UI
        self.create_ui()

    def calculate_subtotal(self, quantity, cost, discount):
        return round((quantity * cost) * (1 - discount / 100), 2)

    def generate_invoice_number(self):
        try:
            existing_invoices = connection.contogetrows(
                "SELECT invoice_number FROM purchases WHERE invoice_number IS NOT NULL", []
            )
            existing_set = {row[0] for row in existing_invoices}
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
        except Exception as e:
            import time
            return f"PUR-{int(time.time())}"

    def add_product(self, e=None):
        try:
            barcode = self.barcode_input.value
            product_name = self.product_input.value
            quantity = int(self.quantity_input.value) if self.quantity_input.value else 0
            discount = float(self.discount_input.value) if self.discount_input.value else 0
            cost = float(self.cost_input.value) if self.cost_input.value else 0
            price = float(self.price_input.value) if self.price_input.value else 0
            
            if not barcode or not product_name or quantity <= 0 or cost <= 0 or price<=0:
                ui.notify('Please fill in all required fields with valid values')
                return
            
            subtotal = self.calculate_subtotal(quantity, cost, discount)
            profit = (price - cost) * quantity if price > 0 else 0
            
            self.rows.append({
                'barcode': barcode,
                'product': product_name,
                'quantity': quantity,
                'discount': discount,
                'cost': cost,
                'price': price,
                'profit': profit,
                'subtotal': subtotal,
            })
            
            self.total_amount += subtotal
            self.total_label.text = f"Total: ${self.total_amount:.2f}"
            self.clear_inputs_inputs()
            self.aggrid.update()
            
        except ValueError as e:
            ui.notify(f'Invalid input: {str(e)}')

    def clear_inputs_inputs(self):
        self.barcode_input.value = ''
        self.product_input.value = ''
        self.quantity_input.value = 1
        self.discount_input.value = 0
        self.cost_input.value = 0.0
        self.price_input.value = 0.0
    
    def clear_inputs(self):
        self.purchases_aggrid.classes('dimmed')
        self.supplier_input.value = 'Default Supplier'
        self.phone_input.value = ''
        self.barcode_input.value = ''
        self.product_input.value = ''
        self.quantity_input.value = 1
        self.discount_input.value = 0
        self.cost_input.value = 0.0
        self.price_input.value = 0.0
        self.discount_percent_input.value = 0
        self.discount_amount_input.value = 0
        self.payment_method.value = 'Cash'  # Reset payment method to Cash
        
        self.rows.clear()
        self.aggrid.options['rowData'] = self.rows
        self.aggrid.update()
        
        self.total_amount = 0
        self.subtotal_label.text = "Subtotal: $0.00"
        self.total_label.text = "Total: $0.00"
        
        self.current_purchase_id = None
        self.new_mode=True

    def update_product_dropdown(self, e):
        try:
            barcode = self.barcode_input.value
            if barcode:
                product_data = []
                connection.contogetrows(
                    f"SELECT barcode, product_name, cost_price FROM products WHERE barcode = '{barcode}'", 
                    product_data
                )
                
                if product_data:
                    product = product_data[0]
                    self.product_input.value = product[1]
                    self.cost_input.value = float(product[2])
                    ui.notify(f"Product loaded: {product[1]}")
                    
                else:
                    ui.notify("Product not found for this barcode")
        except Exception as e:
            ui.notify(f'Error updating product: {str(e)}')

    async def on_row_click_edit_cells(self, e):
        try:
            selected_row = await self.aggrid.get_selected_row()
            
            if selected_row and isinstance(selected_row, dict) and 'barcode' in selected_row:
                ui.notify(f"Selected: {selected_row.get('product', 'Unknown')} - Qty: {selected_row.get('quantity', 0)}")
                self.open_edit_dialog(selected_row)
            else:
                ui.notify("Please select a valid row to edit")
                
        except Exception as ex:
            ui.notify(f"Error opening edit dialog: {str(ex)}")

    def open_product_dialog(self):
        dialog = ui.dialog()
        
        with dialog, ui.card().classes('w-72'):
            ui.label('Select Product').classes('text-xl font-bold mb-4')
            
            headers = []
            connection.contogetheaders("SELECT barcode, product_name, stock_quantity, cost_price FROM products", headers)
            columns = [{'name': header, 'label': header.title(), 'field': header, 'sortable': True} for header in headers]
            
            data = []
            connection.contogetrows("SELECT barcode, product_name, stock_quantity, cost_price FROM products", data)
            rows = []
            for row in data:
                row_dict = {}
                for i, header in enumerate(headers):
                    row_dict[header] = row[i]
                rows.append(row_dict)
            
            table = ui.table(columns=columns, rows=rows, pagination=5).classes('w-full text-xs')
            ui.input('Search').bind_value(table, 'filter').classes('text-xs')
            
            def on_row_click(row_data):
                selected_row = row_data.args[1]
                self.product_input.value = selected_row['product_name']
                self.barcode_input.value = selected_row['barcode']
                self.cost_input.value = selected_row['cost_price']
                dialog.close()
            
            table.on('rowClick', on_row_click)
        
        dialog.open()

    def open_edit_dialog(self, row_data):
        dialog = ui.dialog()
        
        with dialog, ui.card().classes('w-96 p-6'):
            ui.label('Edit Product').classes('text-xl font-bold mb-4')
            
            with ui.column().classes('w-full gap-3'):
                ui.label(f"Barcode: {row_data['barcode']}").classes('font-medium')
                ui.label(f"Product: {row_data['product']}").classes('font-medium')
                
                quantity_input = ui.number('Quantity', value=row_data['quantity'], min=1)
                discount_input = ui.number('Discount %', value=row_data['discount'], min=0, max=100)
                cost_input = ui.number('Cost', value=row_data['cost'], min=0, step=0.01)
                
                with ui.row().classes('w-full justify-end gap-2 mt-4'):
                    ui.button('Cancel', on_click=dialog.close)
                    ui.button('Delete', on_click=lambda: self.delete_row(row_data, dialog)).props('color=negative')
                    ui.button('Save', on_click=lambda: self.save_edited_row(
                        row_data, 
                        quantity_input.value, 
                        discount_input.value, 
                        cost_input.value,
                        dialog
                    )).props('color=primary')
        
        dialog.open()

    def save_edited_row(self, original_row, new_quantity, new_discount, new_cost, dialog):
        try:
            row_index = next(i for i, row in enumerate(self.rows) 
                           if row['barcode'] == original_row['barcode'] and 
                              row['product'] == original_row['product'])
            
            old_subtotal = self.rows[row_index]['subtotal']
            
            self.rows[row_index]['quantity'] = int(new_quantity)
            self.rows[row_index]['discount'] = float(new_discount)
            self.rows[row_index]['cost'] = float(new_cost)
            self.rows[row_index]['subtotal'] = self.calculate_subtotal(
                int(new_quantity), 
                float(new_cost), 
                float(new_discount)
            )
            
            self.total_amount = self.total_amount - old_subtotal + self.rows[row_index]['subtotal']
            self.total_label.text = f"Total: ${self.total_amount:.2f}"
            
            self.aggrid.options['rowData'] = self.rows
            self.aggrid.update()
            
            dialog.close()
            ui.notify('Product updated successfully')
            
        except Exception as e:
            ui.notify(f'Error updating product: {str(e)}')

    def delete_row(self, row_data, dialog):
        try:
            row_index = next(i for i, row in enumerate(self.rows) 
                           if row['barcode'] == row_data['barcode'] and 
                              row['product'] == row_data['product'])
            
            self.total_amount -= self.rows[row_index]['subtotal']
            self.total_label.text = f"Total: ${self.total_amount:.2f}"
            
            del self.rows[row_index]
            self.aggrid.options['rowData'] = self.rows
            self.aggrid.update()
            
            dialog.close()
            ui.notify('Product removed successfully')
            
        except Exception as e:
            ui.notify(f'Error removing product: {str(e)}')

    def update_totals(self):
        subtotal = sum(row['subtotal'] for row in self.rows)
        total_quantity = sum(row['quantity'] for row in self.rows)
        
        self.summary_label.text = f"{len(self.rows)} items"
        self.quantity_total_label.text = f"Total Qty: {total_quantity}"
        
        discount_percent = float(self.discount_percent_input.value or 0)
        discount_amount = float(self.discount_amount_input.value or 0)
        
        if discount_percent == 0 and discount_amount == 0:
            self.subtotal_label.text = f"${subtotal:.2f}"
            final_total = subtotal
        else:
            total_after_percent = subtotal * (1 - discount_percent / 100)
            final_total = total_after_percent - discount_amount
            self.subtotal_label.text = f"${subtotal:.2f}"
        
        self.total_label.text = f"${max(0, round(final_total, 2)):.2f}"

    def get_max_purchase_id(self):
        try:
            max_id_result = []
            connection.contogetrows("SELECT MAX(id) FROM purchases", max_id_result)
            return max_id_result[0][0] if max_id_result and max_id_result[0][0] else 0
        except Exception as e:
            return 0

    def show_undo_confirmation(self):
        dialog = ui.dialog()
        
        with dialog, ui.card().classes('w-96 p-6'):
            ui.label('Confirm Undo').classes('text-xl font-bold mb-4')
            ui.label('Are you sure you want to undo all changes?').classes('mb-4')
            
            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button('Cancel', on_click=dialog.close)
                ui.button('OK', on_click=lambda: self.perform_undo(dialog)).props('color=primary')
        
        dialog.open()

    def delete_purchase(self):
        try:
            purchase_id = None
            
            if hasattr(self, 'current_purchase_id') and self.current_purchase_id:
                purchase_id = self.current_purchase_id
            elif self.rows:
                purchase_id = self.get_max_purchase_id()
            
            if not purchase_id:
                ui.notify('No purchase data available to delete')
                return
            
            dialog = ui.dialog()
            
            with dialog, ui.card().classes('w-96 p-6'):
                ui.label('Confirm Delete').classes('text-xl font-bold mb-4 text-red-600')
                ui.label(f'Are you sure you want to delete purchase ID: {purchase_id}?').classes('mb-2')
                ui.label('This will permanently remove the purchase and all its items from the database.').classes('text-sm text-gray-600 mb-4')
                
                with ui.row().classes('w-full justify-end gap-3 mt-6'):
                    ui.button('No', on_click=dialog.close).props('flat')
                    ui.button('Yes, Delete', on_click=lambda: self.perform_delete_purchase(purchase_id, dialog)).props('color=negative')
            
            dialog.open()
            
        except Exception as e:
            ui.notify(f'Error preparing delete: {str(e)}')

    def perform_delete_purchase(self, purchase_id, dialog):
        try:
            # Get purchase details before deletion
            purchase_data = []
            connection.contogetrows(f"SELECT total_amount, payment_status, supplier_id FROM purchases WHERE id = {purchase_id}",
                purchase_data
            )
            
            if purchase_data:
                purchase_total = purchase_data[0][0]
                payment_status = purchase_data[0][1]
                supplier_id = purchase_data[0][2]
                
                # Delete purchase items first
                connection.deleterow("DELETE FROM purchase_items WHERE purchase_id = ?", [purchase_id])
                
                # Delete the purchase
                connection.deleterow("DELETE FROM purchases WHERE id = ?", [purchase_id])
                
                # Deduct from supplier balance if payment method was 'On Account'
                if payment_status == 'pending' and supplier_id:
                    connection.update_supplierbalance("UPDATE suppliers SET balance = balance - ? WHERE id = ?", (purchase_total, supplier_id))
                    ui.notify(f'Purchase {purchase_id} deleted successfully. Supplier balance deducted by ${purchase_total:.2f}')
                else:
                    ui.notify(f'Purchase {purchase_id} deleted successfully')
                
                dialog.close()
                
                self.purchases_aggrid.update()
                self.clear_inputs()
                self.refresh_purchases_table()
            else:
                ui.notify(f'Purchase {purchase_id} not found')
                dialog.close()
            
        except Exception as e:
            ui.notify(f'Error deleting purchase: {str(e)}')
            dialog.close()

    def perform_undo(self, dialog):
        self.rows.clear()
        self.aggrid.options['rowData'] = self.rows
        self.aggrid.update()
        
        self.total_amount = 0
        self.subtotal_label.text = "Subtotal: $0.00"
        self.total_label.text = "Total: $0.00"
        
        self.clear_inputs()
        dialog.close()
        self.purchases_aggrid.classes(remove='dimmed')
        ui.notify('Undo completed successfully')

    def refresh_purchases_table(self):
        try:
            raw_purchases_data = []
            connection.contogetrows(
                "SELECT p.id, p.purchase_date, s.name, p.total_amount, p.invoice_number, p.payment_status FROM purchases p INNER JOIN suppliers s ON s.id = p.supplier_id ORDER BY p.id DESC", 
                raw_purchases_data
            )
            
            purchases_data = []
            for row in raw_purchases_data:
                purchases_data.append({
                    'id': row[0],
                    'purchase_date': str(row[1]),
                    'supplier_name': str(row[2]),
                    'total_amount': float(row[3]),
                    'invoice_number': str(row[4]),
                    'payment_status': str(row[5])
                })
            
            self.purchases_aggrid.options['rowData'] = purchases_data
            self.purchases_aggrid.update()
            self.purchases_aggrid.classes(remove='dimmed')
            
            self.update_totals()
            
            ui.notify('Purchases table refreshed successfully')
            
        except Exception as e:
            ui.notify(f'Error refreshing purchases table: {str(e)}')

    def save_purchase(self):
        try:
            if not self.rows:
                ui.notify('No items to save!')
                return
            
            purchase_date = str(self.date_input.value)
            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            supplier_name = self.supplier_input.value or 'Default Supplier'
            supplier_id = connection.getid('select id from suppliers where name = ?', [supplier_name])
            
            # Get payment method and set payment status
            payment_method = self.payment_method.value
            payment_status = 'completed' if payment_method == 'Cash' else 'pending'
            
            subtotal = sum(row['subtotal'] for row in self.rows)
            discount_percent = float(self.discount_percent_input.value or 0)
            discount_amount = float(self.discount_amount_input.value or 0)
            total_after_percent = subtotal * (1 - discount_percent / 100)
            final_total = total_after_percent - discount_amount
            
            if hasattr(self, 'current_purchase_id') and self.current_purchase_id:
                purchase_sql = """
                    UPDATE purchases 
                    SET purchase_date = ?, supplier_id = ?, subtotal = ?, discount_amount = ?, 
                        total_amount = ?, created_at = ?, payment_status = ?
                    WHERE id = ?
                """
                purchase_values = (purchase_date, supplier_id, subtotal, discount_amount, final_total, created_at, payment_status, self.current_purchase_id)
                connection.insertingtodatabase(purchase_sql, purchase_values)
                
                delete_items_sql = "DELETE FROM purchase_items WHERE purchase_id = ?"
                connection.insertingtodatabase(delete_items_sql, [self.current_purchase_id])
                
                for row in self.rows:
                    product_id = connection.getid('select id from products where product_name = ?', [row['product']])
                    barcode = row['barcode']
                    product_id_from_barcode = connection.getid('select id from products where barcode = ?', [barcode])
                    final_product_id = product_id_from_barcode or product_id
                    
                    purchase_item_sql = """
                        INSERT INTO purchase_items (purchase_id, barcode, product_id, quantity, unit_cost, total_cost, unit_price, profit, discount_amount)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    purchase_item_values = (
                        self.current_purchase_id,
                        row['barcode'],
                        final_product_id,
                        row['quantity'],
                        row['cost'],
                        row['subtotal'], 
                        row['price'],
                        row['profit'],
                        row['discount']
                    )
                    connection.insertingtodatabase(purchase_item_sql, purchase_item_values)
                    
                    # Update product information in products table
                    update_product_sql = """
                        UPDATE products 
                        SET cost_price = ?, price= ?, stock_quantity = stock_quantity + ?,updated_at=?
                        WHERE id = ?
                    """
                    update_product_values = (
                        row['cost'],
                        row['price'],
                        row['quantity'],
                        created_at,
                        final_product_id
                    )
                    connection.update_product(update_product_sql, update_product_values)
                
                    # Update supplier balance for pending payments (On Account)
                    if supplier_id and payment_status == 'pending':
                        update_supplier_sql = "UPDATE suppliers SET balance = balance + ? WHERE id = ?"
                        connection.update_supplierbalance(update_supplier_sql, (final_total, supplier_id))
                    ui.notify(f'Purchase and products updated successfully! ID: {self.current_purchase_id}. Supplier balance updated for pending payment.')
                else:
                    ui.notify(f'Purchase and products updated successfully! ID: {self.current_purchase_id}. Cash payment - supplier balance not updated.')
                
            else:
                invoice_number = self.generate_invoice_number()
                
                purchase_sql = """
                    INSERT INTO purchases (purchase_date, supplier_id, subtotal, discount_amount, total_amount, invoice_number, created_at, payment_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """
                purchase_values = (purchase_date, supplier_id, subtotal, discount_amount, final_total, invoice_number, created_at, payment_status)
                connection.insertingtodatabase(purchase_sql, purchase_values)
                
                last_purchase_id = connection.getid("SELECT MAX(id) FROM purchases", [])
                
                for row in self.rows:
                    product_id = connection.getid('select id from products where product_name = ?', [row['product']])
                    barcode = row['barcode']
                    product_id_from_barcode = connection.getid('select id from products where barcode = ?', [barcode])
                    final_product_id = product_id_from_barcode or product_id
                    
                    purchase_item_sql = """
                        INSERT INTO purchase_items (purchase_id, barcode, product_id, quantity, unit_cost, total_cost, unit_price, profit, discount_amount)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    purchase_item_values = (
                        last_purchase_id,
                        row['barcode'],
                        final_product_id,
                        row['quantity'],
                        row['cost'],
                        row['subtotal'], 
                        row['price'],
                        row['profit'],
                        row['discount']
                    )
                    connection.insertingtodatabase(purchase_item_sql, purchase_item_values)
                    
                    update_product_sql = """
                        UPDATE products 
                        SET cost_price = ?, price = ?, stock_quantity = stock_quantity + ?,updated_at=?
                        WHERE id = ?
                    """
                    update_product_values = (
                        row['cost'],
                        row['price'],
                        row['quantity'],
                        created_at,
                        final_product_id
                    )
                    connection.update_product(update_product_sql, update_product_values)
                
                # Update supplier balance for pending payments (On Account)
                if supplier_id and payment_status == 'pending':
                    update_supplier_sql = "UPDATE suppliers SET balance = balance + ? WHERE id = ?"
                    connection.update_supplierbalance(update_supplier_sql, (final_total, supplier_id))
                    ui.notify(f'Purchase saved successfully! Invoice: {invoice_number}. Supplier balance updated for pending payment.')
                else:
                    ui.notify(f'Purchase saved successfully! Invoice: {invoice_number}. Cash payment - supplier balance not updated.')
            
            self.refresh_purchases_table()
            self.purchases_aggrid.classes(remove='dimmed')
        except Exception as e:
            ui.notify(f'Error saving purchase: {str(e)}')

    def load_max_purchase(self):
        try:
            max_id = self.get_max_purchase_id()
            if max_id > 0:
                purchase_data = []
                connection.contogetrows(
                    f"SELECT p.id, p.purchase_date, s.name, p.total_amount, p.invoice_number, p.payment_status FROM purchases p INNER JOIN suppliers s ON s.id = p.supplier_id WHERE p.id = {max_id}",
                    purchase_data
                )
                
                if purchase_data:
                    row_data = {
                        'id': purchase_data[0][0],
                        'purchase_date': purchase_data[0][1],
                        'supplier_name': purchase_data[0][2],
                        'total_amount': purchase_data[0][3],
                        'invoice_number': purchase_data[0][4],
                        'payment_status': purchase_data[0][5]
                    }
                    
                    self.supplier_input.value = row_data['supplier_name']
                    self.current_purchase_id = max_id
                    
                    # Set payment method based on payment status
                    if row_data['payment_status'] == 'completed':
                        self.payment_method.value = 'Cash'
                    else:
                        self.payment_method.value = 'On Account'
                    
                    purchase_items_data = []
                    connection.contogetrows(
                        f"SELECT pr.barcode, pr.product_name, pi.quantity, ISNULL(pi.discount_amount, 0), pi.unit_cost, pi.total_cost, pi.unit_price, pi.profit FROM purchase_items pi INNER JOIN products pr ON pr.id = pi.product_id WHERE pi.purchase_id = {max_id}",
                        purchase_items_data
                    )
                    
                    self.rows.clear()
                    for item in purchase_items_data:
                        self.rows.append({
                            'barcode': str(item[0]) if item[0] else '',
                            'product': str(item[1]) if item[1] else 'Unknown Product',
                            'quantity': int(item[2]) if item[2] else 0,
                            'discount': float(item[3]) if item[3] else 0.0,
                            'cost': float(item[4]) if item[4] else 0.0,
                            'subtotal': float(item[5]) if item[5] else 0.0,
                            'price': float(item[6]) if item[6] else 0.0,
                            'profit': float(item[7]) if item[7] else 0.0
                        })
                
                    self.aggrid.options['rowData'] = self.rows
                    self.aggrid.update()
                    
                    self.total_amount = sum(row['subtotal'] for row in self.rows)
                    self.total_label.text = f"Total: ${self.total_amount:.2f}"
                    self.invoicenumber = row_data["invoice_number"]
                    
                    ui.notify(f'✅ Automatically loaded purchase ID: {max_id} - Invoice: {row_data["invoice_number"]} - Payment: {row_data["payment_status"]}')
                else:
                    ui.notify('No purchases found in database')
            else:
                ui.notify('No purchases found in database')
                
        except Exception as e:
            ui.notify(f'Error loading max purchase: {str(e)}')

    def create_ui(self):
        with ui.element('div').classes('flex w-full h-screen'):
            with ui.element('div').classes('w-1/12 bg-gray-100 p-1 flex flex-col gap-1'):
                ui.button('🆕 New', on_click=self.clear_inputs).classes('text-xs py-1 px-2 w-full')
                ui.button('💾 Save', on_click=self.save_purchase).classes('text-xs py-1 px-2 w-full')
                ui.button('↩️ Undo', on_click=self.show_undo_confirmation).classes('text-xs py-1 px-2 w-full')
                ui.button('🗑️ Delete', on_click=self.delete_purchase).classes('text-xs py-1 px-2 w-full')
                ui.button('🔄 Refresh', on_click=self.refresh_purchases_table).classes('text-xs py-1 px-2 w-full')
                            
            with ui.element('div').classes('w-11/12 p-1 flex flex-col gap-1 overflow-y-auto'):
                with ui.splitter(horizontal=True, value=35).classes('w-full h-full') as main_splitter:
                    with main_splitter.separator:
                        ui.icon('lightbulb').classes('text-blue text-sm')
                    with main_splitter.before:
                        with ui.element('div').classes('w-full h-full p-1'):
                            ui.label('Purchase History').classes('text-sm font-bold text-gray-700 mb-1')
                            
                            purchases_columns = [
                                {'headerName': 'ID', 'field': 'id', 'width': 40, 'filter': True, 'headerClass': 'blue-header'},
                                {'headerName': 'Date', 'field': 'purchase_date', 'width': 70, 'filter': True, 'headerClass': 'blue-header'},
                                {'headerName': 'Supplier', 'field': 'supplier_name', 'width': 100, 'filter': True, 'headerClass': 'blue-header'},
                                {'headerName': 'Total', 'field': 'total_amount', 'width': 60,  'filter': True, 'headerClass': 'blue-header'},
                                {'headerName': 'Invoice', 'field': 'invoice_number', 'width': 80, 'filter': True, 'headerClass': 'blue-header'},
                                {'headerName': 'Status', 'field': 'payment_status', 'width': 60, 'filter': True, 'headerClass': 'blue-header'}
                            ]

                            raw_purchases_data = []
                            connection.contogetrows(
                                "SELECT p.id, p.purchase_date, s.name, p.total_amount, p.invoice_number, p.payment_status FROM purchases p INNER JOIN suppliers s ON s.id = p.supplier_id ORDER BY p.id DESC", 
                                raw_purchases_data
                            )
                            
                            purchases_data = []
                            for row in raw_purchases_data:
                                purchases_data.append({
                                    'id': row[0],
                                    'purchase_date': str(row[1]),
                                    'supplier_name': str(row[2]),
                                    'total_amount': float(row[3]),
                                    'invoice_number': str(row[4]),
                                    'payment_status': str(row[5])
                                })

                            self.purchases_aggrid = ui.aggrid({
                                'columnDefs': purchases_columns,
                                'rowData': purchases_data,
                                'defaultColDef': {'flex': 1, 'minWidth': 30, 'sortable': True, 'filter': True},
                                'rowSelection': 'single',
                                'domLayout': 'normal',
                            }).classes('w-full rounded border border-blue-200 ag-theme-quartz-custom').style('overflow-y: auto;height:200px;')
                            
                            async def handle_purchases_aggrid_click():
                                try:
                                    selected_row = await self.purchases_aggrid.get_selected_row()
                                    if selected_row and isinstance(selected_row, dict) and 'id' in selected_row:
                                        purchase_id = selected_row['id']
                                        supplier_name = selected_row['supplier_name']
                                        payment_status = selected_row['payment_status']
                                        
                                        ui.notify(f'Loading items for purchase ID: {purchase_id}')
                                        
                                        self.supplier_input.value = supplier_name
                                        self.current_purchase_id = purchase_id
                                        
                                        # Set payment method based on payment status
                                        if payment_status == 'completed':
                                            self.payment_method.value = 'Cash'
                                        else:
                                            self.payment_method.value = 'On Account'
                                        
                                        purchase_items_data = []
                                        connection.contogetrows(
                                            f"SELECT pr.barcode, pr.product_name, pi.quantity, ISNULL(pi.discount_amount, 0), pi.unit_cost, pi.total_cost, pi.unit_price, pi.profit FROM purchase_items pi INNER JOIN products pr ON pr.id = pi.product_id WHERE pi.purchase_id = {purchase_id}",
                                            purchase_items_data
                                        )
                                        
                                        self.rows.clear()
                                        for item in purchase_items_data:
                                            self.rows.append({
                                                'barcode': str(item[0]) if item[0] else '',
                                                'product': str(item[1]) if item[1] else 'Unknown Product',
                                                'quantity': int(item[2]) if item[2] else 0,
                                                'discount': float(item[3]) if item[3] else 0.0,
                                                'cost': float(item[4]) if item[4] else 0.0,
                                                'subtotal': float(item[5]) if item[5] else 0.0,
                                                'price': float(item[6]) if item[6] else 0.0,
                                                'profit': float(item[7]) if item[7] else 0.0
                                            })
                                    
                                        self.aggrid.options['rowData'] = self.rows
                                        self.aggrid.update()
                                        
                                        self.total_amount = sum(row['subtotal'] for row in self.rows)
                                        self.total_label.text = f"Total: ${self.total_amount:.2f}"
                                        self.invoicenumber = selected_row["invoice_number"]
                                        
                                        self.update_totals()
                                        
                                        ui.notify(f'✅ Loaded {len(self.rows)} items for invoice {selected_row["invoice_number"]} - Payment: {payment_status}')
                                        
                                except Exception as ex:
                                    ui.notify(f'❌ Error loading purchase items: {str(ex)}')
                            
                            self.purchases_aggrid.on('cellClicked', handle_purchases_aggrid_click)
                            
                            ui.timer(0.1, self.load_max_purchase, once=True)
                
                    with main_splitter.after:
                        with ui.element('div').classes('w-full'):
                            with ui.row().classes('w-full items-center gap-1 mb-1 p-1 bg-gray-50 rounded'):
                                self.date_input = ui.input('Date', value=str(dt.today())).classes('w-24 h-7 text-xs')
                                
                                self.supplier_input = ui.input('Supplier', placeholder='Supplier').classes('w-28 h-7 text-xs')
                                self.supplier_input.on('click', lambda: self.supplier_dialog.open())
                                
                                self.phone_input = ui.input('Phone', placeholder='Phone').classes('w-20 h-7 text-xs')
                                
                                ui.input('Currency', value='USD').classes('w-12 h-7 text-xs')
                                
                                # Payment method - compact
                                ui.label('Payment:').classes('text-xs font-medium h-7')
                                self.payment_method = ui.radio(options=['Cash', 'On Account'], value='Cash').props('inline')

                        self.supplier_dialog = ui.dialog()
                        with self.supplier_dialog, ui.card().classes('w-750'):
                            headers = []
                            connection.contogetheaders("SELECT id, name, phone FROM suppliers", headers)
                            columns = [{'name': header, 'label': header.title(), 'field': header, 'sortable': True} for header in headers]
                            
                            data = []
                            connection.contogetrows("SELECT id, name, phone FROM suppliers", data)
                            rows = []
                            for row in data:
                                row_dict = {}
                                for i, header in enumerate(headers):
                                    row_dict[header] = row[i]
                                rows.append(row_dict)
                            
                            table = ui.table(columns=columns, rows=rows, pagination=5).classes('w-full')
                            ui.input('Search').bind_value(table, 'filter').classes('text-xs')
                            
                            def on_row_click(row_data):
                                selected_row = row_data.args[1]
                                self.supplier_input.value = selected_row['name']
                                self.phone_input.value = selected_row['phone']
                                self.supplier_dialog.close()
                                
                            table.on('rowClick', on_row_click)

                        self.product_dialog = ui.dialog()
                        with self.product_dialog, ui.card().classes('w-750'):
                            headers = []
                            connection.contogetheaders("SELECT barcode, product_name, stock_quantity, cost_price FROM products", headers)
                            columns = [{'name': header, 'label': header.title(), 'field': header, 'sortable': True} for header in headers]
                            
                            data = []
                            connection.contogetrows("SELECT barcode, product_name, stock_quantity, cost_price FROM products", data)
                            rows = []
                            for row in data:
                                row_dict = {}
                                for i, header in enumerate(headers):
                                    row_dict[header] = row[i]
                                rows.append(row_dict)
                            
                            table = ui.table(columns=columns, rows=rows, pagination=10).classes('w-full text-xs')
                            ui.input('Search').bind_value(table, 'filter').classes('text-xs')
                            
                            def on_product_select(row_data):
                                selected_row = row_data.args[1]
                                self.product_input.value = selected_row['product_name']
                                self.barcode_input.value = selected_row['barcode']
                                self.cost_input.value = selected_row['cost_price']
                                self.product_dialog.close()
                                
                            table.on('rowClick', on_product_select)

                        with ui.element('div').classes('w-full '):
                            with ui.row().classes('w-full items-center gap-3 p-3 bg-gray-100 rounded-lg shadow-sm'):
                                self.barcode_input = ui.input('Barcode', placeholder='Barcode').classes('w-24 h-10 text-sm').on('change', lambda e: self.update_product_dropdown(e))
                                self.product_input = ui.input('Product', placeholder='Product').classes('w-32 h-10 text-sm').on('click', lambda: self.product_dialog.open())
                                self.quantity_input = ui.number('Qty', value=1, min=1).classes('w-16 h-10 text-sm')
                                self.cost_input = ui.number('Cost', value=0.0, min=0).classes('w-20 h-10 text-sm')
                                self.price_input = ui.number('Price', value=0.0, min=0).classes('w-20 h-10 text-sm')
                                self.discount_input = ui.number('Disc %', value=0, min=0, max=100).classes('w-16 h-10 text-sm')
                                ui.button('Add', on_click=self.add_product).props('size=md').classes('h-10 px-4 text-sm font-medium')
                            uiAggridTheme.addingtheme()
                            
                            with ui.element('div').classes('w-full h-[calc(100vh-480px)] min-h-48 border rounded-lg bg-white shadow-sm mt-4'):
                                self.aggrid = ui.aggrid({
                                    'columnDefs': self.columns,
                                    'rowData': self.rows,
                                    'defaultColDef': {'flex': 1, 'minWidth': 40, 'sortable': True, 'filter': True},
                                    'rowSelection': 'single',
                                    'domLayout': 'normal',
                                }).classes('w-full h-full p-2')
                                
                                async def handle_aggrid_click():
                                    try:
                                        selected_row = await self.aggrid.get_selected_row()
                                        if selected_row:
                                            self.open_edit_dialog(selected_row)
                                            self.update_totals()
                                    except Exception as ex:
                                        ui.notify(f'Error: {str(ex)}')
                                
                                self.aggrid.on('cellClicked', handle_aggrid_click)

                        with ui.element('div').classes('w-full p-4 bg-gray-100 border-t border-gray-300 fixed bottom-0 left-0 right-0 z-10'):
                            with ui.row().classes('w-full justify-between items-center'):
                                with ui.column().classes('gap-1'):
                                    ui.label('SUMMARY').classes('text-sm font-bold text-gray-700')
                                    self.summary_label = ui.label('0 items').classes('text-sm text-gray-600')
                                    self.quantity_total_label = ui.label('Qty: 0').classes('text-sm text-gray-600')
                                
                                with ui.column().classes('gap-2 items-center'):
                                    with ui.row().classes('items-center gap-2'):
                                        ui.label('Discount:').classes('text-sm font-medium')
                                        self.discount_percent_input = ui.number(
                                            value=0,
                                            min=0,
                                            max=100,
                                            on_change=self.update_totals
                                        ).classes('w-24 h-12 text-xl px-2 border-2 border-gray-300 rounded')
                                        ui.label('%').classes('text-sm')
                                        
                                        self.discount_amount_input = ui.number(
                                            value=0,
                                            min=0,
                                            on_change=self.update_totals
                                        ).classes('w-32 h-12 text-xl px-2 border-2 border-gray-300 rounded')
                                
                                with ui.column().classes('gap-1 items-end'):
                                    self.subtotal_label = ui.label('Subtotal: $0.00').classes('text-2xl font-bold')
                                    self.total_label = ui.label('Total: $0.00').classes('text-3xl font-bold text-blue-600')

@ui.page('/purchase')
def purchase_page_route():
    PurchaseUI()
