from nicegui import ui
from connection import connection
from uiaggridtheme import uiAggridTheme
import datetime

def roles_page():
    uiAggridTheme.addingtheme()
    with ui.header().classes('items-center justify-between'):
        ui.label('Roles Management').classes('text-2xl font-bold')
        ui.button('Back to Dashboard', on_click=lambda: ui.navigate.to('/dashboard')).props('flat color=white')

    # Store references to input fields
    input_refs = {}
    
    # Store the initial values for undo functionality
    initial_values = {}
    
    # Available pages for permissions
    available_pages = [
        'dashboard', 'employees', 'products', 'purchase', 'reports', 'sales-reports', 'stock-reports', 'sales',
        'suppliers', 'supplierpayment', 'category', 'consignment', 'customers',
        'customerreceipt', 'expenses', 'expensestype', 'accounting', 'roles', 'timespend',
        'stockoperations', 'cash-drawer', 'currencies', 'services', 'appointments'
    ]

    # Function to clear all input fields
    def clear_input_fields():
        for key in input_refs:
            if key == 'id':
                input_refs[key].set_value('')
            elif key.startswith('permission_'):
                input_refs[key].set_value(False)
            else:
                input_refs[key].set_value('')
        # Clear all permission checkboxes
        for page in available_pages:
            checkbox_key = f'permission_{page}'
            if checkbox_key in input_refs:
                input_refs[checkbox_key].set_value(False)
        # Dim the grid when creating new record
        table.classes('dimmed')

    # Function to save role data
    def save_role():
        # Get values from input fields
        name = input_refs['name'].value
        description = input_refs['description'].value
        id_value = input_refs['id'].value
        
        # Check if required data is entered
        if not name:
            ui.notify('Role name is required', color='red')
            return
        
        # Get permissions
        permissions = {}
        for page in available_pages:
            checkbox_key = f'permission_{page}'
            if checkbox_key in input_refs:
                permissions[page] = bool(input_refs[checkbox_key].value)
        
        # Insert or update data in database using connection
        try:
            if id_value:  # Update existing record
                sql = "UPDATE roles SET name=?, description=?, updated_at=GETDATE() WHERE id=?"
                values = (name, description, id_value)
                connection.insertingtodatabase(sql, values)
                
                # Update permissions
                for page, can_access in permissions.items():
                    # Check if permission exists
                    perm_exists = connection.getrow(
                        "SELECT id FROM role_permissions WHERE role_id=? AND page_name=?",
                        (id_value, page)
                    )
                    
                    if perm_exists:
                        # Update existing permission
                        connection.insertingtodatabase(
                            "UPDATE role_permissions SET can_access=?, updated_at=GETDATE() WHERE role_id=? AND page_name=?",
                            (1 if can_access else 0, id_value, page)
                        )
                    else:
                        # Insert new permission
                        connection.insertingtodatabase(
                            "INSERT INTO role_permissions (role_id, page_name, can_access) VALUES (?, ?, ?)",
                            (id_value, page, 1 if can_access else 0)
                        )
                        
            else:  # Insert new record
                sql = "INSERT INTO roles (name, description) VALUES (?, ?)"
                values = (name, description)
                connection.insertingtodatabase(sql, values)
                
                # Get the newly created role ID
                role_id = connection.getid("SELECT id FROM roles WHERE name=?", name)
                
                if role_id:
                    # Insert permissions
                    for page, can_access in permissions.items():
                        connection.insertingtodatabase(
                            "INSERT INTO role_permissions (role_id, page_name, can_access) VALUES (?, ?, ?)",
                            (role_id, page, 1 if can_access else 0)
                        )
            
            ui.notify('Role saved successfully', color='green')
            # Remove dimming and refresh the table
            table.classes(remove='dimmed')
            refresh_table()
            # Update initial values
            initial_values.update({
                'name': name,
                'description': description,
                'id': id_value or role_id
            })
            # Store permissions in initial values
            for page, can_access in permissions.items():
                initial_values[f'permission_{page}'] = can_access
                
        except Exception as e:
            ui.notify(f'Error saving role: {str(e)}', color='red')

    # Function to undo changes
    def undo_changes():
        for key in input_refs:
            if key in initial_values:
                input_refs[key].set_value(initial_values[key])
        # Remove dimming when undoing changes
        table.classes(remove='dimmed')
        ui.notify('Changes undone', color='blue')

    # Function to delete role
    def delete_role():
        id_value = input_refs['id'].value
        if not id_value:
            ui.notify('Please select a role to delete', color='red')
            return
        
        try:
            # First delete permissions
            connection.deleterow("DELETE FROM role_permissions WHERE role_id=?", id_value)
            # Then delete the role
            connection.deleterow("DELETE FROM roles WHERE id=?", id_value)
            ui.notify('Role deleted successfully', color='green')
            # Remove dimming, clear input fields, and refresh the table
            table.classes(remove='dimmed')
            clear_input_fields()
            refresh_table()
        except Exception as e:
            ui.notify(f'Error deleting role: {str(e)}', color='red')

    # Function to refresh the table
    def refresh_table():
        # Re-fetch data from database
        headers = []
        connection.contogetheaders("SELECT id, name, description, created_at, updated_at FROM roles", headers)
        
        # Convert to AG Grid column format
        column_defs = [
            {'headerName': header.replace('_', ' ').title(), 'field': header, 'sortable': True, 'filter': True, 'width': 150}
            for header in headers
        ]
        
        # Fetch data from database
        data = []
        connection.contogetrows("SELECT id, name, description, created_at, updated_at FROM roles ORDER BY id DESC", data)
        
        # Convert data to list of dictionaries for AG Grid
        new_row_data = []
        for row in data:
            row_dict = {}
            for i, header in enumerate(headers):
                if i < len(row):
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

    # Function to load role permissions
    def load_role_permissions(role_id):
        # Clear all permission checkboxes first
        for page in available_pages:
            checkbox_key = f'permission_{page}'
            if checkbox_key in input_refs:
                input_refs[checkbox_key].set_value(False)
        
        # Load permissions from database
        permissions_data = []
        connection.contogetrows(
            "SELECT page_name, can_access FROM role_permissions WHERE role_id=?",
            permissions_data,
            (role_id,)
        )
        
        # Set permission checkboxes
        for perm in permissions_data:
            page_name = perm[0]
            can_access = bool(perm[1])
            checkbox_key = f'permission_{page_name}'
            if checkbox_key in input_refs:
                input_refs[checkbox_key].set_value(can_access)
                # Store in initial values for undo
                initial_values[checkbox_key] = can_access

    # Main content area with splitter layout
    with ui.element('div').classes('flex w-full h-screen'):
        # Left drawer for action buttons
        with ui.column().classes('w-48 p-4 bg-gray-100 flex-shrink-0'):
            ui.label('Actions').classes('text-lg font-bold mb-4')
            ui.button('New', icon='add', on_click=clear_input_fields).classes('bg-blue-500 text-white w-full mb-2')
            ui.button('Save', icon='save', on_click=save_role).classes('bg-green-500 text-white w-full mb-2')
            ui.button('Undo', icon='undo', on_click=undo_changes).classes('bg-yellow-500 text-white w-full mb-2')
            ui.button('Delete', icon='delete', on_click=delete_role).classes('bg-red-500 text-white w-full mb-2')
            ui.button('Refresh', icon='refresh', on_click=refresh_table).classes('bg-purple-500 text-white w-full mb-2')
        
        # Main content area with splitter
        with ui.column().classes('flex-1 p-4 overflow-y-auto'):
            # Splitter for grid and form sections
            with ui.splitter(horizontal=True, value=40).classes('w-full h-full') as main_splitter:
                with main_splitter.separator:
                    ui.icon('drag_handle').classes('text-gray-400 text-sm')
                
                # Top section - Roles List Grid
                with main_splitter.before:
                    ui.label('Roles List').classes('text-xl font-bold mb-2')
                    
                    # Search functionality
                    search_input = ui.input('Search Roles').classes('w-full mb-2')
                    
                    # Get column headers from database
                    headers = []
                    connection.contogetheaders("SELECT id, name, description, created_at, updated_at FROM roles", headers)
                    
                    # Convert to AG Grid column format
                    column_defs = [
                        {'headerName': header.replace('_', ' ').title(), 'field': header, 'sortable': True, 'filter': True, 'width': 150}
                        for header in headers
                    ]
                    
                    # Fetch data from database
                    data = []
                    connection.contogetrows("SELECT id, name, description, created_at, updated_at FROM roles ORDER BY id DESC", data)
                    
                    # Convert data to list of dictionaries for AG Grid
                    row_data = []
                    for row in data:
                        row_dict = {}
                        for i, header in enumerate(headers):
                            if i < len(row):
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
                                
                                # Load permissions for the selected role
                                role_id = selected_row.get('id')
                                if role_id:
                                    load_role_permissions(role_id)
                                
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
                            # Load permissions for the selected role
                            role_id = first_row.get('id')
                            if role_id:
                                load_role_permissions(role_id)
                            # Remove dimming when selecting from search results
                            table.classes(remove='dimmed')
                    
                    search_input.on('keydown.enter', lambda e: filter_rows(e.sender.value))
                
                # Bottom section - Input fields and permissions
                with main_splitter.after:
                    ui.label('Role Details').classes('text-xl font-bold mb-2')
                    
                    # Input fields for role data
                    with ui.row().classes('w-full mb-4'):
                        input_refs['id'] = ui.input('Role ID').classes('w-1/6 mr-2').props('readonly')
                        input_refs['name'] = ui.input('Role Name *').classes('w-1/3 mr-2')
                        input_refs['description'] = ui.input('Description').classes('w-1/2')
                    
                    # Permissions section
                    ui.label('Page Permissions').classes('text-lg font-semibold mb-2')
                    
                    # Create a grid for permission checkboxes
                    with ui.grid(columns=3).classes('w-full gap-2 mb-4'):
                        for page in available_pages:
                            display_name = page.replace('_', ' ').title()
                            checkbox_key = f'permission_{page}'
                            input_refs[checkbox_key] = ui.checkbox(display_name, value=False).classes('w-full')

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
        from app import session_storage
        user = session_storage.get('user')
        username = user.get('username') if user else 'Guest'
        ui.label(f'User: {username}')

# Register the page route
@ui.page('/roles')
def roles_page_route():
    # Import session functions from app.py
    from app import check_page_access, require_login

    # Check if user is logged in
    if not require_login():
        ui.notify('Please login to access this page', color='red')
        ui.run_javascript('window.location.href = "/"')
        return

    # Check if user has permission to access roles page
    if not check_page_access('roles'):
        ui.notify('You do not have permission to access this page', color='red')
        ui.run_javascript('window.location.href = "/dashboard"')
        return

    roles_page()
