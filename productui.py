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
    # Removed product_photos cache to prevent memory bloat
    current_index = 0
    filtered_data = []
    category_map = {}
    supplier_map = {}
    currency_map = {}

    def handle_photo_upload(e):
        try:
            content = e.content.read()
            base64_str = base64.b64encode(content).decode('ascii')
            mime_type = "image/png"
            input_refs['photo'].set_value(f"data:{mime_type};base64,{base64_str}")
            photo_preview.set_source(f"data:{mime_type};base64,{base64_str}")
            ui.notify('Product photo uploaded', color='positive')
        except Exception as ex:
            ui.notify(f'Upload error: {ex}', color='negative')

    def clear_input_fields():
        for key, ref in input_refs.items():
            if key == 'id': ref.set_value('')
            elif key in ['stock_quantity', 'min_stock_level', 'max_stock_level', 'price', 'cost_price', 'local_price']:
                ref.set_value(0)
            elif key == 'is_active': ref.set_value(True)
            else: ref.set_value('')
        photo_preview.set_source('https://via.placeholder.com/150')
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
                         supplier_id=?, currency_id=?, local_price=?, is_active=?, photo=? WHERE id=?"""
                params = (p_data['product_name'], p_data['barcode'], p_data['sku'], p_data['description'], cat_id,
                          price, float(p_data['cost_price'] or 0), int(p_data['stock_quantity'] or 0),
                          int(p_data['min_stock_level'] or 0), int(p_data['max_stock_level'] or 0),
                          sup_id, cur_id, local_price, bool(p_data['is_active']), p_data['photo'], p_data['id'])
            else: # Insert
                sql = """INSERT INTO products (product_name, barcode, sku, description, category_id,
                         price, cost_price, stock_quantity, min_stock_level, max_stock_level,
                         supplier_id, currency_id, local_price, created_at, is_active, photo)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), ?, ?)"""
                params = (p_data['product_name'], p_data['barcode'], p_data['sku'], p_data['description'], cat_id,
                          price, float(p_data['cost_price'] or 0), int(p_data['stock_quantity'] or 0),
                          int(p_data['min_stock_level'] or 0), int(p_data['max_stock_level'] or 0),
                          sup_id, cur_id, local_price, bool(p_data['is_active']), p_data['photo'])

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
        # Selecting photo presence flag instead of full binary data
        sql = """SELECT p.id, p.product_name, p.barcode, p.sku, p.description,
                 c.category_name as category, p.price, p.cost_price, p.stock_quantity,
                 p.min_stock_level, p.max_stock_level, s.name as supplier,
                 cu.currency_code as currency, p.local_price, p.is_active, 
                 CASE WHEN p.photo IS NOT NULL AND p.photo != '' THEN 1 ELSE 0 END as has_photo
                 FROM products p
                 LEFT JOIN categories c ON p.category_id = c.id
                 LEFT JOIN suppliers s ON p.supplier_id = s.id
                 LEFT JOIN currencies cu ON p.currency_id = cu.id
                 ORDER BY p.id DESC"""
        connection.contogetrows(sql, data)
        rows = []
        
        for r in data:
            rows.append({
                'id': r[0], 'product_name': r[1], 'barcode': r[2], 'sku': r[3], 'description': r[4], 
                'category': r[5], 'price': r[6], 'cost_price': r[7], 'stock_quantity': r[8], 
                'min_stock_level': r[9], 'max_stock_level': r[10], 'supplier': r[11], 
                'currency': r[12], 'local_price': r[13], 'is_active': r[14],
                'has_photo': bool(r[15])
            })
        table.options['rowData'] = rows
        table.update()
        update_profit_analysis()

    def update_profit_analysis():
        try:
            price = float(input_refs['price'].value or 0)
            cost = float(input_refs['cost_price'].value or 0)
            currency_code = input_refs['currency_id'].value
            
            if currency_code and (price > 0 or cost > 0):
                currency_id = currency_map.get(currency_code)
                if currency_id:
                    currency_data = []
                    connection.contogetrows(f"SELECT exchange_rate FROM currencies WHERE id = {currency_id}", currency_data)
                    if currency_data:
                        exchange_rate = float(currency_data[0][0])
                        price_usd = price / exchange_rate if exchange_rate > 0 else 0
                        cost_usd = cost / exchange_rate if exchange_rate > 0 else 0
                        
                        profit_usd = price_usd - cost_usd
                        margin = (profit_usd / price_usd * 100) if price_usd > 0 else 0
                        markup = (profit_usd / cost_usd * 100) if cost_usd > 0 else 0
                        
                        profit_label.set_text(f"${profit_usd:.2f}")
                        margin_label.set_text(f"{margin:.1f}%")
                        markup_label.set_text(f"{markup:.1f}%")
                        return
            profit_label.set_text("$0.00")
            margin_label.set_text("0.0%")
            markup_label.set_text("0.0%")
        except:
            pass

    def generate_barcode():
        code = str(random.randint(100000000000, 999999999999))
        input_refs['barcode'].set_value(EAN13(code).get_fullcode())
        ui.notify('Barcode generated', color='info')

    # Layout Construction
    with ModernPageLayout("Product Management"):
        with ui.column().classes('w-full gap-6 p-4 animate-fade-in'):
            
            with ui.row().classes('w-full gap-6 items-start'):
                # Left Column: Form
                with ui.column().classes('w-[420px] gap-4'):
                    # Product Image Card
                    with ModernCard().classes('w-full p-6 flex flex-col items-center'):
                        ui.label('Product Image').classes('text-lg font-bold mb-4 w-full text-center')
                        photo_preview = ui.image('https://via.placeholder.com/150').classes('w-full h-48 rounded-2xl border-2 border-accent/20 object-cover shadow-inner mb-4')
                        input_refs['photo'] = ui.input().classes('hidden') # State holder
                        ui.upload(on_upload=handle_photo_upload, auto_upload=True).props('flat bordered dense label="Upload Product Image" accept=".jpg,.png,.jpeg"').classes('w-full')

                    with ModernCard().classes('w-full p-6'):
                        ui.label('Product Details').classes('text-lg font-bold mb-4 flex items-center gap-2').style(f'color: {MDS.ACCENT_DARK}')
                        
                        input_refs['id'] = ui.input('ID').props('readonly outlined dense').classes('hidden')
                        input_refs['product_name'] = ModernInput('Product Name', placeholder='Enter name...', icon='label', required=True)
                        input_refs['product_name'].style(f'color: {MDS.ACCENT_DARK}')
                        
                        with ui.row().classes('w-full gap-2 mt-2'):
                            input_refs['barcode'] = ModernInput('Barcode', icon='qr_code').classes('flex-1')
                            ui.button(icon='auto_fix_high', on_click=generate_barcode).props('flat round color=accent').tooltip('Generate EAN-13')
                        
                        input_refs['sku'] = ModernInput('SKU', icon='tag')
                        input_refs['description'] = ModernInput('Description', placeholder='Short description...', icon='description')
                        
                        with ui.row().classes('w-full gap-2 mt-2'):
                            input_refs['category_id'] = ui.select([], label='Category').classes('flex-1').props('outlined dense').style(f'color: {MDS.ACCENT_DARK}')
                            input_refs['supplier_id'] = ui.select([], label='Supplier').classes('flex-1').props('outlined dense').style(f'color: {MDS.ACCENT_DARK}')

                    with ModernCard().classes('w-full p-6'):
                        ui.label('Pricing & Stock').classes('text-lg font-bold mb-4').style(f'color: {MDS.ACCENT_DARK}')
                        
                        with ui.row().classes('w-full gap-2'):
                            input_refs['currency_id'] = ui.select([], label='Currency', on_change=lambda: (update_local_price(), update_profit_analysis())).classes('w-1/3').props('outlined dense').style(f'color: {MDS.ACCENT_DARK}')
                            input_refs['price'] = ui.number('Price', on_change=lambda: (update_local_price(), update_profit_analysis())).classes('flex-1').props('outlined dense').style(f'color: {MDS.ACCENT_DARK}')
                            input_refs['local_price'] = ui.input('Local Price').props('readonly outlined dense').classes('w-1/3').style(f'color: {MDS.ACCENT_DARK}')

                        with ui.row().classes('w-full gap-2 mt-2'):
                            input_refs['cost_price'] = ui.number('Cost Price', on_change=update_profit_analysis).classes('flex-1').props('outlined dense').style(f'color: {MDS.ACCENT_DARK}')
                            input_refs['stock_quantity'] = ui.number('Current Stock').classes('flex-1').props('outlined dense').style(f'color: {MDS.ACCENT_DARK}')

                        with ui.row().classes('w-full gap-2 mt-2'):
                            input_refs['min_stock_level'] = ui.number('Min Level').classes('flex-1').props('outlined dense').style(f'color: {MDS.ACCENT_DARK}')
                            input_refs['max_stock_level'] = ui.number('Max Level').classes('flex-1').props('outlined dense').style(f'color: {MDS.ACCENT_DARK}')
                        
                        input_refs['is_active'] = ui.checkbox('Active Product', value=True).classes('mt-2')

                # Right Column: Data Grid
                with ui.column().classes('flex-1'):
                    with ModernCard().classes('w-full p-4'):
                        ui.label('Product Repository').classes('text-lg font-bold mb-4 ml-2').style(f'color: {MDS.ACCENT_DARK}')
                        
                        columns = [
                            {'headerName': 'Img', 'field': 'photo', 'width': 60, 'cellRenderer': 'img_renderer'},
                            {'headerName': 'Name', 'field': 'product_name', 'flex': 2},
                            {'headerName': 'Category', 'field': 'category'},
                            {'headerName': 'Price', 'field': 'price'},
                            {'headerName': 'Stock', 'field': 'stock_quantity'},
                            {'headerName': 'Supplier', 'field': 'supplier'},
                            {'headerName': 'Currency', 'field': 'currency'},
                            {'headerName': 'Status', 'field': 'is_active', 'cellRenderer': 'agCheckboxRenderer'}
                        ]
                        
                        ui.add_body_html('''
                        <script>
                        window.img_renderer = (params) => {
                            if (!params.data.has_photo) return "";
                            return `<div style="width: 24px; height: 24px; border-radius: 4px; background: rgba(255,255,255,0.1); display: flex; align-items: center; justify-content: center;">
                                <span style="font-size: 8px; opacity: 0.5;">📦</span>
                            </div>`;
                        };
                        </script>
                        ''')

                        table = ui.aggrid({
                            'columnDefs': columns,
                            'rowData': [],
                            'defaultColDef': {'flex': 1, 'sortable': True, 'filter': True},
                            'rowSelection': 'single',
                        }).classes('w-full h-[600px] ag-theme-quartz-dark')
                        def on_row_click(e):
                            try:
                                # Instant response from click event data
                                row = e.args.get('data')
                                if not row: return
                                
                                pid = row.get('id')
                                if pid is None: return
                                
                                # Load metadata immediately
                                input_refs['id'].set_value(str(pid))
                                for key in ['product_name', 'barcode', 'sku', 'description', 'price', 'cost_price', 'stock_quantity', 'min_stock_level', 'max_stock_level', 'local_price', 'is_active']:
                                    if key in row: input_refs[key].set_value(row[key])
                                
                                # Handle selection mapping
                                input_refs['category_id'].set_value(row.get('category', ''))
                                input_refs['supplier_id'].set_value(row.get('supplier', ''))
                                input_refs['currency_id'].set_value(row.get('currency', ''))
                                
                                # Fetch high-resolution image on-demand from database
                                photo_data = []
                                connection.contogetrows(f"SELECT photo FROM products WHERE id = {pid}", photo_data)
                                full_photo = photo_data[0][0] if photo_data else None
                                
                                input_refs['photo'].set_value(full_photo or '')
                                if full_photo:
                                    photo_preview.set_source(full_photo)
                                else:
                                    photo_preview.set_source('https://via.placeholder.com/150')
                                    
                                update_local_price()
                                update_profit_analysis()
                            except Exception as ex:
                                print(f"Product selection error: {ex}")
                                ui.notify(f'Display error: {ex}', color='warning')

                        table.on('cellClicked', on_row_click)

                    with ModernCard().classes('w-full p-6 mt-4'):
                        ui.label('Profit Analysis').classes('text-lg font-bold mb-4').style(f'color: {MDS.SUCCESS}')
                        with ui.row().classes('w-full justify-between items-center'):
                            with ui.column().classes('items-center'):
                                ui.label('Profit (USD)').classes('text-xs text-gray-500 uppercase font-black')
                                profit_label = ui.label('$0.00').classes('text-xl font-black text-success')
                            with ui.column().classes('items-center'):
                                ui.label('Margin').classes('text-xs text-gray-500 uppercase font-black')
                                margin_label = ui.label('0.0%').classes('text-xl font-black text-primary')
                            with ui.column().classes('items-center'):
                                ui.label('Markup').classes('text-xs text-gray-500 uppercase font-black')
                                markup_label = ui.label('0.0%').classes('text-xl font-black text-accent')

                # Action Bar Panel (Right Side of Editor)
                with ui.column().classes('w-80px items-center'):
                    from modern_ui_components import ModernActionBar
                    ModernActionBar(
                        on_new=clear_input_fields,
                        on_save=save_product,
                        on_delete=delete_product,
                        on_refresh=refresh_table,
                        on_chatgpt=lambda: ui.open('https://chatgpt.com', new_tab=True),
                        button_class='h-16',
                        classes=' '
                    ).style('position: static; width: 80px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); margin-top: 0;')

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
        
        input_refs['category_id'].options = list(category_map.keys())
        input_refs['supplier_id'].options = list(supplier_map.keys())
        input_refs['currency_id'].options = list(currency_map.keys())
        
        input_refs['category_id'].update()
        input_refs['supplier_id'].update()
        input_refs['currency_id'].update()
        
        refresh_table()

    ui.timer(0.1, setup_data, once=True)


product_page = product_page_route
