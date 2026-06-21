from nicegui import ui
from connection import connection
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput, ModernActionBar
from session_storage import session_storage
from datetime import datetime
import datetime as dt

def stock_operations_page(standalone=False):
    """Stock Operations UI - can be used standalone or embedded in tabs"""
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
    current_operation_items = []
    cost_diff_state = {'selected_operation_cost_diff': None}
    action_bar = None

    def refresh_history():
        data = []
        sql = """SELECT so.id, so.operation_date, u.username, so.operation_type, so.total_items, so.reference_number
                 FROM stock_operations so
                 JOIN users u ON so.user_id = u.id
                 WHERE so.operation_type != 'return'
                 ORDER BY so.id DESC"""
        connection.contogetrows(sql, data)
        rows = []
        cols = ['id', 'date', 'user', 'type', 'items', 'ref']
        for r in data:
            rows.append({cols[i]: r[i] for i in range(len(cols))})
        if history_grid:
            history_grid.rows = rows

    def clear_form():
        if action_bar:
            action_bar.enter_new_mode()
        if history_grid:
            history_grid.classes('dimmed')
        for k, ref in input_refs.items():
            if k == 'quantity': ref.set_value(1)
            elif k == 'date': ref.set_value(datetime.now().strftime('%Y-%m-%dT%H:%M'))
            elif k == 'type': ref.set_value('manual_adjustment')
            else: ref.set_value('')
        
        current_operation_items.clear()
        if items_grid:
            items_grid.rows = []
            
        try:
            update_saved_state()
            ui.run_javascript("sessionStorage.removeItem('draft_stockops');")
        except: pass

    def add_item_to_op():
        barcode = input_refs.get('barcode').value
        qty = input_refs.get('quantity').value
        reason = input_refs.get('reason').value
        
        if not barcode:
            ui.notify('Please enter or scan a barcode', color='warning')
            return
        
        # Look up product
        res = []
        connection.contogetrows("SELECT id, product_name, barcode FROM products WHERE barcode = ?", res, [barcode])
        if not res:
            ui.notify(f'Product with barcode {barcode} NOT found!', color='negative')
            return
            
        p_id, p_name, p_barcode = res[0]
        
        # Add to state and grid
        current_operation_items.append({
            'product_id': p_id,
            'product_name': p_name,
            'barcode': p_barcode,
            'quantity': qty,
            'reason': reason,
            'action': '✕'
        })
        
        items_grid.rows = current_operation_items
        
        # Clear item entry fields but keep operation detail
        input_refs['barcode'].set_value('')
        input_refs['quantity'].set_value(1)
        input_refs['reason'].set_value('')
        ui.notify(f'Added {p_name} to operation', color='info')

    def save_operation():
        if not current_operation_items:
            ui.notify('Add some items to the operation first!', color='warning')
            return
            
        try:
            op_date = input_refs['date'].value or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            # Fix SQL Server date format (replace T with space and ensure seconds)
            op_date = op_date.replace('T', ' ')
            if len(op_date) == 16: # YYYY-MM-DD HH:MM
                op_date += ':00'
            
            op_type = input_refs['type'].value
            ref_num = input_refs['ref'].value
            u_id = user.get('user_id') or 1
            
            # 1. Save Header
            total_qty = sum(item['quantity'] for item in current_operation_items)
            sql_header = "INSERT INTO stock_operations (operation_date, user_id, operation_type, total_items, reference_number) VALUES (?, ?, ?, ?, ?)"
            connection.insertingtodatabase(sql_header, (op_date, u_id, op_type, total_qty, ref_num))
            
            # Get last ID
            op_id = connection.getid("SELECT MAX(id) FROM stock_operations", [])
            
            # 2. Save Items and Update Stock
            for item in current_operation_items:
                # Get current stock for auditing (previous_quantity)
                curr_stock_res = []
                connection.contogetrows("SELECT stock_quantity FROM products WHERE id = ?", curr_stock_res, [item['product_id']])
                prev_qty = float(curr_stock_res[0][0]) if curr_stock_res else 0.0
                
                # Determine movement sign
                # manual_adjustment: user enters positive/negative as needed
                # damage: treat as output (negative) if positive entered
                # return: treat as input (positive)
                movement = item['quantity']
                if op_type == 'damage' and movement > 0:
                    movement = -movement
                elif op_type == 'return' and movement < 0:
                    movement = abs(movement)
                
                # Insert item using CORRECT column names: operation_id, adjusted_quantity
                sql_item = """INSERT INTO stock_operation_items 
                             (operation_id, product_id, barcode, product_name, previous_quantity, adjusted_quantity, operation_type, reason) 
                             VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""
                
                connection.insertingtodatabase(sql_item, (
                    op_id, 
                    item['product_id'], 
                    item['barcode'], 
                    item['product_name'], 
                    prev_qty, 
                    movement, 
                    op_type, 
                    item['reason']
                ))
                
                # Update product stock
                connection.update_product("UPDATE products SET stock_quantity = stock_quantity + ? WHERE id = ?", (movement, item['product_id']))
                
            ui.notify('Operation saved and stock updated successfully', color='positive')
            if action_bar:
                action_bar.reset_state()
            if history_grid:
                history_grid.classes(remove='dimmed')
            clear_form()
            refresh_history()
            
        except Exception as ex:
            print(f"Error saving stock operation: {ex}")
            ui.notify(f"Save failed: {ex}", color='negative')

    # Wrap content in ModernPageLayout only if standalone, otherwise just render the content
    if standalone:
        layout_container = ModernPageLayout("Stock Control Center")
        layout_container.__enter__()
    
    try:
        with ui.row().classes('w-full gap-6 items-start animate-fade-in p-4'):
            # Left Column: Details & Entry
            with ui.column().classes('w-[380px] gap-4'):
                with ModernCard(glass=True).classes('w-full p-6'):
                    ui.label('Operation Detail').classes('text-[10px] font-black uppercase text-purple-400 tracking-widest mb-4')
                    with ui.column().classes('w-full gap-4'):
                        input_refs['date'] = ui.input('Date/Time').classes('w-full glass-input').props('dark rounded outlined dense type=datetime-local')
                        input_refs['date'].value = datetime.now().strftime('%Y-%m-%dT%H:%M')
                        
                        input_refs['type'] = ui.select(
                            ['manual_adjustment', 'stock_count', 'return', 'damage'], 
                            value='manual_adjustment', 
                            label='Operation Type'
                        ).classes('w-full glass-input').props('dark rounded outlined dense')
                        
                        input_refs['ref'] = ui.input('Reference #').classes('w-full glass-input').props('dark rounded outlined dense')

                with ModernCard(glass=True).classes('w-full p-6'):
                    ui.label('Item Entry').classes('text-[10px] font-black uppercase text-purple-400 tracking-widest mb-4')
                    
                    def handle_product_selection(e, dialog):
                        try:
                            row = e.args[1] if isinstance(e.args, (list, tuple)) and len(e.args) > 1 else None
                            if not row: return
                            input_refs['barcode'].set_value(row['barcode'])
                            input_refs['product_name'].set_value(row['product_name'])
                            dialog.close()
                            ui.notify(f"Selected: {row['product_name']}")
                        except Exception as ex:
                            print(f"Selection error: {ex}")

                    def open_product_dialog():
                        p_data = []
                        connection.contogetrows("SELECT barcode, product_name, stock_quantity FROM products", p_data)
                        product_rows = [{'barcode': r[0], 'product_name': r[1], 'stock': r[2]} for r in p_data]

                        with ui.dialog() as dialog, ui.card().classes('w-full max-w-5xl glass p-6 border border-white/10').style('background: rgba(15, 15, 25, 0.9); backdrop-filter: blur(20px); border-radius: 2rem;'):
                            ui.label('Select Product').classes('text-2xl font-black mb-6 text-white uppercase tracking-widest')
                            
                            def filter_products(val):
                                searchTerm = str(val or '').lower()
                                filtered = [r for r in product_rows if searchTerm in str(r['product_name']).lower() or searchTerm in str(r['barcode']).lower()]
                                product_grid.rows = filtered

                            with ui.row().classes('w-full items-center gap-3 bg-white/5 px-4 py-2 rounded-xl border border-white/10 mb-4'):
                                ui.icon('search', size='1.25rem').classes('text-purple-400')
                                ui.input(placeholder='Type to search name or barcode...').props('borderless dense dark').classes('flex-1 text-white').on_value_change(lambda e: filter_products(e.value))
                            
                            product_columns = [
                                {'name': 'barcode', 'label': 'Barcode', 'field': 'barcode', 'align': 'left'},
                                {'name': 'product_name', 'label': 'Product Name', 'field': 'product_name', 'align': 'left'},
                                {'name': 'stock', 'label': 'Store Stock', 'field': 'stock', 'align': 'center'},
                            ]
                            product_grid = ui.table(
                                columns=product_columns,
                                rows=product_rows,
                                row_key='barcode',
                                selection='single',
                            ).classes('w-full h-80').props('virtual-scroll flat bordered dense hide-pagination :pagination="{rowsPerPage: 0}"')
                            
                            product_grid.on('rowClick', lambda e: handle_product_selection(e, dialog))
                            
                            with ui.row().classes('w-full justify-end mt-4'):
                                ui.button('Cancel', on_click=dialog.close).props('flat color=white')
                        dialog.open()

                    def update_product_info():
                        barcode = input_refs['barcode'].value
                        if not barcode:
                            input_refs['product_name'].set_value('')
                            return
                        res = []
                        connection.contogetrows("SELECT product_name FROM products WHERE barcode = ?", res, [barcode])
                        if res:
                            input_refs['product_name'].set_value(res[0][0])
                        else:
                            input_refs['product_name'].set_value('Product Not Found')

                    with ui.column().classes('w-full gap-4'):
                        input_refs['barcode'] = ui.input('Scan Barcode').classes('w-full glass-input').props('dark rounded outlined dense')
                        input_refs['barcode'].on('keydown.enter', add_item_to_op)
                        input_refs['barcode'].on('value_change', update_product_info)
                        
                        input_refs['product_name'] = ui.input('Product Name (Click to search)').classes('w-full glass-input cursor-pointer').props('dark rounded outlined dense')
                        input_refs['product_name'].on('click', open_product_dialog)
                        
                        with ui.row().classes('w-full items-end gap-2'):
                            input_refs['quantity'] = ui.number('Quantity', value=1).classes('flex-1 glass-input').props('dark rounded outlined dense')
                            with ui.row().classes('gap-1'):
                                ui.button(icon='remove', on_click=lambda: input_refs['quantity'].set_value(input_refs['quantity'].value - 1)).props('unelevated color=red-5').classes('h-10 w-10 rounded-xl shadow-lg')
                                ui.button(icon='add', on_click=lambda: input_refs['quantity'].set_value(input_refs['quantity'].value + 1)).props('unelevated color=green-5').classes('h-10 w-10 rounded-xl shadow-lg')
                        
                        input_refs['reason'] = ui.textarea('Adjustment Reason').classes('w-full glass-input').props('dark rounded outlined dense')
                        
                        ModernButton('Add to Operation', icon='playlist_add', on_click=add_item_to_op, variant='primary').classes('w-full h-12 mt-2')

            # Center Column: Grids (Current Items & History)
            with ui.column().classes('flex-1 gap-4'):
                with ModernCard(glass=True).classes('w-full p-6'):
                    ui.label('Current Operation Items').classes('text-xl font-black mb-6 text-white uppercase tracking-widest')
                    
                    item_cols = [
                        {'name': 'barcode', 'label': 'Barcode', 'field': 'barcode', 'align': 'left'},
                        {'name': 'product_name', 'label': 'Product', 'field': 'product_name', 'align': 'left'},
                        {'name': 'quantity', 'label': 'Qty', 'field': 'quantity', 'align': 'center'},
                        {'name': 'reason', 'label': 'Reason', 'field': 'reason', 'align': 'left'},
                        {'name': 'action', 'label': '', 'field': 'action', 'align': 'center'},
                    ]
                    
                    def handle_item_click(e):
                        try:
                            row = e.args[1] if isinstance(e.args, (list, tuple)) and len(e.args) > 1 else None
                            if not isinstance(row, dict): return
                            barcode = row.get('barcode')
                            if barcode:
                                for i, item in enumerate(current_operation_items):
                                    if item['barcode'] == barcode:
                                        current_operation_items.pop(i)
                                        items_grid.rows = current_operation_items
                                        ui.notify('Item removed')
                                        break
                        except Exception as ex:
                            print(f"Remove error: {ex}")

                    items_grid = ui.table(
                        columns=item_cols,
                        rows=[],
                        row_key='barcode',
                    ).classes('w-full h-[280px]').props('virtual-scroll flat bordered dense hide-pagination :pagination="{rowsPerPage: 0}"')
                    items_grid.on('rowClick', handle_item_click)

                    # Cost difference after inventory for currently shown operation items
                    cost_diff_label = ui.label('Cost diff after inventory: —').classes(
                        'mt-3 text-sm font-bold text-white/80')

                with ModernCard(glass=True).classes('w-full p-6'):
                    ui.label('Operations Registry (History)').classes('text-sm font-black mb-4 text-white/50 uppercase tracking-widest')
                    
                    history_cols = [
                        {'name': 'id', 'label': 'ID', 'field': 'id', 'align': 'left'},
                        {'name': 'date', 'label': 'Date', 'field': 'date', 'align': 'left'},
                        {'name': 'type', 'label': 'Type', 'field': 'type', 'align': 'left'},
                        {'name': 'items', 'label': 'Items', 'field': 'items', 'align': 'center'},
                        {'name': 'ref', 'label': 'Ref', 'field': 'ref', 'align': 'left'},
                    ]
                    
                    history_grid = ui.table(
                        columns=history_cols,
                        rows=[],
                        row_key='id',
                        selection='single',
                    ).classes('w-full h-[400px]').props('virtual-scroll flat bordered dense hide-pagination :pagination="{rowsPerPage: 0}"')

                    def load_history_operation(row):
                        """Load selected history operation items into current grid and compute cost diff."""
                        try:
                            op_id = row.get('id')
                            if op_id is None:
                                return
                            # Pull items with cost price + valuation math
                            item_rows = []
                            sql = """
                                SELECT
                                    soi.product_id,
                                    soi.product_name,
                                    soi.barcode,
                                    CAST(soi.adjusted_quantity AS float) AS adjusted_quantity,
                                    CAST(soi.previous_quantity AS float) AS previous_quantity,
                                    ISNULL(p.cost_price, 0) AS cost_price,
                                    ISNULL(soi.reason, '') AS reason,
                                    ISNULL(soi.operation_type, '') AS operation_type
                                FROM stock_operation_items soi
                                LEFT JOIN products p ON p.id = soi.product_id
                                WHERE soi.operation_id = ?
                                ORDER BY soi.id
                            """
                            connection.contogetrows(sql, item_rows, [op_id])

                            current_operation_items.clear()
                            for r in item_rows:
                                p_id, p_name, p_barcode, adj_qty, prev_qty, cost_price, reason, operation_type = r
                                current_operation_items.append({
                                    'product_id': p_id,
                                    'product_name': p_name,
                                    'barcode': p_barcode,
                                    'quantity': adj_qty,
                                    'reason': reason,
                                    'action': '✕'
                                })
                            items_grid.rows = current_operation_items

                            # Cost diff after inventory (option A):
                            # after_value - before_value = (prev_qty + adj_qty)*cost - prev_qty*cost
                            # = adj_qty * cost, but computed using prev_qty as requested.
                            total_diff = 0.0
                            for r in item_rows:
                                adj_qty = float(r[3] or 0)
                                prev_qty = float(r[4] or 0)
                                cost_price = float(r[5] or 0)
                                before_value = prev_qty * cost_price
                                after_value = (prev_qty + adj_qty) * cost_price
                                total_diff += (after_value - before_value)

                            cost_diff_state['selected_operation_cost_diff'] = total_diff
                            sign_color = 'text-green-300' if total_diff >= 0 else 'text-red-300'
                            cost_diff_label.set_text(
                                f"Cost diff after inventory: {total_diff:+,.2f} (qty*cost)"
                            )
                            cost_diff_label.classes('mt-3 text-sm font-bold ' + sign_color)

                        except Exception as ex:
                            print(f"Error loading operation history: {ex}")
                            ui.notify(f"Load failed: {ex}", color='negative')

                    def handle_history_click(e):
                        try:
                            row = e.args[1] if isinstance(e.args, (list, tuple)) and len(e.args) > 1 else None
                            if not isinstance(row, dict):
                                return
                            load_history_operation(row)
                        except Exception as ex:
                            print(f"History click error: {ex}")

                    history_grid.on('rowClick', handle_history_click)

            # Right Column: Action Bar
            with ui.column().classes('w-60px items-center shrink-0'):

                def _open_stock_print_special():
                    try:
                        from stock_reports import open_print_current_and_grouped_dialog

                        operation_date_val = input_refs.get('date').value if input_refs.get('date') else None
                        date_only = (str(operation_date_val).split('T')[0] if operation_date_val else None)

                        # Defer opening to next tick to avoid immediate UI close/minimize effects.
                        def _do_open():
                            open_print_current_and_grouped_dialog(
                                current_items=current_operation_items,
                                operation_date=date_only,
                                reference_number=(input_refs['ref'].value if 'ref' in input_refs else None),
                                from_date=date_only,
                                to_date=date_only
                            )
                        ui.timer(0, _do_open, once=True)
                    except Exception as e:
                        ui.notify(f'Print Special failed: {e}', color='negative')

                action_bar = ModernActionBar(
                    on_new=clear_form,
                    on_save=save_operation,
                    on_undo=lambda: (action_bar.reset_state() if action_bar else None, history_grid.classes(remove='dimmed') if history_grid else None, ui.notify('Operation reset', color='info')),
                    on_refresh=refresh_history,
                    on_print_special=_open_stock_print_special,
                    on_chatgpt=lambda: ui.run_javascript('window.open("https://chatgpt.com", "_blank");'),
                    button_class='h-10',
                    classes=' '
                ).style('position: static; width: 60px; border-radius: 12px; margin-top: 0;')

        # Dirty state tracking for unsaved changes warning
        saved_state = {}

        def capture_state():
            state = {}
            for k, ref in input_refs.items():
                if hasattr(ref, 'value'):
                    state[k] = ref.value
            return state

        def update_saved_state():
            nonlocal saved_state
            saved_state = capture_state().copy()

        def is_dirty():
            if current_operation_items:
                return True
            current_state = capture_state()
            
            # If barcode is empty, it's not dirty
            if not current_state.get('barcode'):
                return False
                
            for k, v in current_state.items():
                if k == 'date': continue
                s_val = saved_state.get(k, '')
                
                v_str = str(v) if v is not None else ''
                s_str = str(s_val) if s_val is not None else ''
                
                if v_str != s_str:
                    if not v_str and not s_str: continue
                    if k == 'quantity' and v_str == '1' and s_str in ('', '0'): continue
                    if k == 'type' and v_str == 'manual_adjustment' and s_str == '': continue
                    return True
            return False
            
        try:
            from tabbed_dashboard import tab_dirty_callbacks
            tab_dirty_callbacks['stockoperations'] = is_dirty
            tab_dirty_callbacks['stockoperationui'] = is_dirty
        except ImportError:
            pass

        ui.timer(0.1, refresh_history, once=True)
        ui.timer(0.2, update_saved_state, once=True)

        # Auto-Save Drafts
        def save_draft():
            if not is_dirty(): return
            import json
            try:
                state = capture_state()
                state.pop('date', None)
                state['items'] = current_operation_items
                encoded = json.dumps(state).replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')
                ui.run_javascript(f"sessionStorage.setItem('draft_stockops', '{encoded}');")
            except Exception: pass

        def restore_draft_values(state_json):
            import json
            try:
                state = json.loads(state_json)
                for k, v in state.items():
                    if k == 'items':
                        current_operation_items.clear()
                        for item in v:
                            if 'action' not in item:
                                item['action'] = '✕'
                            current_operation_items.append(item)
                        items_grid.rows = current_operation_items
                    elif k in input_refs and hasattr(input_refs[k], 'set_value'):
                        input_refs[k].set_value(v)
                update_saved_state()
                ui.run_javascript("sessionStorage.removeItem('draft_stockops');")
            except Exception as ex:
                print(f"Stock ops draft restore error: {ex}")

        async def check_for_draft():
            import json
            result = await ui.run_javascript("sessionStorage.getItem('draft_stockops');", timeout=5.0)
            if result:
                try:
                    state = json.loads(result)
                    barcode = state.get('barcode', '')
                    num_items = len(state.get('items', []))
                    hint = f'barcode "{barcode}"' if barcode else f'{num_items} items'
                    with ui.dialog() as d, ui.card().classes('p-6 rounded-xl'):
                        ui.label('\U0001f4dd Unsaved Draft Found').classes('text-lg font-bold mb-2')
                        ui.label(f'You have an unsaved draft with {hint}.').classes('text-gray-600 mb-4 text-sm')
                        with ui.row().classes('w-full justify-end gap-3'):
                            ui.button('Discard', on_click=lambda: (ui.run_javascript("sessionStorage.removeItem('draft_stockops');"), d.close())).props('flat color=gray')
                            ui.button('Restore Draft', color='purple', on_click=lambda: (restore_draft_values(result), d.close())).props('unelevated')
                    d.open()
                except Exception: pass

        ui.timer(5.0, save_draft)
        ui.timer(1.5, check_for_draft, once=True)
        
    finally:
        if standalone:
            layout_container.__exit__(None, None, None)


@ui.page('/stockoperations')
def stock_operations_page_route():
    stock_operations_page(standalone=True)

# Alias for legacy imports
StockOperationUI = stock_operations_page_route