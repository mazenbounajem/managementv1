from nicegui import ui
from pathlib import Path
from datetime import date as dt
from connection import connection
from datetime import datetime
from decimal import Decimal
from uiaggridtheme import uiAggridTheme
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage

class StockOperationUI:

    def __init__(self):
        self.operation_id = None

        # Check if user is logged in
        user = session_storage.get('user')
        if not user:
            ui.notify('Please login to access this page', color='red')
            ui.run_javascript('window.location.href = "/login"')
            return

        # Get user permissions
        permissions = connection.get_user_permissions(user['role_id'])
        allowed_pages = {page for page, can_access in permissions.items() if can_access}

        # Create enhanced navigation instance
        navigation = EnhancedNavigation(permissions, user)
        navigation.create_navigation_drawer()  # Create drawer first
        navigation.create_navigation_header()  # Then create header with toggle button

        # --- Global Variables ---
        self.columns = [
            {'headerName': 'Barcode', 'field': 'barcode', 'width': 120, 'headerClass': 'green-header'},
            {'headerName': 'Product', 'field': 'product', 'width': 180, 'headerClass': 'green-header'},
            {'headerName': 'Current Qty', 'field': 'current_quantity', 'width': 100, 'headerClass': 'green-header'},
            {'headerName': 'Operation', 'field': 'operation_type', 'width': 100, 'headerClass': 'green-header'},
            {'headerName': 'Adjust Qty', 'field': 'adjust_quantity', 'width': 100, 'headerClass': 'green-header'},
            {'headerName': 'Final Qty', 'field': 'final_quantity', 'width': 100, 'headerClass': 'green-header'},
            {'headerName': 'Reason', 'field': 'reason', 'width': 150, 'headerClass': 'green-header'}
        ]
        self.rows = []
        self.grid_readonly = False  # Track grid state
        self.new_mode = True  # Track new mode state

        # Initialize UI
        self.create_ui()

    def create_ui(self):
        """Create the main UI layout with working dialogs and compact design."""
        with ui.element('div').classes('flex w-full h-screen'):
            # === LEFT SIDE BUTTONS - ULTRA COMPACT ===
            with ui.element('div').classes('w-1/12 bg-gray-100 p-1 flex flex-col gap-1'):
                ui.button('🆕 New', on_click=self.clear_operations).classes('text-xs py-1 px-2 w-full')
                ui.button('💾 Save', on_click=self.save_operation).classes('text-xs py-1 px-2 w-full')
                ui.button('↩️ Undo', on_click=self.show_undo_confirmation).classes('text-xs py-1 px-2 w-full')
                ui.button('🗑️ Clear', on_click=self.clear_all_operations).classes('text-xs py-1 px-2 w-full')
                ui.button('🔄 Refresh', on_click=self.refresh_operations_table).classes('text-xs py-1 px-2 w-full')

            # === RIGHT SIDE CONTENT - ULTRA COMPACT ===
            with ui.element('div').classes('w-11/12 p-1 flex flex-col gap-1 overflow-y-auto'):
                # --- HORIZONTAL SPLITTER: Operations History and Current Operation ---
                with ui.splitter(horizontal=True, value=35).classes('w-full h-full') as main_splitter:
                    with main_splitter.separator:
                        ui.icon('lightbulb').classes('text-green text-sm')
                    with main_splitter.before:
                        # Operations history grid
                        with ui.element('div').classes('w-full h-full p-1'):
                            ui.label('Stock Operations History').classes('text-sm font-bold text-gray-700 mb-1')

                            # Define columns for operations history grid
                            operations_columns = [
                                {'headerName': 'ID', 'field': 'id', 'width': 50, 'filter': True, 'headerClass': 'green-header'},
                                {'headerName': 'Date', 'field': 'operation_date', 'width': 120, 'filter': True, 'headerClass': 'green-header'},
                                {'headerName': 'User', 'field': 'username', 'width': 100, 'filter': True, 'headerClass': 'green-header'},
                                {'headerName': 'Type', 'field': 'operation_type', 'width': 120, 'filter': True, 'headerClass': 'green-header'},
                                {'headerName': 'Items', 'field': 'total_items', 'width': 60, 'filter': True, 'headerClass': 'green-header'},
                                {'headerName': 'Reference', 'field': 'reference_number', 'width': 120, 'filter': True, 'headerClass': 'green-header'}
                            ]

                            # Fetch operations data
                            raw_operations_data = []
                            connection.contogetrows(
                                """SELECT so.id, so.operation_date, u.username, so.operation_type,
                                          so.total_items, so.reference_number
                                   FROM stock_operations so
                                   INNER JOIN users u ON u.id = so.user_id
                                   ORDER BY so.id DESC""",
                                raw_operations_data
                            )

                            # Convert to AG Grid format
                            operations_data = []
                            for row in raw_operations_data:
                                operations_data.append({
                                    'id': row[0],
                                    'operation_date': str(row[1]),
                                    'username': str(row[2]),
                                    'operation_type': str(row[3]),
                                    'total_items': int(row[4]) if row[4] else 0,
                                    'reference_number': str(row[5]) if row[5] else ''
                                })

                            # Create AG Grid for operations history
                            self.operations_aggrid = ui.aggrid({
                                'columnDefs': operations_columns,
                                'rowData': operations_data,
                                'defaultColDef': {'flex': 1, 'minWidth': 30, 'sortable': True, 'filter': True},
                                'rowSelection': 'single',
                                'domLayout': 'normal',
                            }).classes('w-full rounded border border-red-200 ag-theme-quartz-custom').style('overflow-y: auto;height:200px;')

                            # Add click handler for operations grid
                            async def handle_operations_aggrid_click():
                                try:
                                    selected_row = await self.operations_aggrid.get_selected_row()
                                    if selected_row and isinstance(selected_row, dict) and 'id' in selected_row:
                                        operation_id = selected_row['id']
                                        self.load_operation_details(operation_id)
                                except Exception as ex:
                                    ui.notify(f'Error loading operation details: {str(ex)}')

                            self.operations_aggrid.on('cellClicked', handle_operations_aggrid_click)

                    # --- CURRENT OPERATION SECTION ---
                    with main_splitter.after:
                        # Operation header info
                        with ui.element('div').classes('w-full'):
                            with ui.row().classes('w-full items-center gap-20 mb-1 p-1 bg-blue-100 rounded'):
                                self.operation_date_input = ui.input('Date', value=datetime.now().strftime('%Y-%m-%d %H:%M:%S')).classes('w-40 h-7 text-xs')
                                self.operation_type_select = ui.select(
                                    options=['manual_adjustment', 'stock_count', 'return', 'damage', 'transfer'],
                                    value='manual_adjustment',
                                    label='Operation Type'
                                ).classes('w-40 h-7 text-xs')
                                self.reference_input = ui.input('Reference', placeholder='Reference Number').classes('w-32 h-7 text-xs')
                                self.notes_input = ui.input('Notes', placeholder='Operation notes').classes('w-48 h-7 text-xs')

                        # Product selection and operation entry
                        with ui.element('div').classes('w-full'):
                            with ui.row().classes('w-full items-center gap-3 p-3 bg-gray-100 rounded-lg shadow-sm'):
                                self.barcode_input = ui.input('Barcode', placeholder='Barcode').classes('w-32 h-10 text-sm').on('change', lambda e: self.update_product_from_barcode(e))
                                self.product_input = ui.input('Product', placeholder='Product').classes('w-40 h-10 text-sm').on('click', lambda: self.open_product_dialog())
                                self.operation_select = ui.select(
                                    options=['add', 'subtract'],
                                    value='add',
                                    label='Operation'
                                ).classes('w-24 h-10 text-sm')
                                self.quantity_input = ui.number('Quantity', value=1, min=1).classes('w-24 h-10 text-sm')
                                self.reason_input = ui.input('Reason', placeholder='Reason for adjustment').classes('w-40 h-10 text-sm')
                                ui.button('Add Operation', on_click=self.add_operation_item).props('size=md').classes('h-10 px-4 text-sm font-medium')

                        # Product selection dialog
                        self.product_dialog = ui.dialog()
                        with self.product_dialog, ui.card().classes('w-full'):
                            headers = []
                            connection.contogetheaders("SELECT barcode, product_name, stock_quantity, price FROM products WHERE is_active = 1", headers)
                            columns = [{'name': header, 'label': header.title(), 'field': header, 'sortable': True} for header in headers]

                            # Fetch data from database
                            data = []
                            connection.contogetrows("SELECT barcode, product_name, stock_quantity, price FROM products WHERE is_active = 1", data)
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
                                self.product_dialog.close()

                            table.on('rowClick', on_product_select)

                        # AG Grid container for current operation items
                        with ui.element('div').classes('w-full h-[calc(100vh-480px)] min-h-48 border rounded-lg bg-white shadow-sm mt-4'):
                            # AG Grid for operation items
                            self.aggrid = ui.aggrid({
                                'columnDefs': self.columns,
                                'rowData': self.rows,
                                'defaultColDef': {'flex': 1, 'minWidth': 40, 'sortable': True, 'filter': True},
                                'rowSelection': 'single',
                                'domLayout': 'normal',
                            }).classes('w-full h-full p-2')

                            # Click handler for editing
                            async def handle_aggrid_click():
                                try:
                                    selected_row = await self.aggrid.get_selected_row()
                                    if selected_row:
                                        self.open_edit_dialog(selected_row)
                                except Exception as ex:
                                    ui.notify(f'Error: {str(ex)}')

                            self.aggrid.on('cellClicked', handle_aggrid_click)

                        # Footer section with summary
                        with ui.element('div').classes('w-full p-4 bg-gray-100 border-t border-gray-300 fixed bottom-0 left-0 right-0 z-10'):
                            with ui.row().classes('w-full justify-between items-center'):
                                with ui.column().classes('gap-1'):
                                    ui.label('OPERATION SUMMARY').classes('text-sm font-bold text-gray-700')
                                    self.summary_label = ui.label('0 items').classes('text-sm text-gray-600')

                                with ui.column().classes('gap-1 items-end'):
                                    ui.label('Total Items:').classes('text-sm font-medium')
                                    self.total_items_label = ui.label('0').classes('text-2xl font-bold text-blue-600')

        uiAggridTheme.addingtheme()

    def update_product_from_barcode(self, e):
        """Update product information when barcode is entered"""
        try:
            barcode = self.barcode_input.value
            if barcode:
                product_data = []
                connection.contogetrows(
                    f"SELECT product_name, stock_quantity FROM products WHERE barcode = '{barcode}' AND is_active = 1",
                    product_data
                )

                if product_data:
                    self.product_input.value = product_data[0][0]
                    ui.notify(f"Product loaded: {product_data[0][0]} (Current stock: {product_data[0][1]})")
                else:
                    ui.notify("Product not found for this barcode")
        except Exception as e:
            ui.notify(f'Error updating product: {str(e)}')

    def add_operation_item(self):
        """Add an operation item to the current operation"""
        try:
            barcode = self.barcode_input.value
            product_name = self.product_input.value
            operation_type = self.operation_select.value
            quantity = int(self.quantity_input.value) if self.quantity_input.value else 0
            reason = self.reason_input.value

            if not barcode or not product_name or quantity <= 0:
                ui.notify('Please fill in all required fields with valid values')
                return

            # Get current stock quantity
            product_data = []
            connection.contogetrows(
                f"SELECT id, stock_quantity FROM products WHERE barcode = '{barcode}' AND is_active = 1",
                product_data
            )

            if not product_data:
                ui.notify('Product not found in database')
                return

            product_id = product_data[0][0]
            current_quantity = product_data[0][1]

            # Calculate final quantity based on operation
            if operation_type == 'add':
                final_quantity = current_quantity + quantity
            else:  # subtract
                if current_quantity < quantity:
                    ui.notify(f'Insufficient stock! Available: {current_quantity}, Requested: {quantity}')
                    return
                final_quantity = current_quantity - quantity

            # Add to operation items
            self.rows.append({
                'barcode': barcode,
                'product': product_name,
                'current_quantity': current_quantity,
                'operation_type': operation_type,
                'adjust_quantity': quantity,
                'final_quantity': final_quantity,
                'reason': reason,
                'product_id': product_id
            })

            self.update_summary()
            self.clear_operation_inputs()
            self.aggrid.update()

            ui.notify(f'Operation item added: {product_name} ({operation_type} {quantity})')

        except ValueError as e:
            ui.notify(f'Invalid input: {str(e)}')
        except Exception as e:
            ui.notify(f'Error adding operation item: {str(e)}')

    def clear_operation_inputs(self):
        """Clear the operation input fields"""
        self.barcode_input.value = ''
        self.product_input.value = ''
        self.quantity_input.value = 1
        self.reason_input.value = ''

    def update_summary(self):
        """Update the operation summary"""
        self.summary_label.text = f"{len(self.rows)} items"
        self.total_items_label.text = f"{len(self.rows)}"

    def clear_operations(self):
        """Clear all operation items"""
        self.rows.clear()
        self.aggrid.options['rowData'] = self.rows
        self.aggrid.update()
        self.update_summary()
        self.operation_id = None
        self.new_mode = True
        ui.notify('Operation cleared')

    def save_operation(self):
        """Save the current stock operation"""
        try:
            if not self.rows:
                ui.notify('No items to save!')
                return

            user = session_storage.get('user')
            if not user:
                ui.notify('User session expired. Please login again.')
                return

            operation_date = self.operation_date_input.value
            operation_type = self.operation_type_select.value
            reference_number = self.reference_input.value
            notes = self.notes_input.value

            # Insert main operation record
            operation_sql = """
            INSERT INTO stock_operations
            (operation_date, user_id, operation_type, reference_number, notes, total_items)
            VALUES (?, ?, ?, ?, ?, ?)
            """

            connection.insertingtodatabase(operation_sql, (
                operation_date, user['user_id'], operation_type,
                reference_number, notes, len(self.rows)
            ))

            # Get the operation ID
            operation_id = connection.getid("SELECT MAX(id) FROM stock_operations", [])

            # Insert operation items and update product stock
            for row in self.rows:
                # Insert operation item
                item_sql = """
                INSERT INTO stock_operation_items
                (operation_id, product_id, barcode, product_name, previous_quantity,
                 adjusted_quantity, operation_type, reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """

                connection.insertingtodatabase(item_sql, (
                    operation_id, row['product_id'], row['barcode'], row['product'],
                    row['current_quantity'], row['adjust_quantity'],
                    row['operation_type'], row['reason']
                ))

                # Update product stock quantity
                if row['operation_type'] == 'add':
                    update_sql = "UPDATE products SET stock_quantity = stock_quantity + ? WHERE id = ?"
                else:  # subtract
                    update_sql = "UPDATE products SET stock_quantity = stock_quantity - ? WHERE id = ?"

                connection.insertingtodatabase(update_sql, (row['adjust_quantity'], row['product_id']))

            ui.notify(f'Stock operation saved successfully! ID: {operation_id}')
            self.refresh_operations_table()
            self.clear_operations()

        except Exception as e:
            ui.notify(f'Error saving operation: {str(e)}')

    def load_operation_details(self, operation_id):
        """Load details of a specific operation"""
        try:
            # Fetch operation items
            items_data = []
            connection.contogetrows(
                f"""SELECT soi.barcode, soi.product_name, soi.previous_quantity,
                           soi.operation_type, soi.adjusted_quantity, soi.reason,
                           p.stock_quantity as current_quantity, soi.product_id
                    FROM stock_operation_items soi
                    INNER JOIN products p ON p.id = soi.product_id
                    WHERE soi.operation_id = {operation_id}""",
                items_data
            )

            # Clear current items and load from database
            self.rows.clear()
            for item in items_data:
                barcode, product_name, previous_quantity, operation_type, adjusted_quantity, reason, current_quantity, product_id = item

                # Calculate final quantity
                if operation_type == 'add':
                    final_quantity = previous_quantity + adjusted_quantity
                else:
                    final_quantity = previous_quantity - adjusted_quantity

                self.rows.append({
                    'barcode': str(barcode) if barcode else '',
                    'product': str(product_name) if product_name else 'Unknown Product',
                    'current_quantity': int(current_quantity) if current_quantity else 0,
                    'operation_type': str(operation_type),
                    'adjust_quantity': int(adjusted_quantity) if adjusted_quantity else 0,
                    'final_quantity': final_quantity,
                    'reason': str(reason) if reason else '',
                    'product_id': product_id
                })

            self.aggrid.options['rowData'] = self.rows
            self.aggrid.update()
            self.update_summary()
            self.operation_id = operation_id
            self.new_mode = False

            ui.notify(f'Loaded operation {operation_id} with {len(self.rows)} items')

        except Exception as e:
            ui.notify(f'Error loading operation details: {str(e)}')

    def open_edit_dialog(self, row_data):
        """Open edit dialog for operation item"""
        dialog = ui.dialog()

        with dialog, ui.card().classes('w-96 p-6'):
            ui.label('Edit Operation Item').classes('text-xl font-bold mb-4')

            with ui.column().classes('w-full gap-3'):
                ui.label(f"Barcode: {row_data['barcode']}").classes('font-medium')
                ui.label(f"Product: {row_data['product']}").classes('font-medium')
                ui.label(f"Current Stock: {row_data['current_quantity']}").classes('font-medium')

                operation_select = ui.select(
                    options=['add', 'subtract'],
                    value=row_data['operation_type'],
                    label='Operation Type'
                )
                quantity_input = ui.number('Quantity', value=row_data['adjust_quantity'], min=1)
                reason_input = ui.input('Reason', value=row_data['reason'])

                with ui.row().classes('w-full justify-end gap-2 mt-4'):
                    ui.button('Cancel', on_click=dialog.close)
                    ui.button('Delete', on_click=lambda: self.delete_operation_item(row_data, dialog)).props('color=negative')
                    ui.button('Save', on_click=lambda: self.save_edited_operation_item(
                        row_data,
                        operation_select.value,
                        quantity_input.value,
                        reason_input.value,
                        dialog
                    )).props('color=primary')

        dialog.open()

    def save_edited_operation_item(self, original_row, new_operation, new_quantity, new_reason, dialog):
        """Save edited operation item"""
        try:
            row_index = next(i for i, row in enumerate(self.rows)
                           if row['barcode'] == original_row['barcode'] and
                              row['product'] == original_row['product'])

            # Validate stock if subtracting
            if new_operation == 'subtract':
                if original_row['current_quantity'] < int(new_quantity):
                    ui.notify(f'Insufficient stock! Available: {original_row["current_quantity"]}, Requested: {new_quantity}')
                    return

            # Calculate new final quantity
            if new_operation == 'add':
                final_quantity = original_row['current_quantity'] + int(new_quantity)
            else:
                final_quantity = original_row['current_quantity'] - int(new_quantity)

            self.rows[row_index]['operation_type'] = new_operation
            self.rows[row_index]['adjust_quantity'] = int(new_quantity)
            self.rows[row_index]['final_quantity'] = final_quantity
            self.rows[row_index]['reason'] = new_reason

            self.aggrid.options['rowData'] = self.rows
            self.aggrid.update()

            dialog.close()
            ui.notify('Operation item updated successfully')

        except Exception as e:
            ui.notify(f'Error updating operation item: {str(e)}')

    def delete_operation_item(self, row_data, dialog):
        """Delete an operation item"""
        try:
            row_index = next(i for i, row in enumerate(self.rows)
                           if row['barcode'] == row_data['barcode'] and
                              row['product'] == row_data['product'])

            del self.rows[row_index]
            self.aggrid.options['rowData'] = self.rows
            self.aggrid.update()
            self.update_summary()

            dialog.close()
            ui.notify('Operation item removed successfully')

        except Exception as e:
            ui.notify(f'Error removing operation item: {str(e)}')

    def show_undo_confirmation(self):
        """Show confirmation dialog for undo"""
        dialog = ui.dialog()

        with dialog, ui.card().classes('w-96 p-6'):
            ui.label('Confirm Undo').classes('text-xl font-bold mb-4')
            ui.label('Are you sure you want to undo all changes?').classes('mb-4')

            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button('Cancel', on_click=dialog.close)
                ui.button('OK', on_click=lambda: self.perform_undo(dialog)).props('color=primary')

        dialog.open()

    def perform_undo(self, dialog):
        """Perform undo operation"""
        self.clear_operations()
        dialog.close()
        ui.notify('Undo completed successfully')

    def clear_all_operations(self):
        """Clear all operations with confirmation"""
        if self.rows:
            self.clear_operations()
        else:
            ui.notify('No operations to clear')

    def refresh_operations_table(self):
        """Refresh the operations history table"""
        try:
            raw_operations_data = []
            connection.contogetrows(
                """SELECT so.id, so.operation_date, u.username, so.operation_type,
                          so.total_items, so.reference_number
                   FROM stock_operations so
                   INNER JOIN users u ON u.id = so.user_id
                   ORDER BY so.id DESC""",
                raw_operations_data
            )

            operations_data = []
            for row in raw_operations_data:
                operations_data.append({
                    'id': row[0],
                    'operation_date': str(row[1]),
                    'username': str(row[2]),
                    'operation_type': str(row[3]),
                    'total_items': int(row[4]) if row[4] else 0,
                    'reference_number': str(row[5]) if row[5] else ''
                })

            self.operations_aggrid.options['rowData'] = operations_data
            self.operations_aggrid.update()

            ui.notify('Operations table refreshed successfully')

        except Exception as e:
            ui.notify(f'Error refreshing operations table: {str(e)}')

    def open_product_dialog(self):
        """Open product selection dialog"""
        self.product_dialog.open()

@ui.page('/stockoperations')
def stock_operations_page_route():
    StockOperationUI()
