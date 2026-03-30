from nicegui import ui
from connection import connection
from modern_design_system import ModernDesignSystem as MDS
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput, ModernTable
from session_storage import session_storage
from datetime import datetime

def supplier_page(standalone=False):
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
        sql = """
            SELECT 
                s.id, s.name, s.contact_person, s.email, s.phone, s.address, s.city, 
                s.balance as balance_ll, s.balance_usd,
                ISNULL(SUM(CASE WHEN p.payment_status = 'pending' THEN p.total_amount ELSE 0 END), 0) as pending_invoices,
                s.is_active 
            FROM suppliers s 
            LEFT JOIN purchases p ON p.supplier_id = s.id
            GROUP BY s.id, s.name, s.contact_person, s.email, s.phone, s.address, s.city, s.balance, s.balance_usd, s.is_active 
            ORDER BY s.id DESC
        """
        connection.contogetrows(sql, data)
        rows = []
        cols = ['id', 'name', 'contact', 'email', 'phone', 'address', 'city', 'balance_ll', 'balance_usd', 'is_active']
        for r in data:
            usd_rate_data = []
            connection.contogetrows("SELECT TOP 1 exchange_rate FROM currencies WHERE symbol = '$'", usd_rate_data)
            usd_rate = usd_rate_data[0][0] if usd_rate_data else 1.0
            
            row_dict = {cols[i]: r[i] for i in range(len(cols))}
            rows.append(row_dict)
        table.options['rowData'] = rows
        table.update()

    def clear_inputs():
        for k, ref in input_refs.items():
            if k == 'is_active': ref.set_value(True)
            elif k == 'balance': ref.set_value(0)
            else: ref.set_value('')
        table.run_method('deselectAll')

    def save_supplier():
        try:
            s_data = {k: ref.value for k, ref in input_refs.items()}
            if not s_data['name']:
                return ui.notify('Name required', color='negative')

            if s_data['id']:
                sql = """UPDATE suppliers SET name=?, contact_person=?, email=?, phone=?, 
                         address=?, city=?, balance=?, is_active=? WHERE id=?"""
                params = (s_data['name'], s_data['contact'], s_data['email'], s_data['phone'],
                          s_data['address'], s_data['city'], float(s_data['balance'] or 0),
                          bool(s_data['is_active']), s_data['id'])
            else:
                sql = """INSERT INTO suppliers (name, contact_person, email, phone, address, city, 
                         balance, created_at, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, GETDATE(), ?)"""
                params = (s_data['name'], s_data['contact'], s_data['email'], s_data['phone'],
                          s_data['address'], s_data['city'], float(s_data['balance'] or 0),
                          bool(s_data['is_active']))

            connection.insertingtodatabase(sql, params)
            ui.notify('Supplier saved', color='positive')
            refresh_table()
        except Exception as e:
            ui.notify(f'Error: {e}', color='negative')

    with ModernPageLayout("Supplier Management", standalone=standalone):
        with ui.column().classes('w-full gap-6 p-4 animate-fade-in'):
            
            # Redundant Horizontal Action Bar removed

            with ui.row().classes('w-full gap-6 items-start'):
                # Left Column: Form
                with ui.column().classes('w-1/3 gap-4'):
                    with ModernCard().classes('w-full p-6'):
                        ui.label('Supplier Profile').classes('text-lg font-bold mb-4')
                        input_refs['id'] = ui.input('ID').props('readonly outlined dense').classes('hidden')
                        input_refs['name'] = ModernInput('Company Name', icon='business').style('color: #c05884')
                        input_refs['contact'] = ModernInput('Contact Person', icon='person').style('color: #c05884')
                        input_refs['email'] = ModernInput('Email', icon='email').style('color: #c05884')
                        input_refs['phone'] = ModernInput('Phone', icon='phone').style('color: #c05884')

                    with ModernCard().classes('w-full p-6'):
                        ui.label('Address & Status').classes('text-lg font-bold mb-4')
                        input_refs['address'] = ui.input('Address').style('color: #c05884').props('outlined dense').classes('w-full')
                        input_refs['city'] = ui.input('City').style('color: #c05884').props('outlined dense').classes('w-full mt-2')
                        input_refs['balance'] = ui.number('Current Balance').style('color: #c05884').props('outlined dense').classes('w-full mt-2')
                        input_refs['is_active'] = ui.checkbox('Active', value=True).classes('mt-2')

                # Right Column: List
                with ui.column().classes('flex-1'):
                    with ModernCard().classes('w-full p-4'):
                        ui.label('Supplier List').classes('text-lg font-bold mb-4 ml-2')
                        
                        cols = [
                            {'headerName': 'Company', 'field': 'name', 'flex': 2},
                            {'headerName': 'Contact', 'field': 'contact', 'flex': 1},
                            {'headerName': 'Phone', 'field': 'phone', 'width': 130},
                            {'headerName': 'Balance LL', 'field': 'balance_ll', 'width': 90},
                            {'headerName': 'Balance USD', 'field': 'balance_usd', 'width': 90},
                            {'headerName': 'Pending Invoices', 'field': 'pending_invoices', 'width': 110, 'valueFormatter': '"$" + Number(params.value || 0).toLocaleString()'},
                            {'headerName': 'Active', 'field': 'is_active', 'cellRenderer': 'agCheckboxRenderer'}
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

                # Action Bar Panel (Right Side of Editor)
                with ui.column().classes('w-80px items-center'):
                    from modern_ui_components import ModernActionBar
                    ModernActionBar(
                        on_new=clear_inputs,
                        on_save=save_supplier,
                        on_undo=lambda: ui.notify('Undo not implemented for suppliers'),
                        on_delete=lambda: ui.notify('Delete currently disabled'),
                        on_chatgpt=lambda: ui.open('https://chatgpt.com', new_tab=True),
                        on_refresh=refresh_table,
                        button_class='h-16',
                        classes=' '
                    ).style('position: static; width: 80px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); margin-top: 0;')

    ui.timer(0.1, refresh_table, once=True)


@ui.page('/suppliers')
def supplier_page_route():
    supplier_page()

