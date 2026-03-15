from nicegui import ui
from connection import connection
from modern_design_system import ModernDesignSystem as MDS
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput, ModernTable
from session_storage import session_storage
from datetime import datetime

@ui.page('/purchases')
@ui.page('/purchase')
def purchase_page_route(standalone=False):
    # Auth Check
    user = session_storage.get('user')
    if not user:
        if not standalone:
            ui.notify('Please login', color='negative')
            ui.navigate.to('/login')
        return

    # State
    input_refs = {}
    product_map = {}
    supplier_map = {}
    currency_map = {}

    def clear_inputs():
        for k, ref in input_refs.items():
            if k == 'id': ref.set_value('')
            elif k in ['quantity', 'unit_price', 'total_amount']: ref.set_value(0)
            else: ref.set_value('')
        input_refs['purchase_date'].set_value(datetime.today().strftime('%Y-%m-%d'))

    def calculate_total():
        try:
            qty = float(input_refs['quantity'].value or 0)
            price = float(input_refs['unit_price'].value or 0)
            input_refs['total_amount'].set_value(qty * price)
        except: pass

    def save_purchase():
        try:
            p_data = {k: ref.value for k, ref in input_refs.items()}
            prod_id = product_map.get(p_data['product_id'])
            sup_id = supplier_map.get(p_data['supplier_id'])
            cur_id = currency_map.get(p_data['currency_id'])

            if not all([prod_id, sup_id, cur_id]):
                return ui.notify('Invalid selection', color='negative')

            if p_data['id']:
                sql = "UPDATE purchases SET product_id=?, supplier_id=?, quantity=?, unit_price=?, total_amount=?, currency_id=?, purchase_date=? WHERE id=?"
                params = (prod_id, sup_id, p_data['quantity'], p_data['unit_price'], p_data['total_amount'], cur_id, p_data['purchase_date'], p_data['id'])
            else:
                sql = "INSERT INTO purchases (product_id, supplier_id, quantity, unit_price, total_amount, currency_id, purchase_date) VALUES (?, ?, ?, ?, ?, ?, ?)"
                params = (prod_id, sup_id, p_data['quantity'], p_data['unit_price'], p_data['total_amount'], cur_id, p_data['purchase_date'])

            connection.insertingtodatabase(sql, params)
            ui.notify('Purchase saved', color='positive')
            refresh_table()
        except Exception as e:
            ui.notify(f'Error: {e}', color='negative')

    def delete_purchase():
        pid = input_refs['id'].value
        if not pid: return ui.notify('Select record', color='warning')
        connection.deleterow("DELETE FROM purchases WHERE id=?", pid)
        ui.notify('Record deleted')
        refresh_table()

    def refresh_table():
        data = []
        sql = """SELECT pu.id, pr.product_name, s.name, pu.quantity, pu.unit_price, pu.total_amount, pu.purchase_date
                 FROM purchases pu
                 JOIN products pr ON pu.product_id = pr.id
                 JOIN suppliers s ON pu.supplier_id = s.id
                 ORDER BY pu.purchase_date DESC"""
        connection.contogetrows(sql, data)
        rows = []
        cols = ['id', 'product_name', 'supplier_name', 'quantity', 'unit_price', 'total_amount', 'purchase_date']
        for r in data:
            rows.append({cols[i]: r[i] for i in range(len(cols))})
        table.options['rowData'] = rows
        table.update()

    with ModernPageLayout("Purchase Management"):
        with ui.column().classes('w-full gap-6 p-4 animate-fade-in'):
            
            # Action Banner
            with ModernCard().classes('w-full p-4'):
                with ui.row().classes('w-full items-center justify-between'):
                    with ui.row().classes('items-center gap-4'):
                        ui.icon('shopping_cart').classes('text-3xl text-secondary')
                        ui.label('Procurement Center').classes('text-2xl font-black text-primary-dark')
                    
                    with ui.row().classes('gap-2'):
                        ModernButton.create('Add New', icon='add', on_click=clear_inputs, variant='primary')
                        ModernButton.create('Save', icon='save', on_click=save_purchase, variant='success')
                        ModernButton.create('Delete', icon='delete', on_click=delete_purchase, variant='error')

            with ui.row().classes('w-full gap-6 items-start'):
                # Form Column
                with ui.column().classes('w-1/3 gap-4'):
                    with ModernCard().classes('w-full p-6'):
                        ui.label('Transaction Info').classes('text-lg font-bold mb-4')
                        
                        input_refs['id'] = ui.input().classes('hidden')
                        input_refs['purchase_date'] = ui.input('Date', value=datetime.today().strftime('%Y-%m-%d')).props('type=date outlined dense').classes('w-full')
                        
                        input_refs['supplier_id'] = ui.select([], label='Supplier').classes('w-full mt-2').props('outlined dense')
                        input_refs['product_id'] = ui.select([], label='Product').classes('w-full mt-2').props('outlined dense')
                        input_refs['currency_id'] = ui.select([], label='Currency').classes('w-full mt-2').props('outlined dense')

                    with ModernCard().classes('w-full p-6'):
                        ui.label('Financial Details').classes('text-lg font-bold mb-4')
                        
                        input_refs['quantity'] = ui.number('Quantity', on_change=calculate_total).classes('w-full').props('outlined dense')
                        input_refs['unit_price'] = ui.number('Unit Price', on_change=calculate_total).classes('w-full mt-2').props('outlined dense')
                        input_refs['total_amount'] = ui.number('Total Amount').props('readonly outlined dense').classes('w-full mt-2')

                # Table Column
                with ui.column().classes('flex-1'):
                    with ModernCard().classes('w-full p-4'):
                        ui.label('Recent Purchases').classes('text-lg font-bold mb-4 ml-2')
                        
                        cols_def = [
                            {'headerName': 'Date', 'field': 'purchase_date', 'width': 120},
                            {'headerName': 'Product', 'field': 'product_name', 'flex': 1},
                            {'headerName': 'Supplier', 'field': 'supplier_name'},
                            {'headerName': 'Qty', 'field': 'quantity', 'width': 80},
                            {'headerName': 'Total', 'field': 'total_amount', 'width': 120}
                        ]
                        
                        table = ui.aggrid({
                            'columnDefs': cols_def,
                            'rowData': [],
                            'defaultColDef': {'sortable': True, 'filter': True},
                            'rowSelection': 'single',
                        }).classes('w-full h-[500px] ag-theme-quartz-dark')

                        async def on_row():
                            row = await table.get_selected_row()
                            if row:
                                for k in input_refs:
                                    if k in row: input_refs[k].set_value(row[k])
                                # Manual mapping for selects if needed
                                input_refs['product_id'].set_value(row['product_name'])
                                input_refs['supplier_id'].set_value(row['supplier_name'])
                        table.on('cellClicked', on_row)

    def setup():
        prods = []
        connection.contogetrows("SELECT id, product_name FROM products", prods)
        for p in prods: product_map[p[1]] = p[0]
        
        sups = []
        connection.contogetrows("SELECT id, name FROM suppliers", sups)
        for s in sups: supplier_map[s[1]] = s[0]
        
        curs = []
        connection.contogetrows("SELECT id, currency_code FROM currencies", curs)
        for c in curs: currency_map[c[1]] = c[0]

        input_refs['product_id'].options = list(product_map.keys())
        input_refs['supplier_id'].options = list(supplier_map.keys())
        input_refs['currency_id'].options = list(currency_map.keys())
        
        input_refs['product_id'].update()
        input_refs['supplier_id'].update()
        input_refs['currency_id'].update()
        
        refresh_table()

    ui.timer(0.1, setup, once=True)

# Alias for app.py import
purchase_page = purchase_page_route
