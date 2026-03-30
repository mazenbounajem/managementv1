from nicegui import ui
from connection import connection
from modern_design_system import ModernDesignSystem as MDS
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput, ModernTable, ModernActionBar
from session_storage import session_storage
from datetime import datetime
import datetime as dt # Added for convenience

def supplier_payment_page(standalone=False):
    # Auth
    user = session_storage.get('user')
    if not user:
        if not standalone:
            ui.notify('Please login', color='negative')
            ui.navigate.to('/login')
        return

    # State
    state = {
        'selected_supplier': None,
        'selected_invoices': [],
        'payment_data': []
    }
    input_refs = {}

    def refresh_history():
        data = []
        sql = """SELECT sp.id, sp.payment_date, s.name, sp.amount, sp.payment_method 
                 FROM supplier_payment sp
                 JOIN suppliers s ON sp.supplier_id = s.id
                 ORDER BY sp.id DESC"""
        connection.contogetrows(sql, data)
        rows = []
        cols = ['id', 'date', 'supplier', 'amount', 'method']
        for r in data:
            rows.append({cols[i]: r[i] for i in range(len(cols))})
        history_table.options['rowData'] = rows
        history_table.update()

    def select_supplier():
        with ui.dialog() as d, ModernCard().classes('w-full max-w-2xl p-6'):
            ui.label('Select Supplier').classes('text-xl font-bold mb-4')
            
            s_data = []
            connection.contogetrows("SELECT id, name, balance FROM suppliers", s_data)
            s_rows = [{'id': r[0], 'name': r[1], 'balance': r[2]} for r in s_data]
            
            grid = ui.aggrid({
                'columnDefs': [
                    {'headerName': 'Name', 'field': 'name', 'flex': 1},
                    {'headerName': 'Balance', 'field': 'balance', 'width': 120}
                ],
                'rowData': s_rows,
                'rowSelection': 'single'
            }).classes('w-full h-80 ag-theme-quartz-dark')
            
            async def confirm():
                row = await grid.get_selected_row()
                if row:
                    state['selected_supplier'] = row
                    input_refs['supplier'].set_value(row['name'])
                    d.close()
            
            with ui.row().classes('w-full justify-end mt-4'):
                ModernButton.create('Select', on_click=confirm)

        d.open()

    def process_payment():
        if not state['selected_supplier']:
            return ui.notify('Select supplier first', color='negative')
        
        try:
            val = float(input_refs['amount'].value or 0)
            if val <= 0: return ui.notify('Invalid amount', color='warning')

            sql = "INSERT INTO supplier_payment (supplier_id, amount, payment_date, payment_method, created_at, status) VALUES (?, ?, GETDATE(), ?, GETDATE(), 'completed')"
            connection.insertingtodatabase(sql, (state['selected_supplier']['id'], val, input_refs['method'].value))
            
            # Update supplier balance
            connection.insertingtodatabase("UPDATE suppliers SET balance = balance - ? WHERE id = ?", (val, state['selected_supplier']['id']))
            
            ui.notify('Payment processed', color='positive')
            refresh_history()
            input_refs['amount'].set_value(0)
        except Exception as e:
            ui.notify(f'Error: {e}', color='negative')

    with ModernPageLayout("Payable Management"):
        with ui.row().classes('w-full gap-6 items-start animate-fade-in'):
            # Left Column: Process Form
            with ui.column().classes('w-[360px] gap-4'):
                with ModernCard(glass=True).classes('w-full p-6'):
                    ui.label('Disbursement Details').classes('text-[10px] font-black uppercase text-purple-400 tracking-widest mb-4')
                    with ui.column().classes('w-full gap-4'):
                        input_refs['supplier'] = ui.input('Supplier Entity').props('readonly rounded outlined dense').classes('w-full glass-input')
                        input_refs['supplier'].on('click', select_supplier)
                        
                        input_refs['amount'] = ui.number('Payment Amount', value=0).props('rounded outlined dense').classes('w-full glass-input mt-2')
                        input_refs['method'] = ui.select(
                            ['Cash', 'Card', 'Visa', 'OMT'], 
                            value='Cash', 
                            label='Disbursement Channel'
                        ).classes('w-full glass-input mt-2').props('rounded outlined dense')
                        
                        ModernButton('Execute Payment', icon='payment', on_click=process_payment, variant='primary').classes('w-full h-12 mt-4')

            # Center Column: History
            with ui.column().classes('flex-1 gap-4'):
                with ModernCard(glass=True).classes('w-full p-6'):
                    ui.label('Payment Register').classes('text-xl font-black mb-6 text-white uppercase tracking-widest')
                    
                    cols = [
                        {'headerName': 'ID', 'field': 'id', 'width': 80},
                        {'headerName': 'Date', 'field': 'date', 'flex': 1},
                        {'headerName': 'Vendor', 'field': 'supplier', 'flex': 1.5},
                        {'headerName': 'Amount', 'field': 'amount', 'width': 110, 'valueFormatter': '"$" + x.toLocaleString()'},
                        {'headerName': 'Channel', 'field': 'method', 'width': 100}
                    ]
                    
                    history_table = ui.aggrid({
                        'columnDefs': cols,
                        'rowData': [],
                        'defaultColDef': MDS.get_ag_grid_default_def(),
                        'rowSelection': 'single',
                    }).classes('w-full h-[600px] ag-theme-quartz-dark shadow-inner')

            # Right Column: Action Bar
            with ui.column().classes('w-80px items-center'):
                ModernActionBar(
                    on_new=lambda: input_refs['amount'].set_value(0),
                    on_save=process_payment,
                    on_undo=lambda: ui.notify('Undo not implemented for supplier payments', color='warning'),
                    on_refresh=refresh_history,
                    on_chatgpt=lambda: ui.open('https://chatgpt.com', new_tab=True),
                    button_class='h-16',
                    classes=' '
                ).style('position: static; width: 80px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); margin-top: 0;')

    ui.timer(0.1, refresh_history, once=True)

@ui.page('/supplierpayment')
def supplier_payment_page_route():
    supplier_payment_page()
