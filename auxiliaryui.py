from nicegui import ui
from connection import connection
from datetime import date
from uiaggridtheme import uiAggridTheme
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput
from modern_design_system import ModernDesignSystem as MDS
import accounting_helpers

def auxiliary_content(standalone: bool = False):
    """Content method for auxiliary management that can be used in tabs."""
    AuxiliaryUI(standalone=standalone)

@ui.page('/auxiliary')
def auxiliary_page_route():
    with ModernPageLayout("Auxiliary Management"):
        AuxiliaryUI(standalone=True)

class AuxiliaryUI:
    def __init__(self, standalone=True):
        self.standalone = standalone
        self.input_refs = {}
        self.initial_values = {}
        self.from_date = None
        self.to_date = None
        self.search_text = ''
        self.table = None
        self.all_rows = []
        self._selected_row_index = None
        self.create_ui()

    def clear_input_fields(self):
        self.input_refs['aux_code'].value = None
        self.input_refs['account_name'].value = ''
        self.input_refs['number'].value = ''
        self.input_refs['status'].value = 1
        self.input_refs['id'].value = ''
        if self.table:
            self.table.classes(add='dimmed')
            self.table.run_method('deselectAll')
        self._selected_row_index = None
        ui.notify('Ready for new entry', color='info')

    def _load_last_row(self):
        """Load the most recent auxiliary into the form and undim table."""
        if not getattr(self.table, 'rows', None):
            return
        if not self.table.rows:
            return
        row = self.table.rows[0]
        aux_id = row['id']
        self._selected_row_index = 0

        self.input_refs['id'].value = str(aux_id)
        self.input_refs['aux_code'].value = row.get('auxiliary_id')
        self.input_refs['account_name'].value = row.get('account_name') or ''
        self.input_refs['number'].value = row.get('aux_suffix') or ''
        self.input_refs['status'].value = row.get('status', 1)

        self.initial_values = {
            'aux_code': row.get('auxiliary_id'),
            'account_name': row.get('account_name') or '',
            'number': row.get('aux_suffix') or '',
            'status': row.get('status', 1),
            'id': str(aux_id)
        }

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

    def _apply_row_from_id(self, aux_id):
        """Select a row by id, update form, and apply highlight."""
        if not getattr(self, 'table', None):
            return
        rows = getattr(self.table, 'rows', None) or []
        target_index = next((i for i, r in enumerate(rows) if r.get('id') == aux_id), None)
        if target_index is None:
            return

        row = rows[target_index]
        self._selected_row_index = target_index

        self.input_refs['id'].value = str(aux_id)
        self.input_refs['aux_code'].value = row.get('auxiliary_id')
        self.input_refs['account_name'].value = row.get('account_name') or ''
        self.input_refs['number'].value = row.get('aux_suffix') or ''
        self.input_refs['status'].value = row.get('status', 1)

        self.initial_values = {
            'aux_code': row.get('auxiliary_id'),
            'account_name': row.get('account_name') or '',
            'number': row.get('aux_suffix') or '',
            'status': row.get('status', 1),
            'id': str(aux_id)
        }

        if self.table:
            self.table.classes(remove='dimmed')
            self._apply_selected_row_color()

    def _focus_first_row(self):
        """Focuses the first row of the table when pressing Down Arrow in search."""
        if self.table and self.table.rows:
            aux_id = self.table.rows[0].get('id')
            if aux_id is not None:
                self._apply_row_from_id(aux_id)

    def save_auxiliary(self):
        aux_code = self.input_refs['aux_code'].value
        account_name = self.input_refs['account_name'].value
        aux_suffix = self.input_refs['number'].value
        status = self.input_refs['status'].value
        id_value = self.input_refs['id'].value

        if not aux_code or not account_name or not aux_suffix:
            ui.notify('Code, Name and Number are required', color='warning')
            return

        try:
            full_aux_number = f"{aux_code}.{aux_suffix}"

            dup_check_sql = "SELECT COUNT(*) FROM auxiliary WHERE auxiliary_id=? AND number=?"
            params = [aux_code, full_aux_number]
            if id_value:
                dup_check_sql += " AND id<>?"
                params.append(id_value)

            dup_check_data = []
            connection.contogetrows(dup_check_sql, dup_check_data, params)
            dup_count = 0
            if dup_check_data:
                first = dup_check_data[0]
                v = first[0] if isinstance(first, (list, tuple)) else first
                try:
                    dup_count = int(getattr(v, 'value', v))
                except Exception:
                    dup_count = 0

            if dup_count > 0:
                ui.notify('Duplicate not allowed.', color='warning')
                return

            if id_value:
                sql = "UPDATE auxiliary SET auxiliary_id=?, account_name=?, number=?, update_date=GETDATE(), status=? WHERE id=?"
                values = (aux_code, account_name, full_aux_number, status, id_value)
            else:
                sql = "INSERT INTO auxiliary (auxiliary_id, account_name, number, update_date, status) VALUES (?, ?, ?, GETDATE(), ?)"
                values = (aux_code, account_name, full_aux_number, status)

            connection.insertingtodatabase(sql, values)
            ui.notify('Saved successfully', color='positive')
            if self.table:
                self.table.classes(remove='dimmed')
            self.refresh_table()
        except Exception as e:
            ui.notify(f'Error saving: {str(e)}', color='negative')

    def undo_changes(self):
        for field, val in self.initial_values.items():
            if field in self.input_refs:
                self.input_refs[field].value = val
        if self.table:
            self.table.classes(remove='dimmed')
        ui.notify('Changes reverted', color='info')
        if self._selected_row_index is not None:
            self._apply_selected_row_color()

    def delete_auxiliary(self):
        id_value = self.input_refs['id'].value
        if not id_value:
            ui.notify('Select a record to delete', color='warning')
            return
        try:
            connection.deleterow("DELETE FROM auxiliary WHERE id=?", id_value)
            ui.notify('Deleted successfully', color='positive')
            if self.table:
                self.table.classes(remove='dimmed')
            self.clear_input_fields()
            self.refresh_table()
        except Exception as e:
            ui.notify(f'Error deleting: {str(e)}', color='negative')

    def refresh_table(self):
        try:
            data = []
            sql = """
                SELECT
                    a.id,
                    LTRIM(RTRIM(CAST(a.auxiliary_id AS VARCHAR(50)))) as auxiliary_id,
                    LTRIM(RTRIM(l.Name_en)) AS ledger_name,
                    a.account_name,
                    a.number,
                    a.update_date,
                    a.status,
                    COALESCE(
                        (SELECT SUM(atl.debit) - SUM(atl.credit)
                         FROM accounting_transaction_lines atl
                         WHERE atl.auxiliary_id = a.id),
                        0
                    ) AS net_balance
                FROM auxiliary a
                LEFT JOIN Ledger l ON LTRIM(RTRIM(CAST(a.auxiliary_id AS VARCHAR(50)))) = LTRIM(RTRIM(CAST(l.AccountNumber AS VARCHAR(50))))
                ORDER BY a.id DESC
            """
            connection.contogetrows(sql, data)

            rows = []
            for row in data:
                auxiliary_id = str(row[1]) if row[1] is not None else ''
                aux_suffix = str(row[4]).strip() if row[4] is not None else ''
                rows.append({
                    'id':           row[0],
                    'auxiliary_id': auxiliary_id,
                    'ledger_name':  str(row[2]) if row[2] is not None else '',
                    'account_name': str(row[3]) if row[3] is not None else '',
                    'number':       aux_suffix,
                    'aux_suffix':   aux_suffix,
                    'update_date':  str(row[5])[:10] if row[5] is not None else '',
                    'status':       row[6],
                    'net_balance':  round(float(row[7]), 2) if row[7] is not None else 0.0,
                })

            self.all_rows = rows
            self.table.rows = rows
            self.table.update()
            self._selected_row_index = None
            self._load_last_row()
            self._update_code_options()
        except Exception as e:
            ui.notify(f'Error refreshing: {str(e)}', color='negative')

    def _filter_table(self, query: str):
        if not getattr(self, 'table', None):
            return

        q = (query or "").strip().lower()
        if not q:
            self.table.rows = getattr(self, 'all_rows', [])
            self.table.update()
            self._load_last_row()
            return

        all_rows = getattr(self, 'all_rows', []) or []
        filtered = []
        for row in all_rows:
            if q in str(row.get('auxiliary_id', '')).lower() \
               or q in str(row.get('account_name', '')).lower() \
               or q in str(row.get('ledger_name', '')).lower() \
               or q in str(row.get('number', '')).lower():
                filtered.append(row)

        self.table.rows = filtered
        self.table.update()
        if self.table:
            self.table.classes(remove='dimmed')

    def _update_code_options(self):
        try:
            data = []
            connection.contogetrows("SELECT AccountNumber, Name_en FROM Ledger ORDER BY AccountNumber", data)
            options = {str(row[0]): str(row[0]) for row in data if row[0]}
            self.input_refs['aux_code'].options = options
            self.input_refs['aux_code'].update()
        except Exception as e:
            print(f"Error updating codes from ledger: {e}")

    def get_selected_aux_number(self):
        aux_code = self.input_refs.get('aux_code', None)
        suffix = self.input_refs.get('number', None)
        if aux_code and aux_code.value and suffix and suffix.value:
            return f"{aux_code.value}.{suffix.value}"
        return None

    def view_linked_jv_lines(self):
        """Show all accounting_transaction_lines linked to the selected auxiliary."""
        id_value = self.input_refs.get('id', None)
        aux_db_id = getattr(id_value, 'value', None) if id_value else None
        if not aux_db_id:
            ui.notify('Select an auxiliary account first', color='warning')
            return

        try:
            aux_db_id_int = int(str(aux_db_id).strip())
        except (ValueError, TypeError):
            ui.notify('Invalid auxiliary ID', color='warning')
            return

        lines_data = []
        try:
            sql = """
                SELECT
                    COALESCE(jv.Entry, at_.reference_type) AS voucher_number,
                    CONVERT(VARCHAR(10), at_.transaction_date, 23) AS voucher_date,
                    at_.reference_type,
                    atl.account_number,
                    atl.debit,
                    atl.credit,
                    at_.description
                FROM accounting_transaction_lines atl
                JOIN accounting_transactions at_ ON atl.jv_id = at_.jv_id
                LEFT JOIN journal_voucher jv
                    ON at_.reference_type = 'Journal Voucher'
                    AND CAST(jv.NumberId AS VARCHAR(50)) = CAST(at_.reference_id AS VARCHAR(50))
                WHERE atl.auxiliary_id = ?
                ORDER BY at_.transaction_date DESC
            """
            connection.contogetrows(sql, lines_data, (aux_db_id_int,))
        except Exception as ex:
            ui.notify(f'Error loading JV lines: {ex}', color='negative')
            return

        aux_name = getattr(self.input_refs.get('account_name'), 'value', '') or ''
        aux_code_val = getattr(self.input_refs.get('aux_code'), 'value', '') or ''

        with ui.dialog() as dlg, ui.card().classes('p-6 w-full max-w-5xl glass-card border border-white/10').style('background:#0f172a;max-height:80vh;overflow:auto;'):
            ui.label(f'JV Lines — {aux_code_val} {aux_name}').classes('text-lg font-bold mb-4 text-white')

            rows = [{'voucher_number': str(r[0] or ''), 'voucher_date': str(r[1] or ''),
                     'reference_type': str(r[2] or ''), 'account_number': str(r[3] or ''),
                     'debit': float(r[4] or 0), 'credit': float(r[5] or 0), 'description': str(r[6] or '')}
                    for r in lines_data]

            total_debit = sum(x['debit'] for x in rows)
            total_credit = sum(x['credit'] for x in rows)

            col_defs = [
                {'headerName': 'Voucher #', 'field': 'voucher_number', 'width': 130},
                {'headerName': 'Date', 'field': 'voucher_date', 'width': 110},
                {'headerName': 'Type', 'field': 'reference_type', 'width': 130},
                {'headerName': 'Account No.', 'field': 'account_number', 'width': 130},
                {'headerName': 'Debit', 'field': 'debit', 'width': 110,
                 'valueFormatter': "Number(params.value || 0).toLocaleString('en-US',{minimumFractionDigits:2})"},
                {'headerName': 'Credit', 'field': 'credit', 'width': 110,
                 'valueFormatter': "Number(params.value || 0).toLocaleString('en-US',{minimumFractionDigits:2})"},
                {'headerName': 'Description', 'field': 'description', 'flex': 1},
            ]

            ui.aggrid({
                'columnDefs': col_defs, 'rowData': rows,
                'defaultColDef': {**MDS.get_ag_grid_default_def(), 'resizable': True, 'sortable': True},
                'headerHeight': 48, 'rowHeight': 48, 'domLayout': 'normal',
                'autoSizeStrategy': {'type': 'fitGridWidth'},
            }).classes('w-full h-96 ag-theme-quartz-dark shadow-lg rounded-xl overflow-hidden')

            diff = total_debit - total_credit
            color = '#34d399' if abs(diff) < 0.01 else '#fb7185'
            ui.label(f'Total Debit: {total_debit:,.2f}  |  Total Credit: {total_credit:,.2f}  |  Net: {diff:,.2f}').classes('text-sm font-bold mt-3').style(f'color:{color}')
            with ui.row().classes('w-full justify-end mt-4'):
                ui.button('Close', on_click=dlg.close).props('flat dark')
        dlg.open()

    def print_statement(self):
        """Open Statement of Account dialog for the selected auxiliary number."""
        aux_number = self.get_selected_aux_number()
        if not aux_number:
            ui.notify('Please select an auxiliary from the table first.', color='warning')
            return

        with ui.dialog() as dlg, ui.card().classes('p-6 w-96 glass-card border border-white/10').style('background:#0f172a;'):
            ui.label(f'Statement of Account: {aux_number}').classes('text-lg font-bold mb-4 text-white')
            with ui.column().classes('w-full gap-4'):
                f_input = ui.input('From Date', value=date.today().replace(day=1).strftime('%Y-%m-%d')).props('type=date dark outlined dense color=purple').classes('w-full')
                t_input = ui.input('To Date', value=date.today().strftime('%Y-%m-%d')).props('type=date dark outlined dense color=purple').classes('w-full')

            def _run_report():
                if not f_input.value or not t_input.value:
                    ui.notify('Please select both dates', color='warning')
                    return
                try:
                    import auxiliary_reports
                    auxiliary_reports.report_auxiliary_statement(f_input.value, t_input.value, aux_num=aux_number)
                    dlg.close()
                except Exception as e:
                    ui.notify(f'Report error: {str(e)}', color='negative')

            with ui.row().classes('w-full justify-end gap-3 mt-6'):
                ui.button('Cancel', on_click=dlg.close).props('flat dark')
                ui.button('Generate PDF', icon='print', on_click=_run_report).props('color=purple unelevated').classes('px-4 py-1 font-bold')
        dlg.open()

    def view_transactions(self):
        """Show all accounting transactions for the selected auxiliary number."""
        aux_number = self.get_selected_aux_number()
        if not aux_number:
            ui.notify('Select an auxiliary account first', color='warning')
            return
        from_d = self.from_date.value if self.from_date and self.from_date.value else None
        to_d = self.to_date.value if self.to_date and self.to_date.value else None
        accounting_helpers.show_transactions_dialog(
            account_number=aux_number,
            from_date=from_d,
            to_date=to_d,
            include_jv_journal_voucher_lines=True,
        )

    def create_ui(self):
        with ui.row().classes('w-full gap-6 items-start p-4 animate-fade-in'):
            # Left Column: Form
            with ui.column().classes('w-72 min-w-72 gap-6'):
                with ModernCard(glass=True).classes('w-full p-6'):
                    ui.label('Record Details').classes('text-lg font-black mb-6 text-white')
                    with ui.column().classes('w-full gap-4'):
                        self.input_refs['aux_code'] = ui.select(
                            [None], label='Account (Aux Code)'
                        ).classes('w-full glass-input text-white').props('dark rounded outlined')
                        self.input_refs['number'] = ui.input('Auxiliary Number').classes('w-full glass-input text-white').props('dark rounded outlined')
                        self.input_refs['status'] = ui.select({1: 'Active', 0: 'Inactive'}, label='Status').classes('w-full glass-input text-white').props('dark rounded outlined')
                        self.input_refs['id'] = ui.input('ID (Internal)').classes('w-full glass-input text-white').props('dark rounded outlined readonly')

                with ModernCard(glass=True).classes('w-full p-6'):
                    ui.label('Name & Identity').classes('text-lg font-black mb-6 text-white')
                    with ui.column().classes('w-full gap-4'):
                        self.input_refs['account_name'] = ui.input('Account Name').classes('w-full glass-input text-white').props('dark rounded outlined')

            # Right Column: Grid + Action Bar
            with ui.column().classes('flex-1 gap-6'):
                with ModernCard(glass=True).classes('w-full p-6'):
                    ui.label('Auxiliary List').classes('text-xl font-black text-white ml-2 mb-4')

                    with ui.row().classes('w-full gap-4 items-start'):
                        grid_col = ui.column().classes('flex-1 min-w-0')
                        action_col = ui.column().classes('w-80px min-w-80px items-center')

                        with grid_col:
                            # Toolbar: Date range + search
                            with ui.row().classes('w-full items-center mb-4 gap-4'):
                                with ui.row().classes('items-center gap-2 bg-white/5 px-3 py-1 rounded-xl border border-white/10'):
                                    ui.icon('event', color='white', size='xs')
                                    self.from_date = ui.input('From').classes('w-32 text-sm').props('dark dense borderless type=date')
                                    self.from_date.value = date(date.today().year, 1, 1).isoformat()
                                    ui.label('-').classes('text-white/30')
                                    self.to_date = ui.input('To').classes('w-32 text-sm').props('dark dense borderless type=date')
                                    self.to_date.value = date.today().isoformat()

                                ui.element('div').classes('flex-1')

                                self.aux_search_input = (
                                    ui.input(placeholder='Search auxiliaries...')
                                    .props('outlined dense')
                                    .classes('w-48 text-sm')
                                    .on('update:model-value', lambda e: self._filter_table(e.args))
                                    .on('keydown.down', lambda: self._focus_first_row())
                                )

                            table_cols = [
                                {'name': 'id',           'label': 'ID',          'field': 'id',           'sortable': True, 'align': 'left'},
                                {'name': 'auxiliary_id', 'label': 'Aux Code',    'field': 'auxiliary_id', 'sortable': True, 'align': 'left'},
                                {'name': 'ledger_name',  'label': 'Ledger Name', 'field': 'ledger_name',  'sortable': True, 'align': 'left'},
                                {'name': 'account_name', 'label': 'Account Name','field': 'account_name', 'sortable': True, 'align': 'left'},
                                {'name': 'number',       'label': 'Number',      'field': 'number',       'sortable': True, 'align': 'left'},
                                {'name': 'update_date',  'label': 'Date',        'field': 'update_date',  'sortable': True, 'align': 'left'},
                                {'name': 'status',       'label': 'Status',      'field': 'status',       'sortable': True, 'align': 'center'},
                                {'name': 'net_balance',  'label': 'Net Balance', 'field': 'net_balance',  'sortable': True, 'align': 'right'},
                            ]

                            self.table = ui.table(
                                columns=table_cols,
                                rows=[],
                                row_key='id',
                                selection='single',
                            ).classes('w-full').props('virtual-scroll flat bordered dense hide-pagination :pagination="{rowsPerPage: 0}"')
                            self.table.style('height: 600px; overflow: auto;')

                            def on_row_click(e):
                                try:
                                    row = e.args[1] if isinstance(e.args, (list, tuple)) and len(e.args) > 1 else None
                                    if not isinstance(row, dict):
                                        if isinstance(e.args, (list, tuple)) and e.args and isinstance(e.args[0], dict):
                                            row = e.args[0]
                                    if not row:
                                        return

                                    aux_id = row.get('id')
                                    if aux_id is None:
                                        return

                                    self.input_refs['id'].value = str(aux_id)
                                    self.input_refs['aux_code'].value = row.get('auxiliary_id')
                                    self.input_refs['account_name'].value = row.get('account_name') or ''
                                    self.input_refs['number'].value = row.get('aux_suffix', row.get('number', '')) or ''
                                    self.input_refs['status'].value = row.get('status', 1)

                                    self.initial_values = {
                                        'aux_code': row.get('auxiliary_id'),
                                        'account_name': row.get('account_name') or '',
                                        'number': row.get('aux_suffix', row.get('number', '')) or '',
                                        'status': row.get('status', 1),
                                        'id': str(aux_id)
                                    }

                                    if self.table:
                                        self.table.classes(remove='dimmed')
                                except Exception as ex:
                                    ui.notify(f'Display error: {ex}', color='warning')

                            def on_keydown(e):
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

                                    aux_id = rows[self._selected_row_index].get('id')
                                    if aux_id is None:
                                        return

                                    self._apply_row_from_id(aux_id)
                                except Exception as ex:
                                    ui.notify(f'Keyboard navigation error: {ex}', color='warning')

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
                                    ui.run_javascript("""
                                    try {
                                      const root = document.querySelector('.q-table');
                                      if (!root) return;
                                      root.tabIndex = 0;
                                      root.addEventListener('keydown', (ev) => {
                                        if (ev.key !== 'ArrowDown' && ev.key !== 'ArrowUp') return;
                                        ev.preventDefault();
                                      });
                                    } catch (e) {}
                                    """)

                        with action_col:
                            from modern_ui_components import ModernActionBar
                            ModernActionBar(
                                on_new=self.clear_input_fields,
                                on_save=self.save_auxiliary,
                                on_undo=self.undo_changes,
                                on_delete=self.delete_auxiliary,
                                on_refresh=self.refresh_table,
                                on_chatgpt=lambda: ui.run_javascript('window.open("https://chatgpt.com", "_blank");'),
                                on_print=self.print_statement,
                                on_print_special=lambda: __import__('auxiliary_reports').open_print_special_dialog(),
                                on_view_transaction=self.view_transactions,
                                on_view_jv_lines=self.view_linked_jv_lines,
                                target_table=self.table,
                                button_class='h-16',
                                classes='',
                            ).style('position: static; width: 80px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); margin-top: 0;')

        # Exactly the same pattern as customerui.py
        ui.timer(0.1, self.refresh_table, once=True)
