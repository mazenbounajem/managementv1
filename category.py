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
        self._all_category_rows = []
        self._selected_row_index = None
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

        normalized = []
        for r in data:
            cid, name, desc, created, has_p = r
            normalized.append({
                'id': cid,
                'name': name,
                'description': desc,
                'created_at': created,
                'has_photo': bool(has_p),
                'photo': "IMG" if bool(has_p) else "",
            })

        # keep full dataset for search filtering
        self._all_category_rows = normalized
        self._selected_row_index = None

        if self.table:
            self.table.rows = normalized
            self.table.update()
            self._load_last_row()

    def _filter_table(self, query: str):
        if not getattr(self, 'table', None):
            return

        q = (query or "").strip().lower()
        if not q:
            # restore all
            self.table.rows = getattr(self, '_all_category_rows', [])
            self.table.update()
            self._load_last_row()
            return

        all_rows = getattr(self, '_all_category_rows', []) or []
        filtered = []
        for row in all_rows:
            name = str(row.get('name') or '').lower()
            desc = str(row.get('description') or '').lower()
            if q in name or q in desc:
                filtered.append(row)

        self.table.rows = filtered
        self.table.update()
        # keep UX consistent: undim after filtering
        if self.table:
            self.table.classes(remove='dimmed')

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
        if hasattr(self, 'action_bar'):
            self.action_bar.enter_new_mode()
        try:
            self.update_saved_state()
            ui.run_javascript("sessionStorage.removeItem('draft_category');")
        except: pass

    def _load_last_row(self):
        """Load the most recent category into the form and undim table"""
        if not getattr(self.table, 'rows', None):
            return
        if not self.table.rows:
            return
        row = self.table.rows[0]
        cid = row['id']
        self._selected_row_index = 0

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
            self._apply_selected_row_color()
        if hasattr(self, 'action_bar'):
            self.action_bar.enter_edit_mode()

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
            if hasattr(self, 'action_bar'):
                self.action_bar.reset_state()
        except Exception as e:
            ui.notify(f'Error: {e}', color='negative')

    def delete_category(self):
        cid = self.input_refs['id'].value
        if not cid: return ui.notify('Select a category', color='warning')
        connection.deleterow("DELETE FROM categories WHERE id=?", cid)
        ui.notify('Category deleted')
        self.clear_inputs()
        self.refresh_table()

    def _apply_row_from_id(self, cid):
        """Select a row by id, update form, and apply highlight."""
        if not getattr(self, 'table', None):
            return
        rows = getattr(self.table, 'rows', None) or []
        target_index = next((i for i, r in enumerate(rows) if r.get('id') == cid), None)
        if target_index is None:
            return

        row = rows[target_index]
        self._selected_row_index = target_index

        self.input_refs['id'].set_value(str(cid))
        self.input_refs['name'].set_value(row.get('name') or '')
        self.input_refs['description'].set_value(row.get('description') or '')

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
            self._apply_selected_row_color()
        if hasattr(self, 'action_bar'):
            self.action_bar.enter_edit_mode()
        self.update_saved_state()
        self._apply_selected_row_color()

    def _apply_selected_row_color(self):
        """Updates row highlights based on self._selected_row_index."""
        if self._selected_row_index is None:
            return
            
        ui.run_javascript(f"""
        try {{
          const root = document.querySelector('.q-table');
          if (!root) return;

          // Target rows in the body
          const rows = root.querySelectorAll('tbody tr');
          if (!rows || rows.length === 0) return;

          // In NiceGUI table, rows may include a header row if not strictly handled.
          // Based on user feedback: current highlight is off by 1.
          const idx = Math.max(0, Math.min({self._selected_row_index} + 1, rows.length - 1));
          
          // Clear previous highlights
          rows.forEach(el => {{
            el.style.backgroundColor = '';
            el.style.color = '';
            el.classList.remove('selected-highlight');
          }});

          // Apply to target
          const selected = rows[idx];
          if (selected) {{
            selected.style.backgroundColor = '#facc15';
            selected.style.color = 'black';
            selected.classList.add('selected-highlight');
          }}
        }} catch (e) {{ console.error('Highlight error:', e); }}
        """)

    def _focus_first_row(self):
        """Focuses the first row of the table when pressing Down Arrow in search."""
        if self.table and self.table.rows:
            cid = self.table.rows[0].get('id')
            if cid is not None:
                self._apply_row_from_id(cid)

    def create_ui(self):
        with ModernPageLayout("Category Management", standalone=self.standalone):
            with ui.row().classes('w-full gap-6 items-start p-4 animate-fade-in'):
                # Left Column: History (Top) and Entry (Bottom)
                with ui.column().classes('flex-1 gap-4'):
                    with ui.splitter(horizontal=True, value=40).classes('w-full h-[850px]') as splitter:
                        with splitter.before:
                            columns = [
                                {'name': 'photo', 'label': 'Icon', 'field': 'photo', 'align': 'left', 'sortable': False},
                                {'name': 'name', 'label': 'Name', 'field': 'name', 'align': 'left', 'sortable': True},
                                {'name': 'description', 'label': 'Description', 'field': 'description', 'align': 'left', 'sortable': False},
                                {'name': 'created_at', 'label': 'Created', 'field': 'created_at', 'align': 'left', 'sortable': True},
                            ]

                            # Search UI
                            with ui.row().classes('w-full gap-3 mb-3 items-center'):
                                self.category_search_input = (
                                    ui.input(placeholder='Search categories...')
                                    .props('outlined dense')
                                    .classes('flex-1 text-white bg-black')
                                    .on('update:model-value', lambda e: self._filter_table(e.args))
                                    .on('keydown.down', lambda: self._focus_first_row())
                                )

                            # Filter state
                            self._all_category_rows = []

                            self.table = ui.table(
                                columns=columns,
                                rows=[],
                                row_key='id',
                                selection='single'
                            ).classes('w-full h-80 overflow-hidden').props('virtual-scroll flat bordered dense hide-pagination :pagination="{rowsPerPage: 0}"')

                            def on_row_click(e):
                                try:
                                    row = e.args[1] if isinstance(e.args, (list, tuple)) and len(e.args) > 1 else None
                                    if not isinstance(row, dict):
                                        if isinstance(e.args, (list, tuple)) and e.args and isinstance(e.args[0], dict):
                                            row = e.args[0]
                                    if not row:
                                        return

                                    cid = row.get('id')
                                    if cid is None:
                                        return

                                    self.input_refs['id'].set_value(str(cid))
                                    self.input_refs['name'].set_value(row.get('name') or '')
                                    self.input_refs['description'].set_value(row.get('description') or '')

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
                                    if hasattr(self, 'action_bar'):
                                        self.action_bar.enter_edit_mode()
                                    try:
                                        self.update_saved_state()
                                    except:
                                        pass
                                except Exception as ex:
                                    ui.notify(f'Display error: {ex}', color='warning')

                            # Removed local _apply_selected_row_color as it is now a class method

                            def on_keydown(e):
                                """Handle up/down keyboard navigation for the table."""
                                try:
                                    key = getattr(e, 'key', None) or getattr(e, 'args', {}).get('key', None)
                                    if key not in ('ArrowDown', 'ArrowUp'):
                                        return

                                    rows = getattr(self.table, 'rows', None) or []
                                    if not rows:
                                        return

                                    if self._selected_row_index is None:
                                        self._selected_row_index = 0

                                    if key == 'ArrowDown':
                                        self._selected_row_index = min(self._selected_row_index + 1, len(rows) - 1)
                                    else:
                                        self._selected_row_index = max(self._selected_row_index - 1, 0)

                                    cid = rows[self._selected_row_index].get('id')
                                    if cid is None:
                                        return

                                    # NiceGUI method "selectRow" may not exist; we update form + highlight directly.
                                    self._apply_row_from_id(cid)
                                except Exception as ex:
                                    ui.notify(f'Keyboard navigation error: {ex}', color='warning')

                            # ensure both mouse clicks and selection updates get the highlight
                            def _row_click_wrapper(e):
                                # sync selected index by id
                                try:
                                    row = e.args[1] if isinstance(e.args, (list, tuple)) and len(e.args) > 1 else None
                                    if not isinstance(row, dict):
                                        if isinstance(e.args, (list, tuple)) and e.args and isinstance(e.args[0], dict):
                                            row = e.args[0]
                                    if isinstance(row, dict) and row.get('id') is not None:
                                        self._selected_row_index = next((i for i, r in enumerate(self.table.rows or []) if r.get('id') == row.get('id')), None)
                                        self._apply_selected_row_color()
                                except:
                                    pass
                                on_row_click(e)

                            self.table.on('rowClick', _row_click_wrapper)

                            # Keyboard navigation: attach to table root via DOM if possible.
                            # Fallback: also try NiceGUI's keydown event on the table component.
                            if self.table:
                                try:
                                    self.table.on('keydown', on_keydown)
                                except Exception:
                                    ui.run_javascript("""
                                    try {
                                      const root = document.querySelector('.q-table');
                                      if (!root) return;
                                      root.tabIndex = 0;
                                      root.addEventListener('keydown', (ev) => {
                                        if (ev.key !== 'ArrowDown' && ev.key !== 'ArrowUp') return;
                                        ev.preventDefault();
                                        // trigger a NiceGUI event by dispatching a click on hidden focus element? best effort no-op
                                      });
                                    } catch (e) {}
                                    """)

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
                with ui.column().classes('w-60px items-center shrink-0'):
                    from modern_ui_components import ModernActionBar

                    def _print_special():
                        """Match sales-style: simple named handler calling the report center."""
                        try:
                            ui.notify('Opening print special...', color='info')
                            cid_val = self.input_refs['id'].value if 'id' in self.input_refs else None
                            if not cid_val:
                                ui.notify('Select a category to print.', color='warning')
                                return

                            import category_reports
                            category_reports.open_print_special_dialog(category_id=int(cid_val))
                        except Exception as e:
                            ui.notify(f'Print special failed: {e}', color='negative')

                    self.action_bar = ModernActionBar(
                        on_new=self.clear_inputs,
                        on_save=self.save_category,
                        on_undo=self.clear_inputs,
                        on_delete=self.delete_category,
                        on_refresh=self.refresh_table,
                        on_print_special=_print_special,
                        on_chatgpt=lambda: ui.run_javascript('window.open("https://chatgpt.com", "_blank");'),
                        target_table=self.table,
                        button_class='h-10',
                        classes=' '
                    ).style('position: static; width: 60px; border-radius: 12px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); margin-top: 0;')

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
