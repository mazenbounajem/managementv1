from nicegui import ui
from connection import connection
from uiaggridtheme import uiAggridTheme

def employee_page():
    uiAggridTheme.addingtheme()
    with ui.header().classes('items-center justify-between'):
        ui.label('Employee Management').classes('text-2xl font-bold')
        ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard')).props('flat color=white')

    # Store references to input fields
    input_refs = {}
    
    # Store the initial values for undo functionality
    initial_values = {}
    
    # Position options
    position_options = [
        'Inventory Manager', 'Cashier', 'Store Manager', 'Sales Manager', 'Joker'
    ]
    
    # Department options
    department_options = [
        'Operations', 'Sales', 'Management', 'Marketing', 'Content Creator'
    ]
    
    # Function to clear all input fields
    def clear_input_fields():
        for key in input_refs:
            if key == 'id':
                input_refs[key].set_value('')
            elif key == 'is_active':
                input_refs[key].set_value(True)
            elif key == 'hire_date' or key == 'termination_date':
                input_refs[key].set_value('')
            elif key == 'position':
                input_refs[key].set_value(None)
            elif key == 'department':
                input_refs[key].set_value(None)
            else:
                input_refs[key].set_value('')
        # Dim the grid when creating new record
        table.classes('dimmed')
    
    # Function to save employee data
    def save_employee():
        # Get values from input fields
        first_name = input_refs['first_name'].value
        last_name = input_refs['last_name'].value
        email = input_refs['email'].value
        phone = input_refs['phone'].value
        address = input_refs['address'].value
        city = input_refs['city'].value
        state = input_refs['state'].value
        zip_code = input_refs['zip_code'].value
        hire_date = input_refs['hire_date'].value
        position = input_refs['position'].value
        department = input_refs['department'].value
        salary = input_refs['salary'].value
        role_id = input_refs['role_id'].value
        is_active = bool(input_refs['is_active'].value)
        termination_date = input_refs['termination_date'].value
        id_value = input_refs['id'].value
        
        # Check if all required data is entered
        if not first_name or not last_name:
            ui.notify('Please enter both First Name and Last Name', color='red')
            return
        
        # Insert or update data in database using connection
        try:
            if id_value:  # Update existing record
                sql = """UPDATE employees SET first_name=?, last_name=?, email=?, phone=?, address=?, 
                        city=?, state=?, zip_code=?, hire_date=?, position=?, department=?, salary=?, 
                        role_id=?, is_active=?, termination_date=?, updated_at=GETDATE() 
                        WHERE id=?"""
                values = (first_name, last_name, email, phone, address, city, state, zip_code, 
                         hire_date, position, department, salary, role_id, is_active, 
                         termination_date if termination_date else None, id_value)
            else:  # Insert new record
                sql = """INSERT INTO employees (first_name, last_name, email, phone, address, 
                        city, state, zip_code, hire_date, position, department, salary, role_id, 
                        is_active, termination_date, created_at, updated_at) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), GETDATE())"""
                values = (first_name, last_name, email, phone, address, city, state, zip_code, 
                         hire_date, position, department, salary, role_id, is_active, 
                         termination_date if termination_date else None)
            
            connection.insertingtodatabase(sql, values)
            ui.notify('Employee saved successfully', color='green')
            # Remove dimming and refresh the table to show the new employee
            table.classes(remove='dimmed')
            refresh_table()
            # Update initial values
            initial_values.update({
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'phone': phone,
                'address': address,
                'city': city,
                'state': state,
                'zip_code': zip_code,
                'hire_date': hire_date,
                'position': position,
                'department': department,
                'salary': salary,
                'role_id': role_id,
                'is_active': is_active,
                'termination_date': termination_date,
                'id': id_value
            })
        except Exception as e:
            ui.notify(f'Error saving employee: {str(e)}', color='red')
    
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
    
    # Function to delete employee
    def delete_employee():
        id_value = input_refs['id'].value
        if not id_value:
            ui.notify('Please select an employee to delete', color='red')
            return
        
        try:
            sql = "DELETE FROM employees WHERE id=?"
            connection.deleterow(sql, id_value)
            ui.notify('Employee deleted successfully', color='green')
            # Remove dimming, clear input fields, and refresh the table
            table.classes(remove='dimmed')
            clear_input_fields()
            refresh_table()
        except Exception as e:
            ui.notify(f'Error deleting employee: {str(e)}', color='red')
    
    # Function to refresh the table
    def refresh_table():
        # Re-fetch data from database
        headers = []
        connection.contogetheaders("SELECT id, first_name, last_name, email, phone, address, city, state, zip_code, hire_date, position, department, salary, role_id, is_active, termination_date, created_at, updated_at FROM employees", headers)
        
        # Convert to AG Grid column format
        column_defs = [
            {'headerName': header.replace('_', ' ').title(), 'field': header, 'sortable': True, 'filter': True, 'width': 120}
            for header in headers
        ]
        
        # Fetch data from database
        data = []
        connection.contogetrows("SELECT id, first_name, last_name, email, phone, address, city, state, zip_code, hire_date, position, department, salary, role_id, is_active, termination_date, created_at, updated_at FROM employees ORDER BY id DESC", data)
        
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
            ui.button('Save', icon='save', on_click=save_employee).classes('bg-green-500 text-white w-full mb-2')
            ui.button('Undo', icon='undo', on_click=undo_changes).classes('bg-yellow-500 text-white w-full mb-2')
            ui.button('Delete', icon='delete', on_click=delete_employee).classes('bg-red-500 text-white w-full mb-2')
            ui.button('Refresh', icon='refresh', on_click=refresh_table).classes('bg-purple-500 text-white w-full mb-2')
        
        # Main content area with splitter
        with ui.column().classes('flex-1 p-4 overflow-y-auto'):
            # Splitter for grid and form sections
            with ui.splitter(horizontal=True, value=40).classes('w-full h-full') as main_splitter:
                with main_splitter.separator:
                    ui.icon('drag_handle').classes('text-gray-400 text-sm')
                
                # Top section - Employee List Grid
                with main_splitter.before:
                    ui.label('Employee List').classes('text-xl font-bold mb-2')
                    
                    # Search functionality
                    search_input = ui.input('Search Employees').classes('w-full mb-2')
                    
                    # Get column headers from database
                    headers = []
                    connection.contogetheaders("SELECT id, first_name, last_name, email, phone, address, city, state, zip_code, hire_date, position, department, salary, role_id, is_active, termination_date, created_at, updated_at FROM employees", headers)
                    
                    # Convert to AG Grid column format
                    column_defs = [
                        {'headerName': header.replace('_', ' ').title(), 'field': header, 'sortable': True, 'filter': True, 'width': 120}
                        for header in headers
                    ]
                    
                    # Fetch data from database
                    data = []
                    connection.contogetrows("SELECT id, first_name, last_name, email, phone, address, city, state, zip_code, hire_date, position, department, salary, role_id, is_active, termination_date, created_at, updated_at FROM employees ORDER BY id DESC", data)
                    
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
                                # Remove dimming when selecting a row
                                table.classes(remove='dimmed')
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
                            # Remove dimming when selecting from search results
                            table.classes(remove='dimmed')
                    
                    search_input.on('keydown.enter', lambda e: filter_rows(e.sender.value))
                
                # Bottom section - Input fields
                with main_splitter.after:
                    ui.label('Employee Details').classes('text-xl font-bold mb-2')
                    
                    # Input fields for employee data
                    with ui.row().classes('w-full mb-4'):
                        input_refs['id'] = ui.input('Employee ID').classes('w-1/6 mr-2').props('readonly')
                        input_refs['first_name'] = ui.input('First Name *').classes('w-1/6 mr-2')
                        input_refs['last_name'] = ui.input('Last Name *').classes('w-1/6 mr-2')
                        input_refs['email'] = ui.input('Email').classes('w-1/6 mr-2')
                        input_refs['phone'] = ui.input('Phone').classes('w-1/6 mr-2')
                    
                    with ui.row().classes('w-full mb-4'):
                        input_refs['address'] = ui.input('Address').classes('w-1/3 mr-2')
                        input_refs['city'] = ui.input('City').classes('w-1/6 mr-2')
                        input_refs['state'] = ui.input('State').classes('w-1/6 mr-2')
                        input_refs['zip_code'] = ui.input('Zip Code').classes('w-1/6 mr-2')
                        
                        # Enhanced Hire Date with calendar picker
                        with ui.column().classes('w-1/6 mr-2'):
                            input_refs['hire_date'] = ui.input('Hire Date').props('readonly')
                            with ui.menu().props('no-parent-event') as hire_date_menu:
                                with ui.date().bind_value(input_refs['hire_date']):
                                    with ui.row().classes('justify-end'):
                                        ui.button('Close', on_click=hire_date_menu.close).props('flat')
                            with input_refs['hire_date'].add_slot('append'):
                                ui.icon('edit_calendar').on('click', hire_date_menu.open).classes('cursor-pointer')
                    
                    with ui.row().classes('w-full mb-4'):
                        # Enhanced Position dropdown
                        with ui.column().classes('w-1/4 mr-2'):
                            ui.label('Position')
                            input_refs['position'] = ui.select(
                                options=position_options, 
                                with_input=True,
                                on_change=lambda e: ui.notify(e.value) if e.value else None
                            ).classes('w-full')
                        
                        # Enhanced Department dropdown
                        with ui.column().classes('w-1/4 mr-2'):
                            ui.label('Department')
                            input_refs['department'] = ui.select(
                                options=department_options, 
                                with_input=True,
                                on_change=lambda e: ui.notify(e.value) if e.value else None
                            ).classes('w-full')
                        
                        input_refs['salary'] = ui.input('Salary').classes('w-1/4 mr-2')
                        input_refs['role_id'] = ui.input('Role ID').classes('w-1/4 mr-2')
                    
                    with ui.row().classes('w-full mb-4'):
                        # Enhanced Termination Date with calendar picker
                        with ui.column().classes('w-1/4 mr-2'):
                            input_refs['termination_date'] = ui.input('Termination Date').props('readonly')
                            with ui.menu().props('no-parent-event') as term_date_menu:
                                with ui.date().bind_value(input_refs['termination_date']):
                                    with ui.row().classes('justify-end'):
                                        ui.button('Close', on_click=term_date_menu.close).props('flat')
                            with input_refs['termination_date'].add_slot('append'):
                                ui.icon('edit_calendar').on('click', term_date_menu.open).classes('cursor-pointer')
                        
                        input_refs['is_active'] = ui.switch('Active', value=True).classes('w-1/4')

# Register the page route
@ui.page('/employees')
def employee_page_route():
    employee_page()
