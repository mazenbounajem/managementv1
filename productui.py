from nicegui import ui
from connection import connection
from modern_design_system import ModernDesignSystem as MDS
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput, ModernTable
from session_storage import session_storage
import datetime
from barcode.ean import EAN13
from barcode.writer import SVGWriter
import random
import io
import base64

@ui.page('/products')
def product_page_route(standalone=False):
    # Check if user is logged in
    user = session_storage.get('user')
    if not user:
        if not standalone:
            ui.notify('Please login to access this page', color='red')
            ui.run_javascript('window.location.href = "/login"')
        return

    # Helper and state variables
    input_refs = {}
    initial_values = {}
    current_index = 0
    filtered_data = []
    category_map = {}
    supplier_map = {}
    currency_map = {}

    def clear_input_fields():
        for key, ref in input_refs.items():
            if key == 'id': ref.set_value('')
            elif key in ['stock_quantity', 'min_stock_level', 'max_stock_level', 'price', 'cost_price', 'local_price']:
                ref.set_value(0)
            elif key == 'is_active': ref.set_value(True)
            else: ref.set_value('')
        table.run_method('deselectAll')

    def update_local_price():
        try:
            price = float(input_refs['price'].value or 0)
            currency_code = input_refs['currency_id'].value
            if currency_code and price > 0:
                currency_id = currency_map.get(currency_code)
                if currency_id:
                    currency_data = []
                    connection.contogetrows(f"SELECT exchange_rate FROM currencies WHERE id = {currency_id}", currency_data)
                    if currency_data:
                        exchange_rate = float(currency_data[0][0])
                        local_price = price * exchange_rate
                        input_refs['local_price'].set_value(f"{local_price:.2f}")
                        return
            input_refs['local_price'].set_value('0.00')
        except:
            input_refs['local_price'].set_value('0.00')

    def save_product():
        try:
            p_data = {k: ref.value for k, ref in input_refs.items()}
            if not p_data['product_name']:
                ui.notify('Product Name is required', color='negative')
                return

            cat_id = category_map.get(p_data['category_id'])
            sup_id = supplier_map.get(p_data['supplier_id'])
            cur_id = currency_map.get(p_data['currency_id'])

            if None in [cat_id, sup_id, cur_id]:
                ui.notify('Invalid selection in dropdowns', color='negative')
                return

            price = float(p_data['price'] or 0)
            local_price = float(input_refs['local_price'].value or 0)

            if p_data['id']: # Update
                sql = """UPDATE products SET product_name=?, barcode=?, sku=?, description=?, category_id=?,
                         price=?, cost_price=?, stock_quantity=?, min_stock_level=?, max_stock_level=?,
                         supplier_id=?, currency_id=?, local_price=?, is_active=? WHERE id=?"""
                params = (p_data['product_name'], p_data['barcode'], p_data['sku'], p_data['description'], cat_id,
                          price, float(p_data['cost_price'] or 0), int(p_data['stock_quantity'] or 0),
                          int(p_data['min_stock_level'] or 0), int(p_data['max_stock_level'] or 0),
                          sup_id, cur_id, local_price, bool(p_data['is_active']), p_data['id'])
            else: # Insert
                sql = """INSERT INTO products (product_name, barcode, sku, description, category_id,
                         price, cost_price, stock_quantity, min_stock_level, max_stock_level,
                         supplier_id, currency_id, local_price, created_at, is_active)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), ?)"""
                params = (p_data['product_name'], p_data['barcode'], p_data['sku'], p_data['description'], cat_id,
                          price, float(p_data['cost_price'] or 0), int(p_data['stock_quantity'] or 0),
                          int(p_date['min_stock_level'] or 0), int(p_data['max_stock_level'] or 0),
                          sup_id, cur_id, local_price, bool(p_data['is_active']))

            connection.insertingtodatabase(sql, params)
            ui.notify('Product saved successfully', color='positive')
            refresh_table()
        except Exception as e:
            ui.notify(f'Save error: {e}', color='negative')

    def delete_product():
        pid = input_refs['id'].value
        if not pid: return ui.notify('Select a product to delete', color='warning')
        try:
            connection.deleterow("DELETE FROM products WHERE id=?", pid)
            ui.notify('Product deleted', color='positive')
            clear_input_fields()
            refresh_table()
        except Exception as e:
            ui.notify(f'Delete error: {e}', color='negative')

    def refresh_table():
        data = []
        sql = """SELECT p.id, p.product_name, p.barcode, p.sku, p.description,
                 c.category_name as category, p.price, p.cost_price, p.stock_quantity,
                 p.min_stock_level, p.max_stock_level, s.name as supplier,
                 cu.currency_code as currency, p.local_price, p.is_active
                 FROM products p
                 LEFT JOIN categories c ON p.category_id = c.id
                 LEFT JOIN suppliers s ON p.supplier_id = s.id
                 LEFT JOIN currencies cu ON p.currency_id = cu.id
                 ORDER BY p.id DESC"""
        connection.contogetrows(sql, data)
        rows = []
        cols = ['id', 'product_name', 'barcode', 'sku', 'description', 'category', 'price', 'cost_price', 'stock_quantity', 'min_stock_level', 'max_stock_level', 'supplier', 'currency', 'local_price', 'is_active']
        for r in data:
            rows.append({cols[i]: r[i] for i in range(len(cols))})
        table.options['rowData'] = rows
        table.update()

    def generate_barcode():
        code = str(random.randint(100000000000, 999999999999))
        input_refs['barcode'].set_value(EAN13(code).get_fullcode())
        ui.notify('Barcode generated', color='info')

    # Layout Construction
    with ModernPageLayout("Product Management"):
        with ui.column().classes('w-full gap-6 p-4 animate-fade-in'):
            
            # Action Bar
            with ModernCard().classes('w-full p-4'):
                with ui.row().classes('w-full items-center justify-between'):
                    with ui.row().classes('items-center gap-4'):
                        ui.icon('inventory_2').classes('text-3xl text-primary')
                        ui.label('Inventory Control').classes('text-2xl font-black text-primary-dark')
                    
                    with ui.row().classes('gap-2'):
                        ModernButton.create('New', icon='add', on_click=clear_input_fields, variant='primary')
                        ModernButton.create('Save', icon='save', on_click=save_product, variant='success')
                        ModernButton.create('Delete', icon='delete', on_click=delete_product, variant='error')
                        ui.button(icon='refresh', on_click=refresh_table).props('flat round color=primary')

            with ui.row().classes('w-full gap-6 items-start'):
                # Left Column: Form
                with ui.column().classes('w-1/3 gap-4'):
                    with ModernCard().classes('w-full p-6'):
                        ui.label('Product Details').classes('text-lg font-bold mb-4 flex items-center gap-2')
                        
                        input_refs['id'] = ui.input('ID').props('readonly outlined dense').classes('hidden')
                        input_refs['product_name'] = ModernInput('Product Name', placeholder='Enter name...', icon='label', required=True)
                        
                        with ui.row().classes('w-full gap-2 mt-2'):
                            input_refs['barcode'] = ModernInput('Barcode', icon='qr_code').classes('flex-1')
                            ui.button(icon='auto_fix_high', on_click=generate_barcode).props('flat round color=accent').tooltip('Generate EAN-13')
                        
                        input_refs['sku'] = ModernInput('SKU', icon='tag')
                        
                        with ui.row().classes('w-full gap-2 mt-2'):
                            input_refs['category_id'] = ui.select([], label='Category').classes('flex-1').props('outlined dense')
                            input_refs['supplier_id'] = ui.select([], label='Supplier').classes('flex-1').props('outlined dense')

                    with ModernCard().classes('w-full p-6'):
                        ui.label('Pricing & Stock').classes('text-lg font-bold mb-4')
                        
                        with ui.row().classes('w-full gap-2'):
                            input_refs['currency_id'] = ui.select([], label='Currency', on_change=update_local_price).classes('w-1/3').props('outlined dense')
                            input_refs['price'] = ui.number('Price', on_change=update_local_price).classes('flex-1').props('outlined dense')
                            input_refs['local_price'] = ui.input('Local Price').props('readonly outlined dense').classes('w-1/3')

                        with ui.row().classes('w-full gap-2 mt-2'):
                            input_refs['cost_price'] = ui.number('Cost Price').classes('flex-1').props('outlined dense')
                            input_refs['stock_quantity'] = ui.number('Current Stock').classes('flex-1').props('outlined dense')

                        with ui.row().classes('w-full gap-2 mt-2'):
                            input_refs['min_stock_level'] = ui.number('Min Level').classes('flex-1').props('outlined dense')
                            input_refs['max_stock_level'] = ui.number('Max Level').classes('flex-1').props('outlined dense')
                        
                        input_refs['is_active'] = ui.checkbox('Active Product', value=True).classes('mt-2')

                # Right Column: Data Grid
                with ui.column().classes('flex-1'):
                    with ModernCard().classes('w-full p-4'):
                        ui.label('Product Repository').classes('text-lg font-bold mb-4 ml-2')
                        
                        columns = [
                            {'headerName': 'Name', 'field': 'product_name', 'flex': 2},
                            {'headerName': 'Category', 'field': 'category'},
                            {'headerName': 'Price', 'field': 'price'},
                            {'headerName': 'Stock', 'field': 'stock_quantity'},
                            {'headerName': 'Status', 'field': 'is_active', 'cellRenderer': 'agCheckboxRenderer'}
                        ]
                        
                        table = ui.aggrid({
                            'columnDefs': columns,
                            'rowData': [],
                            'defaultColDef': {'flex': 1, 'sortable': True, 'filter': True},
                            'rowSelection': 'single',
                        }).classes('w-full h-[600px] ag-theme-quartz-dark')

                        async def on_row_click():
                            row = await table.get_selected_row()
                            if row:
                                for key in input_refs:
                                    if key in row: input_refs[key].set_value(row[key])
                                update_local_price()
                        
                        table.on('cellClicked', on_row_click)

    # Initial loading
    def setup_data():
        cats = []
        connection.contogetrows("SELECT id, category_name FROM categories", cats)
        for c in cats: category_map[c[1]] = c[0]
        
        sups = []
        connection.contogetrows("SELECT id, name FROM suppliers", sups)
        for s in sups: supplier_map[s[1]] = s[0]
        
        curs = []
        connection.contogetrows("SELECT id, currency_code FROM currencies", curs)
        for c in curs: currency_map[c[1]] = c[0]
        
        # Update selects after map population
        input_refs['category_id'].options = list(category_map.keys())
        input_refs['supplier_id'].options = list(supplier_map.keys())
        input_refs['currency_id'].options = list(currency_map.keys())
        
        input_refs['category_id'].update()
        input_refs['supplier_id'].update()
        input_refs['currency_id'].update()
        
        refresh_table()

    ui.timer(0.1, setup_data, once=True)

# Alias for app.py import
product_page = product_page_route
