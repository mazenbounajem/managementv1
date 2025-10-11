from nicegui import ui
from pathlib import Path
from datetime import date as dt
from datetime import datetime
from decimal import Decimal
from uiaggridtheme import uiAggridTheme
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage
from purchase_service import PurchaseService
from color_palette import ColorPalette

@ui.page('/purchase')
def purchase_page_route():
    PurchaseUI()

class PurchaseUI:

    def __init__(self):
        self.invoicenumber = ''
        self.service = PurchaseService()
        self.selected_supplier_index = 0
        self.supplier_rows = []
        self.supplier_grid = None
        self.selected_supplier_row = None
        self.product_rows = []
        self.product_grid = None

        # Check if user is logged in
        user = session_storage.get('user')
        if not user:
            ui.notify('Please login to access this page', color='red')
            ui.run_javascript('window.location.href = "/login"')
            return

        # Get user permissions
        permissions = self.service.get_user_permissions(user['role_id'])
        
        # Create enhanced navigation instance
        navigation = EnhancedNavigation(permissions, user)
        navigation.create_navigation_drawer()
        navigation.create_navigation_header()

        self.max_purchase_id = self.service.get_max_purchase_id()

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
        self.old_price = None
        self.old_cost_price = None

        # Initialize UI
        self.create_ui()

    def _load_purchase_details(self, purchase_id):
        """Helper to load purchase details into the UI."""
        try:
            details = self.service.get_purchase_details(purchase_id)
            self.supplier_input.value = details['supplier_name']
            self.phone_input.value = details['phone']
            self.date_input.value = str(details['purchase_date'])
            self.current_purchase_id = purchase_id
            self.payment_method.value = 'Cash' if details['payment_status'] == 'completed' else 'On Account'
            self.invoicenumber = details['invoice_number']
            self.rows = details['rows']
            self.aggrid.options['rowData'] = self.rows
            self.aggrid.update()
            self.total_amount = sum(row['subtotal'] for row in self.rows)
            self.update_totals()
            return f'✅ Loaded {len(self.rows)} items for invoice {self.invoicenumber} - Payment: {details["payment_status"]}'
        except ValueError as e:
            raise e

    def calculate_subtotal(self, quantity, cost, discount):
        return round((quantity * cost) * (1 - discount / 100), 2)

    def add_product(self, e=None):
        try:
            barcode = self.barcode_input.value
            product_name = self.product_input.value
            quantity = int(self.quantity_input.value) if self.quantity_input.value else 0
            discount = float(self.discount_input.value) if self.discount_input.value else 0
            cost = float(self.cost_input.value) if self.cost_input.value else 0
            price = float(self.price_input.value) if self.price_input.value else 0

            if not barcode or not product_name or quantity <= 0 or cost <= 0 or price <= 0:
                ui.notify('Please fill in all required fields with valid values')
                return

            subtotal = self.calculate_subtotal(quantity, cost, discount)
            profit = (price - cost) * quantity if price > 0 else 0

            self.rows.append({
                'barcode': barcode, 'product': product_name, 'quantity': quantity,
                'discount': discount, 'cost': cost, 'price': price, 'profit': profit,
                'subtotal': subtotal, 'old_cost_price': self.old_cost_price,
                'old_price': self.old_price,
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
        self.supplier_input.value = 'Default Supplier'
        self.phone_input.value = ''
        self.rows.clear()
        self.aggrid.options['rowData'] = self.rows
        self.aggrid.update()
        self.total_amount = 0
        self.update_totals()
        self.current_purchase_id = None

    def update_product_dropdown(self, e):
        try:
            barcode = self.barcode_input.value
            if barcode:
                product_data = self.service.get_product_by_barcode(barcode)
                if product_data:
                    product = product_data[0]
                    self.product_input.value = product[1]
                    self.cost_input.value = float(product[2])
                    self.price_input.value = float(product[3])
                    self.old_cost_price = float(product[2])
                    self.old_price = float(product[3])
                    ui.notify(f"Product loaded: {product[1]}")
                else:
                    ui.notify("Product not found for this barcode")
        except Exception as e:
            ui.notify(f'Error updating product: {str(e)}')

    def open_product_dialog(self):
        with ui.dialog() as dialog, ui.card().classes('w-full max-w-6xl').style(f'background-color: {ColorPalette.MAIN_BG}; color: {ColorPalette.MAIN_TEXT}'):
            ui.label('Select Product').classes('text-lg font-bold mb-4').style(f'color: {ColorPalette.MAIN_TEXT}')

            search_input = ui.input('Search').classes('text-xs mb-4').style(f'background-color: {ColorPalette.MAIN_BG}; color: {ColorPalette.MAIN_TEXT}; border: 1px solid {ColorPalette.BORDER_LIGHT}').on('keydown.enter', lambda e: self.filter_product_rows(e.sender.value))

            headers, rows = self.service.get_all_products()
            self.product_rows = rows
            columns = [{'headerName': header, 'field': header, 'sortable': True, 'filter': True} for header in headers]
            self.product_grid = ui.aggrid({
                'columnDefs': columns,
                'rowData': rows,
                'domLayout': 'autoHeight'
            }).classes('w-full ag-theme-quartz-custom')

            self.product_grid.on('cellClicked', lambda e, d=dialog: self.handle_product_grid_click(e, d))

            with ui.row().classes('w-full justify-end mt-4'):
                ui.button('Cancel', on_click=dialog.close).style(f'background-color: {ColorPalette.BUTTON_SECONDARY_BG}; color: {ColorPalette.BUTTON_SECONDARY_TEXT}')
        dialog.open()

    def open_edit_dialog(self, row_data):
        with ui.dialog() as dialog, ui.card().style(f'background-color: {ColorPalette.MAIN_BG}; color: {ColorPalette.MAIN_TEXT}'):
            ui.label('Edit Product').classes('text-lg font-bold mb-4').style(f'color: {ColorPalette.MAIN_TEXT}')
            with ui.column():
                quantity = ui.number('Quantity', value=row_data['quantity']).style(f'background-color: {ColorPalette.MAIN_BG}; color: {ColorPalette.MAIN_TEXT}; border: 1px solid {ColorPalette.BORDER_LIGHT}')
                discount = ui.number('Discount', value=row_data['discount']).style(f'background-color: {ColorPalette.MAIN_BG}; color: {ColorPalette.MAIN_TEXT}; border: 1px solid {ColorPalette.BORDER_LIGHT}')
                cost = ui.number('Cost', value=row_data['cost']).style(f'background-color: {ColorPalette.MAIN_BG}; color: {ColorPalette.MAIN_TEXT}; border: 1px solid {ColorPalette.BORDER_LIGHT}')
                price = ui.number('Price', value=row_data['price']).style(f'background-color: {ColorPalette.MAIN_BG}; color: {ColorPalette.MAIN_TEXT}; border: 1px solid {ColorPalette.BORDER_LIGHT}')
                
                def save():
                    self.save_edited_row(row_data, quantity.value, discount.value, cost.value, price.value)
                    dialog.close()

                def delete():
                    self.delete_row(row_data)
                    dialog.close()

                with ui.row().classes('w-full justify-end mt-4'):
                    ui.button('Save', on_click=save).style(f'background-color: {ColorPalette.SUCCESS}; color: white')
                    ui.button('Delete', on_click=delete).style(f'background-color: {ColorPalette.ERROR}; color: white')
                    ui.button('Cancel', on_click=dialog.close).style(f'background-color: {ColorPalette.BUTTON_SECONDARY_BG}; color: {ColorPalette.BUTTON_SECONDARY_TEXT}')
        dialog.open()

    def save_edited_row(self, original_row, new_quantity, new_discount, new_cost, new_price):
        try:
            row_index = self.rows.index(original_row)
            self.rows[row_index].update({
                'quantity': new_quantity, 'discount': new_discount,
                'cost': new_cost, 'price': new_price,
                'subtotal': self.calculate_subtotal(new_quantity, new_cost, new_discount),
                'profit': (new_price - new_cost) * new_quantity
            })
            self.aggrid.update()
            self.update_totals()
            ui.notify('Product updated successfully')
        except (ValueError, IndexError) as e:
            ui.notify(f'Error updating product: {e}', color='red')

    def delete_row(self, row_data):
        try:
            self.rows.remove(row_data)
            self.aggrid.update()
            self.update_totals()
            ui.notify('Product removed successfully')
        except (ValueError, IndexError) as e:
            ui.notify(f'Error removing product: {e}', color='red')

    def update_totals(self):
        subtotal = sum(row['subtotal'] for row in self.rows)
        total_quantity = sum(row['quantity'] for row in self.rows)

        self.summary_label.text = f"{len(self.rows)} items"
        self.quantity_total_label.text = f"Total Qty: {total_quantity}"

        tax_percent = float(self.tax_percent_input.value or 0)
        tax_amount = float(self.tax_amount_input.value or 0)
        discount_percent = float(self.discount_percent_input.value or 0)
        discount_amount = float(self.discount_amount_input.value or 0)

        calculated_tax_amount = subtotal * (tax_percent / 100)
        if tax_amount > 0:
            calculated_tax_amount = tax_amount

        total_after_tax = subtotal + calculated_tax_amount
        total_after_discount_percent = total_after_tax * (1 - discount_percent / 100)
        final_total = total_after_discount_percent - discount_amount

        self.total_label.text = f"Total: ${max(0, round(final_total, 2)):.2f}"

    def delete_purchase(self):
        if not self.current_purchase_id:
            ui.notify('No purchase selected to delete', color='red')
            return
        
        try:
            message = self.service.delete_purchase(self.current_purchase_id)
            ui.notify(message)
            self.refresh_purchases_table()
            self.clear_inputs()
        except Exception as e:
            ui.notify(f'Error deleting purchase: {e}', color='red')

    def refresh_purchases_table(self):
        try:
            self.purchases_data = self.service.get_all_purchases()
            self.purchases_aggrid.options['rowData'] = self.purchases_data
            self.purchases_aggrid.update()
        except Exception as e:
            ui.notify(f'Error refreshing purchases table: {e}', color='red')

    def save_purchase(self):
        try:
            if not self.rows:
                ui.notify('No items to save!')
                return

            purchase_date = str(self.date_input.value)
            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            supplier_name = self.supplier_input.value or 'Default Supplier'
            supplier_id = self.service.get_supplier_id(supplier_name)
            user = session_storage.get('user')
            session_id = session_storage.get('session_id')
            payment_method = self.payment_method.value
            payment_status = 'completed' if payment_method == 'Cash' else 'pending'
            subtotal = sum(row['subtotal'] for row in self.rows)
            tax_percent = float(self.tax_percent_input.value or 0)
            tax_amount = float(self.tax_amount_input.value or 0)
            calculated_tax_amount = subtotal * (tax_percent / 100)
            if tax_amount > 0:
                calculated_tax_amount = tax_amount
            total_after_tax = subtotal + calculated_tax_amount
            discount_percent = float(self.discount_percent_input.value or 0)
            discount_amount = float(self.discount_amount_input.value or 0)
            total_after_discount_percent = total_after_tax * (1 - discount_percent / 100)
            final_total = total_after_discount_percent - discount_amount

            purchase_data = {
                'purchase_date': purchase_date, 'created_at': created_at, 'supplier_id': supplier_id,
                'subtotal': subtotal, 'discount_amount': discount_amount, 'final_total': final_total,
                'payment_status': payment_status, 'payment_method': payment_method,
                'user': user, 'session_id': session_id,
            }

            self.service.save_purchase(purchase_data, self.rows, self.current_purchase_id)
            self.refresh_purchases_table()
            self.clear_inputs()
            ui.notify('Purchase saved successfully!')

        except Exception as e:
            ui.notify(f'Error saving purchase: {str(e)}', color='red')



    def create_ui(self):
        uiAggridTheme.addingtheme()
        with ui.element('div').classes('flex w-full h-screen'):
            with ui.element('div').classes(f'w-12 p-1 flex flex-col gap-1').style(f'background-color: {ColorPalette.SECONDARY}'):
                ui.button('', icon='add', on_click=self.clear_inputs).classes('w-6 h-6 mb-2').style(f'background-color: {ColorPalette.BUTTON_PRIMARY_BG}; color: {ColorPalette.BUTTON_PRIMARY_TEXT}').tooltip('Add new purchase')
                ui.button('', icon='save', on_click=self.save_purchase).classes('w-6 h-6 mb-2').style(f'background-color: {ColorPalette.SUCCESS}; color: white').tooltip('Save purchase')
                ui.button('', icon='undo', on_click=self.show_undo_confirmation).classes('w-6 h-6 mb-2').style(f'background-color: {ColorPalette.ACCENT}; color: {ColorPalette.MAIN_TEXT}').tooltip('Undo changes')
                ui.button('', icon='delete', on_click=self.delete_purchase).classes('w-6 h-6 mb-2').style(f'background-color: {ColorPalette.ERROR}; color: white').tooltip('Delete purchase')
                ui.button('', icon='refresh', on_click=self.refresh_purchases_table).classes('w-6 h-6 mb-2').style(f'background-color: {ColorPalette.BUTTON_SECONDARY_BG}; color: {ColorPalette.BUTTON_SECONDARY_TEXT}').tooltip('Refresh table')
                ui.button('', icon='print', on_click=self.print_purchase_invoice).classes('w-6 h-6 mb-2').style(f'background-color: {ColorPalette.BUTTON_PRIMARY_BG}; color: {ColorPalette.BUTTON_PRIMARY_TEXT}').tooltip('Print invoice')

            with ui.element('div').classes('flex-1 p-1 flex flex-col').style(f'background-color: {ColorPalette.MAIN_BG}'):
                ui.label('Purchase History').classes('text-sm font-bold mb-1').style(f'color: {ColorPalette.MAIN_TEXT}')

                with ui.splitter(horizontal=True, value=30).classes('w-full flex-grow') as main_splitter:
                    with main_splitter.before:
                        purchases_columns = [
                            {'headerName': 'ID', 'field': 'id', 'width': 40, 'filter': True, 'headerClass': 'blue-header'},
                            {'headerName': 'Date', 'field': 'purchase_date', 'width': 70, 'filter': True, 'headerClass': 'blue-header'},
                            {'headerName': 'Supplier', 'field': 'supplier_name', 'width': 100, 'filter': True, 'headerClass': 'blue-header'},
                            {'headerName': 'Total', 'field': 'total_amount', 'width': 60,  'filter': True, 'headerClass': 'blue-header'},
                            {'headerName': 'Invoice', 'field': 'invoice_number', 'width': 80, 'filter': True, 'headerClass': 'blue-header'},
                            {'headerName': 'Auxiliary', 'field': 'account_code', 'width': 60, 'filter': True, 'headerClass': 'blue-header'},
                            {'headerName': 'Aux Number', 'field': 'auxiliary_number', 'width': 80, 'filter': True, 'headerClass': 'blue-header'},
                            {'headerName': 'Status', 'field': 'payment_status', 'width': 60, 'filter': True, 'headerClass': 'blue-header'}
                        ]

                        self.purchases_data = self.service.get_all_purchases()

                        self.purchases_aggrid = ui.aggrid({
                            'columnDefs': purchases_columns,
                            'rowData': self.purchases_data,
                            'defaultColDef': {'flex': 1, 'minWidth': 30, 'sortable': True, 'filter': True},
                            'rowSelection': 'single',
                            'domLayout': 'autoHeight'
                         }).classes('w-full ag-theme-quartz-custom')

                        async def handle_purchases_aggrid_click(e):
                            try:
                                selected_row_data = e.args['data']
                                if selected_row_data and 'id' in selected_row_data:
                                    purchase_id = selected_row_data['id']

                                    message = self._load_purchase_details(purchase_id)
                                    ui.notify(message)
                            except Exception as ex:
                                ui.notify(f'❌ Error loading purchase items: {str(ex)}', color='red')

                        self.purchases_aggrid.on('cellClicked', handle_purchases_aggrid_click)

                        # Keyboard navigation removed due to API issues; use buttons for navigation
                
                    with main_splitter.after:
                        with ui.element('div').classes('w-full'):
                            self.supplier_dialog = ui.dialog()
                            with self.supplier_dialog, ui.card().classes('w-full max-w-6xl').style(f'background-color: {ColorPalette.MAIN_BG}; color: {ColorPalette.MAIN_TEXT}'):
                                ui.label('Select Supplier').classes('text-lg font-bold mb-4').style(f'color: {ColorPalette.MAIN_TEXT}')

                                search_input = ui.input('Search').classes('text-xs mb-4').style(f'background-color: {ColorPalette.MAIN_BG}; color: {ColorPalette.MAIN_TEXT}; border: 1px solid {ColorPalette.BORDER_LIGHT}').on('keydown.enter', lambda e: self.filter_supplier_rows(e.sender.value))

                                headers, rows = self.service.get_all_suppliers()
                                self.supplier_rows = rows
                                columns = [{'headerName': header, 'field': header, 'sortable': True, 'filter': True} for header in headers]
                                self.supplier_grid = ui.aggrid({
                                    'columnDefs': columns,
                                    'rowData': rows,
                                    'domLayout': 'autoHeight'
                                }).classes('w-full ag-theme-quartz-custom')

                                self.supplier_grid.on('cellClicked', lambda e: self.handle_grid_click(e))

                                with ui.row().classes('w-full justify-end mt-4'):
                                    ui.button('Cancel', on_click=self.supplier_dialog.close).style(f'background-color: {ColorPalette.BUTTON_SECONDARY_BG}; color: {ColorPalette.BUTTON_SECONDARY_TEXT}')

                            with ui.row():
                                self.date_input = ui.input('Date', value=str(dt.today()))
                                self.supplier_input = ui.input('Supplier').on('click', self.open_supplier_dialog)
                                self.phone_input = ui.input('Phone')
                                self.payment_method = ui.radio(['Cash', 'On Account'], value='Cash')

                            with ui.row():
                                self.barcode_input = ui.input('Barcode', on_change=self.update_product_dropdown)
                                self.product_input = ui.input('Product').on('click', self.open_product_dialog)
                                self.quantity_input = ui.number('Qty', value=1)
                                self.cost_input = ui.number('Cost', value=0.0)
                                self.price_input = ui.number('Price', value=0.0)
                                self.discount_input = ui.number('Disc %', value=0)
                                ui.button('Add', on_click=self.add_product).style(f'background-color: {ColorPalette.ACCENT}; color: {ColorPalette.MAIN_TEXT}')
                            
                            self.aggrid = ui.aggrid({
                                'columnDefs': self.columns,
                                'rowData': self.rows,
                                'rowSelection': 'single',
                                'domLayout': 'autoHeight'
                            }).on('cellClicked', lambda e: self.open_edit_dialog(e.args['data']))

        with ui.footer().classes('w-full p-4').style(f'background-color: {ColorPalette.HEADER_BG}; color: {ColorPalette.HEADER_TEXT}'):
            with ui.row().classes('w-full justify-between items-center'):
                with ui.column().classes('gap-1'):
                    ui.label('SUMMARY').classes('text-sm font-bold')
                    self.summary_label = ui.label('0 items')
                    self.quantity_total_label = ui.label('Qty: 0')

                with ui.column().classes('gap-1 items-end'):
                    with ui.row().classes('items-center'):
                        ui.label('Tax:')
                        self.tax_percent_input = ui.number(value=0, suffix='%', on_change=self.update_totals).classes('w-20')
                        self.tax_amount_input = ui.number(value=0, on_change=self.update_totals).classes('w-24')
                    with ui.row().classes('items-center'):
                        ui.label('Discount:')
                        self.discount_percent_input = ui.number(value=0, suffix='%', on_change=self.update_totals).classes('w-20')
                        self.discount_amount_input = ui.number(value=0, on_change=self.update_totals).classes('w-24')
                    self.total_label = ui.label('Total: $0.00').classes('text-3xl font-bold')



    def show_undo_confirmation(self):
        with ui.dialog() as dialog, ui.card().style(f'background-color: {ColorPalette.MAIN_BG}; color: {ColorPalette.MAIN_TEXT}'):
            ui.label('Confirm Action').classes('text-lg font-bold mb-4').style(f'color: {ColorPalette.MAIN_TEXT}')
            ui.label('Are you sure you want to undo all changes?').style(f'color: {ColorPalette.MAIN_TEXT}')
            with ui.row().classes('w-full justify-end mt-4'):
                ui.button('Yes', on_click=lambda: self.perform_undo(dialog)).style(f'background-color: {ColorPalette.WARNING}; color: white')
                ui.button('No', on_click=dialog.close).style(f'background-color: {ColorPalette.BUTTON_SECONDARY_BG}; color: {ColorPalette.BUTTON_SECONDARY_TEXT}')
        dialog.open()

    def perform_undo(self, dialog):
        self.clear_inputs()
        dialog.close()
        ui.notify('Changes undone')

    def print_purchase_invoice(self):
        if not self.current_purchase_id:
            ui.notify('No purchase selected to print', color='red')
            return
        try:
            invoice_data = self.service.get_invoice_data(self.current_purchase_id)
            from invoice_pdf_cairo import generate_purchase_invoice_pdf
            pdf_buffer = generate_purchase_invoice_pdf(**invoice_data)
            ui.download(pdf_buffer.getvalue(), f'Purchase_Invoice_{invoice_data["invoice_number"]}.pdf')
        except Exception as e:
            ui.notify(f'Error printing invoice: {e}', color='red')

    def open_supplier_dialog(self):
        self.supplier_dialog.open()

    def handle_grid_click(self, e):
        row = e.args['data']
        col_id = e.args.get('colId', '')
        if col_id == 'name':
            self.supplier_input.value = row['name']
            self.phone_input.value = row['phone']
            self.supplier_dialog.close()
        elif col_id == 'phone':
            self.phone_input.value = row['phone']
            self.supplier_input.value = row['name']
            self.supplier_dialog.close()
        else:
            self.supplier_input.value = row['name']
            self.phone_input.value = row['phone']
            self.supplier_dialog.close()

    def filter_supplier_rows(self, search_text):
        if not search_text:
            filtered_rows = self.supplier_rows
        else:
            filtered_rows = [row for row in self.supplier_rows if any(search_text.lower() in str(value).lower() for value in row.values())]
        self.supplier_grid.options['rowData'] = filtered_rows
        self.supplier_grid.update()

    def handle_product_grid_click(self, e, dialog):
        row = e.args['data']
        def update_inputs():
            self.product_input.value = row['product_name']
            self.barcode_input.value = row['barcode']
            self.cost_input.value = row['cost_price']
            self.price_input.value = row['price']
            self.old_cost_price = row['cost_price']
            self.old_price = row['price']
        dialog.close()
        ui.timer(0.01, update_inputs, once=True)


