from nicegui import ui
from connection import connection
from uiaggridtheme import uiAggridTheme
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput
from modern_design_system import ModernDesignSystem as MDS
import accounting_helpers

def auxiliary_content(standalone: bool = False):
    """Content method for auxiliary management that can be used in tabs."""
    # Tabbed dashboard callers wrap their own page/layout, so this should only
    # render the module UI.
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
        self.row_data = []
        self.table = None
        self.table_column_defs = None
        self.filtered_row_data = []
        self.from_date = None
        self.to_date = None
        self.search_text = ''
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
        ui.notify('Ready for new entry', color='info')

    def _load_last_row(self):
        """Load first row (last id DESC) into form and undim table"""
        if not self.row_data:
            return
        row = self.row_data[0]
        self.input_refs['id'].value = str(row['id'])
        self.input_refs['aux_code'].value = row['auxiliary_id']
        self.input_refs['account_name'].value = row['account_name'] or ''
        self.input_refs['number'].value = row['number'] or ''
        self.input_refs['status'].value = row['status']
        self.initial_values = {
            'aux_code': row['auxiliary_id'],
            'account_name': row['account_name'] or '',
            'number': row['number'] or '',
            'status': row['status'],
            'id': str(row['id'])
        }
        if self.table:
            self.table.classes(remove='dimmed')

    def save_auxiliary(self):
        aux_code = self.input_refs['aux_code'].value
        account_name = self.input_refs['account_name'].value
        number = self.input_refs['number'].value
        status = self.input_refs['status'].value
        id_value = self.input_refs['id'].value

        if not aux_code or not account_name or not number:
            ui.notify('Code, Name and Number are required', color='warning')
            return

        try:
            # Enforce uniqueness: (auxiliary_id, number) must be unique in auxiliary.
            # "Account (Aux code)" => auxiliary_id
            # "same auxiliary" => Auxiliary Number => number
            dup_check_sql = "SELECT COUNT(*) FROM auxiliary WHERE auxiliary_id=? AND number=?"
            params = [aux_code, number]

            if id_value:
                dup_check_sql += " AND id<>?"
                params.append(id_value)

            dup_check_data = []
            connection.contogetrows(dup_check_sql, dup_check_data, params)

            # connection.contogetrows may return:
            # - list of tuples: [(count,)]
            # - list of pyodbc.Row: [pyodbc.Row(count=?)]
            # - scalar-like values
            dup_count = 0
            if dup_check_data:
                first = dup_check_data[0]

                # tuple/list row: [(count,)] or [count]
                if isinstance(first, (list, tuple)):
                    v = first[0] if first else 0
                else:
                    # pyodbc.Row: try index access first
                    try:
                        v = first[0]
                    except Exception:
                        v = first

                try:
                    dup_count = int(getattr(v, 'value', v))
                except Exception:
                    dup_count = 0

            if dup_count > 0:
                ui.notify('Duplicate not allowed: same Account (Aux Code) and same Auxiliary Number already exists.', color='warning')
                return

            if id_value:
                sql = "UPDATE auxiliary SET auxiliary_id=?, account_name=?, number=?, update_date=GETDATE(), status=? WHERE id=?"
                values = (aux_code, account_name, number, status, id_value)
            else:
                sql = "INSERT INTO auxiliary (auxiliary_id, account_name, number, update_date, status) VALUES (?, ?, ?, GETDATE(), ?)"
                values = (aux_code, account_name, number, status)

            connection.insertingtodatabase(sql, values)
            ui.notify('Saved successfully', color='positive')
            if self.table:
                self.table.classes(remove='dimmed')
            self.refresh_table()
        except Exception as e:
            ui.notify(f'Error saving: {str(e)}', color='negative')

    def undo_changes(self):
        fields = ['aux_code', 'account_name', 'number', 'status', 'id']
        for field in fields:
            if field in self.initial_values:
                self.input_refs[field].value = self.initial_values[field]
        if self.table:
            self.table.classes(remove='dimmed')
        ui.notify('Changes reverted', color='info')

    def delete_auxiliary(self):
        id_value = self.input_refs['id'].value
        if not id_value:
            ui.notify('Select a record to delete', color='warning')
            return

        try:
            sql = "DELETE FROM auxiliary WHERE id=?"
            connection.deleterow(sql, id_value)
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
                SELECT a.id,
                       a.auxiliary_id,
                       l.Name_en as ledger_name,
                       a.account_name,
                       a.number,
                       a.update_date,
                       a.status
                FROM auxiliary a
                LEFT JOIN Ledger l ON a.auxiliary_id = l.AccountNumber

                UNION ALL

                SELECT
                       NULL as id,
                       NULL as auxiliary_id,
                       l.Name_en as ledger_name,
                       'Cash/GL Account' as account_name,
                       atl.account_number as number,
                       GETDATE() as update_date,
                       1 as status
                FROM accounting_transaction_lines atl
                LEFT JOIN Ledger l ON atl.account_number = l.AccountNumber
                WHERE atl.account_number LIKE '5300.%'

                ORDER BY id DESC
            """
            connection.contogetrows(sql, data)

            new_row_data = []
            seen = set()
            for row in data:
                # Extract the auxiliary suffix (e.g., '000001' from '4111.000001')
                full_number = str(row[4]) if row[4] else ''
                aux_suffix = full_number.split('.')[-1] if '.' in full_number else full_number

                auxiliary_id = str(row[1]) if row[1] else ''
                ledger_name = str(row[2]) if row[2] else 'Unknown'
                account_name = row[3]
                status = row[6]
                # Dedupe key: collapse visual duplicates that represent the same auxiliary account.
                # Prefer stable identity fields (ignore UNION source differences like NULL id).
                dedupe_key = (auxiliary_id, full_number, status)

                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)

                # Hide extended auxiliary suffix nodes in the Auxiliary UI for base ledgers:
                # purchases: 6011.<suffix>, 6019.<suffix>
                # sales:      7011.<suffix>, 7090.<suffix>
                # These should be represented by base accounts + suffix aggregation via ledgerextend/reporting,
                # not as editable/printable auxiliary entries here.
                base_prefixes_to_hide = ('6011', '6019', '7011', '7090')
                is_extended_suffix_node = (
                    '.' in full_number
                    and any(full_number.startswith(f'{p}.') for p in base_prefixes_to_hide)
                )

                if not is_extended_suffix_node:
                    new_row_data.append({
                        'id': row[0],
                        'auxiliary_id': auxiliary_id,
                        'auxiliary_code_only': auxiliary_id,
                        'ledger_name': ledger_name,
                        'account_name': account_name,
                        'number': full_number,
                        'aux_suffix': aux_suffix,
                        'update_date': str(row[5]),
                        'status': status
                    })

            self.row_data = new_row_data
            self.update_code_options()
            # Load last entry into form and undim
            self._load_last_row()

            # Apply current search filter by rebuilding grid (ensures filter works reliably).
            self.filter_rows(self.search_text)
        except Exception as e:
            ui.notify(f'Error refreshing: {str(e)}', color='negative')

    def update_code_options(self):
        try:
            data = []
            connection.contogetrows("SELECT AccountNumber, Name_en FROM Ledger ORDER BY AccountNumber", data)
            # Only show the Aux Code number (AccountNumber) in the select.
            options = {str(row[0]): str(row[0]) for row in data if row[0]}
            self.input_refs['aux_code'].options = options
            self.input_refs['aux_code'].update()
        except Exception as e:
            print(f"Error updating codes from ledger: {e}")

    def get_selected_aux_number(self):
        """Return the auxiliary number (e.g. 4111.000001) of the currently loaded account."""
        number = self.input_refs.get('number', None)
        if number and number.value:
            return number.value
        return None

    def print_statement(self):
        """Open Statement of Account dialog for the selected auxiliary number."""
        from nicegui import ui
        aux_number = self.get_selected_aux_number()
        if not aux_number:
            ui.notify('Please select an auxiliary from the table first.', color='warning')
            return

        with ui.dialog() as dlg, ui.card().classes('p-6 w-96 glass-card border border-white/10').style('background:#0f172a;'):
            ui.label(f'Statement of Account: {aux_number}').classes('text-lg font-bold mb-4 text-white')
            
            with ui.column().classes('w-full gap-4'):
                from_date = (date.today().replace(day=1)).strftime('%Y-%m-%d')
                to_date = date.today().strftime('%Y-%m-%d')
                
                f_input = ui.input('From Date', value=from_date).props('type=date dark outlined dense color=purple').classes('w-full')
                t_input = ui.input('To Date', value=to_date).props('type=date dark outlined dense color=purple').classes('w-full')

            def _run_report():
                f = f_input.value
                t = t_input.value
                if not f or not t:
                    ui.notify('Please select both dates', color='warning')
                    return
                
                try:
                    import auxiliary_reports
                    auxiliary_reports.report_auxiliary_statement(f, t, aux_num=aux_number)
                    dlg.close()
                except Exception as e:
                    ui.notify(f'Report error: {str(e)}', color='negative')

            with ui.row().classes('w-full justify-end gap-3 mt-6'):
                ui.button('Cancel', on_click=dlg.close).props('flat dark')
                ui.button('Generate PDF', icon='print', on_click=_run_report).props('color=purple unelevated').classes('px-4 py-1 font-bold')
        dlg.open()

    def print_trial_balance(self):
        """Print full Trial Balance PDF."""
        from nicegui import ui
        try:
            from_d = self.from_date.value if self.from_date and self.from_date.value else None
            to_d = self.to_date.value if self.to_date and self.to_date.value else None
            accounting_helpers.print_trial_balance(from_date=from_d, to_date=to_d)
        except Exception as e:
            ui.notify(f'Trial Balance Error: {e}', color='negative')

    def view_transactions(self):
        """Show all accounting transactions for the selected auxiliary number."""
        aux_number = self.get_selected_aux_number()
        if not aux_number:
            from nicegui import ui
            ui.notify('Select an auxiliary account first', color='warning')
            return
        
        from_d = self.from_date.value if self.from_date and self.from_date.value else None
        to_d = self.to_date.value if self.to_date and self.to_date.value else None
        
        accounting_helpers.show_transactions_dialog(account_number=aux_number, from_date=from_d, to_date=to_d)

    def create_ui(self):
        # NOTE: Layout responsibility belongs to the caller (route/tabbed-dashboard).
        # Avoid nesting ModernPageLayout inside this module UI.
        try:
            with ui.row().classes('w-full gap-6 items-start p-4 animate-fade-in'):
                # Left Column: Form
                with ui.column().classes('w-1/3 gap-6'):
                    with ModernCard(glass=True).classes('w-full p-6'):
                        ui.label('Record Details').classes('text-lg font-black mb-6 text-white')
                        with ui.column().classes('w-full gap-4'):
                            self.input_refs['aux_code'] = ui.select(
                                [None],
                                label='Account (Aux Code)'
                            ).classes('w-full glass-input text-white').props('dark rounded outlined')
                            self.input_refs['number'] = ui.input('Auxiliary Number').classes('w-full glass-input text-white').props('dark rounded outlined')
                            self.input_refs['status'] = ui.select({1: 'Active', 0: 'Inactive'}, label='Status').classes('w-full glass-input text-white').props('dark rounded outlined')
                            self.input_refs['id'] = ui.input('ID (Internal)').classes('w-full glass-input text-white').props('dark rounded outlined readonly')

                    with ModernCard(glass=True).classes('w-full p-6'):
                        ui.label('Name & Identity').classes('text-lg font-black mb-6 text-white')
                        with ui.column().classes('w-full gap-4'):
                            self.input_refs['account_name'] = ui.input('Account Name').classes('w-full glass-input text-white').props('dark rounded outlined')

                # Middle Column: List
                with ui.column().classes('flex-1 gap-6'):
                    with ModernCard(glass=True).classes('w-full p-6'):
                        with ui.row().classes('w-full justify-between items-center mb-4'):
                            ui.label('Auxiliary List').classes('text-xl font-black text-white ml-2')
                            self.search_input = ui.input(placeholder='Search...').classes('w-64 glass-input text-white text-sm').props('dark rounded outlined dense')

                            def _on_search_change(e):
                                val = getattr(e, 'value', None)
                                if val is None:
                                    sender = getattr(e, 'sender', None)
                                    val = getattr(sender, 'value', '') if sender else ''
                                self.filter_rows(val)

                            self.search_input.on('change', _on_search_change)

                        column_defs = [
                            {'headerName': 'Ledger Name', 'field': 'ledger_name', 'width': 130},
                            {'headerName': 'Aux Code', 'field': 'auxiliary_code_only', 'width': 140},
                            {'headerName': 'Name', 'field': 'account_name', 'width': 220, 'flex': 1},
                            {'headerName': 'Auxiliary', 'field': 'aux_suffix', 'width': 100},
                            {'headerName': 'Full Number', 'field': 'number', 'width': 130},
                            {'headerName': 'Status', 'field': 'status', 'width': 100, 'cellRenderer': 'params => params.value == 1 ? "Active" : "Inactive"'}
                        ]

                        self.table = ui.aggrid({
                            'columnDefs': column_defs,
                            'rowData': [],
                            'defaultColDef': MDS.get_ag_grid_default_def(),
                            'rowSelection': 'single',
                        }).classes('w-full h-[600px] ag-theme-quartz-dark')

                        def on_row_click(e):
                            try:
                                args = getattr(e, 'args', None) or {}
                                selected_row = None
                                if isinstance(args, dict):
                                    selected_row = args.get('data') or args.get('row') or args.get('value')
                                if not isinstance(selected_row, dict):
                                    selected_row = {}
                                if not selected_row:
                                    return

                                selected_id = selected_row.get('id', None)
                                selected_aux_id = selected_row.get('auxiliary_id', None)
                                selected_account_name = selected_row.get('account_name', '') or ''
                                selected_number = selected_row.get('number', '') or ''
                                selected_status = selected_row.get('status', 1)

                                self.input_refs['id'].value = str(selected_id) if selected_id is not None else ''
                                self.input_refs['aux_code'].value = str(selected_aux_id) if selected_aux_id else None
                                self.input_refs['account_name'].value = selected_account_name
                                self.input_refs['number'].value = str(selected_number)
                                self.input_refs['status'].value = selected_status

                                self.initial_values = {
                                    'aux_code': str(selected_aux_id) if selected_aux_id else '',
                                    'account_name': selected_account_name,
                                    'number': str(selected_number),
                                    'status': selected_status,
                                    'id': str(selected_id) if selected_id is not None else ''
                                }

                                if self.table:
                                    self.table.classes(remove='dimmed')
                            except Exception as ex:
                                ui.notify(f'Error selecting: {str(ex)}', color='negative')

                        self.table.on('cellClicked', on_row_click)
                        self.table.on('rowClicked', on_row_click)
                        self.table.on('rowDoubleClicked', on_row_click)

                # Right Column: Action Bar
                with ui.column().classes('w-80px items-center'):
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
                        target_table=self.table,
                        button_class='h-16',
                        classes=' '
                    ).style('position: static; width: 80px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); margin-top: 0;')

            ui.timer(0.1, self.refresh_table, once=True)
        finally:
            pass

    def filter_rows(self, search_text):
        self.search_text = (search_text or '').strip()
        st = self.search_text.lower()

        # Compute filtered rows from current cached row_data.
        if not self.row_data:
            filtered = []
        elif not st:
            filtered = list(self.row_data)
        else:
            def match(row):
                aux = str(row.get('auxiliary_code_only', '') or '').lower()
                name = str(row.get('account_name', '') or '').lower()
                return st in aux or st in name
            filtered = [row for row in self.row_data if match(row)]

        # Update the existing aggrid instance.
        if not self.table:
            return

        try:
            if hasattr(self.table, 'options') and self.table.options is not None:
                self.table.options['rowData'] = filtered
            else:
                # Fallback for older wrappers (best-effort).
                self.table.rowData = filtered
            self.table.update()
        except Exception as e:
            ui.notify(f'Error filtering: {str(e)}', color='negative')
