from nicegui import ui
from connection import connection
from modern_design_system import ModernDesignSystem as MDS
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput, ModernTable
from session_storage import session_storage
from datetime import datetime

def customer_receipt_page(standalone=False):
    # Auth
    user = session_storage.get('user')
    if not user:
        if not standalone:
            ui.notify('Please login', color='negative')
            ui.navigate.to('/login')
        return

    # State
    state = {
        'selected_customer': None,
        'selected_invoices': [],
        'receipt_data': []
    }
    input_refs = {}

    def refresh_history():
        data = []
        sql = """SELECT cr.id, cr.payment_date, c.customer_name, cr.amount, cr.payment_method 
                 FROM customer_receipt cr
                 JOIN customers c ON cr.customer_id = c.id
                 ORDER BY cr.id DESC"""
        connection.contogetrows(sql, data)
        rows = []
        cols = ['id', 'date', 'customer', 'amount', 'method']
        for r in data:
            rows.append({cols[i]: r[i] for i in range(len(cols))})
        history_table.options['rowData'] = rows
        history_table.update()

    def select_customer():
        with ui.dialog() as d, ModernCard().classes('w-full max-w-2xl p-6'):
            ui.label('Select customer').classes('text-xl font-bold mb-4')
            
            c_data = []
            connection.contogetrows("SELECT id, customer_name, balance_ll FROM customers", c_data)
            c_rows = [{'id': r[0], 'name': r[1], 'balance': r[2]} for r in c_data]
            
            grid = ui.aggrid({
                'columnDefs': [
                    {'headerName': 'Name', 'field': 'name', 'flex': 1},
                    {'headerName': 'Balance', 'field': 'balance', 'width': 120}
                ],
                'rowData': c_rows,
                'rowSelection': 'single'
            }).classes('w-full h-80 ag-theme-quartz-dark')
            
            async def confirm():
                row = await grid.get_selected_row()
                if row:
                    state['selected_customer'] = row
                    input_refs['customer'].set_value(row['name'])
                    d.close()
            
            with ui.row().classes('w-full justify-end mt-4'):
                ModernButton.create('Select', on_click=confirm)

        d.open()

    def process_receipt():
        if not state['selected_customer']:
            return ui.notify('Select customer first', color='negative')
        
        try:
            val = float(input_refs['amount'].value or 0)
            if val <= 0: return ui.notify('Invalid amount', color='warning')

            sql = "INSERT INTO customer_receipt (customer_id, amount, payment_date, payment_method, created_at) VALUES (?, ?, GETDATE(), ?, GETDATE())"
            connection.insertingtodatabase(sql, (state['selected_customer']['id'], val, input_refs['method'].value))
            
            # Update customer balance
            connection.insertingtodatabase("UPDATE customers SET balance_ll = balance_ll - ? WHERE id = ?", (val, state['selected_customer']['id']))
            
            ui.notify('Receipt processed', color='positive')
            refresh_history()
            input_refs['amount'].set_value(0)
        except Exception as e:
            ui.notify(f'Error: {e}', color='negative')

    with ModernPageLayout("Customer Receipts"):
        with ui.column().classes('w-full gap-6 p-4 animate-fade-in'):
            
            # Action Bar
            with ModernCard().classes('w-full p-4'):
                with ui.row().classes('w-full items-center justify-between'):
                    with ui.row().classes('items-center gap-4'):
                        ui.icon('receipt_long').classes('text-3xl text-primary')
                        ui.label('Revenue Collection').classes('text-2xl font-black text-primary-dark')
                    
                    with ui.row().classes('gap-2'):
                        ModernButton.create('Clear', icon='refresh', on_click=lambda: input_refs['amount'].set_value(0))
                        ModernButton.create('Process', icon='check_circle', on_click=process_receipt, variant='success')

            with ui.row().classes('w-full gap-6 items-start'):
                # Left: Process Form
                with ui.column().classes('w-1/3 gap-4'):
                    with ModernCard().classes('w-full p-6'):
                        ui.label('New Receipt').classes('text-lg font-bold mb-4')
                        input_refs['customer'] = ui.input('Customer').props('readonly outlined dense').classes('w-full')
                        input_refs['customer'].on('click', select_customer)
                        input_refs['amount'] = ui.number('Amount received', value=0).props('outlined dense').classes('w-full mt-2')
                        input_refs['method'] = ui.select(['Cash', 'Card', 'OMT', 'Wish'], value='Cash', label='Method').classes('w-full mt-2').props('outlined dense')

                # Right: History
                with ui.column().classes('flex-1'):
                    with ModernCard().classes('w-full p-4'):
                        ui.label('Recent Receipts').classes('text-lg font-bold mb-4 ml-2')
                        
                        cols = [
                            {'headerName': 'ID', 'field': 'id', 'width': 80},
                            {'headerName': 'Date', 'field': 'date', 'width': 180},
                            {'headerName': 'Customer', 'field': 'customer', 'flex': 1},
                            {'headerName': 'Amount', 'field': 'amount', 'width': 120},
                            {'headerName': 'Method', 'field': 'method', 'width': 120}
                        ]
                        
                        history_table = ui.aggrid({
                            'columnDefs': cols,
                            'rowData': [],
                            'defaultColDef': {'sortable': True, 'filter': True},
                        }).classes('w-full h-[600px] ag-theme-quartz-dark')

    ui.timer(0.1, refresh_history, once=True)

@ui.page('/customerreceipt')
def customer_receipt_page_route():
    customer_receipt_page()
