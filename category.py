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
    return CategoryUI(standalone=standalone)

class CategoryUI:
    def __init__(self, standalone=False):
        self.standalone = standalone
        self.input_refs = {}
        self.photo_preview = None
        self.table = None
        self.create_ui()

    def handle_photo_upload(self, e):
        try:
            content = e.content.read()
            base64_str = base64.b64encode(content).decode('ascii')
            self.input_refs['photo'].set_value(f"data:image/png;base64,{base64_str}")
            self.photo_preview.set_source(f"data:image/png;base64,{base64_str}")
            ui.notify('Category photo uploaded', color='positive')
            e.sender.reset() # Clear the upload list
        except Exception as ex:
            ui.notify(f'Upload error: {ex}', color='negative')

    def remove_photo(self):
        self.input_refs['photo'].set_value('')
        self.photo_preview.set_source('https://via.placeholder.com/150')
        if 'uploader' in self.input_refs:
            self.input_refs['uploader'].reset()
        ui.notify('Banner removed from form')

    def refresh_table(self):
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
        if self.table:
            self.table.options['rowData'] = rows
            self.table.update()
            self._load_last_row()

    def clear_inputs(self):
        for k, ref in self.input_refs.items():
            if k == 'uploader': continue
            ref.set_value('')
        self.photo_preview.set_source('https://via.placeholder.com/150')
        if 'uploader' in self.input_refs:
            self.input_refs['uploader'].reset()
        if self.table:
            self.table.classes(add='dimmed')
            self.table.run_method('deselectAll')
        try:
            self.update_saved_state()
            ui.run_javascript("sessionStorage.removeItem('draft_category');")
        except: pass

    def _load_last_row(self):
        """Load the most recent category into the form and undim table"""
        if not self.table.options.get('rowData'):
            return
        row = self.table.options['rowData'][0]
        cid = row['id']
        self.input_refs['id'].set_value(str(cid))
        self.input_refs['name'].set_value(row.get('name') or '')
        self.input_refs['description'].set_value(row.get('description') or '')
        
        # Fetch photo on-demand
        photo_data = []
        connection.contogetrows("SELECT photo FROM categories WHERE id = ?", photo_data, params=(cid,))
        full_photo = photo_data[0][0] if photo_data else None
        self.input_refs['photo'].set_value(full_photo or '')
        if full_photo:
            self.photo_preview.set_source(full_photo)
        else:
            self.photo_preview.set_source('https://via.placeholder.com/150')
        
        if self.table:
            self.table.classes(remove='dimmed')

    def save_category(self):
        try:
            c_data = {k: ref.value for k, ref in self.input_refs.items() if k != 'uploader'}
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
                self.update_saved_state()
                ui.run_javascript("sessionStorage.removeItem('draft_category');")
            except: pass
            self.refresh_table()
            if self.table:
                self.table.classes(remove='dimmed')
        except Exception as e:
            ui.notify(f'Error: {e}', color='negative')

    def delete_category(self):
        cid = self.input_refs['id'].value
        if not cid: return ui.notify('Select a category', color='warning')
        connection.deleterow("DELETE FROM categories WHERE id=?", cid)
        ui.notify('Category deleted')
        self.clear_inputs()
        self.refresh_table()

    def create_ui(self):
        with ModernPageLayout("Category Management", standalone=self.standalone):
            with ui.row().classes('w-full gap-6 items-start p-4 animate-fade-in'):
                # Left Column: History (Top) and Entry (Bottom)
                with ui.column().classes('flex-1 gap-4'):
                    with ui.splitter(horizontal=True, value=40).classes('w-full h-[850px]') as splitter:
                        with splitter.before:
                            with ModernCard(glass=True).classes('w-full h-full p-6'):
                                ui.label('Available Categories').classes('text-lg font-black text-white mb-4 ml-2')
                                
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
                                    return `<div style="width: 24px; height: 24px; border-radius: 4px; background: #333; display: flex; align-items: center; justify-content: center; overflow: hidden;">
                                        <span style="font-size: 8px; color: #aaa;">IMG</span>
                                    </div>`;
                                };
                                </script>
                                ''')

                                self.table = ui.aggrid({
                                    'columnDefs': cols,
                                    'rowData': [],
                                    'defaultColDef': {'sortable': True, 'filter': True},
                                    'rowSelection': 'single',
                                }).classes('w-full h-80 ag-theme-quartz-dark')

                                def on_row(e):
                                    try:
                                        row = e.args.get('data')
                                        if not row: return
                                        cid = row.get('id')
                                        if cid is None: return
                                        
                                        self.input_refs['id'].set_value(str(cid))
                                        self.input_refs['name'].set_value(row.get('name') or row.get('category_name', ''))
                                        self.input_refs['description'].set_value(row.get('description', ''))
                                        
                                        photo_data = []
                                        connection.contogetrows("SELECT photo FROM categories WHERE id = ?", photo_data, params=(cid,))
                                        full_photo = photo_data[0][0] if photo_data else None
                                        
                                        self.input_refs['photo'].set_value(full_photo or '')
                                        if full_photo:
                                            self.photo_preview.set_source(full_photo)
                                        else:
                                            self.photo_preview.set_source('https://via.placeholder.com/150')
                                        
                                        if self.table:
                                            self.table.classes(remove='dimmed')
                                        try: self.update_saved_state()
                                        except: pass
                                    except Exception as ex:
                                        ui.notify(f'Display error: {ex}', color='warning')

                                self.table.on('cellClicked', on_row)

                        with splitter.after:
                            with ui.row().classes('w-full gap-4 pt-4'):
                                # Category Photo
                                with ModernCard(glass=True).classes('w-[300px] p-6 flex flex-col items-center'):
                                    ui.label('Category Banner').classes('text-[10px] font-black uppercase text-purple-400 tracking-wider mb-4 w-full text-center')
                                    self.photo_preview = ui.image('https://via.placeholder.com/150').classes('w-full h-32 rounded-xl object-cover border-2 border-white/10 mb-4 shadow-sm')
                                    
                                    with ui.row().classes('w-full gap-2 mb-2'):
                                        self.input_refs['photo'] = ui.input().classes('hidden') # State holder
                                        self.input_refs['uploader'] = ui.upload(on_upload=self.handle_photo_upload, auto_upload=True).props('flat bordered dark dense label="Upload Banner" accept=".jpg,.png,.jpeg"').classes('flex-1')
                                        ui.button(icon='delete', on_click=self.remove_photo).props('flat round color=red').tooltip('Remove banner')

                                # Category Info
                                with ModernCard(glass=True).classes('flex-1 p-6'):
                                    ui.label('Category details').classes('text-[10px] font-black uppercase text-purple-400 tracking-wider mb-4')
                                    self.input_refs['id'] = ui.input('ID').props('readonly outlined dense dark').classes('hidden')
                                    self.input_refs['name'] = ModernInput('Category Name', icon='label')
                                    self.input_refs['description'] = ui.textarea('Description').props('outlined dense dark').classes('w-full mt-2')

                # Action Bar Panel (Right Side of Editor)
                with ui.column().classes('w-80px items-center'):
                    from modern_ui_components import ModernActionBar
                    ModernActionBar(
                        on_new=self.clear_inputs,
                        on_save=self.save_category,
                        on_delete=self.delete_category,
                        on_refresh=self.refresh_table,
                        on_chatgpt=lambda: ui.run_javascript('window.open("https://chatgpt.com", "_blank");'),
                        button_class='h-16',
                        classes=' '
                    ).style('position: static; width: 80px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); margin-top: 0;')

        # Initial data load
        ui.timer(0.1, self.refresh_table, once=True)
        ui.timer(0.2, self.update_saved_state, once=True)
        ui.timer(5.0, self.save_draft)
        ui.timer(1.5, self.check_for_draft, once=True)

    # State tracking
    saved_state = {}

    def capture_state(self):
        state = {}
        for k, ref in self.input_refs.items():
            if k == 'uploader': continue
            if hasattr(ref, 'value'):
                state[k] = ref.value
        return state

    def update_saved_state(self):
        self.saved_state = self.capture_state().copy()

    def is_dirty(self):
        current_state = self.capture_state()
        if not current_state.get('id') and not current_state.get('name'):
            return False
        for k, v in current_state.items():
            if k == 'photo': continue
            s_val = self.saved_state.get(k, '')
            if str(v or '') != str(s_val or ''):
                return True
        return False
        
    def save_draft(self):
        if not self.is_dirty(): return
        import json
        try:
            state = {k: v for k, v in self.capture_state().items() if k != 'photo'}
            encoded = json.dumps(state).replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')
            ui.run_javascript(f"sessionStorage.setItem('draft_category', '{encoded}');")
        except Exception: pass

    async def check_for_draft(self):
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
                        ui.button('Restore Draft', color='purple', on_click=lambda: (self.restore_draft_values(result), d.close())).props('unelevated')
                d.open()
            except Exception: pass

    def restore_draft_values(self, state_json):
        import json
        try:
            state = json.loads(state_json)
            for k, v in state.items():
                if k in self.input_refs and hasattr(self.input_refs[k], 'set_value'):
                    self.input_refs[k].set_value(v)
            self.update_saved_state()
            ui.run_javascript("sessionStorage.removeItem('draft_category');")
        except Exception: pass

@ui.page('/category')
def category_page_route():
    category_page(standalone=True)

category_content = lambda standalone=False, user=None: category_page(standalone)
