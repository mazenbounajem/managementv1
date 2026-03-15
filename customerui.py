from nicegui import ui
from connection import connection
from modern_design_system import ModernDesignSystem as MDS
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput, ModernTable
from session_storage import session_storage
from datetime import datetime

def customer_page(standalone=False):
    # Auth
    user = session_storage.get('user')
    if not user:
        if not standalone:
            ui.notify('Please login', color='negative')
            ui.navigate.to('/login')
        return

    # State
    input_refs = {}

    def refresh_table():
        data = []
        sql = """SELECT id, customer_name, email, phone, address, city, balance, is_active 
                 FROM customers ORDER BY id DESC"""
        connection.contogetrows(sql, data)
        rows = []
        cols = ['id', 'customer_name', 'email', 'phone', 'address', 'city', 'balance', 'is_active']
        for r in data:
            rows.append({cols[i]: r[i] for i in range(len(cols))})
        table.options['rowData'] = rows
        table.update()

    def clear_inputs():
        for k, ref in input_refs.items():
            if k == 'is_active': ref.set_value(True)
            elif k == 'balance': ref.set_value(0)
            else: ref.set_value('')
        table.run_method('deselectAll')

    def save_customer():
        try:
            c_data = {k: ref.value for k, ref in input_refs.items()}
            if not c_data['customer_name']:
                return ui.notify('Customer name required', color='negative')

            if c_data['id']:
                sql = """UPDATE customers SET customer_name=?, email=?, phone=?, address=?, 
                         city=?, balance=?, is_active=? WHERE id=?"""
                params = (c_data['customer_name'], c_data['email'], c_data['phone'], c_data['address'],
                          c_data['city'], float(c_data['balance'] or 0), bool(c_data['is_active']), c_data['id'])
            else:
                sql = """INSERT INTO customers (customer_name, email, phone, address, city, balance, 
                         created_at, is_active) VALUES (?, ?, ?, ?, ?, ?, GETDATE(), ?)"""
                params = (c_data['customer_name'], c_data['email'], c_data['phone'], c_data['address'],
                          c_data['city'], float(c_data['balance'] or 0), bool(c_data['is_active']))

            connection.insertingtodatabase(sql, params)
            ui.notify('Customer saved', color='positive')
            refresh_table()
        except Exception as e:
            ui.notify(f'Error: {e}', color='negative')

    with ModernPageLayout("Customer Management"):
        with ui.column().classes('w-full gap-6 p-4 animate-fade-in'):
            
            # Action Bar
            with ModernCard().classes('w-full p-4'):
                with ui.row().classes('w-full items-center justify-between'):
                    with ui.row().classes('items-center gap-4'):
                        ui.icon('people').classes('text-3xl text-primary')
                        ui.label('Customer Network').classes('text-2xl font-black text-primary-dark')
                    
                    with ui.row().classes('gap-2'):
                        ModernButton.create('New', icon='person_add', on_click=clear_inputs, variant='primary')
                        ModernButton.create('Save', icon='save', on_click=save_customer, variant='success')

            with ui.row().classes('w-full gap-6 items-start'):
                # Form
                with ui.column().classes('w-1/3 gap-4'):
                    with ModernCard().classes('w-full p-6'):
                        ui.label('Client Details').classes('text-lg font-bold mb-4')
                        input_refs['id'] = ui.input('ID').props('readonly outlined dense').classes('hidden')
                        input_refs['customer_name'] = ModernInput('Full Name', icon='person')
                        input_refs['email'] = ModernInput('Email', icon='email')
                        input_refs['phone'] = ModernInput('Phone', icon='phone')

                    with ModernCard().classes('w-full p-6'):
                        ui.label('Profile Settings').classes('text-lg font-bold mb-4')
                        input_refs['address'] = ui.input('Address').props('outlined dense').classes('w-full')
                        input_refs['city'] = ui.input('City').props('outlined dense').classes('w-full mt-2')
                        input_refs['balance'] = ui.number('Account Balance').props('outlined dense').classes('w-full mt-2')
                        input_refs['is_active'] = ui.checkbox('Active', value=True).classes('mt-2')

                # List
                with ui.column().classes('flex-1'):
                    with ModernCard().classes('w-full p-4'):
                        ui.label('Client Repository').classes('text-lg font-bold mb-4 ml-2')
                        
                        cols = [
                            {'headerName': 'Name', 'field': 'customer_name', 'flex': 2},
                            {'headerName': 'Email', 'field': 'email', 'flex': 1.5},
                            {'headerName': 'Phone', 'field': 'phone', 'width': 130},
                            {'headerName': 'Balance', 'field': 'balance', 'width': 120},
                            {'headerName': 'Status', 'field': 'is_active', 'cellRenderer': 'agCheckboxRenderer'}
                        ]
                        
                        table = ui.aggrid({
                            'columnDefs': cols,
                            'rowData': [],
                            'defaultColDef': {'sortable': True, 'filter': True},
                            'rowSelection': 'single',
                        }).classes('w-full h-[600px] ag-theme-quartz-dark')

                        async def on_row():
                            row = await table.get_selected_row()
                            if row:
                                for k in input_refs:
                                    if k in row: input_refs[k].set_value(row[k])
                        table.on('cellClicked', on_row)

    ui.timer(0.1, refresh_table, once=True)

@ui.page('/customers')
def customer_page_route():
    customer_page()
