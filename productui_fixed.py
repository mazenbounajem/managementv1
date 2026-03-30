from nicegui import ui
from connection import connection
from uiaggridtheme import uiAggridTheme
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage
import datetime
from barcode.ean import EAN13
from barcode.writer import SVGWriter
import random
import io
import base64

def product_page():
    ui.add_head_html("""
    <style>
    input[type="text"], input[type="number"], input[type="date"], .q-field__control, .q-field__native, .q-input__native {
        background-color: #c05884 !important;
        color: white !important;
        border: 1px solid #a0456a !important;
    }
    input[type="text"]::placeholder, input[type="number"]::placeholder {
        color: rgba(255,255,255,0.7) !important;
    }
    .q-field__control {
        border-radius: 8px !important;
    }
    </style>
    """)
    uiAggridTheme.addingtheme()

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

    # Store references to input fields
    input_refs = {}

    # Store the initial values for undo functionality
    initial_values = {}

    # Navigation variables
    current_index = -1
    current_highlighted_index = -1
    total_records = 0
    record_label = None
    filter_visible = False
    filter_panel = None
    filter_inputs = {}

    category_map = {}
    supplier_map = {}

    # Function to clear all input fields
    def clear_input_fields():
        for key in input_refs:
            if key == 'id':
                input_refs[key].set_value('')
            elif key in ['stock_quantity', 'min_stock_level', 'max_stock_level', 'price', 'cost_price']:
                input_refs[key].set_value(0)
            elif key == 'is_active':
                input_refs[key].set_value(True)
            else:
                input_refs[key].set_value('')

    # Function to save product data
    def save_product():
        product_name = input_refs['product_name'].value
        barcode = input_refs['barcode'].value
        sku = input_refs['sku'].value
        description = input_refs['description'].value
        category_name = input_refs['category_id'].value
        price = float(input_refs['price'].value or 0)
        cost_price = float(input_refs['cost_price'].value or 0)
        stock_quantity = int(input_refs['stock_quantity'].value or 0)
        min_stock_level = int(input_refs['min_stock_level'].value or 0)
        max_stock_level = int(input_refs['max_stock_level'].value or 0)
        supplier_name = input_refs['supplier_id'].value
        is_active = bool(input_refs['is_active'].value)
        id_value = input_refs['id'].value

        if not product_name:
            ui.notify('Please enter Product Name', color='red')
            return

        category_id = category_map.get(category_name)
        supplier_id = supplier_map.get(supplier_name)

        if category_id is None:
            ui.notify(f'Invalid category selected: {category_name}', color='red')
            return
        if supplier_id is None:
            ui.notify(f'Invalid supplier selected: {supplier_name}', color='red')
            return

        try:
            if id_value:  # Update existing record
                sql = """UPDATE products SET product_name=?, barcode=?, sku=?, description=?, category_id=?,
                         price=?, cost_price=?, stock_quantity=?, min_stock_level=?, max_stock_level=?,
                         supplier_id=?, is_active=? WHERE id=?"""
                values = (product_name, barcode, sku, description, category_id, price, cost_price,
                          stock_quantity, min_stock_level, max_stock_level, supplier_id, is_active, id_value)
            else:  # Insert new record
                sql = """INSERT INTO products (product_name, barcode, sku, description, category_id,
                         price, cost_price, stock_quantity, min_stock_level, max_stock_level,
                         supplier_id, created_at, is_active)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), ?)"""
                values = (product_name, barcode, sku, description, category_id, price, cost_price,
                          stock_quantity, min_stock_level, max_stock_level, supplier_id, is_active)

            connection.insertingtodatabase(sql, values)
            ui.notify('Product saved successfully', color='green')
            # Refresh the table to show the new product
            refresh_table()
            # Update initial values
            initial_values.update({
                'product_name': product_name,
                'barcode': barcode,
                'sku': sku,
                'description': description,
                'category_id': category_name,
                'price': price,
                'cost_price': cost_price,
                'stock_quantity': stock_quantity,
                'min_stock_level': min_stock_level,
                'max_stock_level': max_stock_level,
                'supplier_id': supplier_name,
                'is_active': is_active,
                'id': id_value
            })
        except Exception as e:
            ui.notify(f'Error saving product: {str(e)}', color='red')

    # Function to undo changes
    def undo_changes():
        for key in input_refs:
            if key in initial_values:
                input_refs[key].set_value(initial_values[key])
        ui.notify('Changes undone', color='blue')

    # Function to delete product
    def delete_product():
        id_value = input_refs['id'].value
        if not id_value:
            ui.notify('Please select a product to delete', color='red')
            return

        try:
            sql = "DELETE FROM products WHERE id=?"
            connection.deleterow(sql, id_value)
            ui.notify('Product deleted successfully', color='green')
            # Clear input fields
            clear_input_fields()
            # Load the product record with maximum ID
            load_max_product_record()
            # Refresh the table
            refresh_table()
        except Exception as e:
            ui.notify(f'Error deleting product: {str(e)}', color='red')

    # Helper function to manage row highlighting
    def clear_highlights():
        """Clear all row highlights"""
        for row in table.options['rowData']:
            row['highlighted'] = False

    def set_highlight(index):
        """Set highlight for a specific row index"""
        if 0 <= index < len(table.options['rowData']):
            table.options['rowData'][index]['highlighted'] = True

    # Navigation functions
    def first_record():
        nonlocal current_index
        current_row_data = table.options['rowData']
        if len(current_row_data) > 0:
            current_index = 0
            clear_highlights()
            set_highlight(current_index)
            selected_row = current_row_data[current_index]
            # Set inputs
            for key in input_refs:
                if key in selected_row:
                    input_refs[key].set_value(selected_row[key])
            # Store initial values
            initial_values.update({
                'product_name': selected_row.get('product_name', ''),
                'barcode': selected_row.get('barcode', ''),
                'sku': selected_row.get('sku', ''),
                'description': selected_row.get('description', ''),
                'category_id': selected_row.get('category_id', ''),
                'price': selected_row.get('price', 0),
                'cost_price': selected_row.get('cost_price', 0),
                'stock_quantity': selected_row.get('stock_quantity', 0),
                'min_stock_level': selected_row.get('min_stock_level', 0),
                'max_stock_level': selected_row.get('max_stock_level', 0),
                'supplier_id': selected_row.get('supplier_id', ''),
                'is_active': selected_row.get('is_active', True),
                'id': selected_row.get('id', '')
            })
            # Scroll to row
            table.run_method('ensureIndexVisible', current_index)
            table.update()
            record_label.text = f'{current_index + 1} of {len(current_row_data)} records'

    def prev_10():
        nonlocal current_index
        current_row_data = table.options['rowData']
        new_index = max(0, current_index - 10)
        if new_index != current_index:
            current_index = new_index
            clear_highlights()
            set_highlight(current_index)
            selected_row = current_row_data[current_index]
            # Set inputs
            for key in input_refs:
                if key in selected_row:
                    input_refs[key].set_value(selected_row[key])
            # Store initial values
            initial_values.update({
                'product_name': selected_row.get('product_name', ''),
                'barcode': selected_row.get('barcode', ''),
                'sku': selected_row.get('sku', ''),
                'description': selected_row.get('description', ''),
                'category_id': selected_row.get('category_id', ''),
                'price': selected_row.get('price', 0),
                'cost_price': selected_row.get('cost_price', 0),
                'stock_quantity': selected_row.get('stock_quantity', 0),
                'min_stock_level': selected_row.get('min_stock_level', 0),
                'max_stock_level': selected_row.get('max_stock_level', 0),
                'supplier_id': selected_row.get('supplier_id', ''),
                'is_active': selected_row.get('is_active', True),
                'id': selected_row.get('id', '')
            })
            # Scroll to row
            table.run_method('ensureIndexVisible', current_index)
            table.update()
            record_label.text = f'{current_index + 1} of {len(current_row_data)} records'

    def prev_record():
        nonlocal current_index
        current_row_data = table.options['rowData']
        if current_index > 0:
            current_index -= 1
            clear_highlights()
            set_highlight(current_index)
            selected_row = current_row_data[current_index]
            # Set inputs
            for key in input_refs:
                if key in selected_row:
                    input_refs[key].set_value(selected_row[key])
            # Store initial values
            initial_values.update({
                'product_name': selected_row.get('product_name', ''),
                'barcode': selected_row.get('barcode', ''),
                'sku': selected_row.get('sku', ''),
                'description': selected_row.get('description', ''),
                'category_id': selected_row.get('category_id', ''),
                'price': selected_row.get('price', 0),
                'cost_price': selected_row.get('cost_price', 0),
                'stock_quantity': selected_row.get('stock_quantity', 0),
                'min_stock_level': selected_row.get('min_stock_level', 0),
                'max_stock_level': selected_row.get('max_stock_level', 0),
                'supplier_id': selected_row.get('supplier_id', ''),
                'is_active': selected_row.get('is_active', True),
                'id': selected_row.get('id', '')
            })
            # Scroll to row
            table.run_method('ensureIndexVisible', current_index)
            table.update()
            record_label.text = f'{current_index + 1} of {len(current_row_data)} records'

    def next_record():
        nonlocal current_index
        current_row_data = table.options['rowData']
        if current_index < len(current_row_data) - 1:
            current_index += 1
            clear_highlights()
            set_highlight(current_index)
            selected_row = current_row_data[current_index]
            # Set inputs
            for key in input_refs:
                if key in selected_row:
                    input_refs[key].set_value(selected_row[key])
            # Store initial values
            initial_values.update({
                'product_name': selected_row.get('product_name', ''),
                'barcode': selected_row.get('barcode', ''),
                'sku': selected_row.get('sku', ''),
                'description': selected_row.get('description', ''),
                'category_id': selected_row.get('category_id', ''),
                'price': selected_row.get('price', 0),
                'cost_price': selected_row.get('cost_price', 0),
                'stock_quantity': selected_row.get('stock_quantity', 0),
                'min_stock_level': selected_row.get('min_stock_level', 0),
                'max_stock_level': selected_row.get('max_stock_level', 0),
                'supplier_id': selected_row.get('supplier_id', ''),
                'is_active': selected_row.get('is_active', True),
                'id': selected_row.get('id', '')
            })
            # Scroll to row
            table.run_method('ensureIndexVisible', current_index)
            table.update()
            record_label.text = f'{current_index + 1} of {len(current_row_data)} records'

    def next_10():
        nonlocal current_index
        current_row_data = table.options['rowData']
        new_index = min(len(current_row_data) - 1, current_index + 10)
        if new_index != current_index:
            current_index = new_index
            clear_highlights()
            set_highlight(current_index)
            selected_row = current_row_data[current_index]
            # Set inputs
            for key in input_refs:
                if key in selected_row:
                    input_refs[key].set_value(selected_row[key])
            # Store initial values
            initial_values.update({
                'product_name': selected_row.get('product_name', ''),
                'barcode': selected_row.get('barcode', ''),
                'sku': selected_row.get('sku', ''),
                'description': selected_row.get('description', ''),
                'category_id': selected_row.get('category_id', ''),
                'price': selected_row.get('price', 0),
                'cost_price': selected_row.get('cost_price', 0),
                'stock_quantity': selected_row.get('stock_quantity', 0),
                'min_stock_level': selected_row.get('min_stock_level', 0),
                'max_stock_level': selected_row.get('max_stock_level', 0),
                'supplier_id': selected_row.get('supplier_id', ''),
                'is_active': selected_row.get('is_active', True),
                'id': selected_row.get('id', '')
            })
            # Scroll to row
            table.run_method('ensureIndexVisible', current_index)
            table.update()
            record_label.text = f'{current_index + 1} of {len(current_row_data)} records'

    def last_record():
        nonlocal current_index
        current_row_data = table.options['rowData']
        if len(current_row_data) > 0:
            current_index = len(current_row_data) - 1
            clear_highlights()
            set_highlight(current_index)
            selected_row = current_row_data[current_index]
            # Set inputs
            for key in input_refs:
                if key in selected_row:
                    input_refs[key].set_value(selected_row[key])
            # Store initial values
            initial_values.update({
                'product_name': selected_row.get('product_name', ''),
                'barcode': selected_row.get('barcode', ''),
                'sku': selected_row.get('sku', ''),
                'description': selected_row.get('description', ''),
                'category_id': selected_row.get('category_id', ''),
                'price': selected_row.get('price', 0),
                'cost_price': selected_row.get('cost_price', 0),
                'stock_quantity': selected_row.get('stock_quantity', 0),
                'min_stock_level': selected_row.get('min_stock_level', 0),
                'max_stock_level': selected_row.get('max_stock_level', 0),
                'supplier_id': selected_row.get('supplier_id', ''),
                'is_active': selected_row.get('is_active', True),
                'id': selected_row.get('id', '')
            })
            # Scroll to row
            table.run_method('ensureIndexVisible', current_index)
            table.update()
            record_label.text = f'{current_index + 1} of {len(current_row_data)} records'

    def toggle_filter():
        nonlocal filter_visible
        filter_visible = not filter_visible
        if filter_visible:
            filter_panel.style('display: block')
        else:
            filter_panel.style('display: none')

    def apply_filter():
        filters = {k: v.value for k, v in filter_inputs.items() if v.value}
        if not filters:
            table.options['rowData'] = row_data
        else:
            filtered = [row for row in row_data if all(
                str(row.get(k, '')).lower().find(v.lower()) != -1 for k, v in filters.items()
            )]
            table.options['rowData'] = filtered
        table.update()
        # Reset current_index
        nonlocal current_index
        current_index = -1
        record_label.text = f'0 of {len(table.options["rowData"])} records'

    # Function to get the maximum product ID
    def get_max_product_id():
        """Get the maximum product ID from the products table."""
        try:
            # Get max product ID from database
            max_id_result = []
            connection.contogetrows("SELECT MAX(id) FROM products", max_id_result)

            if max_id_result and max_id_result[0][0]:
                max_id = max_id_result[0][0]
                return max_id
            else:
                return 0

        except Exception as e:
            print(f"Error getting max product ID: {e}")
            return 0

    # Function to load the product with maximum ID
    def load_max_product():
        """Set the ID input to max_id + 1 and clear other input fields for new product entry."""
        try:
            max_id = get_max_product_id()
            next_id = max_id + 1

            # Set ID input to next_id
            input_refs['id'].set_value(str(next_id))

            # Clear other input fields
            input_refs['product_name'].set_value('')
            input_refs['barcode'].set_value('')
            input_refs['sku'].set_value('')
            input_refs['description'].set_value('')
            input_refs['category_id'].set_value('')
            input_refs['price'].set_value('0.00')
            input_refs['cost_price'].set_value('0.00')
            input_refs['stock_quantity'].set_value(0)
            input_refs['min_stock_level'].set_value(0)
            input_refs['max_stock_level'].set_value(0)
            input_refs['supplier_id'].set_value('')
            input_refs['is_active'].set_value(True)

            # Update initial_values accordingly
            initial_values.update({
                'product_name': '',
                'barcode': '',
                'sku': '',
                'description': '',
                'category_id': '',
                'price': 0.00,
                'cost_price': 0.00,
                'stock_quantity': 0,
                'min_stock_level': 0,
                'max_stock_level': 0,
                'supplier_id': '',
                'is_active': True,
                'id': str(next_id)
            })

            ui.notify(f'✅ Ready for new product entry with ID: {next_id}')

        except Exception as e:
            ui.notify(f'Error setting next product ID: {str(e)}')
            print(f"Error setting next product ID: {e}")

    # Function to load the product record with maximum ID
    def load_max_product_record():
        """Automatically load the product with the maximum ID when entering the interface."""
        try:
            max_id = get_max_product_id()
            if max_id > 0:
                # Fetch the product data for the max ID
                product_data = []
                sql = f"""SELECT p.id, p.product_name, p.barcode, p.sku, p.description,
                         c.category_name as category_name, p.price, p.cost_price, p.stock_quantity,
                         p.min_stock_level, p.max_stock_level, s.name as supplier_name,
                         p.is_active
                         FROM products p
                         LEFT JOIN categories c ON p.category_id = c.id
                         LEFT JOIN suppliers s ON p.supplier_id = s.id
                         WHERE p.id = {max_id}"""
                connection.contogetrows(sql, product_data)

                if product_data:
                    row_data = {
                        'id': product_data[0][0],
                        'product_name': product_data[0][1],
                        'barcode': product_data[0][2] or '',
                        'sku': product_data[0][3] or '',
                        'description': product_data[0][4] or '',
                        'category_id': product_data[0][5] or '',
                        'price': float(product_data[0][6] or 0),
                        'cost_price': float(product_data[0][7] or 0),
                        'stock_quantity': int(product_data[0][8] or 0),
                        'min_stock_level': int(product_data[0][9] or 0),
                        'max_stock_level': int(product_data[0][10] or 0),
                        'supplier_id': product_data[0][11] or '',
                        'is_active': bool(product_data[0][12])
                    }

                    # Update input fields with the product data
                    input_refs['id'].set_value(row_data['id'])
                    input_refs['product_name'].set_value(row_data['product_name'])
                    input_refs['barcode'].set_value(row_data['barcode'])
                    input_refs['sku'].set_value(row_data['sku'])
                    input_refs['description'].set_value(row_data['description'])
                    input_refs['category_id'].set_value(row_data['category_id'])
                    input_refs['price'].set_value(str(row_data['price']))
                    input_refs['cost_price'].set_value(str(row_data['cost_price']))
                    input_refs['stock_quantity'].set_value(row_data['stock_quantity'])
                    input_refs['min_stock_level'].set_value(row_data['min_stock_level'])
                    input_refs['max_stock_level'].set_value(row_data['max_stock_level'])
                    input_refs['supplier_id'].set_value(row_data['supplier_id'])
                    input_refs['is_active'].set_value(row_data['is_active'])

                    # Store initial values for undo functionality
                    initial_values.update({
                        'product_name': row_data['product_name'],
                        'barcode': row_data['barcode'],
                        'sku': row_data['sku'],
                        'description': row_data['description'],
                        'category_id': row_data['category_id'],
                        'price': str(row_data['price']),
                        'cost_price': str(row_data['cost_price']),
                        'stock_quantity': row_data['stock_quantity'],
                        'min_stock_level': row_data['min_stock_level'],
                        'max_stock_level': row_data['max_stock_level'],
                        'supplier_id': row_data['supplier_id'],
                        'is_active': row_data['is_active'],
                        'id': row_data['id']
                    })

                    # Highlight the loaded row in the table
                    def highlight_loaded_row():
                        clear_highlights()
                        for idx, row in enumerate(table.options['rowData']):
                            if row.get('id') == row_data['id']:
                                set_highlight(idx)
                                table.update()
                                nonlocal current_index
                                current_index = idx
                                if record_label:
                                    record_label.text = f'{current_index + 1} of {len(table.options["rowData"])} records'
                                break

                    highlight_loaded_row()

                    ui.notify(f'✅ Automatically loaded product ID: {max_id} - {row_data["product_name"]}')
                else:
                    ui.notify('No products found in database')
            else:
                ui.notify('No products found in database')

        except Exception as e:
            ui.notify(f'Error loading max product: {str(e)}')
            print(f"Error loading max product: {e}")

    # Function to refresh the table
    def refresh_table():
        # Re-fetch data from database
        headers = []
        connection.contogetheaders("SELECT id, product_name, barcode, sku, description, category_id, price, cost_price, stock_quantity, min_stock_level, max_stock_level, supplier_id, created_at, is_active FROM products", headers)

        # Convert to AG Grid column format
        column_defs = [
            {'headerName': header.replace('_', ' ').title(), 'field': header, 'sortable': True, 'filter': True, 'width': 120}
            for header in headers
        ]

        # Fetch data from database
        data = []
        sql = """SELECT p.id, p.product_name, p.barcode, p.sku, p.description,
                 c.category_name as category, p.price, p.cost_price, p.stock_quantity,
                 p.min_stock_level, p.max_stock_level, s.name as supplier,
                 p.created_at, p.is_active
                 FROM products p
                 LEFT JOIN categories c ON p.category_id = c.id
                 LEFT JOIN suppliers s ON p.supplier_id = s.id
                 ORDER BY p.id DESC"""
        connection.contogetrows(sql, data)

        # Convert data to list of dictionaries for AG Grid
        new_row_data = []
        for row in data:
            row_dict = {}
            for i, header in enumerate(headers):
                row_dict[header] = row[i]
            row_dict['highlighted'] = False  # Add highlighted field for row styling
            new_row_data.append(row_dict)

        # Update AG Grid with new data
        table.options['columnDefs'] = column_defs
        table.options['rowData'] = new_row_data
        table.update()

        # Update total records label
        total_rows_label.text = f'Total Records: {len(new_row_data)}'

        # Update global row_data for search functionality
        nonlocal row_data
        row_data = new_row_data

        # Update navigation
        nonlocal total_records, current_index
        total_records = len(new_row_data)
        current_index = -1
        if record_label:
            record_label.text = f'0 of {total_records} records'

        # Reset filter
        for inp in filter_inputs.values():
            inp.set_value('')
        nonlocal filter_visible
        filter_visible = False
        if filter_panel:
            filter_panel.style('display: none')

        # Clear input fields
        clear_input_fields()

    def load_categories():
        sql = "SELECT id, category_name FROM categories ORDER BY category_name"
        data = []
        connection.contogetrows(sql, data)
        category_map.clear()
        for row in data:
            if len(row) >= 2:
                category_map[row[1]] = row[0]

    def load_suppliers():
        sql = "SELECT id, name FROM suppliers ORDER BY name"
        data = []
        connection.contogetrows(sql, data)
        supplier_map.clear()
        for row in data:
            if len(row) >= 2:
                supplier_map[row[1]] = row[0]

    def generate_barcode():
        try:
            # Generate a random 12-digit number for EAN-13 (library will add check digit)
            random_code = str(random.randint(100000000000, 999999999999))
            ean = EAN13(random_code)
            generated_barcode = ean.get_fullcode()
            input_refs['barcode'].set_value(generated_barcode)
            ui.notify('EAN-13 barcode generated successfully', color='green')
        except Exception as e:
            ui.notify(f'Error generating barcode: {str(e)}', color='red')

    def print_product():
        with ui.dialog() as dialog, ui.card().classes('w-full max-w-md'):
            ui.label('Print Report').classes('text-xl font-bold mb-4')
            report_select = ui.select(['Barcode Report', 'Stock Operation Report'], label='Select Report Type', value='Barcode Report')
            from_date = ui.input('From Date').props('type=date').classes('mb-2')
            to_date = ui.input('To Date').props('type=date').classes('mb-2')
            ui.button('View Report', on_click=lambda: view_report(report_select.value, from_date.value, to_date.value, dialog)).classes('mt-4')
        dialog.open()

    def view_report(selected_report, from_date, to_date, dialog):
        product_id = input_refs['id'].value
        if not product_id:
            ui.notify('Please select a product', color='red')
            return

        dialog.close()

        if selected_report == 'Barcode Report':
            barcode = input_refs['barcode'].value
            product_name = input_refs['product_name'].value
            # Generate barcode SVG image
            try:
                ean = EAN13(barcode, writer=SVGWriter())
                svg_data = ean.render()
            except Exception as e:
                ui.notify(f'Error generating barcode image: {str(e)}', color='red')
                svg_data = None

            with ui.element('div').classes('printable') as print_div:
                ui.label(f'Product: {product_name}').classes('text-lg font-bold mb-2')
                if svg_data:
                    encoded = base64.b64encode(svg_data.encode('utf-8')).decode('utf-8')
                    data_url = f"data:image/svg+xml;base64,{encoded}"
                    ui.image(data_url).classes('mb-4')
                else:
                    ui.label(f'Barcode: {barcode}').classes('text-2xl mb-4')
            ui.run_javascript('window.print()')
            ui.notify('Barcode report generated and print dialog opened', color='blue')

        elif selected_report == 'Stock Operation Report':
            if not from_date or not to_date:
                ui.notify('Please select from and to dates', color='red')
                return
            # Query sales
            sql_sales = f"SELECT COALESCE(SUM(quantity), 0) FROM sales WHERE product_id = {product_id} AND sale_date BETWEEN '{from_date}' AND '{to_date}'"
            sales_data = []
            connection.contogetrows(sql_sales, sales_data)
            total_sold = sales_data[0][0] if sales_data else 0

            # Query purchases
            sql_purchases = f"SELECT COALESCE(SUM(quantity), 0) FROM purchases WHERE product_id = {product_id} AND purchase_date BETWEEN '{from_date}' AND '{to_date}'"
            purchases_data = []
            connection.contogetrows(sql_purchases, purchases_data)
            total_purchased = purchases_data[0][0] if purchases_data else 0

            net_quantity = total_purchased - total_sold

            with ui.element('div').classes('printable') as print_div:
                ui.label(f'Stock Operation Report for Product ID: {product_id}').classes('text-lg font-bold mb-2')
                ui.label(f'Period: {from_date} to {to_date}').classes('mb-2')
                ui.label(f'Total Sold: {total_sold}').classes('mb-2')
                ui.label(f'Total Purchased: {total_purchased}').classes('mb-2')
                ui.label(f'Net Quantity: {net_quantity}').classes('mb-2')
            ui.run_javascript('window.print()')
            ui.notify('Stock operation report generated and print dialog opened', color='blue')

    def generate_stock_transaction_report():
        """Generate stock transaction report for the selected product and display inline in browser"""
        product_id = input_refs['id'].value
        if not product_id:
            ui.notify('Please select a product to generate stock transaction report', color='red')
            return

        try:
            # Import the report class
            from stockreports.stock_transaction_report import generate_stock_transaction_report as generate_report

            # Generate the report as bytes (in-memory)
            success, result = generate_report(int(product_id), return_bytes=True)

            if success:
                # result is now PDF bytes, not a file path
                pdf_bytes = result

                # Convert PDF bytes to base64 for inline display
                import base64
                pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
                pdf_data_url = f"data:application/pdf;base64,{pdf_base64}"

                # Create a full-screen modal dialog to display the PDF inline
                with ui.dialog() as pdf_dialog:
                    with ui.card().classes('w-screen h-screen max-w-none max-h-none m-0 rounded-none'):
                        # Header with close button
                        with ui.row().classes('w-full justify-between items-center p-4 bg-gray-100 border-b'):
                            ui.label('Stock Transaction Report').classes('text-xl font-bold')
                            ui.button('✕ Close', on_click=pdf_dialog.close).classes('bg-red-500 hover:bg-red-700 text-white px-4 py-2 rounded')

                        # PDF display area taking full remaining space
                        ui.html(f'''
                            <iframe src="{pdf_data_url}"
                                    width="100%"
                                    height="100%"
                                    style="border: none; min-height: calc(100vh - 80px);">
                                <p>Your browser does not support iframes.
                                <a href="{pdf_data_url}" target="_blank">Click here to view the PDF</a></p>
                            </iframe>
                        ''').classes('w-full flex-1')

                pdf_dialog.open()
                ui.notify('Stock transaction report generated and displayed', color='green')
            else:
                ui.notify(f'Failed to generate report: {result}', color='red')

        except Exception as e:
            ui.notify(f'Error generating stock transaction report: {str(e)}', color='red')

    # Load dropdown options
    load_categories()
    load_suppliers()

    # Main content area with splitter layout
    with ui.element('div').classes('flex w-full h-screen'):
        # Left drawer for action buttons
        with ui.column().classes('w-20 p-4 bg-gray-100 flex-shrink-0'):
            ui.label('Actions').classes('text-lg font-bold mb-4')
            ui.button('', icon='add', on_click=clear_input_fields).classes('bg-blue-500 text-white w-full mb-2').tooltip('Create a new product record')
            ui.button('', icon='save', on_click=save_product).classes('bg-green-500 text-white w-full mb-2').tooltip('Save current product information')
            ui.button('', icon='undo', on_click=undo_changes).classes('bg-yellow-500 text-white w-full mb-2').tooltip('Undo changes to product data')
            ui.button('', icon='delete', on_click=delete_product).classes('bg-red-500 text-white w-full mb-2').tooltip('Delete the selected product')
            ui.button('', icon='refresh', on_click=refresh_table).classes('bg-purple-500 text-white w-full mb-2').tooltip('Refresh the product list')
            ui.button('', icon='print', on_click=print_product).classes('bg-orange-500 text-white w-full mb-2').tooltip('Print reports for selected product')
            ui.button('', icon='analytics', on_click=generate_stock_transaction_report).classes('bg-purple-500 text-white w-full mb-2').tooltip('Generate stock transaction report for selected product')

        # Main content area with splitter
        with ui.column().classes('flex-1 p-4 overflow-y-auto'):
            # Splitter for grid and form sections
            with ui.splitter(horizontal=True, value=20).classes('w-full h-full') as main_splitter:
                with main_splitter.separator:
                    ui.icon('drag_handle').classes('text-gray-400 text-sm')

                # Top section - Product List Grid
                with main_splitter.before:
                    # Search functionality
                    # Container for table and navigation buttons
                    with ui.element('div').classes('relative w-full'):
                        # Navigation buttons positioned absolutely over the table
                        with ui.row().classes(' top--20 left-0 z-5 items-center gap-1').style('height: 25px; background: transparent; padding: 2px;'):
                            ui.button('', icon='first_page', on_click=first_record).classes('bg-blue-500 hover:bg-blue-700 text-white px-2 py-1 text-xs rounded').tooltip('Go to first record')
                            ui.button('', icon='skip_previous', on_click=prev_10).classes('bg-blue-500 hover:bg-blue-700 text-white px-2 py-1 text-xs rounded').tooltip('Go to previous 10 records')
                            ui.button('', icon='chevron_left', on_click=prev_record).classes('bg-blue-500 hover:bg-blue-700 text-white px-2 py-1 text-xs rounded').tooltip('Go to previous record')
                            record_label = ui.label('0 of 0 records').classes('text-xs text-gray-600')
                            ui.button('', icon='chevron_right', on_click=next_record).classes('bg-blue-500 hover:bg-blue-700 text-white px-2 py-1 text-xs rounded').tooltip('Go to next record')
                            ui.button('', icon='skip_next', on_click=next_10).classes('bg-blue-500 hover:bg-blue-700 text-white px-2 py-1 text-xs rounded').tooltip('Go to next 10 records')
                            ui.button('', icon='last_page', on_click=last_record).classes('bg-blue-500 hover:bg-blue-700 text-white px-2 py-1 text-xs rounded').tooltip('Go to last record')
                            search_input = ui.input('Search Products').classes('w-full')
                        # Get column headers from database
                        headers = []
                        connection.contogetheaders("SELECT id, product_name, barcode, sku, description, category_id, price, cost_price, stock_quantity, min_stock_level, max_stock_level, supplier_id, created_at, is_active FROM products", headers)

                        # Convert to AG Grid column format
                        column_defs = [
                            {'headerName': header.replace('_', ' ').title(), 'field': header, 'sortable': True, 'filter': True, 'width': 120}
                            for header in headers
                        ]

                        # Fetch data from database
                        data = []
                        sql = """SELECT p.id, p.product_name, p.barcode, p.sku, p.description,
                                 c.category_name as category, p.price, p.cost_price, p.stock_quantity,
                                 p.min_stock_level, p.max_stock_level, s.name as supplier,
                                 p.created_at, p.is_active
                                 FROM products p
                                 LEFT JOIN categories c ON p.category_id = c.id
                                 LEFT JOIN suppliers s ON p.supplier_id = s.id
                                 ORDER BY p.id DESC"""
                        connection.contogetrows(sql, data)

                        # Convert data to list of dictionaries for AG Grid
                        row_data = []
                        for row in data:
                            row_dict = {}
                            for i, header in enumerate(headers):
                                row_dict[header] = row[i]
                            row_dict['highlighted'] = False  # Add
