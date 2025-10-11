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
    uiAggridTheme.addingtheme()
    ui.add_css('''
    .ag-theme-quartz-custom .highlighted-row {
        background-color: #1976D2 !important;
        color: #ffffff !important;
    }
    ''')

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

    # Navigation and filter variables
    current_index = 0
    filtered_data = []
    filter_panel_visible = False
    filter_criteria = {}
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
        # Dim the grid when creating new record
        table.classes('dimmed')

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
            # Remove dimming and refresh the table
            table.classes(remove='dimmed')
            refresh_table()
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

    def undo_changes():
        for key in input_refs:
            if key in initial_values:
                input_refs[key].set_value(initial_values[key])
        # Remove dimming when undoing changes
        table.classes(remove='dimmed')
        ui.notify('Changes undone', color='blue')

    def delete_product():
        id_value = input_refs['id'].value
        if not id_value:
            ui.notify('Please select a product to delete', color='red')
            return
        try:
            sql = "DELETE FROM products WHERE id=?"
            connection.deleterow(sql, id_value)
            ui.notify('Product deleted successfully', color='green')
            # Remove dimming, clear input fields, and refresh the table
            table.classes(remove='dimmed')
            clear_input_fields()
            refresh_table()
        except Exception as e:
            ui.notify(f'Error deleting product: {str(e)}', color='red')

    def refresh_table():
        headers = []
        connection.contogetheaders("SELECT id, product_name, barcode, sku, description, category_id, price, cost_price, stock_quantity, min_stock_level, max_stock_level, supplier_id, created_at, is_active FROM products", headers)
        
        # Convert to AG Grid column format
        column_defs = [
            {'headerName': header.replace('_', ' ').title(), 'field': header, 'sortable': True, 'filter': True, 'width': 120}
            for header in headers
        ]
        
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
                value = row[i] if i < len(row) else ''
                if header == 'is_active':
                    row_dict[header] = bool(value)
                elif header in ['price', 'cost_price']:
                    row_dict[header] = float(value or 0)
                elif header in ['stock_quantity', 'min_stock_level', 'max_stock_level']:
                    row_dict[header] = int(value or 0)
                else:
                    row_dict[header] = value
            row_dict['highlighted'] = False
            new_row_data.append(row_dict)
        
        # Update AG Grid with new data
        table.options['columnDefs'] = column_defs
        table.options['rowData'] = new_row_data
        table.update()
        
        # Update global row_data for search functionality
        nonlocal row_data
        row_data = new_row_data
        nonlocal filtered_data
        filtered_data = new_row_data[:]

        # Remove dimming and clear input fields
        table.classes(remove='dimmed')
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
                    for key in input_refs:
                        if key in row_data:
                            input_refs[key].set_value(row_data[key])

                    # Store initial values for undo functionality
                    initial_values.update({
                        'product_name': row_data['product_name'],
                        'barcode': row_data['barcode'],
                        'sku': row_data['sku'],
                        'description': row_data['description'],
                        'category_id': row_data['category_id'],
                        'price': row_data['price'],
                        'cost_price': row_data['cost_price'],
                        'stock_quantity': row_data['stock_quantity'],
                        'min_stock_level': row_data['min_stock_level'],
                        'max_stock_level': row_data['max_stock_level'],
                        'supplier_id': row_data['supplier_id'],
                        'is_active': row_data['is_active'],
                        'id': row_data['id']
                    })

                    ui.notify(f'✅ Automatically loaded product ID: {max_id} - {row_data["product_name"]}')
                else:
                    pass
            else:
                pass

        except Exception as e:
            ui.notify(f'Error loading max product: {str(e)}')
            print(f"Error loading max product: {e}")

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

    # Navigation and filter functions
    def first_record():
        nonlocal current_index
        if filtered_data:
            current_index = 0
            update_record_label()
            load_record_at_index(current_index)

    def prev_10():
        nonlocal current_index
        if filtered_data:
            current_index = max(0, current_index - 10)
            update_record_label()
            load_record_at_index(current_index)

    def prev_record():
        nonlocal current_index
        if filtered_data and current_index > 0:
            current_index -= 1
            update_record_label()
            load_record_at_index(current_index)
            set_highlight(current_index)

    def next_record():
        nonlocal current_index
        if filtered_data and current_index < len(filtered_data) - 1:
            current_index += 1
            update_record_label()
            load_record_at_index(current_index)
            set_highlight(current_index)

    def next_10():
        nonlocal current_index
        if filtered_data:
            current_index = min(len(filtered_data) - 1, current_index + 10)
            update_record_label()
            load_record_at_index(current_index)

    def last_record():
        nonlocal current_index
        if filtered_data:
            current_index = len(filtered_data) - 1
            update_record_label()
            load_record_at_index(current_index)

    def update_record_label():
        if filtered_data:
            record_label.text = f"{current_index + 1} of {len(filtered_data)}"
        else:
            record_label.text = "0 of 0"

    def load_record_at_index(index):
        if filtered_data and 0 <= index < len(filtered_data):
            row_data = filtered_data[index]
            for key in input_refs:
                if key in row_data:
                    input_refs[key].set_value(row_data[key])
            initial_values.update({k: v for k, v in row_data.items() if k in input_refs})
            set_highlight(index)

    def filter_rows(search_text):
        nonlocal filtered_data, current_index
        if not search_text:
            filtered_data = row_data[:]
        else:
            filtered_data = [row for row in row_data if any(
                search_text.lower() in str(value).lower() for value in row.values()
            )]
        current_index = 0
        table.options['rowData'] = filtered_data
        table.update()
        update_record_label()
        clear_highlights()
        if filtered_data:
            load_record_at_index(0)

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

    def clear_filters():
        table.run_method('setFilterModel', {})
        # Reset current_index
        nonlocal current_index
        current_index = -1
        record_label.text = f'0 of {len(table.options["rowData"])} records'
        filter_info_button.style('display: none')

    def clear_highlights():
        for row in filtered_data:
            row['highlighted'] = False
        table.options['rowData'] = filtered_data
        table.update()

    def clear_single_filter():
        # Clear the current filter criteria and update UI
        filter_criteria.clear()
        clear_filters()

    def set_highlight(index):
        clear_highlights()
        if 0 <= index < len(filtered_data):
            filtered_data[index]['highlighted'] = True
            table.options['rowData'] = filtered_data
            table.update()

    def on_filter_changed(col, filter_type, value):
        filter_criteria[col] = {'type': filter_type, 'value': value}

    # Load dropdown options
    load_categories()
    load_suppliers()

    # Initialize headers for filter panel
    headers = []
    connection.contogetheaders("SELECT id, product_name, barcode, sku, description, category_id, price, cost_price, stock_quantity, min_stock_level, max_stock_level, supplier_id, created_at, is_active FROM products", headers)

    # Main content area with splitter layout
    with ui.element('div').classes('flex w-full h-screen'):
        # Left drawer for action buttons
        with ui.column().classes('w-20 p-4 bg-gray-100 flex-shrink-0'):
            ui.label('Actions').classes('text-lg font-bold mb-4')
            ui.button('', icon='add', on_click=clear_input_fields).classes('bg-blue-500 text-white w-full mb-2')
            ui.button('', icon='save', on_click=save_product).classes('bg-green-500 text-white w-full mb-2')
            ui.button('', icon='undo', on_click=undo_changes).classes('bg-yellow-500 text-white w-full mb-2')
            ui.button('', icon='delete', on_click=delete_product).classes('bg-red-500 text-white w-full mb-2')
            ui.button('', icon='refresh', on_click=refresh_table).classes('bg-purple-500 text-white w-full mb-2')
            ui.button('', icon='print', on_click=print_product).classes('bg-orange-500 text-white w-full mb-2')
            ui.button('', icon='analytics', on_click=generate_stock_transaction_report).classes('bg-purple-500 text-white w-full mb-2')
        
        # Main content area with splitter
        with ui.column().classes('flex-1 p-4 overflow-y-auto'):
            
            # Splitter for grid and form sections
            with ui.splitter(horizontal=True, value=25).classes('w-full h-full') as main_splitter:
                with main_splitter.separator:
                    ui.icon('drag_handle').classes('text-gray-400 text-sm')
                
                # Top section - Product List Grid
                with main_splitter.before:
                    #ui.label('Product List').classes('text-xl font-bold mb-2')
                    with ui.element('div').classes('relative w-full'):
                        # Navigation buttons positioned absolutely over the table
                        with ui.row().classes(' top--10 left-0 z-5 items-center gap-1').style('height: 20px; background: transparent; padding: 0 4px; margin-bottom: 0;'):
                            ui.button('', icon='first_page', on_click=first_record).classes('bg-blue-500 hover:bg-blue-700 text-white px-2 py-1 text-xs rounded').tooltip('Go to first record')
                            ui.button('', icon='skip_previous', on_click=prev_10).classes('bg-blue-500 hover:bg-blue-700 text-white px-2 py-1 text-xs rounded').tooltip('Go to previous 10 records')
                            ui.button('', icon='chevron_left', on_click=prev_record).classes('bg-blue-500 hover:bg-blue-700 text-white px-2 py-1 text-xs rounded').tooltip('Go to previous record')
                            record_label = ui.label('0 of 0 records').classes('text-xs text-gray-600')
                            ui.button('', icon='chevron_right', on_click=next_record).classes('bg-blue-500 hover:bg-blue-700 text-white px-2 py-1 text-xs rounded').tooltip('Go to next record')
                            ui.button('', icon='skip_next', on_click=next_10).classes('bg-blue-500 hover:bg-blue-700 text-white px-2 py-1 text-xs rounded').tooltip('Go to next 10 records')
                            ui.button('', icon='last_page', on_click=last_record).classes('bg-blue-500 hover:bg-blue-700 text-white px-2 py-1 text-xs rounded').tooltip('Go to last record')
                        
                            search_input = ui.input('Search Products').classes('w-46')

                        # Filter info button (moved from navigation row)
                       
                        # Total rows label
                       

                        # Filter panel
                        filter_panel = ui.card().classes('p-2 mt-2').style('display: none;')
                        with filter_panel:
                            ui.label('Advanced Filters').classes('text-sm font-bold mb-2')
                            with ui.row().classes('w-full gap-2'):
                                filter_col_select = ui.select(headers, label='Column').classes('flex-1')
                                filter_type_select = ui.select(['contains', 'equals', 'starts_with'], label='Type', value='contains').classes('flex-1')
                                filter_value_input = ui.input('Value').classes('flex-1')
                                ui.button('Apply', on_click=apply_filter).classes('bg-blue-500 hover:bg-blue-700 text-white px-3 py-1 text-xs rounded')
                    
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
                            value = row[i] if i < len(row) else ''
                            if header == 'is_active':
                                row_dict[header] = bool(value)
                            elif header in ['price', 'cost_price']:
                                row_dict[header] = float(value or 0)
                            elif header in ['stock_quantity', 'min_stock_level', 'max_stock_level']:
                                row_dict[header] = int(value or 0)
                            else:
                                row_dict[header] = value
                        row_dict['highlighted'] = False
                        row_data.append(row_dict)

                    # Initialize filtered_data
                    filtered_data = row_data[:]

                    # Update record label initially
                    update_record_label()

                    # Create AG Grid table with scroll functionality
                    table = ui.aggrid({
                        'columnDefs': column_defs,
                        'rowData': row_data,
                        'defaultColDef': {'flex': 1, 'minWidth': 100, 'sortable': True, 'filter': True},
                        'rowSelection': 'single',
                        'domLayout': 'normal',
                        'pagination': False,
                        
                        'rowClassRules': {
                            'highlighted-row': 'data.highlighted === true'
                        }
                    }).classes('w-full ag-theme-quartz-custom').style('height: 220px; overflow-y: auto;')
                    
                    # Add row selection functionality for AG Grid
                    async def on_row_click():
                        nonlocal current_index
                        try:
                            selected_row = await table.get_selected_row()
                            if selected_row:
                                for key in input_refs:
                                    if key in selected_row:
                                        input_refs[key].set_value(selected_row[key])
                                initial_values.update({k: v for k, v in selected_row.items() if k in input_refs})
                                # Find the index of the selected row in filtered_data and highlight it
                                index = next((i for i, row in enumerate(filtered_data) if row.get('id') == selected_row.get('id')), -1)
                                if index != -1:
                                    set_highlight(index)
                                    current_index = index
                                    update_record_label()
                        except Exception as e:
                            ui.notify(f'Error selecting row: {str(e)}')
                    
                    table.on('cellClicked', on_row_click)
                    
                    # Add search functionality for AG Grid
                    def filter_rows(search_text):
                        if not search_text:
                            # Reset to all data
                            table.options['rowData'] = row_data
                            total_rows_label.text = f'Total Records: {len(row_data)}'
                        else:
                            # Filter rows based on search text
                            filtered_rows = [row for row in row_data if any(
                                search_text.lower() in str(value).lower() for value in row.values()
                            )]
                            table.options['rowData'] = filtered_rows
                            total_rows_label.text = f'Total Records: {len(filtered_rows)}'
                        table.update()

                        # Select the first row of the filtered results if available
                        if filtered_rows:
                            first_row = filtered_rows[0]
                            for key in input_refs:
                                if key in first_row:
                                    input_refs[key].set_value(first_row[key])

                    # Connect search input to filter function
                    search_input.on('keydown.enter', lambda e: filter_rows(e.sender.value))

                    # Function to clear filters
                    def clear_filters():
                        table.run_method('setFilterModel', {})
                        table.update()
                        nonlocal current_index
                        current_index = -1
                        record_label.text = f'0 of {len(table.options["rowData"])} records'
                        filter_info_button.style('display: none;')

                    # Event listener for filter changes
                    import asyncio
                    filter_change_task = None

                    async def on_filter_changed():
                        nonlocal filter_change_task
                        if filter_change_task and not filter_change_task.done():
                            filter_change_task.cancel()
                        async def handle_filter_change():
                            try:
                                filter_model = await asyncio.wait_for(table.run_method('getFilterModel'), timeout=10.0)
                                if filter_model:
                                    filter_texts = []
                                    for col, val in filter_model.items():
                                        if isinstance(val, dict):
                                            filter_value = val.get('filter', '')
                                        else:
                                            filter_value = str(val)
                                        if filter_value:
                                            filter_texts.append(f"{col.replace('_', ' ').title()}: {filter_value}")
                                    if filter_texts:
                                        filter_info_button.style('display: flex;')
                                        filter_info_button.text = ' ✕ '.join(filter_texts) + ' ✕'
                                    else:
                                        filter_info_button.style('display: none;')
                                else:
                                    filter_info_button.style('display: none;')
                            except asyncio.CancelledError:
                                pass
                            except asyncio.TimeoutError:
                                # Keep the button visible with "Filters active" if detailed info fails
                                filter_info_button.style('display: flex;')
                                filter_info_button.text = 'Filters active ✕'
                            except Exception as e:
                                # Keep the button visible with "Filters active" if detailed info fails
                                filter_info_button.style('display: flex;')
                                filter_info_button.text = 'Filters active ✕'
                        filter_change_task = asyncio.create_task(handle_filter_change())

                    table.on('filterChanged', on_filter_changed)
                
                # Bottom section - Input fields
                with main_splitter.after:
                    filter_info_button = ui.button('✕ Clear Filter', on_click=clear_filters).classes('bg-red-500 hover:bg-red-700 text-white text-xs px-2 py-1 rounded').style('display: none;')
       

                    # Add Price History button function
                    def show_price_history():
                        product_id = input_refs['id'].value
                        if not product_id:
                            ui.notify('Please select a product to view price history', color='red')
                            return

                        # Fetch price history data from database using contogetheaders and contogetrows
                        headers = []
                        sql_headers = "SELECT old_price, new_price, old_cost_price, new_cost_price, change_date, changed_by FROM price_cost_date_history"
                        connection.contogetheaders(sql_headers, headers)

                        data = []
                        sql = f"SELECT old_price, new_price, old_cost_price, new_cost_price, change_date, changed_by FROM price_cost_date_history WHERE product_id = {product_id} ORDER BY change_date DESC"
                        connection.contogetrows(sql, data)

                        # Convert data to list of dictionaries for ui.table
                        rows = []
                        for row in data:
                            row_dict = {}
                            for i, header in enumerate(headers):
                                row_dict[header] = row[i] if i < len(row) else ''
                            rows.append(row_dict)

                        # Create modal dialog with price history table
                        with ui.dialog() as dialog, ui.card().classes('w-full max-w-4xl'):
                            ui.label('Price History').classes('text-xl font-bold mb-4')
                            if rows:
                                ui.table(columns=[{'name': h, 'label': h.replace('_', ' ').title(), 'field': h} for h in headers], rows=rows).classes('w-full text-xs')
                            else:
                                ui.label('No price history found for this product').classes('text-gray-600')
                            ui.button('Close', on_click=dialog.close).classes('mt-4')

                        dialog.open()

                    # Input fields for product data - organized with 4 inputs per row for better screen fit
                    with ui.row().classes('w-full mb-4'):
                        input_refs['id'] = ui.input('Product ID').props('readonly').classes('w-1/5 mr-2')
                        input_refs['product_name'] = ui.input('Product Name *').classes('w-1/5 mr-2')
                        with ui.row().classes('w-1/5 mr-2'):
                            input_refs['barcode'] = ui.input('Barcode').classes('flex-1 mr-1')
                            with ui.button(on_click=generate_barcode).classes('w-8 p-0'):
                                ui.image('https://img.icons8.com/material-outlined/24/barcode.png').classes('w-6 h-6')
                        input_refs['sku'] = ui.input('SKU').classes('w-1/5 mr-2')

                    with ui.row().classes('w-full mb-4'):
                        input_refs['description'] = ui.input('Description').classes('w-1/5 mr-2')
                        input_refs['category_id'] = ui.select(list(category_map.keys()), label='Category').classes('w-1/5 mr-2')
                        input_refs['category_id']._options_dict = category_map
                        input_refs['price'] = ui.input('Price').props('readonly').classes('w-1/5 mr-2')

                    with ui.row().classes('w-full mb-4'):
                        input_refs['cost_price'] = ui.input('Cost Price').props('readonly').classes('w-1/5 mr-2')
                        input_refs['stock_quantity'] = ui.input('Stock Quantity').props('readonly').classes('w-1/5 mr-2')
                        input_refs['min_stock_level'] = ui.input('Min Stock Level').classes('w-1/5 mr-2')
                        input_refs['max_stock_level'] = ui.input('Max Stock Level').classes('w-1/5 mr-2')

                    with ui.row().classes('w-full mb-4'):
                        input_refs['supplier_id'] = ui.select(list(supplier_map.keys()), label='Supplier').classes('w-1/5 mr-2')
                        input_refs['supplier_id']._options_dict = supplier_map
                        input_refs['is_active'] = ui.checkbox('Is Active', value=True).classes('w-1/5 mr-2')
                        input_refs['photo'] = ui.upload(label='Product Photo').classes('w-1/5 mr-2')
                        ui.button('Price History', on_click=show_price_history).classes('w-1/5 mr-2')

                    # Automatically load the product with max ID after UI is created
                    ui.timer(0.1, load_max_product, once=True)

    # Footer with system time, company name, and username
    with ui.footer().classes('flex justify-between items-center p-4 bg-gray-100 text-sm text-gray-600'):
        # System time
        def update_time():
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            time_label.set_text(f'System Time: {now}')
        time_label = ui.label()
        update_time()
        ui.timer(1.0, update_time)

        # Company name from database
        company_info = connection.get_company_info()
        company_name = company_info.get('company_name') if company_info else 'Company Name'
        ui.label(f'Company: {company_name}')

        # Username from session
        user = session_storage.get('user')
        username = user.get('username') if user else 'Guest'
        ui.label(f'User: {username}')


@ui.page('/products')
def product_page_route():
    product_page()
