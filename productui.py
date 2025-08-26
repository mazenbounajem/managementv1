from nicegui import ui
from connection import connection
from uiaggridtheme import uiAggridTheme

def product_page():
    uiAggridTheme.addingtheme()
    with ui.header().classes('items-center justify-between'):
        ui.label('Product Management').classes('text-2xl font-bold')
        ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard')).props('flat color=white')

    # Store references to input fields
    input_refs = {}
    
    # Store the initial values for undo functionality
    initial_values = {}
    
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
            new_row_data.append(row_dict)
        
        # Update AG Grid with new data
        table.options['columnDefs'] = column_defs
        table.options['rowData'] = new_row_data
        table.update()
        
        # Update global row_data for search functionality
        nonlocal row_data
        row_data = new_row_data
        
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

    # Load dropdown options
    load_categories()
    load_suppliers()

    # Main content area with splitter layout
    with ui.element('div').classes('flex w-full h-screen'):
        # Left drawer for action buttons
        with ui.column().classes('w-48 p-4 bg-gray-100 flex-shrink-0'):
            ui.label('Actions').classes('text-lg font-bold mb-4')
            ui.button('New', icon='add', on_click=clear_input_fields).classes('bg-blue-500 text-white w-full mb-2')
            ui.button('Save', icon='save', on_click=save_product).classes('bg-green-500 text-white w-full mb-2')
            ui.button('Undo', icon='undo', on_click=undo_changes).classes('bg-yellow-500 text-white w-full mb-2')
            ui.button('Delete', icon='delete', on_click=delete_product).classes('bg-red-500 text-white w-full mb-2')
            ui.button('Refresh', icon='refresh', on_click=refresh_table).classes('bg-purple-500 text-white w-full mb-2')
        
        # Main content area with splitter
        with ui.column().classes('flex-1 p-4 overflow-y-auto'):
            # Splitter for grid and form sections
            with ui.splitter(horizontal=True, value=40).classes('w-full h-full') as main_splitter:
                with main_splitter.separator:
                    ui.icon('drag_handle').classes('text-gray-400 text-sm')
                
                # Top section - Product List Grid
                with main_splitter.before:
                    ui.label('Product List').classes('text-xl font-bold mb-2')
                    
                    # Search functionality
                    search_input = ui.input('Search Products').classes('w-full mb-2')
                    
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
                            value = row[i] if i < len(row) else ''
                            if header == 'is_active':
                                row_dict[header] = bool(value)
                            elif header in ['price', 'cost_price']:
                                row_dict[header] = float(value or 0)
                            elif header in ['stock_quantity', 'min_stock_level', 'max_stock_level']:
                                row_dict[header] = int(value or 0)
                            else:
                                row_dict[header] = value
                        row_data.append(row_dict)
                    
                    # Create AG Grid table with scroll functionality
                    table = ui.aggrid({
                        'columnDefs': column_defs,
                        'rowData': row_data,
                        'defaultColDef': {'flex': 1, 'minWidth': 100, 'sortable': True, 'filter': True},
                        'rowSelection': 'single',
                        'domLayout': 'normal',
                        'pagination': True,
                        'paginationPageSize': 5
                    }).classes('w-full ag-theme-quartz-custom').style('height: 200px; overflow-y: auto;')
                    
                    # Add row selection functionality for AG Grid
                    async def on_row_click():
                        try:
                            selected_row = await table.get_selected_row()
                            if selected_row:
                                for key in input_refs:
                                    if key in selected_row:
                                        input_refs[key].set_value(selected_row[key])
                                initial_values.update({k: v for k, v in selected_row.items() if k in input_refs})
                        except Exception as e:
                            ui.notify(f'Error selecting row: {str(e)}')
                    
                    table.on('cellClicked', on_row_click)
                    
                    # Add search functionality for AG Grid
                    def filter_rows(search_text):
                        if not search_text:
                            # Reset to all data
                            table.options['rowData'] = row_data
                        else:
                            # Filter rows based on search text
                            filtered_rows = [row for row in row_data if any(
                                search_text.lower() in str(value).lower() for value in row.values()
                            )]
                            table.options['rowData'] = filtered_rows
                        table.update()
                        
                        # Select the first row of the filtered results if available
                        if filtered_rows:
                            first_row = filtered_rows[0]
                            for key in input_refs:
                                if key in first_row:
                                    input_refs[key].set_value(first_row[key])
                    
                    search_input.on('keydown.enter', lambda e: filter_rows(e.sender.value))
                
                # Bottom section - Input fields
                with main_splitter.after:
                    ui.label('Product Details').classes('text-xl font-bold mb-2')
                    
                    # Input fields for product data
                    with ui.row().classes('w-full mb-4'):
                        input_refs['id'] = ui.input('Product ID').props('readonly').classes('w-1/6 mr-2')
                        input_refs['product_name'] = ui.input('Product Name *').classes('w-1/6 mr-2')
                        input_refs['barcode'] = ui.input('Barcode').classes('w-1/6 mr-2')
                        input_refs['sku'] = ui.input('SKU').classes('w-1/6 mr-2')
                        input_refs['description'] = ui.input('Description').classes('w-1/6 mr-2')
                        input_refs['category_id'] = ui.select(list(category_map.keys()), label='Category').classes('w-1/6 mr-2')
                        input_refs['category_id']._options_dict = category_map

                    with ui.row().classes('w-full mb-4'):
                        input_refs['price'] = ui.input('Price').classes('w-1/6 mr-2')
                        input_refs['cost_price'] = ui.input('Cost Price').classes('w-1/6 mr-2')
                        input_refs['stock_quantity'] = ui.input('Stock Quantity').classes('w-1/6 mr-2')
                        input_refs['min_stock_level'] = ui.input('Min Stock Level').classes('w-1/6 mr-2')
                        input_refs['max_stock_level'] = ui.input('Max Stock Level').classes('w-1/6 mr-2')
                        input_refs['supplier_id'] = ui.select(list(supplier_map.keys()), label='Supplier').classes('w-1/6 mr-2')
                        input_refs['supplier_id']._options_dict = supplier_map

                    input_refs['is_active'] = ui.checkbox('Is Active', value=True).classes('mb-4')


@ui.page('/products')
def product_page_route():
    product_page()
