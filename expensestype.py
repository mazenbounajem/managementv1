from nicegui import ui
from connection import connection
from uiaggridtheme import uiAggridTheme
from navigation_improvements import EnhancedNavigation

def expensestype_page():
    uiAggridTheme.addingtheme()
    with ui.header().classes('items-center justify-between'):
        ui.label('Expense Types Management').classes('text-2xl font-bold')
        ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard')).props('flat color=white')

    # Store references to input fields
    input_refs = {}
    
    # Store the initial values for undo functionality
    initial_values = {}
    
    # Function to clear all input fields
    def clear_input_fields():
        input_refs['expense_type_name'].set_value('')
        input_refs['description'].set_value('')
        input_refs['id'].set_value('')
        # Dim the grid when creating new record
        table.classes('dimmed')
    
    # Function to save expense type data
    def save_expense_type():
        # Get values from input fields
        expense_type_name = input_refs['expense_type_name'].value
        description = input_refs['description'].value
        id_value = input_refs['id'].value
        
        # Check if all required data is entered
        if not expense_type_name:
            ui.notify('Please enter Expense Type Name', color='red')
            return
        
        # Insert or update data in database using connection
        try:
            if id_value:  # Update existing record
                sql = "UPDATE expense_types SET expense_type_name=?, description=? WHERE id=?"
                values = (expense_type_name, description, id_value)
            else:  # Insert new record
                sql = "INSERT INTO expense_types (expense_type_name, description, created_at) VALUES (?, ?, GETDATE())"
                values = (expense_type_name, description)
            
            connection.insertingtodatabase(sql, values)
            ui.notify('Expense type saved successfully', color='green')
            # Remove dimming and refresh the table to show the new expense type
            table.classes(remove='dimmed')
            refresh_table()
            # Update initial values
            initial_values.update({
                'expense_type_name': expense_type_name,
                'description': description,
                'id': id_value
            })
        except Exception as e:
            ui.notify(f'Error saving expense type: {str(e)}', color='red')
    
    # Function to undo changes
    def undo_changes():
        if 'expense_type_name' in input_refs and 'expense_type_name' in initial_values:
            input_refs['expense_type_name'].set_value(initial_values['expense_type_name'])
        if 'description' in input_refs and 'description' in initial_values:
            input_refs['description'].set_value(initial_values['description'])
        if 'id' in input_refs and 'id' in initial_values:
            input_refs['id'].set_value(initial_values['id'])
        # Remove dimming when undoing changes
        table.classes(remove='dimmed')
        ui.notify('Changes undone', color='blue')
    
    # Function to delete expense type
    def delete_expense_type():
        id_value = input_refs['id'].value
        if not id_value:
            ui.notify('Please select an expense type to delete', color='red')
            return
        
        try:
            sql = "DELETE FROM expense_types WHERE id=?"
            connection.deleterow(sql, id_value)
            ui.notify('Expense type deleted successfully', color='green')
            # Remove dimming, clear input fields, and refresh the table
            table.classes(remove='dimmed')
            clear_input_fields()
            refresh_table()
        except Exception as e:
            ui.notify(f'Error deleting expense type: {str(e)}', color='red')
    
    # Function to refresh the table
    def refresh_table():
        # Re-fetch data from database
        headers = []
        connection.contogetheaders("SELECT id, expense_type_name, description, created_at FROM expense_types", headers)
        
        # Convert to AG Grid column format
        column_defs = [
            {'headerName': header.replace('_', ' ').title(), 'field': header, 'sortable': True, 'filter': True, 'width': 150}
            for header in headers
        ]
        
        # Fetch data from database
        data = []
        connection.contogetrows("SELECT id, expense_type_name, description, created_at FROM expense_types", data)
        
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
        
        # Remove dimming and clear input fields
        table.classes(remove='dimmed')
        clear_input_fields()

    # Main content area with splitter layout
    with ui.element('div').classes('flex w-full h-screen'):
        # Left drawer for action buttons
        with ui.column().classes('w-48 p-4 bg-gray-100 flex-shrink-0'):
            ui.label('Actions').classes('text-lg font-bold mb-4')
            ui.button('New', icon='add', on_click=clear_input_fields).classes('bg-blue-500 text-white w-full mb-2')
            ui.button('Save', icon='save', on_click=save_expense_type).classes('bg-green-500 text-white w-full mb-2')
            ui.button('Undo', icon='undo', on_click=undo_changes).classes('bg-yellow-500 text-white w-full mb-2')
            ui.button('Delete', icon='delete', on_click=delete_expense_type).classes('bg-red-500 text-white w-full mb-2')
            ui.button('Refresh', icon='refresh', on_click=refresh_table).classes('bg-purple-500 text-white w-full mb-2')
        
        # Main content area with splitter
        with ui.column().classes('flex-1 p-4 overflow-y-auto'):
            # Splitter for grid and form sections
            with ui.splitter(horizontal=True, value=40).classes('w-full h-full') as main_splitter:
                with main_splitter.separator:
                    ui.icon('drag_handle').classes('text-gray-400 text-sm')
                
                # Top section - Expense Types List Grid
                with main_splitter.before:
                    ui.label('Expense Types List').classes('text-xl font-bold mb-2')
                    
                    # Search functionality
                    search_input = ui.input('Search Expense Types').classes('w-full mb-2')
                    
                    # Get column headers from database
                    headers = []
                    connection.contogetheaders("SELECT id, expense_type_name, description, created_at FROM expense_types", headers)
                    
                    # Convert to AG Grid column format
                    column_defs = [
                        {'headerName': header.replace('_', ' ').title(), 'field': header, 'sortable': True, 'filter': True, 'width': 150}
                        for header in headers
                    ]
                    
                    # Fetch data from database
                    data = []
                    connection.contogetrows("SELECT id, expense_type_name, description, created_at FROM expense_types", data)
                    
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
                                if 'expense_type_name' in input_refs and 'expense_type_name' in selected_row:
                                    input_refs['expense_type_name'].set_value(selected_row['expense_type_name'])
                                if 'description' in input_refs and 'description' in selected_row:
                                    input_refs['description'].set_value(selected_row['description'])
                                
                                # Store initial values for undo functionality
                                initial_values.update({
                                    'expense_type_name': input_refs['expense_type_name'].value,
                                    'description': input_refs['description'].value,
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
                            if 'expense_type_name' in input_refs and 'expense_type_name' in first_row:
                                input_refs['expense_type_name'].set_value(first_row['expense_type_name'])
                            if 'description' in input_refs and 'description' in first_row:
                                input_refs['description'].set_value(first_row['description'])
                    
                    search_input.on('keydown.enter', lambda e: filter_rows(e.sender.value))
                
                # Bottom section - Input fields
                with main_splitter.after:
                    ui.label('Expense Type Details').classes('text-xl font-bold mb-2')
                    
                    # Input fields for expense type data
                    with ui.row().classes('w-full mb-4'):
                        input_refs['expense_type_name'] = ui.input('Expense Type Name').classes('w-1/3 mr-2')
                        input_refs['description'] = ui.input('Description').classes('w-1/3 mr-2')
                        input_refs['id'] = ui.input('Expense Type ID').classes('w-1/3').props('readonly')

# Register the page route
@ui.page('/expensestype')
def expensestype_page_route():
    expensestype_page()
