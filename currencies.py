from nicegui import ui
from connection import connection
from session_storage import session_storage
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput

def currencies_content(standalone=False):
    """Content method for currencies that can be used in tabs"""
    if standalone:
        with ModernPageLayout("Currency Management", standalone=standalone):
            CurrencyUI(standalone=False)
    else:
        CurrencyUI(standalone=False)

@ui.page('/currencies')
def currencies_page_route():
    currencies_content(standalone=True)

class CurrencyUI:
    def __init__(self, standalone=True):
        self.standalone = standalone
        self.input_refs = {}
        self.initial_values = {}
        self.row_data = []
        self.table = None
        self.search_input = None
        self._all_category_rows = []
        self._selected_row_index = None
        self.create_ui()

    def clear_input_fields(self):
        self.input_refs['currency_code'].value = ''
        self.input_refs['currency_name'].value = ''
        self.input_refs['symbol'].value = ''
        self.input_refs['exchange_rate'].value = 1.0
        self.input_refs['is_active'].value = True
        self.input_refs['id'].value = ''
        if self.table:
            self.table.classes(add='dimmed')
            self.table.selected = None
        if hasattr(self, 'action_bar'):
            self.action_bar.enter_new_mode()
        ui.notify('Ready for new currency', color='info')

    def _load_last_row(self):
        """Load the most recent currency into the form and undim table"""
        if not getattr(self.table, 'rows', None):
            return
        if not self.table.rows:
            return
        row = self.table.rows[0]
        cid = row['id']
        self._selected_row_index = 0

        self.input_refs['id'].value = str(cid)
        self.input_refs['currency_code'].value = row.get('currency_code') or ''
        self.input_refs['currency_name'].value = row.get('currency_name') or ''
        self.input_refs['symbol'].value = row.get('symbol') or ''
        self.input_refs['exchange_rate'].value = row.get('exchange_rate') or 1.0
        self.input_refs['is_active'].value = row.get('is_active')

        self.initial_values = {
            'currency_code': row.get('currency_code') or '',
            'currency_name': row.get('currency_name') or '',
            'symbol': row.get('symbol') or '',
            'exchange_rate': row.get('exchange_rate') or 1.0,
            'is_active': row.get('is_active'),
            'id': str(cid)
        }

        if self.table:
            self.table.classes(remove='dimmed')
            self._apply_selected_row_color()

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

        self.input_refs['id'].value = str(cid)
        self.input_refs['currency_code'].value = row.get('currency_code') or ''
        self.input_refs['currency_name'].value = row.get('currency_name') or ''
        self.input_refs['symbol'].value = row.get('symbol') or ''
        self.input_refs['exchange_rate'].value = row.get('exchange_rate') or 1.0
        self.input_refs['is_active'].value = row.get('is_active')

        if self.table:
            self.table.classes(remove='dimmed')

        self._apply_selected_row_color()

    def _apply_selected_row_color(self):
        """Updates row highlights based on self._selected_row_index."""
        if self._selected_row_index is None:
            return

        ui.run_javascript(f"""
        try {{
          const root = document.querySelector('.q-table');
          if (!root) return;

          const rows = root.querySelectorAll('tbody tr');
          if (!rows || rows.length === 0) return;

          const idx = Math.max(0, Math.min({self._selected_row_index} + 1, rows.length - 1));

          rows.forEach(el => {{
            el.style.backgroundColor = '';
            el.style.color = '';
            el.classList.remove('selected-highlight');
          }});

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

    def save_currency(self):
        currency_code = self.input_refs['currency_code'].value.upper()
        currency_name = self.input_refs['currency_name'].value
        symbol = self.input_refs['symbol'].value
        exchange_rate = float(self.input_refs['exchange_rate'].value) if self.input_refs['exchange_rate'].value else 1.0
        is_active = self.input_refs['is_active'].value
        id_value = self.input_refs['id'].value

        if not currency_code or not currency_name:
            ui.notify('Currency Code and Name are required', color='warning')
            return

        try:
            if id_value:
                sql = "UPDATE currencies SET currency_code=?, currency_name=?, symbol=?, exchange_rate=?, is_active=?, updated_at=GETDATE() WHERE id=?"
                values = (currency_code, currency_name, symbol, exchange_rate, is_active, id_value)
            else:
                sql = "INSERT INTO currencies (currency_code, currency_name, symbol, exchange_rate, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, GETDATE(), GETDATE())"
                values = (currency_code, currency_name, symbol, exchange_rate, is_active)

            connection.insertingtodatabase(sql, values)
            ui.notify('Currency saved successfully', color='positive')
            if self.table:
                self.table.classes(remove='dimmed')
            if hasattr(self, 'action_bar'):
                self.action_bar.reset_state()
            self.refresh_table()
        except Exception as e:
            ui.notify(f'Error saving currency: {str(e)}', color='negative')

    def undo_changes(self):
        for field in ['currency_code', 'currency_name', 'symbol', 'exchange_rate', 'is_active', 'id']:
            if field in self.initial_values:
                self.input_refs[field].value = self.initial_values[field]
        if self.table:
            self.table.classes(remove='dimmed')
        if hasattr(self, 'action_bar'):
            self.action_bar.reset_state()
        ui.notify('Changes reverted', color='info')

    def delete_currency(self):
        id_value = self.input_refs['id'].value
        if not id_value:
            ui.notify('Please select a currency to delete', color='warning')
            return

        try:
            sql = "DELETE FROM currencies WHERE id=?"
            connection.deleterow(sql, id_value)
            ui.notify('Currency deleted successfully', color='positive')
            if self.table:
                self.table.classes(remove='dimmed')
            self.clear_input_fields()
            self.refresh_table()
        except Exception as e:
            ui.notify(f'Error deleting currency: {str(e)}', color='negative')

    def refresh_table(self):
        try:
            data = []
            connection.contogetrows("SELECT id, currency_code, currency_name, symbol, exchange_rate, is_active, created_at FROM currencies ORDER BY id DESC", data)

            normalized = []
            for row in data:
                normalized.append({
                    'id': row[0],
                    'currency_code': row[1],
                    'currency_name': row[2],
                    'symbol': row[3] or '',
                    'exchange_rate': float(row[4]) if row[4] is not None else 1.0,
                    'is_active': bool(row[5]),
                    'is_active_display': 'Active' if bool(row[5]) else 'Inactive',
                    'created_at': str(row[6])
                })

            self._all_category_rows = normalized
            self._selected_row_index = None

            if self.table:
                self.table.rows = normalized
                self.table.classes(remove='dimmed')
                self._load_last_row()

            self.row_data = normalized
            if not normalized:
                self.clear_input_fields()
        except Exception as e:
            ui.notify(f'Error refreshing data: {str(e)}', color='negative')


    def create_ui(self):
        # Wrap content in ModernPageLayout only if standalone, otherwise just render the content
        if self.standalone:
            layout_container = ModernPageLayout("Currency Management", standalone=True)
            layout_container.__enter__()
        
        try:
            with ui.row().classes('w-full gap-6 items-start'):
                # Left Column: List
                with ui.column().classes('w-1/2 gap-4'):
                    with ModernCard(glass=True).classes('w-full p-6'):
                        with ui.row().classes('w-full gap-3 mb-3 items-center'):
                            ui.label('Active Currencies').classes('text-xl font-black text-white uppercase tracking-widest opacity-70')
                            self.search_input = (
                                ui.input(placeholder='Search currencies...')
                                .props('outlined dense')
                                .classes('flex-1 text-white bg-black')
                                .on('update:model-value', lambda e: self._filter_table(e.args))
                                .on('keydown.down', lambda: self._focus_first_row())
                            )

                        self._all_category_rows = []

                        columns = [
                            {'name': 'currency_code', 'label': 'Code', 'field': 'currency_code', 'align': 'left', 'sortable': True},
                            {'name': 'currency_name', 'label': 'Name', 'field': 'currency_name', 'align': 'left', 'sortable': True},
                            {'name': 'exchange_rate', 'label': 'Rate', 'field': 'exchange_rate', 'align': 'right', 'sortable': True},
                            {'name': 'is_active', 'label': 'Active', 'field': 'is_active_display', 'align': 'center', 'sortable': False},
                        ]

                        self.table = ui.table(
                            columns=columns,
                            rows=[],
                            row_key='id',
                            selection='single'
                        ).classes('w-full h-[550px]').props('virtual-scroll flat bordered dense hide-pagination :pagination="{rowsPerPage: 0}"')

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

                                self.input_refs['id'].value = str(cid)
                                self.input_refs['currency_code'].value = row.get('currency_code') or ''
                                self.input_refs['currency_name'].value = row.get('currency_name') or ''
                                self.input_refs['symbol'].value = row.get('symbol') or ''
                                self.input_refs['exchange_rate'].value = row.get('exchange_rate') or 1.0
                                self.input_refs['is_active'].value = row.get('is_active')

                                self.initial_values = {
                                    'currency_code': row.get('currency_code') or '',
                                    'currency_name': row.get('currency_name') or '',
                                    'symbol': row.get('symbol') or '',
                                    'exchange_rate': row.get('exchange_rate') or 1.0,
                                    'is_active': row.get('is_active'),
                                    'id': str(cid)
                                }

                                if self.table:
                                    self.table.classes(remove='dimmed')
                            except Exception as ex:
                                ui.notify(f'Error selecting currency: {str(ex)}', color='negative')

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

                                self._apply_row_from_id(cid)
                            except Exception as ex:
                                ui.notify(f'Keyboard navigation error: {ex}', color='negative')

                        def _row_click_wrapper(e):
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

                        if self.table:
                            try:
                                self.table.on('keydown', on_keydown)
                            except Exception:
                                pass

                # Center Column: Details Form
                with ui.column().classes('flex-1 gap-4'):
                    with ModernCard(glass=True).classes('w-full p-6'):
                        ui.label('Exchange Rate Settings').classes('text-lg font-black mb-6 text-white uppercase tracking-widest')
                        
                        with ui.column().classes('w-full gap-4'):
                            with ui.row().classes('w-full gap-4'):
                                self.input_refs['currency_code'] = ui.input('Currency Code').classes('flex-1 glass-input text-white').props('dark rounded outlined dense')
                                self.input_refs['symbol'] = ui.input('Currency Symbol').classes('w-32 glass-input text-white').props('dark rounded outlined dense')
                            
                            self.input_refs['currency_name'] = ui.input('Full Currency Name').classes('w-full glass-input text-white').props('dark rounded outlined dense')
                            
                            with ui.row().classes('w-full gap-4'):
                                self.input_refs['exchange_rate'] = ui.number('Base Exchange Rate').classes('flex-1 glass-input text-white').props('dark rounded outlined dense')
                                self.input_refs['is_active'] = ui.switch('Status: Primary/Active', value=True).classes('text-white scale-90')
                            
                            self.input_refs['id'] = ui.input('System Reference ID').classes('w-full glass-input text-white opacity-50 font-mono').props('dark rounded outlined readonly dense')

                # Right Column: Action Bar
                with ui.column().classes('w-80px items-center'):
                    from modern_ui_components import ModernActionBar
                    self.action_bar = ModernActionBar(
                        on_new=self.clear_input_fields,
                        on_save=self.save_currency,
                        on_undo=self.undo_changes,
                        on_delete=self.delete_currency,
                        on_chatgpt=lambda: ui.run_javascript('window.open("https://chatgpt.com", "_blank");'),
                        on_refresh=self.refresh_table,
                        target_table=self.table,
                        button_class='h-16',
                        classes=' '
                    )
                    self.action_bar.style('position: static; width: 80px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); margin-top: 0;')

            ui.timer(0.1, self.refresh_table, once=True)
        finally:
            if self.standalone:
                layout_container.__exit__(None, None, None)

    def _filter_table(self, query: str):
        if not getattr(self, 'table', None):
            return

        q = (query or "").strip().lower()
        if not q:
            self.table.rows = getattr(self, '_all_category_rows', [])
            self._load_last_row()
            return

        all_rows = getattr(self, '_all_category_rows', []) or []
        filtered = []
        for row in all_rows:
            code = str(row.get('currency_code') or '').lower()
            name = str(row.get('currency_name') or '').lower()
            if q in code or q in name:
                filtered.append(row)

        self.table.rows = filtered
        if self.table:
            self.table.classes(remove='dimmed')