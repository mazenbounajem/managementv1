from nicegui import ui
from connection import connection
from uiaggridtheme import uiAggridTheme
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage

def supplier_page():
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

    # Store references to input fields
    input_refs = {}

    # Store the initial values for undo functionality
    initial_values = {}

    # Function to get the next auxiliary number for suppliers
    def get_next_auxiliary_number_suppliers():
        try:
            data = []
            connection.contogetrows("SELECT MAX(CAST(auxiliary_number AS INT)) FROM suppliers WHERE auxiliary_id = '40111'", data)
            if data and data[0][0] is not None:
                return data[0][0] + 1
            else:
                return 1
        except Exception as e:
            print(f"Error getting next auxiliary number for suppliers: {e}")
            return 1
    
    # Function to clear all input fields
    def clear_input_fields():
        for key in input_refs:
            if key == 'id':
                input_refs[key].set_value('')
            elif key == 'is_active':
                input_refs[key].set_value(True)
            elif key == 'balance':
                input_refs[key].set_value('0.00')
            elif key == 'auxiliary_id':
                input_refs[key].set_value('40111')
            elif key == 'auxiliary_number':
                input_refs[key].set_value(f"{get_next_auxiliary_number_suppliers():05d}")
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
        auxiliary_id = input_refs['auxiliary_id'].value
        auxiliary_number = input_refs['auxiliary_number'].value
        id_value = input_refs['id'].value

        # Check if all required data is entered
        if not name:
            ui.notify('Please enter Supplier Name', color='red')
            return

        # Insert or update data in database using connection
        try:
            if id_value:  # Update existing record
                sql = """UPDATE suppliers SET name=?, contact_person=?, email=?, phone=?, address=?,
                        city=?, state=?, zip_code=?, country=?, auxiliary_id=?, auxiliary_number=?, is_active=?
                        WHERE id=?"""
                values = (name, contact_person, email, phone, address, city, state, zip_code, country, auxiliary_id, auxiliary_number, is_active, id_value)
                connection.insertingtodatabase(sql, values)
            else:  # Insert new record
                sql = """INSERT INTO suppliers (name, contact_person, email, phone, address,
                        city, state, zip_code, country, auxiliary_id, auxiliary_number, created_at, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), ?)"""
                values = (name, contact_person, email, phone, address, city, state, zip_code, country, auxiliary_id, auxiliary_number, is_active)
                connection.insertingtodatabase(sql, values)

                # Get the new supplier id
                new_id_data = []
                connection.contogetrows("SELECT @@IDENTITY", new_id_data)
                new_supplier_id = new_id_data[0][0]

                id_value = new_supplier_id

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
                'auxiliary_id': auxiliary_id,
                'auxiliary_number': auxiliary_number,
                'is_active': is_active,
                'id': id_value
            })
        except Exception as e:
            ui.notify(f'Error saving supplier: {str(e)}', color='red')
    
    # Function to undo changes
    def undo_changes():
        for key in input_refs:
            if key in initial_values:
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
    
    # Function to get the maximum supplier ID
    def get_max_supplier_id():
        """Get the maximum supplier ID from the suppliers table."""
        try:
            # Get max supplier ID from database
            max_id_result = []
            connection.contogetrows("SELECT MAX(id) FROM suppliers", max_id_result)

            if max_id_result and max_id_result[0][0]:
                max_id = max_id_result[0][0]
                return max_id
            else:
                return 0

        except Exception as e:
            print(f"Error getting max supplier ID: {e}")
            return 0

    # Function to load the supplier with maximum ID
    def load_max_supplier():
        """Automatically load the supplier with the maximum ID when entering the interface."""
        try:
            max_id = get_max_supplier_id()
            if max_id > 0:
                # Fetch the supplier data for the max ID
                supplier_data = []
                sql = """SELECT id, name, contact_person, email, phone, address, city, state, zip_code, country, balance, auxiliary_id, auxiliary_number, is_active
                         FROM suppliers WHERE id = ?"""
                connection.contogetrows(sql, [max_id], supplier_data)

                if supplier_data:
                    row_data = {
                        'id': supplier_data[0][0],
                        'name': supplier_data[0][1],
                        'contact_person': supplier_data[0][2] or '',
                        'email': supplier_data[0][3] or '',
                        'phone': supplier_data[0][4] or '',
                        'address': supplier_data[0][5] or '',
                        'city': supplier_data[0][6] or '',
                        'state': supplier_data[0][7] or '',
                        'zip_code': supplier_data[0][8] or '',
                        'country': supplier_data[0][9] or '',
                        'balance': supplier_data[0][10] or '0.00',
                        'auxiliary_id': supplier_data[0][11] or '',
                        'auxiliary_number': supplier_data[0][12] or '',
                        'is_active': bool(supplier_data[0][13])
                    }

                    # Update input fields with the supplier data
                    for key in input_refs:
                        if key in row_data:
                            input_refs[key].set_value(row_data[key])

                    # Store initial values for undo functionality
                    initial_values.update({
                        'name': row_data['name'],
                        'contact_person': row_data['contact_person'],
                        'email': row_data['email'],
                        'phone': row_data['phone'],
                        'address': row_data['address'],
                        'city': row_data['city'],
                        'state': row_data['state'],
                        'zip_code': row_data['zip_code'],
                        'country': row_data['country'],
                        'balance': row_data['balance'],
                        'auxiliary_id': row_data['auxiliary_id'],
                        'auxiliary_number': row_data['auxiliary_number'],
                        'is_active': row_data['is_active'],
                        'id': row_data['id']
                    })

                    ui.notify(f'✅ Automatically loaded supplier ID: {max_id} - {row_data["name"]}')
                else:
                    ui.notify('No suppliers found in database')
            else:
                ui.notify('No suppliers found in database')

        except Exception as e:
            ui.notify(f'Error loading max supplier: {str(e)}')
            print(f"Error loading max supplier: {e}")

    # Function to refresh the table
    def refresh_table():
        # Re-fetch data from database
        headers = []
        connection.contogetheaders("SELECT id, name, contact_person, email, phone, address, city, state, zip_code, country, balance, auxiliary_id, auxiliary_number, created_at, is_active FROM suppliers", headers)

        # Convert to AG Grid column format
        column_defs = [
            {'headerName': header.replace('_', ' ').title(), 'field': header, 'sortable': True, 'filter': True, 'width': 120}
            for header in headers
        ]

        # Fetch data from database
        data = []
        connection.contogetrows("SELECT id, name, contact_person, email, phone, address, city, state, zip_code, country, balance, auxiliary_id, auxiliary_number, created_at, is_active FROM suppliers ORDER BY id DESC", data)

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
        # Function to generate statement of account
        def generate_statement_of_account():
            supplier_id = input_refs.get('id').value if input_refs.get('id') else None
            if not supplier_id:
                ui.notify('Please select a supplier to generate statement of account', color='red')
                return

            try:
                # Get supplier name for dialog title and display
                supplier_data = []
                connection.contogetrows(f"SELECT name FROM suppliers WHERE id = {supplier_id}", supplier_data)
                supplier_name = supplier_data[0][0] if supplier_data else "Unknown Supplier"

                # Query all payments for the supplier from purchase_payment table
                payments_sql = f"""
                SELECT purchase_invoice_number, debit, credit, purchase_date, status
                FROM purchase_payment
                WHERE supplier_id = {supplier_id}
                ORDER BY purchase_date
                """
                payments_data = []
                connection.contogetrows(payments_sql, payments_data)

                # Get current supplier balance from database
                supplier_balance_data = []
                connection.contogetrows(f"SELECT balance FROM suppliers WHERE id = {supplier_id}", supplier_balance_data)
                current_balance = supplier_balance_data[0][0] if supplier_balance_data else 0

                # Calculate running balance starting from current balance
                balance = current_balance
                rows = []

                for payment in payments_data:
                    invoice_number, debit, credit, purchase_date, status = payment

                    balance += debit - credit
                    rows.append({
                        'Supplier': supplier_name,
                        'Type': f'Payment - {invoice_number}',
                        'Date': purchase_date,
                        'Debit': debit,
                        'Credit': credit,
                        'Balance': balance
                    })

                # Prepare headers
                headers = ['Supplier', 'Type', 'Date', 'Debit', 'Credit', 'Balance']

                # Create modal dialog to display statement of account
                with ui.dialog() as dialog:
                    with ui.card().classes('w-screen h-screen max-w-none max-h-none m-0 rounded-none'):
                        # Header with close button
                        with ui.row().classes('w-full justify-between items-center p-4 bg-gray-100 border-b'):
                            ui.label(f'Statement of Account - {supplier_name}').classes('text-xl font-bold')
                            ui.button('Print PDF', on_click=lambda: print_statement_pdf(supplier_id, rows)).classes('bg-blue-500 hover:bg-blue-700 text-white px-4 py-2 rounded mr-2')
                            ui.button('✕ Close', on_click=dialog.close).classes('bg-red-500 hover:bg-red-700 text-white px-4 py-2 rounded')

                        # Table display area
                        ui.table(columns=[{'name': h, 'label': h, 'field': h} for h in headers], rows=rows).classes('w-full flex-1 p-4')

                dialog.open()
                ui.notify('Statement of account generated and displayed', color='green')

            except Exception as e:
                ui.notify(f'Error generating statement of account: {str(e)}', color='red')

        # Function to print statement of account as PDF
        def print_statement_pdf(supplier_id, rows):
            try:
                import base64
                from reportlab.lib import colors
                from reportlab.lib.pagesizes import letter
                from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
                from reportlab.lib.styles import getSampleStyleSheet
                from io import BytesIO

                # Get supplier name
                supplier_data = []
                connection.contogetrows(f"SELECT name FROM suppliers WHERE id = {supplier_id}", supplier_data)
                supplier_name = supplier_data[0][0] if supplier_data else "Unknown Supplier"

                # Create PDF buffer
                buffer = BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=letter)
                elements = []

                # Styles
                styles = getSampleStyleSheet()
                title_style = styles['Heading1']

                # Title
                title = Paragraph(f"Statement of Account - {supplier_name}", title_style)
                elements.append(title)
                elements.append(Spacer(1, 12))

                # Prepare table data
                table_data = [['Supplier', 'Type', 'Date', 'Debit', 'Credit', 'Balance']]
                for row in rows:
                    table_data.append([
                        row['Supplier'],
                        row['Type'],
                        str(row['Date']),
                        f"${row['Debit']:.2f}",
                        f"${row['Credit']:.2f}",
                        f"${row['Balance']:.2f}"
                    ])

                # Create table with full width for A4
                from reportlab.lib.pagesizes import A4
                page_width, page_height = A4
                table = Table(table_data, colWidths=[page_width/len(table_data[0]) for _ in table_data[0]])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 14),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))

                elements.append(table)

                # Build PDF
                doc.build(elements)

                # Get PDF bytes
                pdf_bytes = buffer.getvalue()
                buffer.close()

                # Convert to base64 for inline display
                pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
                pdf_data_url = f"data:application/pdf;base64,{pdf_base64}"

                # Create full-screen modal dialog to display PDF
                with ui.dialog() as pdf_dialog:
                    with ui.card().classes('w-screen h-screen max-w-none max-h-none m-0 rounded-none'):
                        # Header with close button
                        with ui.row().classes('w-full justify-between items-center p-4 bg-gray-100 border-b'):
                            ui.label('Statement of Account PDF').classes('text-xl font-bold')
                            ui.button('✕ Close', on_click=pdf_dialog.close).classes('bg-red-500 hover:bg-red-700 text-white px-4 py-2 rounded')

                        # PDF display area
                        ui.html(f'''
                            <iframe src="{pdf_data_url}"
                                    width="100%"
                                    height="100%"
                                    style="border: none; min-height: calc(100vh - 80px);">
                                <p>Your browser does not support iframes.
                                <a href="{pdf_data_url}" target="_blank">Click here to view the PDF</a></p>
                            </iframe>
                        ''').classes('w-full flex-1')

                pdf_dialog.open()
                ui.notify('Statement of account PDF generated and displayed', color='green')

            except Exception as e:
                ui.notify(f'Error generating PDF: {str(e)}', color='red')

        # Left drawer for action buttons
        with ui.column().classes('w-48 p-4 bg-gray-100 flex-shrink-0'):
            ui.label('Actions').classes('text-lg font-bold mb-4')
            ui.button('New', icon='add', on_click=clear_input_fields).classes('bg-blue-500 text-white w-full mb-2')
            ui.button('Save', icon='save', on_click=save_supplier).classes('bg-green-500 text-white w-full mb-2')
            ui.button('Undo', icon='undo', on_click=undo_changes).classes('bg-yellow-500 text-white w-full mb-2')
            ui.button('Delete', icon='delete', on_click=delete_supplier).classes('bg-red-500 text-white w-full mb-2')
            ui.button('Refresh', icon='refresh', on_click=refresh_table).classes('bg-purple-500 text-white w-full mb-2')
            ui.button('Statement of Account', icon='account_balance_wallet', on_click=generate_statement_of_account).classes('bg-indigo-600 text-white w-full mb-2')
        
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
                    connection.contogetheaders("SELECT id, name, contact_person, email, phone, address, city, state, zip_code, country, balance, auxiliary_id, auxiliary_number, created_at, is_active FROM suppliers", headers)

                    # Convert to AG Grid column format
                    column_defs = [
                        {'headerName': header.replace('_', ' ').title(), 'field': header, 'sortable': True, 'filter': True, 'width': 120}
                        for header in headers
                    ]

                    # Fetch data from database
                    data = []
                    connection.contogetrows("SELECT id, name, contact_person, email, phone, address, city, state, zip_code, country, balance, auxiliary_id, auxiliary_number, created_at, is_active FROM suppliers ORDER BY id DESC", data)
                    
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
                                initial_values.update({
                                    'name': selected_row.get('name', ''),
                                    'contact_person': selected_row.get('contact_person', ''),
                                    'email': selected_row.get('email', ''),
                                    'phone': selected_row.get('phone', ''),
                                    'address': selected_row.get('address', ''),
                                    'city': selected_row.get('city', ''),
                                    'state': selected_row.get('state', ''),
                                    'zip_code': selected_row.get('zip_code', ''),
                                    'country': selected_row.get('country', ''),
                                    'balance': selected_row.get('balance', '0.00'),
                                    'auxiliary_id': selected_row.get('auxiliary_id', '40111'),
                                    'auxiliary_number': selected_row.get('auxiliary_number', '00001'),
                                    'is_active': selected_row.get('is_active', True),
                                    'id': selected_row.get('id', '')
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

                        # Hidden fields for auxiliary_id and auxiliary_number
                        input_refs['auxiliary_id'] = ui.input('Auxiliary ID').style('display: none')
                        input_refs['auxiliary_number'] = ui.input('Auxiliary Number').style('display: none')

                        # Automatically load the supplier with max ID after UI is created
                        ui.timer(0.1, load_max_supplier, once=True)

# Register the page route
@ui.page('/suppliers')
def supplier_page_route():
    supplier_page()
