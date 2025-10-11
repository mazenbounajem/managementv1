from nicegui import ui
from connection import connection
from uiaggridtheme import uiAggridTheme
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage

def auxiliary_page():
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
    initial_values = {'Auxiliary': None, 'name': '', 'account_number': '', 'status': 1, 'auxiliary_id': ''}

    # Flag to prevent recursive triggering
    is_updating_from_grid = False

    # Function to clear all input fields
    def clear_input_fields():
        input_refs['Auxiliary'].set_value(None)
        input_refs['name'].set_value('')
        input_refs['account_number'].set_value('')
        input_refs['status'].set_value(1)
        input_refs['update_date'].set_value('')
        input_refs['auxiliary_id'].set_value('')

    # Function to save auxiliary data
    def save_auxiliary():
        # Get values from input fields
        aux_id = input_refs['Auxiliary'].value
        name = input_refs['name'].value
        account_number = input_refs['account_number'].value
        status = input_refs['status'].value
        auxiliary_id = input_refs['auxiliary_id'].value

        # Check if all required data is entered
        if not aux_id or not name or not account_number:
            ui.notify('Please enter Ledger ID, Name and Account Number', color='red')
            return

        # Insert or update data in database using connection
        try:
            if auxiliary_id:  # Update existing record
                sql = "UPDATE auxiliary SET auxiliary_id=?, account_name=?, number=?, update_date=GETDATE(), status=? WHERE id=?"
                values = (aux_id, name, account_number, status, auxiliary_id)
            else:  # Insert new record
                sql = "INSERT INTO auxiliary (auxiliary_id, account_name, number, update_date, status) VALUES (?, ?, ?, GETDATE(), ?)"
                values = (aux_id, name, account_number, status)

            connection.insertingtodatabase(sql, values)
            ui.notify('Auxiliary saved successfully', color='green')
            # Refresh the table to show the new auxiliary
            refresh_table()
            # Update initial values
            initial_values.update({
                'Auxiliary': aux_id,
                'name': name,
                'account_number': account_number,
                'status': status,
                'auxiliary_id': auxiliary_id
            })
        except Exception as e:
            ui.notify(f'Error saving auxiliary: {str(e)}', color='red')

    # Function to undo changes
    def undo_changes():
        if 'Auxiliary' in input_refs and 'Auxiliary' in initial_values:
            input_refs['Auxiliary'].set_value(initial_values['Auxiliary'])
        if 'name' in input_refs and 'name' in initial_values:
            input_refs['name'].set_value(initial_values['name'])
        if 'account_number' in input_refs and 'account_number' in initial_values:
            input_refs['account_number'].set_value(initial_values['account_number'])
        if 'status' in input_refs and 'status' in initial_values:
            input_refs['status'].set_value(initial_values['status'])
        if 'auxiliary_id' in input_refs and 'auxiliary_id' in initial_values:
            input_refs['auxiliary_id'].set_value(initial_values['auxiliary_id'])
        ui.notify('Changes undone', color='blue')

    # Function to delete auxiliary
    def delete_auxiliary():
        auxiliary_id = input_refs['auxiliary_id'].value
        if not auxiliary_id:
            ui.notify('Please select an auxiliary to delete', color='red')
            return

        try:
            sql = "DELETE FROM auxiliary WHERE id=?"
            connection.deleterow(sql, auxiliary_id)
            ui.notify('Auxiliary deleted successfully', color='green')
            # Clear input fields
            clear_input_fields()
            # Refresh the table
            refresh_table()
        except Exception as e:
            ui.notify(f'Error deleting auxiliary: {str(e)}', color='red')

    # Function to refresh the table
    def refresh_table():
        # Re-fetch data from database
        headers = []
        connection.contogetheaders("SELECT * FROM auxiliary WHERE auxiliary_id LIKE '62%'", headers)

        # Convert to AG Grid column format
        column_defs = [
            {'headerName': header.replace('_', ' ').title(), 'field': header, 'sortable': True, 'filter': True, 'width': 120 if header != 'id' else 80}
            for header in headers
        ]
        # Hide the id column
        for col in column_defs:
            if col['field'] == 'id':
                col['hide'] = True

        # Fetch data from database
        data = []
        connection.contogetrows("SELECT * FROM auxiliary WHERE auxiliary_id LIKE '62%'", data)

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

        # Update auxiliary options

        # Update Auxiliary options
        aux_options = [row['auxiliary_id'] for row in new_row_data]
        aux_options.insert(0, None)
        input_refs['Auxiliary'].options = aux_options
        input_refs['Auxiliary'].update()

        # Clear input fields
        clear_input_fields()

    # Main content area with splitter layout
    with ui.element('div').classes('flex w-full h-screen'):
        # Left drawer for action buttons
        with ui.column().classes('w-20 p-4 bg-gray-100 flex-shrink-0'):
            
            ui.button('', icon='add', on_click=clear_input_fields).classes('w-6 h-6 mb-2').tooltip('New')
            ui.button('', icon='save', on_click=save_auxiliary).classes('w-6 h-6 mb-2').tooltip('Save')
            ui.button('', icon='undo', on_click=undo_changes).classes('w-6 h-6 mb-2').tooltip('Undo')
            ui.button('', icon='delete', on_click=delete_auxiliary).classes('w-6 h-6 mb-2').tooltip('Delete')
            ui.button('', icon='refresh', on_click=refresh_table).classes('w-6 h-6 mb-2').tooltip('Refresh')

        # Main content area with splitter
        with ui.column().classes('flex-1 p-4 overflow-y-auto'):
            # Splitter for grid and form sections
            with ui.splitter(horizontal=True, value=40).classes('w-full h-full') as main_splitter:
                with main_splitter.separator:
                    ui.icon('drag_handle').classes('text-gray-400 text-sm')

                # Top section - Auxiliary List Grid
                with main_splitter.before:
                    ui.label('Auxiliary List').classes('text-xl font-bold mb-2')

                    # Search functionality
                    search_input = ui.input('Search Auxiliaries').classes('w-full mb-2')

                    # Get column headers from database
                    headers = []
                    connection.contogetheaders("SELECT * FROM auxiliary WHERE auxiliary_id LIKE '62%'", headers)

                    # Convert to AG Grid column format
                    column_defs = [
                        {'headerName': header.replace('_', ' ').title(), 'field': header, 'sortable': True, 'filter': True, 'width': 120 if header != 'id' else 80}
                        for header in headers
                    ]
                    # Hide the id column
                    for col in column_defs:
                        if col['field'] == 'id':
                            col['hide'] = True

                    # Fetch data from database
                    data = []
                    connection.contogetrows("SELECT * FROM auxiliary WHERE auxiliary_id LIKE '62%'", data)

                    # Convert data to list of dictionaries for AG Grid
                    row_data = []
                    for row in data:
                        row_dict = {}
                        for i, header in enumerate(headers):
                            row_dict[header] = row[i]
                        row_data.append(row_dict)

                    # Function to handle row click
                    def on_row_click(event):
                        nonlocal is_updating_from_grid
                        row_data = event.args['data']
                        # Update input fields with the selected row data
                        if 'Auxiliary' in input_refs:
                            input_refs['Auxiliary'].set_value(row_data['auxiliary_id'])
                        if 'name' in input_refs and 'account_name' in row_data:
                            input_refs['name'].set_value(row_data['account_name'])
                        if 'account_number' in input_refs and 'number' in row_data:
                            input_refs['account_number'].set_value(row_data['number'])
                        if 'status' in input_refs and 'status' in row_data:
                            input_refs['status'].set_value(row_data['status'])
                        if 'update_date' in input_refs and 'update_date' in row_data:
                            input_refs['update_date'].set_value(str(row_data['update_date']))
                        if 'auxiliary_id' in input_refs and 'id' in row_data:
                            is_updating_from_grid = True
                            input_refs['auxiliary_id'].set_value(row_data['id'])
                            is_updating_from_grid = False

                        # Store initial values for undo functionality
                        initial_values.update({
                            'Auxiliary': row_data.get('auxiliary_id', None),
                            'name': row_data.get('account_name', ''),
                            'account_number': row_data.get('number', ''),
                            'status': row_data.get('status', 1),
                            'auxiliary_id': row_data.get('id', '')
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
                            if 'auxiliary_id' in input_refs and 'id' in first_row:
                                input_refs['auxiliary_id'].set_value(first_row['id'])
                            if 'Auxiliary' in input_refs and 'auxiliary_id' in first_row:
                                input_refs['Auxiliary'].set_value(first_row['auxiliary_id'])
                            if 'name' in input_refs and 'account_name' in first_row:
                                input_refs['name'].set_value(first_row['account_name'])
                            if 'account_number' in input_refs and 'number' in first_row:
                                input_refs['account_number'].set_value(first_row['number'])
                            if 'status' in input_refs and 'status' in first_row:
                                input_refs['status'].set_value(first_row['status'])

                    search_input.on('keydown.enter', lambda e: filter_rows(e.sender.value))

                # Bottom section - Input fields
                with main_splitter.after:
                    ui.label('Auxiliary Details').classes('text-xl font-bold mb-2')

                    # Fetch auxiliary options for select
                    auxdata_data = []
                    connection.contogetrows("SELECT auxiliary_id from auxiliary WHERE auxiliary_id LIKE '62%'", auxdata_data)
                    aux_options = [row[0] for row in auxdata_data]
                    aux_options.insert(0, None)

                    # Input fields for auxiliary data
                    with ui.row().classes('w-full mb-4'):
                        input_refs['Auxiliary'] = ui.select(options=aux_options, label='Auxiliary').classes('w-1/4 mr-2')
                        input_refs['name'] = ui.input('Name').classes('w-1/4 mr-2')
                        input_refs['account_number'] = ui.input('Auxiliary Number').classes('w-1/4 mr-2')
                        input_refs['status'] = ui.select(options=[0, 1], label='Status').classes('w-1/4 mr-2')
                        input_refs['update_date'] = ui.input('Update Date').classes('w-1/4 mr-2').props('readonly')
                        input_refs['auxiliary_id'] = ui.input('Auxiliary ID').props('readonly').classes('w-1/4')

# Register the page route
@ui.page('/auxiliary')
def auxiliary_page_route():
    auxiliary_page()
