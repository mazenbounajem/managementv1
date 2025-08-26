from nicegui import ui
from connection import connection
from uiaggridtheme import uiAggridTheme

def supplier_page():
    uiAggridTheme.addingtheme()
    with ui.header().classes('items-center justify-between'):
        ui.label('Supplier Management').classes('text-2xl font-bold')
        ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard')).props('flat color=white')

    # Store references to input fields
    input_refs = {}
    
    # Store the initial values for undo functionality
    initial_values = {}
    
    # Function to clear all input fields
    def clear_input_fields():
        for key in input_refs:
            if key == 'id':
                input_refs[key].set_value('')
            elif key == 'is_active':
                input_refs[key].set_value(True)
            elif key == 'balance':
                input_refs[key].set_value('0.00')
            else:
                input_refs[key].set_value('')
        # Dim the grid when creating new record
        table.classes('dimmed')
    
    # Function to save supplier data
    def save_supplier():
        # Get values from input fields
        name = input_refs['name'].value
        contact_person = input_refs['contact_person'].value
        email = input_refs['email'].value
        phone = input_refs['phone'].value
        address = input_refs['address'].value
        city = input_refs['city'].value
        state = input_refs['state'].value
        zip_code = input_refs['zip_code'].value
        country = input_refs['country'].value
        is_active = bool(input_refs['is_active'].value)
        id_value = input_refs['id'].value
        
        # Check if all required data is entered
        if not name:
            ui.notify('Please enter Supplier Name', color='red')
            return
        
        # Insert or update data in database using connection
        try:
            if id_value:  # Update existing record
                sql = """UPDATE suppliers SET name=?, contact_person=?, email=?, phone=?, address=?, 
                        city=?, state=?, zip_code=?, country=?, is_active=? 
                        WHERE id=?"""
                values = (name, contact_person, email, phone, address, city, state, zip_code, country, is_active, id_value)
            else:  # Insert new record
                sql = """INSERT INTO suppliers (name, contact_person, email, phone, address, 
                        city, state, zip_code, country, created_at, is_active) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), ?)"""
                values = (name, contact_person, email, phone, address, city, state, zip_code, country, is_active)
            
            connection.insertingtodatabase(sql, values)
            ui.notify('Supplier saved successfully', color='green')
            # Remove dimming and refresh the table to show the new supplier
            table.classes(remove='dimmed')
            refresh_table()
            # Update initial values
            initial_values.update({
                'name': name,
                'contact_person': contact_person,
                'email': email,
                'phone': phone,
                'address': address,
                'city': city,
                'state': state,
                'zip_code': zip_code,
                'country': country,
                'is_active': is_active,
                'id': id_value
            })
        except Exception as e:
            ui.notify(f'Error saving supplier: {str(e)}', color='red')
    
    # Function to undo changes
    def undo_changes():
        for key in input_refs:
            if key in initial_values:
                if key == 'id':
                    input_refs[key].set_value(initial_values[key])
                elif key == 'is_active':
                    input_refs[key].set_value(initial_values[key])
                else:
                    input_refs[key].set_value(initial_values[key])
        # Remove dimming when undoing changes
        table.classes(remove='dimmed')
        ui.notify('Changes undone', color='blue')
    
    # Function to delete supplier
    def delete_supplier():
        id_value = input_refs['id'].value
        if not id_value:
            ui.notify('Please select a supplier to delete', color='red')
            return
        
        try:
            sql = "DELETE FROM suppliers WHERE id=?"
            connection.deleterow(sql, id_value)
            ui.notify('Supplier deleted successfully', color='green')
            # Remove dimming, clear input fields, and refresh the table
            table.classes(remove='dimmed')
            clear_input_fields()
            refresh_table()
        except Exception as e:
            ui.notify(f'Error deleting supplier: {str(e)}', color='red')
    
    # Function to refresh the table
    def refresh_table():
        # Re-fetch data from database
        headers = []
        connection.contogetheaders("SELECT id, name, contact_person, email, phone, address, city, state, zip_code, country, balance, created_at, is_active FROM suppliers", headers)
        
        # Convert to AG Grid column format
        column_defs = [
            {'headerName': header.replace('_', ' ').title(), 'field': header, 'sortable': True, 'filter': True, 'width': 120}
            for header in headers
        ]
        
        # Fetch data from database
        data = []
        connection.contogetrows("SELECT id, name, contact_person, email, phone, address, city, state, zip_code, country, balance, created_at, is_active FROM suppliers ORDER BY id DESC", data)
        
        # Convert data to list of dictionaries for AG Grid
        new_row_data = []
        for row in data:
            row_dict = {}
            for i, header in enumerate(headers):
                if i < len(row):
                    if header == 'is_active':
                        row_dict[header] = bool(row[i])
                    else:
                        row_dict[header] = row[i]
                else:
                    row_dict[header] = ''
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

    # Main content area with splitter layout
    with ui.element('div').classes('flex w-full h-screen'):
        # Left drawer for action buttons
        with ui.column().classes('w-48 p-4 bg-gray-100 flex-shrink-0'):
            ui.label('Actions').classes('text-lg font-bold mb-4')
            ui.button('New', icon='add', on_click=clear_input_fields).classes('bg-blue-500 text-white w-full mb-2')
            ui.button('Save', icon='save', on_click=save_supplier).classes('bg-green-500 text-white w-full mb-2')
            ui.button('Undo', icon='undo', on_click=undo_changes).classes('bg-yellow-500 text-white w-full mb-2')
            ui.button('Delete', icon='delete', on_click=delete_supplier).classes('bg-red-500 text-white w-full mb-2')
            ui.button('Refresh', icon='refresh', on_click=refresh_table).classes('bg-purple-500 text-white w-full mb-2')
        
        # Main content area with splitter
        with ui.column().classes('flex-1 p-4 overflow-y-auto'):
            # Splitter for grid and form sections
            with ui.splitter(horizontal=True, value=40).classes('w-full h-full') as main_splitter:
                with main_splitter.separator:
                    ui.icon('drag_handle').classes('text-gray-400 text-sm')
                
                # Top section - Supplier List Grid
                with main_splitter.before:
                    ui.label('Supplier List').classes('text-xl font-bold mb-2')
                    
                    # Search functionality
                    search_input = ui.input('Search Suppliers').classes('w-full mb-2')
                    
                    # Get column headers from database
                    headers = []
                    connection.contogetheaders("SELECT id, name, contact_person, email, phone, address, city, state, zip_code, country, balance, created_at, is_active FROM suppliers", headers)
                    
                    # Convert to AG Grid column format
                    column_defs = [
                        {'headerName': header.replace('_', ' ').title(), 'field': header, 'sortable': True, 'filter': True, 'width': 120}
                        for header in headers
                    ]
                    
                    # Fetch data from database
                    data = []
                    connection.contogetrows("SELECT id, name, contact_person, email, phone, address, city, state, zip_code, country, balance, created_at, is_active FROM suppliers ORDER BY id DESC", data)
                    
                    # Convert data to list of dictionaries for AG Grid
                    row_data = []
                    for row in data:
                        row_dict = {}
                        for i, header in enumerate(headers):
                            if i < len(row):
                                if header == 'is_active':
                                    row_dict[header] = bool(row[i])
                                else:
                                    row_dict[header] = row[i]
                            else:
                                row_dict[header] = ''
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
                                
                                # Store initial values for undo functionality
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
                    ui.label('Supplier Details').classes('text-xl font-bold mb-2')
                    
                    # Input fields for supplier data
                    with ui.row().classes('w-full mb-4'):
                        input_refs['id'] = ui.input('Supplier ID').classes('w-1/6 mr-2').props('readonly')
                        input_refs['name'] = ui.input('Supplier Name *').classes('w-1/6 mr-2')
                        input_refs['contact_person'] = ui.input('Contact Person').classes('w-1/6 mr-2')
                        input_refs['email'] = ui.input('Email').classes('w-1/6 mr-2')
                        input_refs['phone'] = ui.input('Phone').classes('w-1/6 mr-2')
                    
                    with ui.row().classes('w-full mb-4'):
                        input_refs['address'] = ui.input('Address').classes('w-1/4 mr-2')
                        input_refs['city'] = ui.input('City').classes('w-1/6 mr-2')
                        input_refs['state'] = ui.input('State').classes('w-1/6 mr-2')
                        input_refs['zip_code'] = ui.input('Zip Code').classes('w-1/6 mr-2')
                        input_refs['country'] = ui.input('Country', value='USA').classes('w-1/6 mr-2')
                        input_refs['balance'] = ui.input('Balance').classes('w-1/6 mr-2')
                        input_refs['is_active'] = ui.switch('Active', value=True).classes('w-1/6')

# Register the page route
@ui.page('/suppliers')
def supplier_page_route():
    supplier_page()
