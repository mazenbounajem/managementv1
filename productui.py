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
            e.sender.reset() # Clear the upload list
        except Exception as ex:
            ui.notify(f'Upload error: {ex}', color='negative')

    def remove_photo():
        input_refs['photo'].set_value('')
        photo_preview.set_source('https://via.placeholder.com/150')
        if 'uploader' in input_refs:
            input_refs['uploader'].reset()
        ui.notify('Photo removed from form')

    def clear_input_fields():
        for key, ref in input_refs.items():
            if key == 'id': ref.set_value('')
            elif key in ['stock_quantity', 'min_stock_level', 'max_stock_level', 'price', 'cost_price', 'local_price']:
                ref.set_value(0)
            elif key == 'is_active': ref.set_value(True)
            elif key == 'uploader': continue # Skip the uploader component
            else: ref.set_value('')
        photo_preview.set_source('https://via.placeholder.com/150')
        if 'uploader' in input_refs:
            input_refs['uploader'].reset()
        if table:
            table.classes(add='dimmed')
            table.run_method('deselectAll')
        if hasattr(footer_container, 'action_bar'):
            footer_container.action_bar.enter_new_mode()
        try:
            update_saved_state()
            ui.run_javascript("sessionStorage.removeItem('draft_products');")
        except: pass

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
            p_data = {k: ref.value for k, ref in input_refs.items() if k != 'uploader'}
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
                dup_chk = []
                connection.contogetrows("SELECT COUNT(*) FROM products WHERE product_name=? AND id!=?", dup_chk, params=[p_data['product_name'], p_data['id']])
                if dup_chk and dup_chk[0][0] > 0:
                    return ui.notify('A product with this name already exists', color='negative')
                    
                sql = """UPDATE products SET product_name=?, barcode=?, sku=?, description=?, category_id=?,
                         price=?, cost_price=?, stock_quantity=?, min_stock_level=?, max_stock_level=?,
                         supplier_id=?, currency_id=?, local_price=?, is_active=?, photo=? WHERE id=?"""
                params = (p_data['product_name'], p_data['barcode'], p_data['sku'], p_data['description'], cat_id,
                          price, float(p_data['cost_price'] or 0), int(p_data['stock_quantity'] or 0),
                          int(p_data['min_stock_level'] or 0), int(p_data['max_stock_level'] or 0),
                          sup_id, cur_id, local_price, bool(p_data['is_active']), p_data['photo'], p_data['id'])
            else: # Insert
                dup_chk = []
                connection.contogetrows("SELECT COUNT(*) FROM products WHERE product_name=?", dup_chk, params=[p_data['product_name']])
                if dup_chk and dup_chk[0][0] > 0:
                    return ui.notify('A product with this name already exists', color='negative')
                    
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
            try:
                update_saved_state()
                ui.run_javascript("sessionStorage.removeItem('draft_products');")
            except: pass
            refresh_table()
        except Exception as e:
            ui.notify(f'Save error: {e}', color='negative')

    def delete_product():
        pid = input_refs['id'].value
        if not pid: return ui.notify('Select a product to delete', color='warning')
        tx_chk = []
        connection.contogetrows("SELECT (SELECT COUNT(*) FROM sale_items WHERE product_id=?) + (SELECT COUNT(*) FROM purchase_items WHERE product_id=?)", tx_chk, params=[pid, pid])
        if tx_chk and tx_chk[0][0] > 0:
            return ui.notify('Cannot delete product with existing transactions. Delete them or set to inactive.', color='negative')
            
        try:
            connection.deleterow("DELETE FROM products WHERE id=?", [pid])
            ui.notify('Product deleted', color='positive')
            clear_input_fields()
            refresh_table()
        except Exception as e:
            ui.notify(f'Delete error: {e}', color='negative')

    def print_transactions():
        pid = input_refs['id'].value
        if not pid: return ui.notify('Select a product first', color='warning')
        p_name = input_refs['product_name'].value
        with ui.dialog() as d, ui.card().classes('w-full max-w-4xl p-6 border border-white/10 rounded-3xl').style('background: rgba(15, 15, 25, 0.82); backdrop-filter: blur(20px);'):
            ui.label(f'Stock Transactions for {p_name}').classes('text-2xl font-black text-white tracking-wider mb-4 font-outfit')
            sql = """
                SELECT 'Sale' as type, s.sale_date as date, s.invoice_number as ref, si.quantity as qty, si.unit_price as price
                FROM sale_items si JOIN sales s ON s.id = si.sales_id WHERE si.product_id = ?
                UNION ALL
                SELECT 'Purchase' as type, p.purchase_date as date, p.invoice_number as ref, pi.quantity as qty, pi.unit_price as price
                FROM purchase_items pi JOIN purchases p ON p.id = pi.purchase_id WHERE pi.product_id = ?
                ORDER BY date DESC
            """
            data = []
            connection.contogetrows(sql, data, params=[pid, pid])
            if not data:
                ui.label('No transactions found.').classes('text-gray-400')
            else:
                columns = [
                    {'headerName': 'Type', 'field': 'type'},
                    {'headerName': 'Date', 'field': 'date'},
                    {'headerName': 'Ref', 'field': 'ref'},
                    {'headerName': 'Qty', 'field': 'qty'},
                    {'headerName': 'Price', 'field': 'price'},
                ]
                rows = [{'type': r[0], 'date': r[1], 'ref': r[2], 'qty': r[3], 'price': r[4]} for r in data]
                ui.aggrid({'columnDefs': columns, 'rowData': rows, 'domLayout': 'normal'}).classes('w-full h-80 ag-theme-quartz-dark shadow-inner').style('background: transparent; border: none;')
            with ui.row().classes('w-full justify-end mt-4'):
                ui.button('Close', on_click=d.close).props('flat text-color=gray').classes('px-4 py-2 rounded-xl')
        d.open()

    def show_price_history():
        pid = input_refs['id'].value
        if not pid: return ui.notify('Select a product first', color='warning')
        p_name = input_refs['product_name'].value
        with ui.dialog() as d, ui.card().classes('w-full max-w-2xl p-6 border border-white/10 rounded-3xl').style('background: rgba(15, 15, 25, 0.82); backdrop-filter: blur(20px);'):
            ui.label(f'Price History for {p_name}').classes('text-2xl font-black text-white tracking-wider mb-4 font-outfit')
            sql = """
                SELECT p.purchase_date as date, p.invoice_number as ref, pi.unit_price as cost, pi.quantity as qty
                FROM purchase_items pi JOIN purchases p ON p.id = pi.purchase_id
                WHERE pi.product_id = ? ORDER BY p.purchase_date DESC
            """
            data = []
            connection.contogetrows(sql, data, params=[pid])
            if not data:
                ui.label('No purchase history found to determine cost changes.').classes('text-gray-400')
            else:
                columns = [
                    {'headerName': 'Date', 'field': 'date'},
                    {'headerName': 'Ref', 'field': 'ref'},
                    {'headerName': 'Qty Purchased', 'field': 'qty'},
                    {'headerName': 'Cost Price', 'field': 'cost'},
                ]
                rows = [{'date': r[0], 'ref': r[1], 'qty': r[2], 'cost': r[3]} for r in data]
                ui.aggrid({'columnDefs': columns, 'rowData': rows, 'domLayout': 'normal'}).classes('w-full h-64 ag-theme-quartz-dark shadow-inner').style('background: transparent; border: none;')
            with ui.row().classes('w-full justify-end mt-4'):
                ui.button('Close', on_click=d.close).props('flat text-color=gray').classes('px-4 py-2 rounded-xl')
        d.open()

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

    def open_suppliers_tab():
        """Trigger opening the suppliers tab in the dashboard."""
        try:
            from tabbed_dashboard import current_open_tab
            if current_open_tab:
                current_open_tab('suppliers')
                ui.notify('Opening Suppliers tab...', color='info')
            else:
                ui.navigate.to('/suppliers')
        except:
            ui.navigate.to('/suppliers')

    def refresh_dropdowns():
        cats = []
        connection.contogetrows("SELECT id, category_name FROM categories", cats)
        category_map.clear()
        for c in cats: category_map[c[1]] = c[0]
        
        sups = []
        connection.contogetrows("SELECT id, name FROM suppliers", sups)
        supplier_map.clear()
        for s in sups: supplier_map[s[1]] = s[0]
        
        curs = []
        connection.contogetrows("SELECT id, currency_code FROM currencies", curs)
        currency_map.clear()
        for c in curs: currency_map[c[1]] = c[0]
        
        input_refs['category_id'].options = list(category_map.keys())
        input_refs['supplier_id'].options = list(supplier_map.keys())
        input_refs['currency_id'].options = list(currency_map.keys())
        
        input_refs['category_id'].update()
        input_refs['supplier_id'].update()
        input_refs['currency_id'].update()

    def print_transactions():
        try:
            pid = input_refs['id'].value
            product_name = input_refs['product_name'].value
            if not pid:
                ui.notify('Select a product to view transactions', color='warning')
                return

            transactions = []
            
            # Fetch Sales
            sales_data = []
            try:
                connection.contogetrows(f"""
                    SELECT s.sale_date, 'Sale' as type, s.invoice_number, si.quantity, si.unit_price, si.total_price 
                    FROM sale_items si 
                    JOIN sales s ON si.sales_id = s.id 
                    WHERE si.product_id = {pid}
                """, sales_data)
                for r in sales_data:
                    date_val = str(r[0])[:19] if r[0] else ''
                    transactions.append({
                        'date': date_val, 
                        'type': r[1], 
                        'reference': str(r[2]), 
                        'quantity': -float(r[3] or 0), 
                        'price': float(r[4] or 0), 
                        'total': -float(r[5] or 0)
                    })
            except Exception as e:
                print(f"Error fetching sales: {e}")

            # Fetch Purchases
            purchases_data = []
            try:
                connection.contogetrows(f"""
                    SELECT p.purchase_date, 'Purchase' as type, p.invoice_number, pi.quantity, pi.unit_cost, pi.total_cost 
                    FROM purchase_items pi 
                    JOIN purchases p ON pi.purchase_id = p.id 
                    WHERE pi.product_id = {pid}
                """, purchases_data)
                for r in purchases_data:
                    date_val = str(r[0])[:19] if r[0] else ''
                    transactions.append({
                        'date': date_val, 
                        'type': r[1], 
                        'reference': str(r[2]), 
                        'quantity': float(r[3] or 0), 
                        'price': float(r[4] or 0), 
                        'total': float(r[5] or 0)
                    })
            except Exception as e:
                print(f"Error fetching purchases: {e}")

            if not transactions:
                ui.notify('No transactions found for this product.', color='info')
                return

            # Sort transactions by date descending
            transactions.sort(key=lambda x: x['date'], reverse=True)

            with ui.dialog() as dialog, ui.card().classes('w-[900px] max-w-full p-6'):
                with ui.row().classes('w-full justify-between items-center mb-4'):
                    ui.label(f'Transactions: {product_name}').classes('text-xl font-bold').style(f'color: {MDS.ACCENT_DARK}')
                    ui.button(icon='close', on_click=dialog.close).props('flat round dense')
                
                columns = [
                    {'headerName': 'Date', 'field': 'date', 'sortable': True},
                    {'headerName': 'Type', 'field': 'type', 'sortable': True, 'filter': True},
                    {'headerName': 'Reference', 'field': 'reference', 'sortable': True, 'filter': True},
                    {'headerName': 'Quantity', 'field': 'quantity', 'sortable': True, 'cellClassRules': {'text-red-500': 'x < 0', 'text-green-500': 'x > 0'}},
                    {'headerName': 'Unit Cost/Price', 'field': 'price', 'sortable': True},
                    {'headerName': 'Total', 'field': 'total', 'sortable': True, 'cellClassRules': {'text-red-500': 'x < 0', 'text-green-500': 'x > 0'}},
                ]
                
                ui.aggrid({
                    'columnDefs': columns,
                    'rowData': transactions,
                    'defaultColDef': {'flex': 1, 'sortable': True},
                }).classes('w-full h-[500px] ag-theme-quartz-dark')
                
            dialog.open()
        except Exception as ex:
            ui.notify(f'Display error: {ex}', color='negative')

    def show_price_history():
        try:
            pid = input_refs['id'].value
            product_name = input_refs['product_name'].value
            if not pid:
                ui.notify('Select a product to view price history', color='warning')
                return

            history_data = []
            try:
                connection.contogetrows(f"""
                    SELECT p.purchase_date, pi.unit_cost, pi.unit_price, p.invoice_number, s.name
                    FROM purchase_items pi
                    JOIN purchases p ON pi.purchase_id = p.id
                    LEFT JOIN suppliers s ON p.supplier_id = s.id
                    WHERE pi.product_id = {pid}
                """, history_data)
            except Exception as e:
                print(f"Error fetching price history: {e}")

            if not history_data:
                ui.notify('No purchase history found to track price changes.', color='info')
                return

            history = []
            for r in history_data:
                date_val = str(r[0])[:19] if r[0] else ''
                history.append({
                    'date': date_val,
                    'cost': float(r[1] or 0),
                    'price': float(r[2] or 0),
                    'invoice': str(r[3]),
                    'supplier': str(r[4] or 'Unknown')
                })

            history.sort(key=lambda x: x['date'], reverse=True)

            with ui.dialog() as dialog, ui.card().classes('w-[700px] max-w-full p-6'):
                with ui.row().classes('w-full justify-between items-center mb-4'):
                    ui.label(f'Price History: {product_name}').classes('text-xl font-bold').style(f'color: {MDS.ACCENT_DARK}')
                    ui.button(icon='close', on_click=dialog.close).props('flat round dense')
                
                columns = [
                    {'headerName': 'Date', 'field': 'date', 'sortable': True},
                    {'headerName': 'Unit Cost', 'field': 'cost', 'sortable': True},
                    {'headerName': 'Unit Price', 'field': 'price', 'sortable': True},
                    {'headerName': 'Invoice #', 'field': 'invoice', 'sortable': True},
                    {'headerName': 'Supplier', 'field': 'supplier', 'sortable': True, 'filter': True},
                ]
                
                ui.aggrid({
                    'columnDefs': columns,
                    'rowData': history,
                    'defaultColDef': {'flex': 1, 'sortable': True},
                }).classes('w-full h-[400px] ag-theme-quartz-dark')
                
            dialog.open()
        except Exception as ex:
            ui.notify(f'Display error: {ex}', color='negative')

    def setup_data():
        refresh_dropdowns()
        refresh_table()
        # Auto-load the last product into the form
        try:
            last_data = []
            sql = """SELECT TOP 1 p.id, p.product_name, p.barcode, p.sku, p.description,
                     c.category_name as category, p.price, p.cost_price, p.stock_quantity,
                     p.min_stock_level, p.max_stock_level, s.name as supplier,
                     cu.currency_code as currency, p.local_price, p.is_active
                     FROM products p
                     LEFT JOIN categories c ON p.category_id = c.id
                     LEFT JOIN suppliers s ON p.supplier_id = s.id
                     LEFT JOIN currencies cu ON p.currency_id = cu.id
                     ORDER BY p.id DESC"""
            connection.contogetrows(sql, last_data)
            if last_data:
                r = last_data[0]
                row = {
                    'id': r[0], 'product_name': r[1], 'barcode': r[2], 'sku': r[3],
                    'description': r[4], 'category': r[5], 'price': r[6], 'cost_price': r[7],
                    'stock_quantity': r[8], 'min_stock_level': r[9], 'max_stock_level': r[10],
                    'supplier': r[11], 'currency': r[12], 'local_price': r[13], 'is_active': r[14]
                }
                pid = row['id']
                input_refs['id'].set_value(str(pid))
                for key in ['product_name', 'barcode', 'sku', 'description', 'price', 'cost_price',
                            'stock_quantity', 'min_stock_level', 'max_stock_level', 'local_price', 'is_active']:
                    if key in row:
                        input_refs[key].set_value(row[key])
                input_refs['category_id'].set_value(row.get('category', ''))
                input_refs['supplier_id'].set_value(row.get('supplier', ''))
                input_refs['currency_id'].set_value(row.get('currency', ''))
                photo_data = []
                connection.contogetrows(f"SELECT photo FROM products WHERE id = {pid}", photo_data)
                full_photo = photo_data[0][0] if photo_data else None
                input_refs['photo'].set_value(full_photo or '')
                if full_photo:
                    photo_preview.set_source(full_photo)
                update_local_price()
                update_profit_analysis()
        except Exception as ex:
            print(f"Auto-load last product error: {ex}")

    # Layout Construction
    with ModernPageLayout("Product Management", standalone=standalone):
        with ui.column().classes('w-full gap-6 p-4 animate-fade-in'):
            
            with ui.row().classes('w-full gap-6 items-start'):
                # Left Column: Form
                with ui.column().classes('w-[420px] gap-4'):
                    # Product Image Card
                    with ModernCard().classes('w-full p-6 flex flex-col items-center'):
                        ui.label('Product Image').classes('text-lg font-bold mb-4 w-full text-center')
                        photo_preview = ui.image('https://via.placeholder.com/150').classes('w-full h-48 rounded-2xl border-2 border-accent/20 object-cover shadow-inner mb-2')
                        
                        with ui.row().classes('w-full gap-2 mb-2'):
                            input_refs['photo'] = ui.input().classes('hidden') # State holder
                            input_refs['uploader'] = ui.upload(on_upload=handle_photo_upload, auto_upload=True).props('flat bordered dense label="Upload Image" accept=".jpg,.png,.jpeg"').classes('flex-1')
                            ui.button(icon='delete', on_click=remove_photo).props('flat round color=red').tooltip('Remove current photo')

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
                            input_refs['category_id'] = ui.select([], label='Category').classes('flex-1').props('outlined dense').style(f'color: {MDS.ACCENT_DARK}').on('focus', lambda: refresh_dropdowns())
                            with ui.row().classes('flex-1 items-center gap-1'):
                                input_refs['supplier_id'] = ui.select([], label='Supplier').classes('flex-1').props('outlined dense').style(f'color: {MDS.ACCENT_DARK}').on('focus', lambda: refresh_dropdowns())
                                ui.button(icon='add', on_click=open_suppliers_tab).props('flat round dense color=accent').tooltip('Open Suppliers in new tab')

                    with ModernCard().classes('w-full p-6'):
                        with ui.row().classes('w-full justify-between items-center mb-4'):
                            ui.label('Pricing & Stock').classes('text-lg font-bold').style(f'color: {MDS.ACCENT_DARK}')
                            ui.button(icon='history', on_click=lambda: show_price_history()).props('flat round dense').tooltip('Price History')
                        
                        with ui.row().classes('w-full gap-2'):
                            input_refs['currency_id'] = ui.select([], label='Currency', on_change=lambda: (update_local_price(), update_profit_analysis())).classes('w-1/3').props('outlined dense').style(f'color: {MDS.ACCENT_DARK}').on('focus', lambda: refresh_dropdowns())
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
                        with ui.row().classes('w-full justify-between items-center mb-4 ml-2'):
                            ui.label('Product Repository').classes('text-lg font-bold').style(f'color: {MDS.ACCENT_DARK}')
                            with ui.row().classes('items-center bg-white/10 rounded-full px-3 py-1 shadow-sm border border-gray-300 dark:border-gray-600'):
                                ui.icon('search', color='gray').classes('text-lg')
                                search_input = ui.input(placeholder='Search by name or barcode...').props('borderless dense').classes('ml-2 w-64 text-sm outline-none')
                        
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
                        
                        search_input.on('update:model-value', lambda e: (
                            table.options.update({'quickFilterText': e.sender.value}),
                            table.update()
                        ))
                        
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
                                    
                                if table:
                                    table.classes(remove='dimmed')
                                if hasattr(footer_container, 'action_bar'):
                                    footer_container.action_bar.enter_edit_mode()
                                try: update_saved_state()
                                except: pass
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
                with ui.column().classes('w-80px items-center') as footer_container:
                    from modern_ui_components import ModernActionBar
                    footer_container.action_bar = ModernActionBar(
                        on_new=clear_input_fields,
                        on_save=save_product,
                        on_undo=lambda: (footer_container.action_bar.reset_state(), refresh_table()),
                        on_delete=delete_product,
                        on_refresh=refresh_table,
                        on_chatgpt=lambda: ui.open('https://chatgpt.com', new_tab=True),
                        on_print=print_transactions,
                        on_print_special=show_price_history,
                        target_table=table,
                        button_class='h-16',
                        classes=' '
                    )
                    footer_container.action_bar.style('position: static; width: 80px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); margin-top: 0;')

    # Register refresh callback for tabbed dashboard

    # Register refresh callback for tabbed dashboard
    try:
        from tabbed_dashboard import tab_refresh_callbacks
        tab_refresh_callbacks['products'] = refresh_dropdowns
    except ImportError:
        pass

    ui.timer(0.1, setup_data, once=True)

    # Dirty state tracking for unsaved changes warning
    saved_state = {}

    def capture_state():
        state = {}
        for k, ref in input_refs.items():
            if k == 'uploader': continue
            if hasattr(ref, 'value'):
                state[k] = ref.value
        return state

    def update_saved_state():
        nonlocal saved_state
        saved_state = capture_state().copy()

    def is_dirty():
        current_state = capture_state()
        
        # If no product selected and form is empty, it's not dirty
        if not current_state.get('id') and not current_state.get('product_name'):
            return False
            
        for k, v in current_state.items():
            if k == 'photo': continue
            s_val = saved_state.get(k, '')
            
            # Normalize to strings for comparison
            v_str = str(v) if v is not None else ''
            s_str = str(s_val) if s_val is not None else ''
            
            if v_str != s_str:
                # Ignore empty vs unset vs 0 variations
                if not v_str and not s_str: continue
                if v_str in ('0', '0.0', '0.00', 'None', '') and s_str in ('0', '0.0', '0.00', 'None', ''): continue
                if v_str == 'False' and s_str == '': continue
                if v_str == 'True' and s_str == '1': continue
                if v_str == 'False' and s_str == '0': continue
                return True
        return False
        
    try:
        from tabbed_dashboard import tab_dirty_callbacks
        tab_dirty_callbacks['products'] = is_dirty
    except ImportError:
        pass

    # Initial state capture
    ui.timer(0.2, update_saved_state, once=True)

    # ── Auto-Save Drafts (saved to browser sessionStorage every 5 s) ─────────
    def save_draft():
        if not is_dirty(): return
        import json
        try:
            state = {k: v for k, v in capture_state().items() if k != 'photo'}
            encoded = json.dumps(state).replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')
            ui.run_javascript(f"sessionStorage.setItem('draft_products', '{encoded}');")
        except Exception: pass

    def restore_draft_values(state_json):
        import json
        try:
            state = json.loads(state_json)
            for k, v in state.items():
                if k in input_refs and hasattr(input_refs[k], 'set_value'):
                    input_refs[k].set_value(v)
            update_local_price()
            update_profit_analysis()
            update_saved_state()
            ui.run_javascript("sessionStorage.removeItem('draft_products');")
        except Exception as ex:
            print(f"Draft restore error: {ex}")

    async def check_for_draft():
        import json
        result = await ui.run_javascript("sessionStorage.getItem('draft_products');", timeout=5.0)
        if result:
            try:
                state = json.loads(result)
                product_name = state.get('product_name', '')
                hint = f'"{product_name}"' if product_name else 'an unsaved product'
                with ui.dialog() as d, ui.card().classes('p-6 rounded-xl'):
                    ui.label('📝 Unsaved Draft Found').classes('text-lg font-bold mb-2')
                    ui.label(f'You have an unsaved draft for {hint}.').classes('text-gray-600 mb-4 text-sm')
                    ui.label('Would you like to restore it?').classes('text-gray-600 mb-6 text-sm')
                    with ui.row().classes('w-full justify-end gap-3'):
                        ui.button('Discard', on_click=lambda: (ui.run_javascript("sessionStorage.removeItem('draft_products');"), d.close())).props('flat color=gray')
                        ui.button('Restore Draft', color='purple', on_click=lambda: (restore_draft_values(result), d.close())).props('unelevated')
                d.open()
            except Exception: pass

    ui.timer(5.0, save_draft)                   # silently auto-save every 5 s
    ui.timer(1.5, check_for_draft, once=True)   # check for draft on page open

product_page = product_page_route
