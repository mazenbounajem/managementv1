from nicegui import ui
from connection import connection
from modern_design_system import ModernDesignSystem as MDS
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput, ModernTable
from session_storage import session_storage
from datetime import datetime
import base64
import io

def category_page(standalone=False):
    # Auth
    user = session_storage.get('user')
    if not user:
        if not standalone:
            ui.notify('Please login', color='negative')
            ui.navigate.to('/login')
        return

    # State
    input_refs = {}
    # Removed category_photos cache to keep memory lightweight

    def handle_photo_upload(e):
        try:
            content = e.content.read()
            base64_str = base64.b64encode(content).decode('ascii')
            input_refs['photo'].set_value(f"data:image/png;base64,{base64_str}")
            photo_preview.set_source(f"data:image/png;base64,{base64_str}")
            ui.notify('Category photo uploaded', color='positive')
        except Exception as ex:
            ui.notify(f'Upload error: {ex}', color='negative')

    def refresh_table():
        data = []
        # Select metadata and flag for photo existence
        sql = "SELECT id, category_name, description, created_at, CASE WHEN photo IS NOT NULL AND photo != '' THEN 1 ELSE 0 END as has_photo FROM categories ORDER BY id DESC"
        connection.contogetrows(sql, data)
        rows = []
        
        for r in data:
            cid, name, desc, created, has_p = r
            rows.append({
                'id': cid, 
                'name': name, 
                'description': desc, 
                'created_at': created, 
                'has_photo': bool(has_p)
            })
        table.options['rowData'] = rows
        table.update()

    def clear_inputs():
        for k, ref in input_refs.items():
            ref.set_value('')
        photo_preview.set_source('https://via.placeholder.com/150')
        table.run_method('deselectAll')
        try:
            update_saved_state()
            ui.run_javascript("sessionStorage.removeItem('draft_category');")
        except: pass

    def save_category():
        try:
            c_data = {k: ref.value for k, ref in input_refs.items()}
            if not c_data['name']:
                return ui.notify('Category name required', color='negative')

            if c_data['id']:
                sql = "UPDATE categories SET category_name=?, description=?, photo=? WHERE id=?"
                params = (c_data['name'], c_data['description'], c_data['photo'], c_data['id'])
            else:
                sql = "INSERT INTO categories (category_name, description, photo, created_at) VALUES (?, ?, ?, GETDATE())"
                params = (c_data['name'], c_data['description'], c_data['photo'])

            connection.insertingtodatabase(sql, params)
            ui.notify('Category saved', color='positive')
            try:
                update_saved_state()
                ui.run_javascript("sessionStorage.removeItem('draft_category');")
            except: pass
            refresh_table()
        except Exception as e:
            ui.notify(f'Error: {e}', color='negative')

    def delete_category():
        cid = input_refs['id'].value
        if not cid: return ui.notify('Select a category', color='warning')
        connection.deleterow("DELETE FROM categories WHERE id=?", cid)
        ui.notify('Category deleted')
        clear_inputs()
        refresh_table()

    with ModernPageLayout("Category Management", standalone=standalone):
        with ui.column().classes('w-full gap-6 p-4 animate-fade-in'):
            
            with ui.row().classes('w-full gap-6 items-start'):
                # Left Column: Form
                with ui.column().classes('w-[380px] gap-4'):
                    # Category Photo
                    with ModernCard().classes('w-full p-6 flex flex-col items-center'):
                        ui.label('Category Banner').classes('text-lg font-bold mb-4 w-full text-center')
                        photo_preview = ui.image('https://via.placeholder.com/150').classes('w-full h-32 rounded-xl object-cover border-2 border-accent/10 mb-4 shadow-sm')
                        input_refs['photo'] = ui.input().classes('hidden') # State holder
                        ui.upload(on_upload=handle_photo_upload, auto_upload=True).props('flat bordered dense label="Upload Banner" accept=".jpg,.png,.jpeg"').classes('w-full')

                    with ModernCard().classes('w-full p-6'):
                        ui.label('Category Info').classes('text-lg font-bold mb-4')
                        input_refs['id'] = ui.input('ID').props('readonly outlined dense').classes('hidden')
                        input_refs['name'] = ModernInput('Category Name', icon='label')
                        input_refs['description'] = ui.textarea('Description').props('outlined dense').classes('w-full mt-2')

                # Right Column: List
                with ui.column().classes('flex-1'):
                    with ModernCard().classes('w-full p-4'):
                        ui.label('Available Categories').classes('text-lg font-bold mb-4 ml-2')
                        
                        cols = [
                            {'headerName': 'Icon', 'field': 'photo', 'width': 60, 'cellRenderer': 'img_renderer'},
                            {'headerName': 'Name', 'field': 'name', 'flex': 1},
                            {'headerName': 'Description', 'field': 'description', 'flex': 2},
                            {'headerName': 'Created', 'field': 'created_at', 'width': 180}
                        ]
                        
                        ui.add_body_html('''
                        <script>
                        window.img_renderer = (params) => {
                            if (!params.data.has_photo) return "";
                            // Using the tiny preview stored in the grid
                            return `<div style="width: 24px; height: 24px; border-radius: 4px; background: #333; display: flex; align-items: center; justify-content: center; overflow: hidden;">
                                <span style="font-size: 8px; color: #aaa;">IMG</span>
                            </div>`;
                        };
                        </script>
                        ''')

                        table = ui.aggrid({
                            'columnDefs': cols,
                            'rowData': [],
                            'defaultColDef': {'sortable': True, 'filter': True},
                            'rowSelection': 'single',
                        }).classes('w-full h-[500px] ag-theme-quartz-dark')

                        def on_row(e):
                            try:
                                # Instant response from click event data
                                row = e.args.get('data')
                                if not row: return
                                
                                cid = row.get('id')
                                if cid is None: return
                                
                                # Update inputs immediately
                                input_refs['id'].set_value(str(cid))
                                input_refs['name'].set_value(row.get('name') or row.get('category_name', ''))
                                input_refs['description'].set_value(row.get('description', ''))
                                
                                # Fetch high-res photo on-demand from database
                                photo_data = []
                                connection.contogetrows("SELECT photo FROM categories WHERE id = ?", photo_data, params=(cid,))
                                full_photo = photo_data[0][0] if photo_data else None
                                
                                input_refs['photo'].set_value(full_photo or '')
                                if full_photo:
                                    photo_preview.set_source(full_photo)
                                    photo_preview.set_source('https://via.placeholder.com/150')
                                
                                try: update_saved_state()
                                except: pass
                            except Exception as ex:
                                print(f"Category selection error: {ex}")
                                ui.notify(f'Display error: {ex}', color='warning')

                        table.on('cellClicked', on_row)

                # Action Bar Panel (Right Side of Editor)
                with ui.column().classes('w-80px items-center'):
                    from modern_ui_components import ModernActionBar
                    ModernActionBar(
                        on_new=clear_inputs,
                        on_save=save_category,
                        on_delete=delete_category,
                        on_refresh=refresh_table,
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
        
        # If no category selected and form is empty, it's not dirty
        if not current_state.get('id') and not current_state.get('name'):
            return False
            
        for k, v in current_state.items():
            if k == 'photo': continue
            s_val = saved_state.get(k, '')
            
            v_str = str(v) if v is not None else ''
            s_str = str(s_val) if s_val is not None else ''
            
            if v_str != s_str:
                if not v_str and not s_str: continue
                return True
        return False
        
    try:
        from tabbed_dashboard import tab_dirty_callbacks
        tab_dirty_callbacks['category'] = is_dirty
        tab_dirty_callbacks['category_content'] = is_dirty
    except ImportError:
        pass

    ui.timer(0.1, refresh_table, once=True)
    ui.timer(0.2, update_saved_state, once=True)

    # ── Auto-Save Drafts ────────────────────────────────────────────────────────
    def save_draft():
        if not is_dirty(): return
        import json
        try:
            state = {k: v for k, v in capture_state().items() if k != 'photo'}
            encoded = json.dumps(state).replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')
            ui.run_javascript(f"sessionStorage.setItem('draft_category', '{encoded}');")
        except Exception: pass

    def restore_draft_values(state_json):
        import json
        try:
            state = json.loads(state_json)
            for k, v in state.items():
                if k in input_refs and hasattr(input_refs[k], 'set_value'):
                    input_refs[k].set_value(v)
            update_saved_state()
            ui.run_javascript("sessionStorage.removeItem('draft_category');")
        except Exception as ex:
            print(f"Category draft restore error: {ex}")

    async def check_for_draft():
        import json
        result = await ui.run_javascript("sessionStorage.getItem('draft_category');", timeout=5.0)
        if result:
            try:
                state = json.loads(result)
                name = state.get('name', '')
                hint = f'"{name}"' if name else 'an unsaved category'
                with ui.dialog() as d, ui.card().classes('p-6 rounded-xl'):
                    ui.label('\U0001f4dd Unsaved Draft Found').classes('text-lg font-bold mb-2')
                    ui.label(f'You have an unsaved draft for {hint}.').classes('text-gray-600 mb-4 text-sm')
                    with ui.row().classes('w-full justify-end gap-3'):
                        ui.button('Discard', on_click=lambda: (ui.run_javascript("sessionStorage.removeItem('draft_category');"), d.close())).props('flat color=gray')
                        ui.button('Restore Draft', color='purple', on_click=lambda: (restore_draft_values(result), d.close())).props('unelevated')
                d.open()
            except Exception: pass

    ui.timer(5.0, save_draft)
    ui.timer(1.5, check_for_draft, once=True)




@ui.page('/category')
def category_page_route():
    category_page()

category_content = lambda standalone=False, user=None: category_page(standalone)
