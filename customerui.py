from nicegui import ui
from connection import connection
from uiaggridtheme import uiAggridTheme

def customer_page():
    uiAggridTheme.addingtheme()
    with ui.header().classes('items-center justify-between'):
        ui.label('Customer Management').classes('text-2xl font-bold')
        ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard')).props('flat color=white')

    # Store references to input fields
    input_refs = {}
    
    # Store the initial values for undo functionality
    initial_values = {}
    
    # Function to clear all input fields
    def clear_input_fields():
        input_refs['customer_name'].set_value('')
        input_refs['email'].set_value('')
        input_refs['phone'].set_value('')
        input_refs['address'].set_value('')
        input_refs['city'].set_value('')
        input_refs['state'].set_value('')
        input_refs['zip_code'].set_value('')
        input_refs['balance'].set_value('0.00')
        input_refs['is_active'].set_value('1')
        input_refs['id'].set_value('')
    
    # Function to save customer data
    def save_customer():
        # Get values from input fields
        customer_name = input_refs['customer_name'].value
        email = input_refs['email'].value
        phone = input_refs['phone'].value
        address = input_refs['address'].value
        city = input_refs['city'].value
        state = input_refs['state'].value
        zip_code = input_refs['zip_code'].value
        is_active = input_refs['is_active'].value
        id_value = input_refs['id'].value
        
        # Check if all required data is entered
        if not customer_name:
            ui.notify('Please enter Customer Name', color='red')
            return
        
        # Insert or update data in database using connection
        try:
            if id_value:  # Update existing record
                sql = "UPDATE customers SET customer_name=?, email=?, phone=?, address=?, city=?, state=?, zip_code=?, is_active=? WHERE id=?"
                values = (customer_name, email, phone, address, city, state, zip_code, is_active, id_value)
            else:  # Insert new record
                sql = "INSERT INTO customers (customer_name, email, phone, address, city, state, zip_code, is_active, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, GETDATE())"
                values = (customer_name, email, phone, address, city, state, zip_code, is_active)
            
            connection.insertingtodatabase(sql, values)
            ui.notify('Customer saved successfully', color='green')
            # Refresh the table to show the new customer
            refresh_table()
            # Update initial values
            initial_values.update({
                'customer_name': customer_name,
                'email': email,
                'phone': phone,
                'address': address,
                'city': city,
                'state': state,
                'zip_code': zip_code,
                'is_active': is_active,
                'id': id_value
            })
        except Exception as e:
            ui.notify(f'Error saving customer: {str(e)}', color='red')
    
    # Function to undo changes
    def undo_changes():
        if 'customer_name' in input_refs and 'customer_name' in initial_values:
            input_refs['customer_name'].set_value(initial_values['customer_name'])
        if 'email' in input_refs and 'email' in initial_values:
            input_refs['email'].set_value(initial_values['email'])
        if 'phone' in input_refs and 'phone' in initial_values:
            input_refs['phone'].set_value(initial_values['phone'])
        if 'address' in input_refs and 'address' in initial_values:
            input_refs['address'].set_value(initial_values['address'])
        if 'city' in input_refs and 'city' in initial_values:
            input_refs['city'].set_value(initial_values['city'])
        if 'state' in input_refs and 'state' in initial_values:
            input_refs['state'].set_value(initial_values['state'])
        if 'zip_code' in input_refs and 'zip_code' in initial_values:
            input_refs['zip_code'].set_value(initial_values['zip_code'])
        if 'is_active' in input_refs and 'is_active' in initial_values:
            input_refs['is_active'].set_value(initial_values['is_active'])
        if 'id' in input_refs and 'id' in initial_values:
            input_refs['id'].set_value(initial_values['id'])
        ui.notify('Changes undone', color='blue')
    
    # Function to delete customer
    def delete_customer():
        id_value = input_refs['id'].value
        if not id_value:
            ui.notify('Please select a customer to delete', color='red')
            return
        
        try:
            sql = "DELETE FROM customers WHERE id=?"
            connection.deleterow(sql, id_value)
            ui.notify('Customer deleted successfully', color='green')
            # Clear input fields
            clear_input_fields()
            # Refresh the table
            refresh_table()
        except Exception as e:
            ui.notify(f'Error deleting customer: {str(e)}', color='red')
    
    # Function to refresh the table
    def refresh_table():
        # Re-fetch data from database
        headers = []
        connection.contogetheaders("SELECT id, customer_name, email, phone, address, city, state, zip_code, balance, is_active, created_at FROM customers", headers)
        
        # Convert to AG Grid column format
        column_defs = [
            {'headerName': header.replace('_', ' ').title(), 'field': header, 'sortable': True, 'filter': True, 'width': 120}
            for header in headers
        ]
        
        # Fetch data from database
        data = []
        connection.contogetrows("SELECT id, customer_name, email, phone, address, city, state, zip_code, balance, is_active, created_at FROM customers", data)
        
        # Convert data to list of dictionaries for AG Grid
        new_row_data = []
        for row in data:
            row_dict = {}
            for i, header in enumerate(headers):
                row_dict[header] = row[i]
            new_row_data.append(row_dict)
        
        # Update AG Grid with new data
        table.options['columnDefs'] = column_defs
        table.options['rowData'] = new_row_data
        table.update()
        
        # Update global row_data for search functionality
        nonlocal row_data
        row_data = new_row_data
        
        # Clear input fields
        clear_input_fields()

    # Main content area with splitter layout
    with ui.element('div').classes('flex w-full h-screen'):
        # Left drawer for action buttons
        with ui.column().classes('w-48 p-4 bg-gray-100 flex-shrink-0'):
            ui.label('Actions').classes('text-lg font-bold mb-4')
            ui.button('New', icon='add', on_click=clear_input_fields).classes('bg-blue-500 text-white w-full mb-2')
            ui.button('Save', icon='save', on_click=save_customer).classes('bg-green-500 text-white w-full mb-2')
            ui.button('Undo', icon='undo', on_click=undo_changes).classes('bg-yellow-500 text-white w-full mb-2')
            ui.button('Delete', icon='delete', on_click=delete_customer).classes('bg-red-500 text-white w-full mb-2')
            ui.button('Refresh', icon='refresh', on_click=refresh_table).classes('bg-purple-500 text-white w-full mb-2')
        
        # Main content area with splitter
        with ui.column().classes('flex-1 p-4 overflow-y-auto'):
            # Splitter for grid and form sections
            with ui.splitter(horizontal=True, value=40).classes('w-full h-full') as main_splitter:
                with main_splitter.separator:
                    ui.icon('drag_handle').classes('text-gray-400 text-sm')
                
                # Top section - Customer List Grid
                with main_splitter.before:
                    ui.label('Customer List').classes('text-xl font-bold mb-2')
                    
                    # Search functionality
                    search_input = ui.input('Search Customers').classes('w-full mb-2')
                    
                    # Get column headers from database
                    headers = []
                    connection.contogetheaders("SELECT id, customer_name, email, phone, address, city, state, zip_code, balance, is_active, created_at FROM customers", headers)
                    
                    # Convert to AG Grid column format
                    column_defs = [
                        {'headerName': header.replace('_', ' ').title(), 'field': header, 'sortable': True, 'filter': True, 'width': 120}
                        for header in headers
                    ]
                    
                    # Fetch data from database
                    data = []
                    connection.contogetrows("SELECT id, customer_name, email, phone, address, city, state, zip_code, balance, is_active, created_at FROM customers", data)
                    
                    # Convert data to list of dictionaries for AG Grid
                    row_data = []
                    for row in data:
                        row_dict = {}
                        for i, header in enumerate(headers):
                            row_dict[header] = row[i]
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
                                if 'id' in input_refs and 'id' in selected_row:
                                    input_refs['id'].set_value(selected_row['id'])
                                if 'customer_name' in input_refs and 'customer_name' in selected_row:
                                    input_refs['customer_name'].set_value(selected_row['customer_name'])
                                if 'email' in input_refs and 'email' in selected_row:
                                    input_refs['email'].set_value(selected_row['email'])
                                if 'phone' in input_refs and 'phone' in selected_row:
                                    input_refs['phone'].set_value(selected_row['phone'])
                                if 'address' in input_refs and 'address' in selected_row:
                                    input_refs['address'].set_value(selected_row['address'])
                                if 'city' in input_refs and 'city' in selected_row:
                                    input_refs['city'].set_value(selected_row['city'])
                                if 'state' in input_refs and 'state' in selected_row:
                                    input_refs['state'].set_value(selected_row['state'])
                                if 'zip_code' in input_refs and 'zip_code' in selected_row:
                                    input_refs['zip_code'].set_value(selected_row['zip_code'])
                                if 'is_active' in input_refs and 'is_active' in selected_row:
                                    input_refs['is_active'].set_value(selected_row['is_active'])
                                
                                # Store initial values for undo functionality
                                initial_values.update({
                                    'customer_name': input_refs['customer_name'].value,
                                    'email': input_refs['email'].value,
                                    'phone': input_refs['phone'].value,
                                    'address': input_refs['address'].value,
                                    'city': input_refs['city'].value,
                                    'state': input_refs['state'].value,
                                    'zip_code': input_refs['zip_code'].value,
                                    'is_active': input_refs['is_active'].value,
                                    'id': input_refs['id'].value
                                })
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
                            if 'id' in input_refs and 'id' in first_row:
                                input_refs['id'].set_value(first_row['id'])
                            if 'customer_name' in input_refs and 'customer_name' in first_row:
                                input_refs['customer_name'].set_value(first_row['customer_name'])
                            if 'email' in input_refs and 'email' in first_row:
                                input_refs['email'].set_value(first_row['email'])
                            if 'phone' in input_refs and 'phone' in first_row:
                                input_refs['phone'].set_value(first_row['phone'])
                            if 'address' in input_refs and 'address' in first_row:
                                input_refs['address'].set_value(first_row['address'])
                            if 'city' in input_refs and 'city' in first_row:
                                input_refs['city'].set_value(first_row['city'])
                            if 'state' in input_refs and 'state' in first_row:
                                input_refs['state'].set_value(first_row['state'])
                            if 'zip_code' in input_refs and 'zip_code' in first_row:
                                input_refs['zip_code'].set_value(first_row['zip_code'])
                            if 'is_active' in input_refs and 'is_active' in first_row:
                                input_refs['is_active'].set_value(first_row['is_active'])
                    
                    search_input.on('keydown.enter', lambda e: filter_rows(e.sender.value))
                
                # Bottom section - Input fields
                with main_splitter.after:
                    ui.label('Customer Details').classes('text-xl font-bold mb-2')
                    
                    # Input fields for customer data
                    with ui.row().classes('w-full mb-4'):
                        input_refs['customer_name'] = ui.input('Customer Name').classes('w-1/4 mr-2')
                        input_refs['email'] = ui.input('Email').classes('w-1/4 mr-2')
                        input_refs['phone'] = ui.input('Phone').classes('w-1/4 mr-2')
                        input_refs['address'] = ui.input('Address').classes('w-1/4 mr-2')
                        input_refs['city'] = ui.input('City').classes('w-1/4 mr-2')
                        input_refs['state'] = ui.input('State').classes('w-1/4 mr-2')
                        input_refs['zip_code'] = ui.input('Zip Code').classes('w-1/4 mr-2')
                        input_refs['is_active'] = ui.input('Is Active', value='1').classes('w-1/4 mr-2')
                        input_refs['id'] = ui.input('Customer ID').classes('w-1/4').props('readonly')

# Register the page route
@ui.page('/customers')
def customer_page_route():
    customer_page()
