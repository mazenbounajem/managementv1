from nicegui import ui
from connection import connection
from modern_design_system import ModernDesignSystem as MDS
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput, ModernTable, ModernActionBar
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
        input_refs['date'].set_value(datetime.now().strftime('%Y-%m-%dT%H:%M'))
        try:
            update_saved_state()
            ui.run_javascript("sessionStorage.removeItem('draft_stockops');")
        except: pass

    # Wrap content in ModernPageLayout only if standalone, otherwise just render the content
    if standalone:
        layout_container = ModernPageLayout("Stock Control Center")
        layout_container.__enter__()
    
    try:
        with ui.row().classes('w-full gap-6 items-start animate-fade-in p-4'):
            # Left Column: Active Operation / Inputs
            with ui.column().classes('w-[360px] gap-4'):
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
                    with ui.column().classes('w-full gap-4'):
                        input_refs['barcode'] = ui.input('Scan Barcode').classes('w-full glass-input').props('dark rounded outlined dense')
                        input_refs['quantity'] = ui.number('Quantity', value=1).classes('w-full glass-input').props('dark rounded outlined dense')
                        input_refs['reason'] = ui.textarea('Adjustment Reason').classes('w-full glass-input').props('dark rounded outlined dense')
                        ModernButton('Add to Operation', icon='playlist_add', on_click=lambda: ui.notify('Item added (Simulation)', color='info'), variant='primary').classes('w-full h-12 mt-2')

            # Center Column: History Registry
            with ui.column().classes('flex-1 gap-4'):
                with ModernCard(glass=True).classes('w-full p-6'):
                    ui.label('Operations Registry').classes('text-xl font-black mb-6 text-white uppercase tracking-widest')
                    
                    history_cols = [
                        {'headerName': 'ID', 'field': 'id', 'width': 70},
                        {'headerName': 'Date', 'field': 'date', 'flex': 1},
                        {'headerName': 'Type', 'field': 'type', 'width': 130},
                        {'headerName': 'Items', 'field': 'items', 'width': 80},
                        {'headerName': 'Ref', 'field': 'ref', 'width': 120}
                    ]
                    
                    history_grid = ui.aggrid({
                        'columnDefs': history_cols,
                        'rowData': [],
                        'defaultColDef': MDS.get_ag_grid_default_def(),
                        'rowSelection': 'single',
                    }).classes('w-full h-[600px] ag-theme-quartz-dark shadow-inner')

            # Right Column: Action Bar
            with ui.column().classes('w-80px items-center'):
                ModernActionBar(
                    on_new=clear_form,
                    on_save=lambda: ui.notify('Operation saved successfully (Simulation)', color='positive'),
                    on_undo=lambda: ui.notify('Undo not applicable here', color='warning'),
                    on_refresh=refresh_history,
                    on_chatgpt=lambda: ui.open('https://chatgpt.com', new_tab=True),
                    button_class='h-16',
                    classes=' '
                ).style('position: static; width: 80px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); margin-top: 0;')

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
                encoded = json.dumps(state).replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')
                ui.run_javascript(f"sessionStorage.setItem('draft_stockops', '{encoded}');")
            except Exception: pass

        def restore_draft_values(state_json):
            import json
            try:
                state = json.loads(state_json)
                for k, v in state.items():
                    if k in input_refs and hasattr(input_refs[k], 'set_value'):
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
                    hint = f'barcode "{barcode}"' if barcode else 'an unsaved stock operation'
                    with ui.dialog() as d, ui.card().classes('p-6 rounded-xl'):
                        ui.label('\U0001f4dd Unsaved Draft Found').classes('text-lg font-bold mb-2')
                        ui.label(f'You have an unsaved draft for {hint}.').classes('text-gray-600 mb-4 text-sm')
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