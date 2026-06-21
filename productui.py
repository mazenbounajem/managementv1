from nicegui import ui
from connection import connection
from modern_design_system import ModernDesignSystem as MDS
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput, ModernTable
from session_storage import session_storage
from reports import Reports
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

    is_employee = bool((user or {}).get('role_name') == 'Employee')

    # Helper and state variables
    input_refs = {}
    initial_values = {}
    # Removed product_photos cache to prevent memory bloat
    current_index = 0
    filtered_data = []
    category_map = {}
    supplier_map = {}
    currency_map = {}

    def capture_state():
        """
        Snapshot current form values for dirty-checking / draft storage.
        """
        state = {}
        for k, ref in input_refs.items():
            if k == 'uploader':
                continue
            # Some refs may not exist yet during page construction
            if not hasattr(ref, 'value'):
                continue
            if k == 'photo':
                # store empty string instead of None for stable comparisons
                state[k] = ref.value or ''
            else:
                state[k] = ref.value
        return state

    saved_state = capture_state().copy()

    def update_saved_state():
        """
        Update the baseline snapshot used by is_dirty().
        """
        nonlocal saved_state
        saved_state = capture_state().copy()

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

    def undo_changes():
        """
        Restore inputs from saved_state (used by Undo button).
        After undo:
        - Make the table active (not dimmed)
        - Enable ALL action-bar buttons except Save
        """
        try:
            # Restore simple input values
            for k, ref in input_refs.items():
                if k == 'uploader':
                    continue
                if k not in saved_state:
                    continue
                if hasattr(ref, 'set_value'):
                    ref.set_value(saved_state[k])

            # Restore photo preview if photo exists in saved_state
            if 'photo' in saved_state:
                if saved_state.get('photo'):
                    photo_preview.set_source(saved_state.get('photo'))
                else:
                    photo_preview.set_source('https://via.placeholder.com/150')

            # Activate table (remove dimmed)
            table_obj = locals().get('table')
            if table_obj:
                table_obj.classes(remove='dimmed')

            # Recalc profit
            update_profit_analysis()

            # Enable all default action-bar buttons except Save and Undo after undo
            if hasattr(footer_container, 'action_bar'):
                footer_container.action_bar.reset_state()

            # IMPORTANT: do NOT call update_saved_state() here,
            # otherwise Undo would become a no-op (snapshot becomes current).
        except Exception as ex:
            ui.notify(f'Undo error: {ex}', color='negative')

    def clear_input_fields():
        for key, ref in input_refs.items():
            if key == 'id': ref.set_value('')
            elif key in ['stock_quantity', 'min_stock_level', 'max_stock_level', 'price', 'cost_price', 'local_price', 'price_ttc', 'vat_percentage']:
                ref.set_value(0)
            elif key in ['is_active', 'is_vat_subjected']: ref.set_value(True if key == 'is_active' else False)
            elif key == 'uploader': continue 
            else: ref.set_value('')
        photo_preview.set_source('https://via.placeholder.com/150')
        if 'uploader' in input_refs:
            input_refs['uploader'].reset()
        if table:
            table.classes(add='dimmed')
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

    def update_ht_from_ttc():
        try:
            ttc = float(input_refs['price_ttc'].value or 0)
            is_vat = input_refs['is_vat_subjected'].value
            vat_pct = float(f"{input_refs['vat_percentage'].value or 0}")
            if is_vat and vat_pct > 0:
                ht = ttc / (1 + vat_pct / 100)
                input_refs['price'].set_value(round(ht, 4))
            else:
                input_refs['price'].set_value(ttc)
            update_local_price()
            update_profit_analysis()
        except: pass

    def update_ttc_from_ht():
        try:
            ht = float(input_refs['price'].value or 0)
            is_vat = input_refs['is_vat_subjected'].value
            vat_pct = float(f"{input_refs['vat_percentage'].value or 0}")
            if is_vat and vat_pct > 0:
                ttc = ht * (1 + vat_pct / 100)
                input_refs['price_ttc'].set_value(round(ttc, 4))
            else:
                input_refs['price_ttc'].set_value(ht)
            update_local_price()
            update_profit_analysis()
        except: pass

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
                         supplier_id=?, currency_id=?, local_price=?, is_active=?, photo=?,
                         is_vat_subjected=?, vat_percentage=?, price_ttc=? WHERE id=?"""
                params = (p_data['product_name'], p_data['barcode'], p_data['sku'], p_data['description'], cat_id,
                          price, float(p_data['cost_price'] or 0), int(p_data['stock_quantity'] or 0),
                          int(p_data['min_stock_level'] or 0), int(p_data['max_stock_level'] or 0),
                          sup_id, cur_id, local_price, bool(p_data['is_active']), p_data['photo'],
                          bool(p_data.get('is_vat_subjected', False)), float(p_data.get('vat_percentage') or 0),
                          float(p_data.get('price_ttc') or 0), p_data['id'])
            else: # Insert
                dup_chk = []
                connection.contogetrows("SELECT COUNT(*) FROM products WHERE product_name=?", dup_chk, params=[p_data['product_name']])
                if dup_chk and dup_chk[0][0] > 0:
                    return ui.notify('A product with this name already exists', color='negative')
                    
                sql = """INSERT INTO products (product_name, barcode, sku, description, category_id,
                         price, cost_price, stock_quantity, min_stock_level, max_stock_level,
                         supplier_id, currency_id, local_price, created_at, is_active, photo,
                         is_vat_subjected, vat_percentage, price_ttc)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), ?, ?, ?, ?, ?)"""
                params = (p_data['product_name'], p_data['barcode'], p_data['sku'], p_data['description'], cat_id,
                          price, float(p_data['cost_price'] or 0), int(p_data['stock_quantity'] or 0),
                          int(p_data['min_stock_level'] or 0), int(p_data['max_stock_level'] or 0),
                          sup_id, cur_id, local_price, bool(p_data['is_active']), p_data['photo'],
                          bool(p_data.get('is_vat_subjected', False)), float(p_data.get('vat_percentage') or 0),
                          float(p_data.get('price_ttc') or 0))

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
        connection.contogetrows(
            "SELECT (SELECT COUNT(*) FROM sale_items WHERE product_id=?) + (SELECT COUNT(*) FROM purchase_items WHERE product_id=?)",
            tx_chk, params=[pid, pid]
        )
        if tx_chk and tx_chk[0][0] > 0:
            return ui.notify('Cannot delete product with existing transactions. Delete them or set to inactive.', color='negative')
            
        def confirm_and_delete():
            with ui.dialog() as d, ui.card().classes('p-8 rounded-3xl border border-white/10 shadow-2xl').style(
                'background: rgba(15, 15, 25, 0.95); backdrop-filter: blur(20px); width: 400px;'
            ):
                with ui.column().classes('w-full items-center gap-6'):
                    with ui.element('div').classes('p-4 rounded-full bg-red-500/10 border border-red-500/20 shadow-[0_0_20px_rgba(239,68,68,0.2)]'):
                        ui.icon('delete_forever', color='red-500').classes('text-5xl')
                    
                    with ui.column().classes('items-center gap-1'):
                        ui.label('Confirm Deletion').classes('text-2xl font-black text-white tracking-tight')
                        ui.label('This action is permanent').classes('text-[10px] uppercase font-black text-red-500 tracking-[0.2em]')
                    
                    product_name = input_refs['product_name'].value or "this item"
                    ui.label(
                        f'Are you sure you want to delete "{product_name}"? All associated metadata will be removed.'
                    ).classes('text-gray-400 text-center text-sm leading-relaxed px-2')
                    
                    with ui.row().classes('w-full gap-3 mt-2'):
                        ui.button('Cancel', on_click=d.close).props('flat color=white').classes('flex-1 rounded-2xl h-12 font-bold')
                        
                        def perform_deletion():
                            try:
                                connection.deleterow("DELETE FROM products WHERE id=?", [pid])
                                ui.notify(f'Product "{product_name}" deleted', color='positive', icon='check_circle')
                                clear_input_fields()
                                refresh_table()
                                d.close()
                            except Exception as e:
                                ui.notify(f'Delete error: {e}', color='negative')
                                d.close()
                                
                        ui.button(
                            'Delete Now',
                            on_click=perform_deletion
                        ).props('unelevated color=red-600').classes('flex-1 rounded-2xl h-12 font-black shadow-lg shadow-red-600/20')
            d.open()

        confirm_and_delete()

    def print_transactions():
        pid = input_refs['id'].value
        if not pid: return ui.notify('Select a product first', color='warning')
        p_name = input_refs['product_name'].value
        with ui.dialog() as d, ui.card().classes('w-full max-w-4xl p-6 border border-white/10 rounded-3xl').style(
            'background: rgba(15, 15, 25, 0.82); backdrop-filter: blur(20px);'
        ):
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

    def _generate_fast_moving_pdf(f, t):
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from io import BytesIO
        from pdf_viewer_helper import show_pdf_modal

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        story.append(Paragraph('Fast Moving Items', styles['Title']))
        story.append(Spacer(1, 12))
        story.append(Paragraph(f'Period: {f} to {t}', styles['Normal']))
        story.append(Spacer(1, 20))
        data = Reports.fetch_fast_moving_items(f, t, limit=20)
        if data:
            headers = ['Rank', 'Product', 'Barcode', 'Qty Sold', 'Revenue', 'Transactions', 'Last Sale']
            rows = [[r.get('rank', ''), r.get('product_name', ''), r.get('barcode', ''),
                     r.get('total_qty_sold', ''), f"${float(r.get('total_revenue', 0)):,.2f}",
                     r.get('num_transactions', ''), str(r.get('last_sale_date', ''))] for r in data]
            tbl = Table([headers] + rows)
            tbl.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(tbl)
        else:
            story.append(Paragraph('No data available.', styles['Normal']))
        doc.build(story)
        buffer.seek(0)
        pdf_bytes = buffer.read()
        buffer.close()
        show_pdf_modal(pdf_bytes, filename=f'fast_moving_{date.today().strftime("%Y%m%d")}.pdf', title='Fast Moving Items')

    def _generate_slow_moving_pdf(f, t):
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from io import BytesIO
        from pdf_viewer_helper import show_pdf_modal

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        story.append(Paragraph('Slow Moving Items', styles['Title']))
        story.append(Spacer(1, 12))
        story.append(Paragraph(f'Period: {f} to {t}', styles['Normal']))
        story.append(Spacer(1, 20))
        data = Reports.fetch_slow_moving_items(f, t, limit=20)
        if data:
            headers = ['Rank', 'Product', 'Barcode', 'Qty Sold', 'Revenue', 'Transactions', 'Last Sale']
            rows = [[r.get('rank', ''), r.get('product_name', ''), r.get('barcode', ''),
                     r.get('total_qty_sold', ''), f"${float(r.get('total_revenue', 0)):,.2f}",
                     r.get('num_transactions', ''), str(r.get('last_sale_date', ''))] for r in data]
            tbl = Table([headers] + rows)
            tbl.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(tbl)
        else:
            story.append(Paragraph('No data available.', styles['Normal']))
        doc.build(story)
        buffer.seek(0)
        pdf_bytes = buffer.read()
        buffer.close()
        show_pdf_modal(pdf_bytes, filename=f'slow_moving_{date.today().strftime("%Y%m%d")}.pdf', title='Slow Moving Items')

    def _generate_monthly_sales_pdf(f, t):
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from io import BytesIO
        from pdf_viewer_helper import show_pdf_modal

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        story.append(Paragraph('Monthly Sales by Item', styles['Title']))
        story.append(Spacer(1, 12))
        story.append(Paragraph(f'Period: {f} to {t}', styles['Normal']))
        story.append(Spacer(1, 20))
        data = Reports.fetch_sales_by_item(f, t)
        if data:
            headers = ['Product', 'Barcode', 'Qty Sold', 'Revenue', 'Cost', 'Profit', 'Margin %']
            rows = [[r.get('product_name', ''), r.get('barcode', ''),
                     r.get('total_qty_sold', ''), f"${float(r.get('total_revenue', 0)):,.2f}",
                     f"${float(r.get('total_cost', 0)):,.2f}", f"${float(r.get('total_profit', 0)):,.2f}",
                     f"{float(r.get('profit_margin_pct', 0)):,.2f}%"] for r in data]
            tbl = Table([headers] + rows)
            tbl.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(tbl)
        else:
            story.append(Paragraph('No data available.', styles['Normal']))
        doc.build(story)
        buffer.seek(0)
        pdf_bytes = buffer.read()
        buffer.close()
        show_pdf_modal(pdf_bytes, filename=f'monthly_sales_{date.today().strftime("%Y%m%d")}.pdf', title='Monthly Sales by Item')

    def _generate_stock_status_pdf():
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from io import BytesIO
        from pdf_viewer_helper import show_pdf_modal

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        story.append(Paragraph('Daily Product List (Stock Status)', styles['Title']))
        story.append(Spacer(1, 20))
        data = Reports.fetch_stock()
        if data:
            headers = ['Product', 'Barcode', 'Category', 'Stock', 'Price', 'Cost', 'Supplier']
            rows = [[r.get('product_name', ''), r.get('barcode', ''), r.get('category_name', ''),
                     r.get('stock_quantity', ''), f"${float(r.get('price', 0)):,.2f}",
                     f"${float(r.get('cost_price', 0)):,.2f}", r.get('supplier_name', '')] for r in data[:100]]
            tbl = Table([headers] + rows)
            tbl.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(tbl)
        else:
            story.append(Paragraph('No data available.', styles['Normal']))
        doc.build(story)
        buffer.seek(0)
        pdf_bytes = buffer.read()
        buffer.close()
        show_pdf_modal(pdf_bytes, filename=f'stock_status_{date.today().strftime("%Y%m%d")}.pdf', title='Daily Product List (Stock Status)')

    def open_stock_print_special_dialog():
        with ui.dialog() as dlg, ui.card().classes('w-full max-w-2xl p-8').style('background: rgba(15,15,25,0.95); backdrop-filter: blur(20px); border: 1px solid rgba(255,255,255,0.1);'):
            with ui.column().classes('w-full items-center gap-6'):
                ui.label('Stock Reports').classes('text-2xl font-black text-white tracking-wider')
                ui.label('Select a report to generate').classes('text-sm text-gray-400')

                with ui.row().classes('w-full gap-4 justify-center flex-wrap'):
                    ui.button('Fast Moving Items', icon='trending_up',
                              on_click=lambda: (_generate_fast_moving_pdf(f, t), dlg.close())
                             ).props('unelevated color=green').classes('w-52 py-8 rounded-2xl font-bold text-sm')

                    ui.button('Slow Moving Items', icon='trending_down',
                              on_click=lambda: (_generate_slow_moving_pdf(f, t), dlg.close())
                             ).props('unelevated color=orange').classes('w-52 py-8 rounded-2xl font-bold text-sm')

                    ui.button('Monthly Sales by Item', icon='receipt_long',
                              on_click=lambda: (_generate_monthly_sales_pdf(f, t), dlg.close())
                             ).props('unelevated color=blue').classes('w-52 py-8 rounded-2xl font-bold text-sm')

                    ui.button('Stock Status', icon='inventory',
                              on_click=lambda: (_generate_stock_status_pdf(), dlg.close())
                             ).props('unelevated color=purple').classes('w-52 py-8 rounded-2xl font-bold text-sm')

                with ui.row().classes('w-full justify-center mt-4'):
                    ui.button('Cancel', on_click=dlg.close).props('flat text-color=grey-5').classes('px-6')

        from datetime import date
        f = date.today().replace(day=1).strftime('%Y-%m-%d')
        t = date.today().strftime('%Y-%m-%d')
        dlg.open()

    def show_price_history():
        pid = input_refs['id'].value
        if not pid: return ui.notify('Select a product first', color='warning')
        p_name = input_refs['product_name'].value
        with ui.dialog() as d, ui.card().classes('w-full max-w-2xl p-6 border border-white/10 rounded-3xl').style(
            'background: rgba(15, 15, 25, 0.82); backdrop-filter: blur(20px);'
        ):
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

    # ---- ui.table state helpers (replaces ag-grid) ----
    _all_rows = []
    _selected_row_index = None
    _selected_row_id = None
    _filter_text = ''

    def _apply_row_from_id(pid):
        nonlocal _selected_row_index, _selected_row_id
        if not table:
            return

        rows = getattr(table, 'rows', None) or []
        target_index = next((i for i, r in enumerate(rows) if r.get('id') == pid), None)
        if target_index is None:
            return

        _selected_row_index = target_index
        _selected_row_id = pid

        row = rows[_selected_row_index]
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
        else:
            photo_preview.set_source('https://via.placeholder.com/150')

        if hasattr(footer_container, 'action_bar'):
            footer_container.action_bar.enter_edit_mode()

        # keep selected row highlight in sync
        _apply_selected_row_color()
        update_ttc_from_ht()
        try:
            update_saved_state()
        except:
            pass

    def _apply_selected_row_color():
        if _selected_row_index is None:
            return
        idx = _selected_row_index
        ui.run_javascript(f"""
        try {{
          const root = document.querySelector('.q-table');
          if (!root) return;

          const rows = root.querySelectorAll('tbody tr');
          if (!rows || rows.length === 0) return;

          const safeIdx = Math.max(0, Math.min({idx}, rows.length - 1));

          rows.forEach(el => {{
            el.style.backgroundColor = '';
            el.style.color = '';
            el.classList.remove('selected-highlight');
          }});

          const selected = rows[safeIdx];
          if (selected) {{
            selected.style.backgroundColor = '#facc15';
            selected.style.color = 'black';
            selected.classList.add('selected-highlight');
          }}
        }} catch (e) {{ }}
        """)

    def _apply_all_filters():
        nonlocal _all_rows, _selected_row_index, _selected_row_id, _filter_text
        if not table:
            return
        q = _filter_text.strip().lower()
        filtered = []
        for r in (_all_rows or []):
            if q and q not in str(r.get('product_name') or '').lower() and q not in str(r.get('barcode') or '').lower():
                continue
            filtered.append(r)
        table.rows = filtered
        table.update()
        table.classes(remove='dimmed')
        if filtered:
            _apply_row_from_id(filtered[0].get('id'))

    filter_table = _apply_all_filters

    def refresh_table():
        nonlocal _all_rows, _selected_row_index, _selected_row_id
        data = []
        sql = """SELECT p.id, p.product_name, p.barcode, p.sku, p.description,
                 c.category_name as category, p.price, p.cost_price, p.stock_quantity,
                 p.min_stock_level, p.max_stock_level, s.name as supplier,
                 cu.currency_code as currency, p.local_price, p.is_active, 
                 CASE WHEN p.photo IS NOT NULL AND p.photo != '' THEN 1 ELSE 0 END as has_photo,
                 p.is_vat_subjected, p.vat_percentage, p.price_ttc
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
                'has_photo': bool(r[15]),
                'is_vat_subjected': bool(r[16]), 'vat_percentage': r[17], 'price_ttc': r[18]
            })

        _all_rows = rows
        _selected_row_index = None
        _selected_row_id = None

        if table:
            table.rows = rows
            table.update()
            table.classes(remove='dimmed')
            if rows:
                _apply_row_from_id(rows[0].get('id'))

        update_profit_analysis()

    def update_profit_analysis():
        if not can_profit:
            return
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
        code = "528" + str(random.randint(100000000, 999999999))
        input_refs['barcode'].set_value(EAN13(code).get_fullcode())
        ui.notify('Lebanese EAN-13 Barcode generated', color='info')

    def print_barcode():
        val = input_refs['barcode'].value
        if not val:
            ui.notify('No barcode to print.', color='warning')
            return
        try:
            from io import BytesIO
            import base64
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import mm
            from reportlab.graphics.barcode.eanbc import Ean13BarcodeWidget
            from reportlab.graphics.shapes import Drawing
            from reportlab.graphics import renderPDF
            
            pdf_buf = BytesIO()
            c = canvas.Canvas(pdf_buf, pagesize=(50*mm, 30*mm))
            
            name = input_refs['product_name'].value or "Product"
            price = input_refs['price_ttc'].value or input_refs['price'].value or 0
            try: price_str = f"L.L. {float(price):,.0f}" if float(price) > 1000 else f"${float(price):.2f}"
            except: price_str = str(price)
            
            c.setFont("Helvetica-Bold", 8)
            n = name[:22]
            c.drawCentredString(25*mm, 24*mm, n)
            
            if len(val) == 13 and val.isdigit():
                barcode_w = Ean13BarcodeWidget(val)
                barcode_w.barHeight = 10*mm
                barcode_w.barWidth = 0.25*mm
                d = Drawing(40*mm, 15*mm)
                d.add(barcode_w)
                renderPDF.draw(d, c, 5*mm, 8*mm)
            else:
                c.setFont("Helvetica", 8)
                c.drawCentredString(25*mm, 14*mm, "INVALID EAN-13 FORMAT")
            
            c.setFont("Helvetica-Bold", 7)
            c.drawCentredString(25*mm, 2*mm, f"Price: {price_str}")
            
            c.save()
            pdf_buf.seek(0)
            b64 = base64.b64encode(pdf_buf.read()).decode('utf-8')
            from reports_framework import show_pdf
            show_pdf(b64, 'Barcode Label')
            
        except Exception as e:
            ui.notify(f'Barcode error: {e}', color='negative')

    def open_suppliers_tab():
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
        
        vats = []
        connection.contogetrows("SELECT DISTINCT vat_percentage FROM vat_settings ORDER BY vat_percentage DESC", vats)
        input_refs['vat_percentage'].options = [float(v[0]) for v in vats]
        input_refs['vat_percentage'].update()

    def setup_data():
        refresh_dropdowns()
        refresh_table()
        try:
            last_data = []
            sql = """SELECT TOP 1 p.id, p.product_name, p.barcode, p.sku, p.description,
                     c.category_name as category, p.price, p.cost_price, p.stock_quantity,
                     p.min_stock_level, p.max_stock_level, s.name as supplier,
                     cu.currency_code as currency, p.local_price, p.is_active,
                     p.is_vat_subjected, p.vat_percentage, p.price_ttc
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
                    'supplier': r[11], 'currency': r[12], 'local_price': r[13], 'is_active': r[14],
                    'is_vat_subjected': bool(r[15]), 'vat_percentage': r[16], 'price_ttc': r[17]
                }
                pid = row['id']
                input_refs['id'].set_value(str(pid))
                for key in ['product_name', 'barcode', 'sku', 'description', 'price', 'cost_price',
                            'stock_quantity', 'min_stock_level', 'max_stock_level', 'local_price', 'is_active', 'is_vat_subjected', 'vat_percentage', 'price_ttc']:
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

    user = session_storage.get('user') or {}
    can_profit = connection.check_page_permission(user.get('role_id'), 'profit-analytics') if user else False

    with ModernPageLayout("Product Management", standalone=standalone):
        with ui.row().classes('w-full gap-6 items-start p-4 animate-fade-in'):
            with ui.column().classes('flex-1 gap-4'):
                with ui.splitter(horizontal=True, value=40).classes('w-full h-[850px]') as splitter:
                    with splitter.before:
                        with ModernCard(glass=True).classes('w-full p-4'):
                            with ui.row().classes('w-full justify-between items-center mb-4 ml-2'):
                                ui.label('Product Repository').classes('text-lg font-bold').style(f'color: {MDS.ACCENT_DARK}')
                                with ui.row().classes('items-center bg-white/10 rounded-full px-3 py-1 shadow-sm border border-gray-300 dark:border-gray-600'):
                                    ui.icon('search', color='gray').classes('text-lg')
                                    search_input = ui.input(placeholder='Search by name or barcode...').props('borderless dense').classes('ml-2 w-64 text-sm outline-none')
                            def on_search_change(e):
                                nonlocal _filter_text
                                _filter_text = e.sender.value if hasattr(e, 'sender') else (e.args if isinstance(e.args, str) else '')
                                _apply_all_filters()
                            search_input.on('update:model-value', on_search_change)

                            def _focus_first_row_from_search():
                                ui.run_javascript("""
                                try {
                                  const root = document.querySelector('.q-table');
                                  if (root) { root.tabIndex = 0; root.focus(); }
                                } catch (e) {}
                                """)
                                if table and getattr(table, 'rows', None) and len(table.rows) > 0:
                                    first_id = table.rows[0].get('id')
                                    if first_id is not None:
                                        _apply_row_from_id(first_id)

                            search_input.on('keydown.down', lambda: _focus_first_row_from_search())

                            columns = [
                                {'name': 'has_photo', 'label': 'Img', 'field': 'has_photo', 'align': 'left', 'sortable': True},
                                {'name': 'product_name', 'label': 'Name', 'field': 'product_name', 'align': 'left', 'sortable': True},
                                {'name': 'category', 'label': 'Category', 'field': 'category', 'align': 'left', 'sortable': True},
                                {'name': 'price', 'label': 'Price', 'field': 'price', 'align': 'left', 'sortable': True},
                                {'name': 'stock_quantity', 'label': 'Stock', 'field': 'stock_quantity', 'align': 'left', 'sortable': True},
                                {'name': 'supplier', 'label': 'Supplier', 'field': 'supplier', 'align': 'left', 'sortable': True},
                                {'name': 'currency', 'label': 'Currency', 'field': 'currency', 'align': 'left', 'sortable': True},
                                {'name': 'is_active', 'label': 'Status', 'field': 'is_active', 'align': 'left', 'sortable': True},
                            ]

                            table = ui.table(
                                columns=columns,
                                rows=[],
                                row_key='id',
                                selection='single',
                                pagination={'rowsPerPage': 10}
                            ).classes('w-full h-80 overflow-hidden').props('flat bordered dense')

                            def on_row_click(e):
                                try:
                                    row = e.args[1] if isinstance(e.args, (list, tuple)) and len(e.args) > 1 else None
                                    if not isinstance(row, dict):
                                        return
                                    pid = row.get('id')
                                    if pid is None:
                                        return
                                    table.classes(remove='dimmed')
                                    _apply_row_from_id(pid)
                                except Exception as ex:
                                    print(f"Product selection error: {ex}")
                                    ui.notify(f'Display error: {ex}', color='warning')

                            table.on('rowClick', on_row_click)

                            ui.run_javascript("""
                            try {
                              const root = document.querySelector('.q-table');
                              if (!root) return;
                              root.tabIndex = 0;
                              if (!root.__bb_prod_arrow_nav) {
                                root.__bb_prod_arrow_nav = true;
                                root.addEventListener('keydown', (ev) => {
                                  if (ev.key !== 'ArrowDown' && ev.key !== 'ArrowUp') return;
                                  ev.preventDefault();
                                  const rows = root.querySelectorAll('tbody tr');
                                  const visibleRows = Array.from(rows).filter(r => r && r.offsetParent !== null);
                                  if (!visibleRows.length) return;
                                  let currentIndex = visibleRows.findIndex(r => r.classList && r.classList.contains('selected-highlight'));
                                  if (currentIndex < 0) currentIndex = 0;
                                  const nextIndex = ev.key === 'ArrowDown'
                                    ? Math.min(currentIndex + 1, visibleRows.length - 1)
                                    : Math.max(currentIndex - 1, 0);
                                  const target = visibleRows[nextIndex];
                                  if (target) target.click();
                                });
                              }
                            } catch (e) {}
                            """)

                    with splitter.after:
                        with ui.row().classes('w-full gap-4 pt-4'):
                            with ui.column().classes('flex-1 gap-4'):
                                with ModernCard(glass=True).classes('w-full p-6'):
                                    ui.label('Product Details').classes('text-[10px] font-black uppercase text-purple-400 tracking-wider mb-4')
                                    input_refs['id'] = ui.input('ID').props('readonly outlined dense dark').classes('hidden')
                                    with ui.row().classes('w-full gap-2 items-end'):
                                        with ui.element('div').classes('flex-2'):
                                            input_refs['product_name'] = ModernInput('Product Name', placeholder='Enter name...', icon='label', required=True)
                                            input_refs['product_name'].style(f'color: {MDS.ACCENT_DARK}')
                                        with ui.element('div').classes('flex-1'):
                                            input_refs['sku'] = ModernInput('SKU', icon='tag')
                                        with ui.element('div').classes('flex-1'):
                                            input_refs['barcode'] = ModernInput('Barcode', icon='qr_code')
                                        ui.button(icon='auto_fix_high', on_click=generate_barcode).props('flat round color=accent').tooltip('Generate EAN-13')
                                        ui.button(icon='print', on_click=print_barcode).props('flat round color=primary').tooltip('Print Barcode Label')
                                        ui.button(icon='history', on_click=show_price_history).props('flat round color=secondary').tooltip('View Price History')
                                    with ui.row().classes('w-full gap-2 items-end'):
                                        with ui.element('div').classes('flex-1'):
                                            input_refs['description'] = ModernInput('Description', placeholder='Short description...', icon='description')
                                        with ui.element('div').classes('flex-1'):
                                            input_refs['category_id'] = ui.select([], label='Category').classes('w-full').props('outlined dense dark').style(f'color: {MDS.ACCENT_DARK}').on('focus', lambda: refresh_dropdowns())
                                        with ui.element('div').classes('flex-1'):
                                            with ui.row().classes('w-full items-center gap-1'):
                                                input_refs['supplier_id'] = ui.select([], label='Supplier').classes('flex-1').props('outlined dense dark').style(f'color: {MDS.ACCENT_DARK}').on('focus', lambda: refresh_dropdowns())
                                                ui.button(icon='add', on_click=open_suppliers_tab).props('flat round dense color=accent').tooltip('Open Suppliers in new tab')

                                with ModernCard(glass=True).classes('w-full p-6'):
                                    ui.label('Pricing & Stock').classes('text-[10px] font-black uppercase text-purple-400 tracking-wider mb-4')
                                    with ui.row().classes('w-full gap-2 items-end'):
                                        input_refs['is_vat_subjected'] = ui.checkbox('Subject to VAT', on_change=lambda: update_ttc_from_ht()).classes('text-xs font-black text-white uppercase tracking-widest')
                                        input_refs['vat_percentage'] = ui.select([], label='VAT %', on_change=lambda: update_ttc_from_ht()).classes('flex-1').props('outlined dense dark stack-label').style(f'color: {MDS.ACCENT_DARK}').on('focus', lambda: refresh_dropdowns())
                                        input_refs['currency_id'] = ui.select([], label='Currency', on_change=lambda: (update_local_price(), update_profit_analysis())).classes('flex-1').props('outlined dense dark stack-label').style(f'color: {MDS.ACCENT_DARK}').on('focus', lambda: refresh_dropdowns())
                                        input_refs['price'] = ui.number('Price (HT)', on_change=lambda: (update_ttc_from_ht())).classes('flex-1 font-bold').props('outlined dense dark stack-label').style(f'color: {MDS.ACCENT_DARK}')
                                        input_refs['price_ttc'] = ui.number('Price (TTC)', on_change=lambda: (update_ht_from_ttc())).classes('flex-1 font-bold').props('outlined dense dark stack-label').style(f'color: {MDS.ACCENT_DARK}')
                                    with ui.row().classes('w-full gap-2 mt-2'):
                                        input_refs['local_price'] = ui.input('Local (HT)').props('readonly outlined dense dark stack-label').classes('flex-1').style(f'color: {MDS.ACCENT_DARK}')
                                        input_refs['cost_price'] = ui.number('Cost Price', on_change=update_profit_analysis).classes('flex-1').props('outlined dense dark stack-label').style(f'color: {MDS.ACCENT_DARK}')
                                        input_refs['stock_quantity'] = ui.number('Current Stock').classes('flex-1').props('outlined dense').style(f'color: {MDS.ACCENT_DARK}')
                                        input_refs['min_stock_level'] = ui.number('Min Level').classes('flex-1').props('outlined dense').style(f'color: {MDS.ACCENT_DARK}')
                                        input_refs['max_stock_level'] = ui.number('Max Level').classes('flex-1').props('outlined dense').style(f'color: {MDS.ACCENT_DARK}')
                                    input_refs['is_active'] = ui.checkbox('Active Product', value=True).classes('mt-2')

                            with ui.column().classes('w-[280px] gap-4'):
                                with ModernCard(glass=True).classes('w-full p-6 flex flex-col items-center'):
                                    ui.label('Product Image').classes('text-[10px] font-black uppercase text-purple-400 tracking-wider mb-4 w-full text-center')
                                    photo_preview = ui.image('https://via.placeholder.com/150').classes('w-full h-32 rounded-xl object-cover border-2 border-white/10 mb-4 shadow-sm')
                                    with ui.row().classes('w-full gap-2 mb-2'):
                                        input_refs['photo'] = ui.input().classes('hidden')
                                        input_refs['uploader'] = ui.upload(on_upload=handle_photo_upload, auto_upload=True).props('flat bordered dark dense label="Upload Image" accept=".jpg,.png,.jpeg"').classes('flex-1')
                                        ui.button(icon='delete', on_click=remove_photo).props('flat round color=red').tooltip('Remove current photo')

                                if can_profit:
                                    with ModernCard(glass=True).classes('w-full p-6'):
                                        ui.label('Profit Analysis').classes('text-[10px] font-black uppercase text-green-400 tracking-wider mb-4')
                                        with ui.column().classes('w-full gap-3'):
                                            with ui.row().classes('w-full justify-between items-center'):
                                                ui.label('Profit (USD)').classes('text-xs text-gray-500 uppercase font-black')
                                                profit_label = ui.label('$0.00').classes('text-xl font-black text-success')
                                            with ui.row().classes('w-full justify-between items-center'):
                                                ui.label('Margin').classes('text-xs text-gray-500 uppercase font-black')
                                                margin_label = ui.label('0.0%').classes('text-xl font-black text-primary')
                                            with ui.row().classes('w-full justify-between items-center'):
                                                ui.label('Markup').classes('text-xs text-gray-500 uppercase font-black')
                                                markup_label = ui.label('0.0%').classes('text-xl font-black text-primary')

            with ui.column().classes('w-80px items-center shrink-0') as footer_container:
                from modern_ui_components import ModernActionBar
                footer_container.action_bar = ModernActionBar(
                    on_new=clear_input_fields,
                    on_save=save_product,
                    on_undo=undo_changes,
                    on_delete=delete_product,
                    on_refresh=refresh_table,
                    on_chatgpt=lambda: ui.run_javascript('window.open("https://chatgpt.com", "_blank");'),
                    on_print=print_transactions,
                    on_print_special=open_stock_print_special_dialog,
                    target_table=table,
                    button_class='h-16',
                    classes=' '
                )
                footer_container.action_bar.style('position: static; width: 80px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); margin-top: 0;')

        ui.timer(0.1, setup_data, once=True)
        ui.timer(0.2, refresh_table, once=True)
    def is_dirty():
        current_state = capture_state()

        if not current_state.get('id') and not current_state.get('product_name'):
            return False

        for k, v in current_state.items():
            if k == 'photo': continue
            s_val = saved_state.get(k, '')

            v_str = str(v) if v is not None else ''
            s_str = str(s_val) if s_val is not None else ''

            if v_str != s_str:
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

    ui.timer(0.2, update_saved_state, once=True)

    def save_draft():
        if not is_dirty(): return
        import json
        try:
            state = {k: v for k, v in capture_state().items() if k != 'photo'}
            encoded = json.dumps(state).replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')
            ui.run_javascript(f"sessionStorage.setItem('draft_products', '{encoded}');")
        except Exception:
            pass

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
            except Exception:
                pass

    ui.timer(5.0, save_draft)
    ui.timer(1.5, check_for_draft, once=True)

product_page = product_page_route
