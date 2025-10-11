from nicegui import ui
from connection import connection
from uiaggridtheme import uiAggridTheme
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage

def currencies_content():
    uiAggridTheme.addingtheme()

    # Store references to input fields
    input_refs = {}

    # Store the initial values for undo functionality
    initial_values = {}

    # Store row_data globally for this function
    row_data = []

    # Function to clear all input fields
    def clear_input_fields():
        input_refs['currency_code'].set_value('')
        input_refs['currency_name'].set_value('')
        input_refs['symbol'].set_value('')
        input_refs['exchange_rate'].set_value('')
        input_refs['is_active'].set_value(True)
        input_refs['id'].set_value('')
        # Dim the grid when creating new record
        table.classes('dimmed')

    # Function to save currency data
    def save_currency():
        # Get values from input fields
        currency_code = input_refs['currency_code'].value.upper()
        currency_name = input_refs['currency_name'].value
        symbol = input_refs['symbol'].value
        exchange_rate = float(input_refs['exchange_rate'].value) if input_refs['exchange_rate'].value else 1.0
        is_active = input_refs['is_active'].value
        id_value = input_refs['id'].value

        # Check if all required data is entered
        if not currency_code or not currency_name:
            ui.notify('Please enter Currency Code and Currency Name', color='red')
            return

        # Insert or update data in database using connection
        try:
            if id_value:  # Update existing record
                sql = "UPDATE currencies SET currency_code=?, currency_name=?, symbol=?, exchange_rate=?, is_active=?, updated_at=GETDATE() WHERE id=?"
                values = (currency_code, currency_name, symbol, exchange_rate, is_active, id_value)
            else:  # Insert new record
                sql = "INSERT INTO currencies (currency_code, currency_name, symbol, exchange_rate, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, GETDATE(), GETDATE())"
                values = (currency_code, currency_name, symbol, exchange_rate, is_active)

            connection.insertingtodatabase(sql, values)
            ui.notify('Currency saved successfully', color='green')
            # Remove dimming and refresh the table to show the new currency
            table.classes(remove='dimmed')
            refresh_table()
            # Update initial values
            initial_values.update({
                'currency_code': currency_code,
                'currency_name': currency_name,
                'symbol': symbol,
                'exchange_rate': str(exchange_rate),
                'is_active': is_active,
                'id': id_value
            })
        except Exception as e:
            ui.notify(f'Error saving currency: {str(e)}', color='red')

    # Function to undo changes
    def undo_changes():
        if 'currency_code' in input_refs and 'currency_code' in initial_values:
            input_refs['currency_code'].set_value(initial_values['currency_code'])
        if 'currency_name' in input_refs and 'currency_name' in initial_values:
            input_refs['currency_name'].set_value(initial_values['currency_name'])
        if 'symbol' in input_refs and 'symbol' in initial_values:
            input_refs['symbol'].set_value(initial_values['symbol'])
        if 'exchange_rate' in input_refs and 'exchange_rate' in initial_values:
            input_refs['exchange_rate'].set_value(initial_values['exchange_rate'])
        if 'is_active' in input_refs and 'is_active' in initial_values:
            input_refs['is_active'].set_value(initial_values['is_active'])
        if 'id' in input_refs and 'id' in initial_values:
            input_refs['id'].set_value(initial_values['id'])
        # Remove dimming when undoing changes
        table.classes(remove='dimmed')
        ui.notify('Changes undone', color='blue')

    # Function to delete currency
    def delete_currency():
        id_value = input_refs['id'].value
        if not id_value:
            ui.notify('Please select a currency to delete', color='red')
            return

        try:
            sql = "DELETE FROM currencies WHERE id=?"
            connection.deleterow(sql, id_value)
            ui.notify('Currency deleted successfully', color='green')
            # Remove dimming, clear input fields, and refresh the table
            table.classes(remove='dimmed')
            clear_input_fields()
            refresh_table()
        except Exception as e:
            ui.notify(f'Error deleting currency: {str(e)}', color='red')

    # Function to get the maximum currency ID
    def get_max_currency_id():
        """Get the maximum currency ID from the currencies table."""
        try:
            # Get max currency ID from database
            max_id_result = []
            connection.contogetrows("SELECT MAX(id) FROM currencies", max_id_result)

            if max_id_result and max_id_result[0][0]:
                max_id = max_id_result[0][0]
                return max_id
            else:
                return 0

        except Exception as e:
            print(f"Error getting max currency ID: {e}")
            return 0

    # Function to load the currency with maximum ID
    def load_max_currency():
        """Automatically load the currency with the maximum ID when entering the interface."""
        try:
            max_id = get_max_currency_id()
            if max_id > 0:
                # Fetch the currency data for the max ID
                currency_data = []
                connection.contogetrows(
                    f"SELECT id, currency_code, currency_name, symbol, exchange_rate, is_active FROM currencies WHERE id = {max_id}",
                    currency_data
                )

                if currency_data:
                    row_data = {
                        'id': currency_data[0][0],
                        'currency_code': currency_data[0][1],
                        'currency_name': currency_data[0][2],
                        'symbol': currency_data[0][3] if currency_data[0][3] else '',
                        'exchange_rate': str(currency_data[0][4]) if currency_data[0][4] else '1.0',
                        'is_active': bool(currency_data[0][5])
                    }

                    # Update input fields with the currency data
                    input_refs['id'].set_value(row_data['id'])
                    input_refs['currency_code'].set_value(row_data['currency_code'])
                    input_refs['currency_name'].set_value(row_data['currency_name'])
                    input_refs['symbol'].set_value(row_data['symbol'])
                    input_refs['exchange_rate'].set_value(row_data['exchange_rate'])
                    input_refs['is_active'].set_value(row_data['is_active'])

                    # Store initial values for undo functionality
                    initial_values.update({
                        'currency_code': row_data['currency_code'],
                        'currency_name': row_data['currency_name'],
                        'symbol': row_data['symbol'],
                        'exchange_rate': row_data['exchange_rate'],
                        'is_active': row_data['is_active'],
                        'id': row_data['id']
                    })

                    ui.notify(f'✅ Automatically loaded currency ID: {max_id} - {row_data["currency_code"]} - {row_data["currency_name"]}')
                else:
                    ui.notify('No currencies found in database')
            else:
                ui.notify('No currencies found in database')

        except Exception as e:
            ui.notify(f'Error loading max currency: {str(e)}')
            print(f"Error loading max currency: {e}")

    # Function to refresh the table
    def refresh_table():
        # Re-fetch data from database
        headers = []
        connection.contogetheaders("SELECT id, currency_code, currency_name, symbol, exchange_rate, is_active, created_at FROM currencies", headers)

        # Convert to AG Grid column format
        column_defs = [
            {'headerName': header.replace('_', ' ').title(), 'field': header, 'sortable': True, 'filter': True, 'width': 120}
            for header in headers
        ]

        # Fetch data from database
        data = []
        connection.contogetrows("SELECT id, currency_code, currency_name, symbol, exchange_rate, is_active, created_at FROM currencies", data)

        # Convert data to list of dictionaries for AG Grid
        nonlocal row_data
        row_data = []
        for row in data:
            row_dict = {}
            for i, header in enumerate(headers):
                if header == 'is_active':
                    row_dict[header] = bool(row[i])
                elif header == 'exchange_rate':
                    row_dict[header] = str(row[i]) if row[i] is not None else '1.0'
                else:
                    row_dict[header] = row[i]
            row_data.append(row_dict)

        # Update AG Grid with new data
        table.options['columnDefs'] = column_defs
        table.options['rowData'] = row_data
        table.update()

        # Remove dimming and clear input fields
        table.classes(remove='dimmed')
        clear_input_fields()

    # Main content area with splitter layout
    with ui.element('div').classes('flex w-full h-screen'):
        # Left drawer for action buttons
        with ui.column().classes('w-48 p-4 bg-gray-100 flex-shrink-0'):
            ui.label('Actions').classes('text-lg font-bold mb-4')
            ui.button('New', icon='add', on_click=clear_input_fields).classes('bg-blue-500 text-white w-full mb-2')
            ui.button('Save', icon='save', on_click=save_currency).classes('bg-green-500 text-white w-full mb-2')
            ui.button('Undo', icon='undo', on_click=undo_changes).classes('bg-yellow-500 text-white w-full mb-2')
            ui.button('Delete', icon='delete', on_click=delete_currency).classes('bg-red-500 text-white w-full mb-2')
            ui.button('Refresh', icon='refresh', on_click=refresh_table).classes('bg-purple-500 text-white w-full mb-2')

        # Main content area with splitter
        with ui.column().classes('flex-1 p-4 overflow-y-auto'):
            # Splitter for grid and form sections
            with ui.splitter(horizontal=True, value=40).classes('w-full h-full') as main_splitter:
                with main_splitter.separator:
                    ui.icon('drag_handle').classes('text-gray-400 text-sm')

                # Top section - Currency List Grid
                with main_splitter.before:
                    ui.label('Currency List').classes('text-xl font-bold mb-2')

                    # Search functionality
                    search_input = ui.input('Search Currencies').classes('w-full mb-2')

                    # Get column headers from database
                    headers = []
                    connection.contogetheaders("SELECT id, currency_code, currency_name, symbol, exchange_rate, is_active, created_at FROM currencies", headers)

                    # Convert to AG Grid column format
                    column_defs = [
                        {'headerName': header.replace('_', ' ').title(), 'field': header, 'sortable': True, 'filter': True, 'width': 120}
                        for header in headers
                    ]

                    # Fetch data from database
                    data = []
                    connection.contogetrows("SELECT id, currency_code, currency_name, symbol, exchange_rate, is_active, created_at FROM currencies", data)

                    # Convert data to list of dictionaries for AG Grid
                    row_data = []
                    for row in data:
                        row_dict = {}
                        for i, header in enumerate(headers):
                            if header == 'is_active':
                                row_dict[header] = bool(row[i])
                            elif header == 'exchange_rate':
                                row_dict[header] = str(row[i]) if row[i] is not None else '1.0'
                            else:
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
                                for key in input_refs:
                                    if key in selected_row:
                                        if key == 'is_active':
                                            input_refs[key].set_value(bool(selected_row[key]))
                                        elif key == 'exchange_rate':
                                            input_refs[key].set_value(str(selected_row[key]) if selected_row[key] else '1.0')
                                        else:
                                            input_refs[key].set_value(selected_row[key])
                                initial_values.update({k: v for k, v in selected_row.items() if k in input_refs})
                                ui.notify(f'Selected currency: {selected_row.get("currency_code", "")} - {selected_row.get("currency_name", "")}', color='blue')
                        except Exception as e:
                            ui.notify(f'Error selecting row: {str(e)}')
                            print(f"Error selecting row: {e}")

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
                                    if key == 'is_active':
                                        input_refs[key].set_value(bool(first_row[key]))
                                    elif key == 'exchange_rate':
                                        input_refs[key].set_value(str(first_row[key]) if first_row[key] else '1.0')
                                    else:
                                        input_refs[key].set_value(first_row[key])

                    search_input.on('keydown.enter', lambda e: filter_rows(e.sender.value))

                # Bottom section - Input fields
                with main_splitter.after:
                    ui.label('Currency Details').classes('text-xl font-bold mb-2')

                    # Input fields for currency data
                    with ui.row().classes('w-full mb-4'):
                        input_refs['currency_code'] = ui.input('Currency Code').classes('w-1/6 mr-2')
                        input_refs['currency_name'] = ui.input('Currency Name').classes('w-1/4 mr-2')
                        input_refs['symbol'] = ui.input('Symbol').classes('w-1/6 mr-2')
                        input_refs['exchange_rate'] = ui.input('Exchange Rate').classes('w-1/6 mr-2')
                        input_refs['is_active'] = ui.checkbox('Active').classes('w-1/6 mr-2')
                        input_refs['id'] = ui.input('Currency ID').classes('w-1/6').props('readonly')

                    # Automatically load the currency with max ID after UI is created
                    ui.timer(0.1, load_max_currency, once=True)

def currencies_page():
    uiAggridTheme.addingtheme()

    # Check if user is logged in
    user = session_storage.get('user')
    if not user:
        ui.notify('Please login to access this page', color='red')
        # Use timer to defer redirect to avoid AssertionError on startup
        ui.timer(0.01, lambda: ui.run_javascript('window.location.href = "/login"'), once=True)
        return

    # Get user permissions
    permissions = connection.get_user_permissions(user['role_id'])
    allowed_pages = {page for page, can_access in permissions.items() if can_access}

    # Create enhanced navigation instance
    navigation = EnhancedNavigation(permissions, user)
    navigation.create_navigation_drawer()  # Create drawer first
    navigation.create_navigation_header()  # Then create header with toggle button

    currencies_content()

# Register the page route
@ui.page('/currencies')
def currencies_page_route():
    currencies_page()
