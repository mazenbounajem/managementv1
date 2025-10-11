from nicegui import ui
from connection import connection
from uiaggridtheme import uiAggridTheme
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage

def category_content():
    uiAggridTheme.addingtheme()

    # Store references to input fields
    input_refs = {}

    # Store the initial values for undo functionality
    initial_values = {}

    # Store row_data globally for this function
    row_data = []

    # Navigation variables
    current_index = -1
    current_highlighted_index = -1
    total_records = 0
    record_label = None
    filter_visible = False
    filter_panel = None
    filter_inputs = {}
    filter_info_button = None



    # Table reference (will be set when table is created)
    table = None

    # Function to clear all input fields
    def clear_input_fields():
        input_refs['category_name'].set_value('')
        input_refs['description'].set_value('')
        input_refs['id'].set_value('')
        # Dim the grid when creating new record
        if table:
            table.classes('dimmed')

    # Function to save category data
    def save_category():
        # Get values from input fields
        category_name = input_refs['category_name'].value
        description = input_refs['description'].value
        id_value = input_refs['id'].value

        # Check if all required data is entered
        if not category_name:
            ui.notify('Please enter Category Name', color='red')
            return

        # Insert or update data in database using connection
        try:
            if id_value:  # Update existing record
                sql = "UPDATE categories SET category_name=?, description=? WHERE id=?"
                values = (category_name, description, id_value)
            else:  # Insert new record
                sql = "INSERT INTO categories (category_name, description, created_at) VALUES (?, ?, GETDATE())"
                values = (category_name, description)

            connection.insertingtodatabase(sql, values)
            ui.notify('Category saved successfully', color='green')
            # Remove dimming and refresh the table to show the new category
            if table:
                table.classes(remove='dimmed')
            refresh_table()
            # Update initial values
            initial_values.update({
                'category_name': category_name,
                'description': description,
                'id': id_value
            })
        except Exception as e:
            ui.notify(f'Error saving category: {str(e)}', color='red')

    # Function to undo changes
    def undo_changes():
        if 'category_name' in input_refs and 'category_name' in initial_values:
            input_refs['category_name'].set_value(initial_values['category_name'])
        if 'description' in input_refs and 'description' in initial_values:
            input_refs['description'].set_value(initial_values['description'])
        if 'id' in input_refs and 'id' in initial_values:
            input_refs['id'].set_value(initial_values['id'])
        # Remove dimming when undoing changes
        if table:
            table.classes(remove='dimmed')
        ui.notify('Changes undone', color='blue')

    # Function to delete category
    def delete_category():
        id_value = input_refs['id'].value
        if not id_value:
            ui.notify('Please select a category to delete', color='red')
            return

        try:
            sql = "DELETE FROM categories WHERE id=?"
            connection.deleterow(sql, id_value)
            ui.notify('Category deleted successfully', color='green')
            # Remove dimming, clear input fields, and refresh the table
            if table:
                table.classes(remove='dimmed')
            clear_input_fields()
            refresh_table()
        except Exception as e:
            ui.notify(f'Error deleting category: {str(e)}', color='red')

    # Function to get the maximum category ID
    def get_max_category_id():
        """Get the maximum category ID from the categories table."""
        try:
            # Get max category ID from database
            max_id_result = []
            connection.contogetrows("SELECT MAX(id) FROM categories", max_id_result)

            if max_id_result and max_id_result[0][0]:
                max_id = max_id_result[0][0]
                return max_id
            else:
                return 0

        except Exception as e:
            print(f"Error getting max category ID: {e}")
            return 0

    # Function to load the category with maximum ID
    def load_max_category():
        """Automatically load the category with the maximum ID when entering the interface."""
        try:
            max_id = get_max_category_id()
            if max_id > 0:
                # Fetch the category data for the max ID
                category_data = []
                connection.contogetrows(
                    f"SELECT id, category_name, description FROM categories WHERE id = {max_id}",
                    category_data
                )

                if category_data:
                    row_data = {
                        'id': category_data[0][0],
                        'category_name': category_data[0][1],
                        'description': category_data[0][2] if category_data[0][2] else ''
                    }

                    # Update input fields with the category data
                    input_refs['id'].set_value(row_data['id'])
                    input_refs['category_name'].set_value(row_data['category_name'])
                    input_refs['description'].set_value(row_data['description'])

                    # Store initial values for undo functionality
                    initial_values.update({
                        'category_name': row_data['category_name'],
                        'description': row_data['description'],
                        'id': row_data['id']
                    })

                    ui.notify(f'✅ Automatically loaded category ID: {max_id} - {row_data["category_name"]}')
                    # Highlight the loaded row
                    highlight_loaded_row(max_id)
                else:
                    ui.notify('No categories found in database')
            else:
                ui.notify('No categories found in database')

        except Exception as e:
            ui.notify(f'Error loading max category: {str(e)}')
            print(f"Error loading max category: {e}")

    # Function to refresh the table
    def refresh_table():
        # Re-fetch data from database
        headers = []
        connection.contogetheaders("SELECT id, category_name, description, created_at FROM categories", headers)

        # Convert to AG Grid column format
        column_defs = [
            {'headerName': header.replace('_', ' ').title(), 'field': header, 'sortable': True, 'filter': True, 'width': 150}
            for header in headers
        ]

        # Fetch data from database
        data = []
        connection.contogetrows("SELECT id, category_name, description, created_at FROM categories", data)

        # Convert data to list of dictionaries for AG Grid
        nonlocal row_data
        row_data = []
        for row in data:
            row_dict = {}
            for i, header in enumerate(headers):
                row_dict[header] = row[i]
            row_data.append(row_dict)

        # Update AG Grid with new data
        if table:
            table.options['columnDefs'] = column_defs
            table.options['rowData'] = row_data
            table.update()

            # Remove dimming and clear input fields
            table.classes(remove='dimmed')
        clear_input_fields()

        # Update navigation
        nonlocal total_records, current_index
        total_records = len(row_data)
        current_index = -1
        if record_label:
            record_label.text = f'0 of {total_records} records'

        # Reset filter
        for inp in filter_inputs.values():
            inp.set_value('')
        nonlocal filter_visible
        filter_visible = False
        if filter_panel:
            filter_panel.style('display: none')

    # Helper function to manage row highlighting
    def clear_highlights():
        """Clear all row highlights"""
        if table:
            for row in table.options['rowData']:
                row['highlighted'] = False

    def set_highlight(index):
        """Set highlight for a specific row index"""
        if table and 0 <= index < len(table.options['rowData']):
            table.options['rowData'][index]['highlighted'] = True

    def highlight_loaded_row(record_id):
        """Highlight the row with the specified record ID"""
        if table:
            for i, row in enumerate(table.options['rowData']):
                if row.get('id') == record_id:
                    clear_highlights()
                    set_highlight(i)
                    nonlocal current_index
                    current_index = i
                    table.update()
                    record_label.text = f'{current_index + 1} of {len(table.options["rowData"])} records'
                    break

    # Navigation functions
    def first_record():
        nonlocal current_index
        if table:
            current_row_data = table.options['rowData']
            if len(current_row_data) > 0:
                current_index = 0
                clear_highlights()
                set_highlight(current_index)
                selected_row = current_row_data[current_index]
                # Set inputs
                for key in input_refs:
                    if key in selected_row:
                        input_refs[key].set_value(selected_row[key])
                # Store initial values
                initial_values.update({
                    'category_name': selected_row.get('category_name', ''),
                    'description': selected_row.get('description', ''),
                    'id': selected_row.get('id', '')
                })
                # Scroll to row
                table.run_method('ensureIndexVisible', current_index)
                table.update()
                record_label.text = f'{current_index + 1} of {len(current_row_data)} records'

    def prev_10():
        nonlocal current_index
        if table:
            current_row_data = table.options['rowData']
            new_index = max(0, current_index - 10)
            if new_index != current_index:
                current_index = new_index
                clear_highlights()
                set_highlight(current_index)
                selected_row = current_row_data[current_index]
                # Set inputs
                for key in input_refs:
                    if key in selected_row:
                        input_refs[key].set_value(selected_row[key])
                # Store initial values
                initial_values.update({
                    'category_name': selected_row.get('category_name', ''),
                    'description': selected_row.get('description', ''),
                    'id': selected_row.get('id', '')
                })
                # Scroll to row
                table.run_method('ensureIndexVisible', current_index)
                table.update()
                record_label.text = f'{current_index + 1} of {len(current_row_data)} records'

    def prev_record():
        nonlocal current_index
        if table:
            current_row_data = table.options['rowData']
            if current_index > 0:
                current_index -= 1
                clear_highlights()
                set_highlight(current_index)
                selected_row = current_row_data[current_index]
                # Set inputs
                for key in input_refs:
                    if key in selected_row:
                        input_refs[key].set_value(selected_row[key])
                # Store initial values
                initial_values.update({
                    'category_name': selected_row.get('category_name', ''),
                    'description': selected_row.get('description', ''),
                    'id': selected_row.get('id', '')
                })
                # Scroll to row
                table.run_method('ensureIndexVisible', current_index)
                table.update()
                record_label.text = f'{current_index + 1} of {len(current_row_data)} records'

    def next_record():
        nonlocal current_index
        if table:
            current_row_data = table.options['rowData']
            if current_index < len(current_row_data) - 1:
                current_index += 1
                clear_highlights()
                set_highlight(current_index)
                selected_row = current_row_data[current_index]
                # Set inputs
                for key in input_refs:
                    if key in selected_row:
                        input_refs[key].set_value(selected_row[key])
                # Store initial values
                initial_values.update({
                    'category_name': selected_row.get('category_name', ''),
                    'description': selected_row.get('description', ''),
                    'id': selected_row.get('id', '')
                })
                # Scroll to row
                table.run_method('ensureIndexVisible', current_index)
                table.update()
                record_label.text = f'{current_index + 1} of {len(current_row_data)} records'

    def next_10():
        nonlocal current_index
        if table:
            current_row_data = table.options['rowData']
            new_index = min(len(current_row_data) - 1, current_index + 10)
            if new_index != current_index:
                current_index = new_index
                clear_highlights()
                set_highlight(current_index)
                selected_row = current_row_data[current_index]
                # Set inputs
                for key in input_refs:
                    if key in selected_row:
                        input_refs[key].set_value(selected_row[key])
                # Store initial values
                initial_values.update({
                    'category_name': selected_row.get('category_name', ''),
                    'description': selected_row.get('description', ''),
                    'id': selected_row.get('id', '')
                })
                # Scroll to row
                table.run_method('ensureIndexVisible', current_index)
                table.update()
                record_label.text = f'{current_index + 1} of {len(current_row_data)} records'

    def last_record():
        nonlocal current_index
        if table:
            current_row_data = table.options['rowData']
            if len(current_row_data) > 0:
                current_index = len(current_row_data) - 1
                clear_highlights()
                set_highlight(current_index)
                selected_row = current_row_data[current_index]
                # Set inputs
                for key in input_refs:
                    if key in selected_row:
                        input_refs[key].set_value(selected_row[key])
                # Store initial values
                initial_values.update({
                    'category_name': selected_row.get('category_name', ''),
                    'description': selected_row.get('description', ''),
                    'id': selected_row.get('id', '')
                })
                # Scroll to row
                table.run_method('ensureIndexVisible', current_index)
                table.update()
                record_label.text = f'{current_index + 1} of {len(current_row_data)} records'

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
        table.update()
        # Reset current_index
        nonlocal current_index
        current_index = -1
        record_label.text = f'0 of {len(table.options["rowData"])} records'
        if filter_info_button:
            filter_info_button.style('display: none;')

    # Main content area with splitter layout
    with ui.element('div').classes('flex w-full h-screen'):
        # Left drawer for action buttons
        with ui.column().classes('w-20 p-4 bg-gray-100 flex-shrink-0'):
            ui.label('Actions').classes('text-lg font-bold mb-4')
            ui.button('', icon='add', on_click=clear_input_fields).classes('bg-blue-500 text-white w-full mb-2').tooltip('Add new category')
            ui.button('', icon='save', on_click=save_category).classes('bg-green-500 text-white w-full mb-2').tooltip('Save category changes')
            ui.button('', icon='undo', on_click=undo_changes).classes('bg-yellow-500 text-white w-full mb-2').tooltip('Undo changes')
            ui.button('', icon='delete', on_click=delete_category).classes('bg-red-500 text-white w-full mb-2').tooltip('Delete selected category')
            ui.button('', icon='refresh', on_click=refresh_table).classes('bg-purple-500 text-white w-full mb-2').tooltip('Refresh table data')

        # Main content area with splitter
        with ui.column().classes('flex-1 p-4 overflow-y-auto'):
            # Splitter for grid and form sections
            with ui.splitter(horizontal=True, value=20).classes('w-full h-full') as main_splitter:
                with main_splitter.separator:
                    ui.icon('drag_handle').classes('text-gray-400 text-sm')

                # Top section - Category List Grid
                with main_splitter.before:
                    #ui.label('Category List').classes('text-xl font-bold mb-2')

                    # Container for table and navigation buttons
                    with ui.element('div').classes('relative w-full'):
                        # Navigation buttons positioned absolutely over the table
                        with ui.row().classes(' top--20 left-0 z-5 items-center gap-1').style('height: 25px; background: transparent; padding: 2px;'):
                            ui.button('', icon='first_page', on_click=first_record).classes('bg-blue-500 hover:bg-blue-700 text-white px-2 py-1 text-xs rounded').tooltip('Go to first record')
                            ui.button('', icon='skip_previous', on_click=prev_10).classes('bg-blue-500 hover:bg-blue-700 text-white px-2 py-1 text-xs rounded').tooltip('Go to previous 10 records')
                            ui.button('', icon='chevron_left', on_click=prev_record).classes('bg-blue-500 hover:bg-blue-700 text-white px-2 py-1 text-xs rounded').tooltip('Go to previous record')
                            record_label = ui.label('0 of 0 records').classes('text-xs text-gray-600')
                            ui.button('', icon='chevron_right', on_click=next_record).classes('bg-blue-500 hover:bg-blue-700 text-white px-2 py-1 text-xs rounded').tooltip('Go to next record')
                            ui.button('', icon='skip_next', on_click=next_10).classes('bg-blue-500 hover:bg-blue-700 text-white px-2 py-1 text-xs rounded').tooltip('Go to next 10 records')
                            ui.button('', icon='last_page', on_click=last_record).classes('bg-blue-500 hover:bg-blue-700 text-white px-2 py-1 text-xs rounded').tooltip('Go to last record')
                            search_input = ui.input('Search Categories').classes('w-46')

                    # Get column headers from database
                    headers = []
                    connection.contogetheaders("SELECT id, category_name, description, created_at FROM categories", headers)

                    # Convert to AG Grid column format
                    column_defs = [
                        {'headerName': header.replace('_', ' ').title(), 'field': header, 'sortable': True, 'filter': True, 'width': 150}
                        for header in headers
                    ]

                    # Fetch data from database
                    data = []
                    connection.contogetrows("SELECT id, category_name, description, created_at FROM categories", data)

                    # Convert data to list of dictionaries for AG Grid
                    row_data = []
                    for row in data:
                        row_dict = {}
                        for i, header in enumerate(headers):
                            row_dict[header] = row[i]
                        row_dict['highlighted'] = False
                        row_data.append(row_dict)

                    # Create AG Grid table with scroll functionality
                    table = ui.aggrid({
                        'columnDefs': column_defs,
                        'rowData': row_data,
                        'defaultColDef': {'flex': 1, 'minWidth': 100, 'sortable': True, 'filter': True},
                        'rowSelection': 'single',
                        'domLayout': 'normal',
                        'pagination': False,
                        
                        'rowClassRules': {
                            'highlighted-row': 'data.highlighted'
                        }
                    }).classes('w-full ag-theme-quartz-custom').style('height: 200px; overflow-y: auto;')

                    # Add CSS for highlighted row
                    ui.add_css('''
                        .ag-theme-quartz-custom .highlighted-row {
                            background-color: #1976D2 !important;
                            color: #ffffff !important;
                            border: 2px solid #0d47a1 !important;
                        }
                    ''')

                    # Initialize selection and navigation if data exists
                    if row_data:
                        current_index = 0
                        clear_highlights()
                        set_highlight(current_index)
                        first_row = row_data[0]
                        for key in input_refs:
                            if key in first_row:
                                input_refs[key].set_value(first_row[key])
                        if record_label:
                            record_label.text = f'1 of {len(row_data)} records'

                    # Add row selection functionality for AG Grid
                    async def on_row_click():
                        try:
                            selected_row = await table.get_selected_row()
                            if selected_row:
                                # Find the index of the selected row
                                nonlocal current_index
                                for i, row in enumerate(table.options['rowData']):
                                    if row.get('id') == selected_row.get('id'):
                                        current_index = i
                                        break
                                # Clear previous highlights and set new highlight
                                clear_highlights()
                                set_highlight(current_index)
                                table.update()
                                # Set inputs
                                for key in input_refs:
                                    if key in selected_row:
                                        input_refs[key].set_value(selected_row[key])
                                initial_values.update({k: v for k, v in selected_row.items() if k in input_refs})
                                record_label.text = f'{current_index + 1} of {len(table.options["rowData"])} records'
                                ui.notify(f'Selected category: {selected_row.get("category_name", "")}', color='blue')
                        except Exception as e:
                            ui.notify(f'Error selecting row: {str(e)}')
                            print(f"Error selecting row: {e}")

                    table.on('cellClicked', on_row_click)

                    # Add filter changed event handler
                    def on_filter_changed():
                        nonlocal current_index
                        current_index = -1
                        record_label.text = f'0 of {len(table.options["rowData"])} records'

                    table.on('filterChanged', on_filter_changed)

                    # Event listener for filter changes to show clear button
                    import asyncio
                    filter_change_task = None

                    async def on_filter_changed_async():
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
                                        if filter_info_button:
                                            filter_info_button.style('display: flex;')
                                            filter_info_button.text = ' ✕ '.join(filter_texts) + ' ✕'
                                    else:
                                        if filter_info_button:
                                            filter_info_button.style('display: none;')
                                else:
                                    if filter_info_button:
                                        filter_info_button.style('display: none;')
                            except asyncio.CancelledError:
                                pass
                            except asyncio.TimeoutError:
                                # Keep the button visible with "Filters active" if detailed info fails
                                if filter_info_button:
                                    filter_info_button.style('display: flex;')
                                    filter_info_button.text = 'Filters active ✕'
                            except Exception as e:
                                # Keep the button visible with "Filters active" if detailed info fails
                                if filter_info_button:
                                    filter_info_button.style('display: flex;')
                                    filter_info_button.text = 'Filters active ✕'
                        filter_change_task = asyncio.create_task(handle_filter_change())

                    table.on('filterChanged', on_filter_changed_async)

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

                        # Reset navigation for filtered results
                        nonlocal current_index
                        current_index = -1
                        record_label.text = f'0 of {len(table.options["rowData"])} records'

                        # Select the first row of the filtered results if available
                        if table.options['rowData']:
                            first_row = table.options['rowData'][0]
                            for key in input_refs:
                                if key in first_row:
                                    input_refs[key].set_value(first_row[key])

                    search_input.on('keydown.enter', lambda e: filter_rows(e.sender.value))

                # Bottom section - Input fields
                with main_splitter.after:
                    
                    filter_info_button = ui.button('✕ Clear Filter', on_click=clear_filters).classes('bg-red-500 hover:bg-red-700 text-white text-xs px-2 py-1 rounded').style('display: none;')
                    ui.label('Category Details').classes('text-xl font-bold mb-2')
                    # Input fields for category data
                    with ui.row().classes('w-full mb-4'):
                        input_refs['category_name'] = ui.input('Category Name').classes('w-1/3 mr-2')
                        input_refs['description'] = ui.input('Description').classes('w-1/3 mr-2')
                        input_refs['id'] = ui.input('Category ID').classes('w-1/3').props('readonly')

                    # Filter info button
                   
                    # Automatically load the category with max ID after UI is created
                    ui.timer(0.1, load_max_category, once=True)

def category_page():
    uiAggridTheme.addingtheme()

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

    category_content()

# Register the page route
@ui.page('/category')
def category_page_route():
    category_page()
