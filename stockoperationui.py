from nicegui import ui
from connection import connection
from modern_design_system import ModernDesignSystem as MDS
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput, ModernTable
from session_storage import session_storage
from datetime import datetime

def stock_operations_page(standalone=False):
    # Auth
    user = session_storage.get('user')
    if not user:
        if not standalone:
            ui.notify('Please login', color='negative')
            ui.navigate.to('/login')
        return

    # State
    input_refs = {}
    history_data = []

    def refresh_history():
        data = []
        sql = """SELECT so.id, so.operation_date, u.username, so.operation_type, so.total_items, so.reference_number
                 FROM stock_operations so
                 JOIN users u ON so.user_id = u.id
                 ORDER BY so.id DESC"""
        connection.contogetrows(sql, data)
        rows = []
        cols = ['id', 'date', 'user', 'type', 'items', 'ref']
        for r in data:
            rows.append({cols[i]: r[i] for i in range(len(cols))})
        history_grid.options['rowData'] = rows
        history_grid.update()

    def clear_form():
        for k, ref in input_refs.items():
            if k == 'quantity': ref.set_value(1)
            else: ref.set_value('')
        input_refs['date'].set_value(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    with ModernPageLayout("Stock Operations"):
        with ui.column().classes('w-full gap-6 p-4 animate-fade-in'):
            
            # Header Action Bar
            with ModernCard().classes('w-full p-4'):
                with ui.row().classes('w-full items-center justify-between'):
                    with ui.row().classes('items-center gap-4'):
                        ui.icon('inventory').classes('text-3xl text-primary')
                        ui.label('Stock Control Center').classes('text-2xl font-black text-primary-dark')
                    
                    with ui.row().classes('gap-2'):
                        ModernButton.create('New Operation', icon='add', on_click=clear_form, variant='primary')
                        ModernButton.create('Save All', icon='save', variant='success')
                        ModernButton.create('Refresh History', icon='history', on_click=refresh_history, variant='outline')

            with ui.row().classes('w-full gap-6 items-start'):
                # Left Column: Active Operation
                with ui.column().classes('w-1/3 gap-4'):
                    with ModernCard().classes('w-full p-6'):
                        ui.label('Operation Details').classes('text-lg font-bold mb-4')
                        input_refs['date'] = ui.input('Date', value=datetime.now().strftime('%Y-%m-%d %H:%M:%S')).props('outlined dense').classes('w-full')
                        input_refs['type'] = ui.select(['manual_adjustment', 'stock_count', 'return', 'damage'], value='manual_adjustment', label='Type').classes('w-full mt-2').props('outlined dense')
                        input_refs['ref'] = ModernInput('Reference #', icon='tag')

                    with ModernCard().classes('w-full p-6'):
                        ui.label('Add Item').classes('text-lg font-bold mb-4')
                        input_refs['barcode'] = ModernInput('Barcode', icon='qr_code')
                        input_refs['quantity'] = ui.number('Quantity', value=1).classes('w-full mt-2').props('outlined dense')
                        input_refs['reason'] = ui.input('Reason').props('outlined dense').classes('w-full mt-2')
                        ModernButton.create('Add to List', icon='playlist_add').classes('w-full mt-4')

                # Right Column: History & Current Items
                with ui.column().classes('flex-1 gap-4'):
                    with ModernCard().classes('w-full p-4'):
                        ui.label('Operation History').classes('text-lg font-bold mb-4 ml-2')
                        
                        history_cols = [
                            {'headerName': 'ID', 'field': 'id', 'width': 70},
                            {'headerName': 'Date', 'field': 'date', 'width': 160},
                            {'headerName': 'Type', 'field': 'type'},
                            {'headerName': 'Items', 'field': 'items', 'width': 80},
                            {'headerName': 'Ref', 'field': 'ref'}
                        ]
                        
                        history_grid = ui.aggrid({
                            'columnDefs': history_cols,
                            'rowData': [],
                            'defaultColDef': {'sortable': True, 'filter': True},
                            'rowSelection': 'single',
                        }).classes('w-full h-[400px] ag-theme-quartz-dark')

    ui.timer(0.1, refresh_history, once=True)

@ui.page('/stockoperations')
def stock_operations_page_route():
    stock_operations_page()

# Alias for legacy imports
StockOperationUI = stock_operations_page_route
