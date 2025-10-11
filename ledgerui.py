from nicegui import ui
from connection import connection
from uiaggridtheme import uiAggridTheme
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage

def ledger_page():
    uiAggridTheme.addingtheme()

    # Check if user is logged in
    user = session_storage.get('user')
    if not user:
        ui.notify('Please login to access this page', color='red')
        # Use a timer to delay the redirect to avoid startup issues
        ui.timer(0.1, lambda: ui.run_javascript('window.location.href = "/login"'), once=True)
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
    
    # Function to clear all input fields
    def clear_input_fields():
        input_refs['account_number'].set_value('')
        input_refs['sub_number'].set_value('')
        input_refs['parent_id'].set_value(None)
        input_refs['name_en'].set_value('')
        input_refs['name_fr'].set_value('')
        input_refs['name_ar'].set_value('')
        input_refs['status'].set_value(1)
        input_refs['update_date'].set_value('')
        input_refs['id'].set_value('')
    
    # Function to save ledger data
    def save_ledger():
        # Get values from input fields
        account_number = input_refs['account_number'].value
        sub_number = input_refs['sub_number'].value
        parent_id = input_refs['parent_id'].value
        name_en = input_refs['name_en'].value
        name_fr = input_refs['name_fr'].value
        name_ar = input_refs['name_ar'].value
        status = input_refs['status'].value
        id_value = input_refs['id'].value
        
        # Check if all required data is entered
        if not account_number or not name_en:
            ui.notify('Please enter Account Number and English Name', color='red')
            return
        
        # Insert or update data in database using connection
        try:
            if id_value:  # Update existing record
                sql = "UPDATE Ledger SET AccountNumber=?, SubNumber=?, ParentId=?, Name_en=?, Name_fr=?, Name_ar=?, UpdateDate=GETDATE(), Status=? WHERE Id=?"
                values = (account_number, sub_number, parent_id, name_en, name_fr, name_ar, status, id_value)
            else:  # Insert new record
                sql = "INSERT INTO Ledger (AccountNumber, SubNumber, ParentId, Name_en, Name_fr, Name_ar, UpdateDate, Status) VALUES (?, ?, ?, ?, ?, ?, GETDATE(), ?)"
                values = (account_number, sub_number, parent_id, name_en, name_fr, name_ar, status)
            
            connection.insertingtodatabase(sql, values)
            ui.notify('Ledger saved successfully', color='green')
            # Refresh the table to show the new ledger
            refresh_table()
            # Update initial values
            initial_values.update({
                'account_number': account_number,
                'sub_number': sub_number,
                'parent_id': parent_id,
                'name_en': name_en,
                'name_fr': name_fr,
                'name_ar': name_ar,
                'status': status,
                'id': id_value
            })
        except Exception as e:
            ui.notify(f'Error saving ledger: {str(e)}', color='red')
    
    # Function to undo changes
    def undo_changes():
        if 'account_number' in input_refs and 'account_number' in initial_values:
            input_refs['account_number'].set_value(initial_values['account_number'])
        if 'sub_number' in input_refs and 'sub_number' in initial_values:
            input_refs['sub_number'].set_value(initial_values['sub_number'])
        if 'parent_id' in input_refs and 'parent_id' in initial_values:
            input_refs['parent_id'].set_value(initial_values['parent_id'])
        if 'name_en' in input_refs and 'name_en' in initial_values:
            input_refs['name_en'].set_value(initial_values['name_en'])
        if 'name_fr' in input_refs and 'name_fr' in initial_values:
            input_refs['name_fr'].set_value(initial_values['name_fr'])
        if 'name_ar' in input_refs and 'name_ar' in initial_values:
            input_refs['name_ar'].set_value(initial_values['name_ar'])
        if 'status' in input_refs and 'status' in initial_values:
            input_refs['status'].set_value(initial_values['status'])
        if 'id' in input_refs and 'id' in initial_values:
            input_refs['id'].set_value(initial_values['id'])
        ui.notify('Changes undone', color='blue')
    
    # Function to delete ledger
    def delete_ledger():
        id_value = input_refs['id'].value
        if not id_value:
            ui.notify('Please select a ledger to delete', color='red')
            return
        
        try:
            sql = "DELETE FROM Ledger WHERE Id=?"
            connection.deleterow(sql, id_value)
            ui.notify('Ledger deleted successfully', color='green')
            # Clear input fields
            clear_input_fields()
            # Refresh the table
            refresh_table()
        except Exception as e:
            ui.notify(f'Error deleting ledger: {str(e)}', color='red')
    


    # Function to refresh the table
    def refresh_table():
        # Re-fetch data from database
        headers = []
        connection.contogetheaders("SELECT Id, AccountNumber, SubNumber, ParentId, Name_en, Name_fr, Name_ar, UpdateDate, Status FROM Ledger", headers)

        # Convert to AG Grid column format
        column_defs = [
            {'headerName': header.replace('_', ' ').title(), 'field': header, 'sortable': True, 'filter': True, 'width': 120}
            for header in headers
        ]

        # Fetch data from database
        data = []
        connection.contogetrows("SELECT Id, AccountNumber, SubNumber, ParentId, Name_en, Name_fr, Name_ar, UpdateDate, Status FROM Ledger", data)

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
            ui.button('Save', icon='save', on_click=save_ledger).classes('bg-green-500 text-white w-full mb-2')
            ui.button('Undo', icon='undo', on_click=undo_changes).classes('bg-yellow-500 text-white w-full mb-2')
            ui.button('Delete', icon='delete', on_click=delete_ledger).classes('bg-red-500 text-white w-full mb-2')
            ui.button('Refresh', icon='refresh', on_click=refresh_table).classes('bg-purple-500 text-white w-full mb-2')

        # Main content area with splitter
        with ui.column().classes('flex-1 p-4 overflow-y-auto'):
            # Splitter for grid and form sections
            with ui.splitter(horizontal=True, value=40).classes('w-full h-full') as main_splitter:
                with main_splitter.separator:
                    ui.icon('drag_handle').classes('text-gray-400 text-sm')

                # Top section - Ledger List Grid
                with main_splitter.before:
                    ui.label('Ledger List').classes('text-xl font-bold mb-2')

                    # Search functionality
                    search_input = ui.input('Search Ledgers').classes('w-full mb-2')

                    # Get column headers from database
                    headers = []
                    connection.contogetheaders("SELECT Id, AccountNumber, SubNumber, ParentId, Name_en, Name_fr, Name_ar, UpdateDate, Status FROM Ledger", headers)

                    # Convert to AG Grid column format
                    column_defs = [
                        {'headerName': header.replace('_', ' ').title(), 'field': header, 'sortable': True, 'filter': True, 'width': 120}
                        for header in headers
                    ]

                    # Fetch data from database
                    data = []
                    connection.contogetrows("SELECT Id, AccountNumber, SubNumber, ParentId, Name_en, Name_fr, Name_ar, UpdateDate, Status FROM Ledger", data)

                    # Convert data to list of dictionaries for AG Grid
                    row_data = []
                    for row in data:
                        row_dict = {}
                        for i, header in enumerate(headers):
                            row_dict[header] = row[i]
                        row_data.append(row_dict)

                    # Function to handle row click
                    def on_row_click(event):
                        row_data = event.args['data']
                        # Update input fields with the selected row data
                        if 'account_number' in input_refs and 'AccountNumber' in row_data:
                            input_refs['account_number'].set_value(row_data['AccountNumber'])
                        if 'sub_number' in input_refs and 'SubNumber' in row_data:
                            input_refs['sub_number'].set_value(row_data['SubNumber'])
                        if 'parent_id' in input_refs and 'ParentId' in row_data:
                            input_refs['parent_id'].set_value(row_data['ParentId'])
                        if 'name_en' in input_refs and 'Name_en' in row_data:
                            input_refs['name_en'].set_value(row_data['Name_en'])
                        if 'name_fr' in input_refs and 'Name_fr' in row_data:
                            input_refs['name_fr'].set_value(row_data['Name_fr'])
                        if 'name_ar' in input_refs and 'Name_ar' in row_data:
                            input_refs['name_ar'].set_value(row_data['Name_ar'])
                        if 'status' in input_refs and 'Status' in row_data:
                            input_refs['status'].set_value(row_data['Status'])
                        if 'update_date' in input_refs and 'UpdateDate' in row_data:
                            input_refs['update_date'].set_value(str(row_data['UpdateDate']))
                        if 'id' in input_refs and 'Id' in row_data:
                            input_refs['id'].set_value(row_data['Id'])

                        # Store initial values for undo functionality
                        initial_values.update({
                            'account_number': row_data.get('AccountNumber', ''),
                            'sub_number': row_data.get('SubNumber', ''),
                            'parent_id': row_data.get('ParentId', None),
                            'name_en': row_data.get('Name_en', ''),
                            'name_fr': row_data.get('Name_fr', ''),
                            'name_ar': row_data.get('Name_ar', ''),
                            'status': row_data.get('Status', 1),
                            'id': row_data.get('Id', '')
                        })

                    # Create AG Grid table with scroll functionality
                    table = ui.aggrid({
                        'columnDefs': column_defs,
                        'rowData': row_data,
                        'defaultColDef': {'flex': 1, 'minWidth': 100, 'sortable': True, 'filter': True},
                        'rowSelection': 'single',
                        'domLayout': 'normal'
                    }).classes('w-full ag-theme-quartz-custom').style('height: 250px; overflow-y: auto;')

                    # Add row click event handler
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
                            if 'id' in input_refs and 'Id' in first_row:
                                input_refs['id'].set_value(first_row['Id'])
                            if 'account_number' in input_refs and 'AccountNumber' in first_row:
                                input_refs['account_number'].set_value(first_row['AccountNumber'])
                            if 'sub_number' in input_refs and 'SubNumber' in first_row:
                                input_refs['sub_number'].set_value(first_row['SubNumber'])
                            if 'parent_id' in input_refs and 'ParentId' in first_row:
                                input_refs['parent_id'].set_value(first_row['ParentId'])
                            if 'name_en' in input_refs and 'Name_en' in first_row:
                                input_refs['name_en'].set_value(first_row['Name_en'])
                            if 'name_fr' in input_refs and 'Name_fr' in first_row:
                                input_refs['name_fr'].set_value(first_row['Name_fr'])
                            if 'name_ar' in input_refs and 'Name_ar' in first_row:
                                input_refs['name_ar'].set_value(first_row['Name_ar'])
                            if 'status' in input_refs and 'Status' in first_row:
                                input_refs['status'].set_value(first_row['Status'])

                    search_input.on('keydown.enter', lambda e: filter_rows(e.sender.value))

                # Bottom section - Input fields
                with main_splitter.after:
                    ui.label('Ledger Details').classes('text-xl font-bold mb-2')

                    # Fetch parent options from ledgers table
                    parent_options = []
                    try:
                        # Fetch ledger data for parent selection
                        ledger_data = []
                        connection.contogetrows("SELECT Id, Name_en FROM ledgers WHERE Status = 1 ORDER BY Name_en", ledger_data)

                        # Create options with ledger names and IDs
                        parent_options = [{'label': f"{row[1]} (ID: {row[0]})", 'value': row[0]} for row in ledger_data]
                        parent_options.insert(0, {'label': 'None', 'value': None})
                    except Exception as e:
                        print(f"Error fetching ledger options: {e}")
                        # Fallback to basic options if there's an error
                        parent_options = [{'label': 'None', 'value': None}]

                    # Input fields for ledger data
                    with ui.row().classes('w-full mb-4'):
                        input_refs['account_number'] = ui.input('Account Number').classes('w-1/4 mr-2')
                        input_refs['sub_number'] = ui.input('Sub Number').classes('w-1/4 mr-2')
                        input_refs['parent_id'] = ui.select(options=parent_options, label='Parent ID').classes('w-1/4 mr-2')
                        input_refs['name_en'] = ui.input('Name (EN)').classes('w-1/4 mr-2')
                        input_refs['name_fr'] = ui.input('Name (FR)').classes('w-1/4 mr-2')
                        input_refs['name_ar'] = ui.input('Name (AR)').classes('w-1/4 mr-2')
                        input_refs['status'] = ui.select(options=[0, 1], label='Status').classes('w-1/4 mr-2')
                        input_refs['update_date'] = ui.input('Update Date').classes('w-1/4 mr-2').props('readonly')
                        input_refs['id'] = ui.input('Ledger ID').classes('w-1/4').props('readonly')

# Register the page route
@ui.page('/ledger')
def ledger_page_route():
    ledger_page()
