from nicegui import ui
from connection import connection
from uiaggridtheme import uiAggridTheme
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage
from datetime import datetime
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput
from modern_design_system import ModernDesignSystem as MDS
import logging


def journal_voucher_content(standalone=False):
    """Content method for journal vouchers that can be used in tabs"""
    if standalone:
        with ModernPageLayout("Journal Vouchers", standalone=standalone):
            JournalVoucherUI(standalone=False)
    else:
        JournalVoucherUI(standalone=False)


@ui.page('/journal_voucher')
def journal_voucher_page_route():
    journal_voucher_content(standalone=True)


class JournalVoucherUI:
    def __init__(self, standalone=True):
        self.standalone = standalone
        self.current_header_id = None  # journal_voucher.NumberId

        self.header_inputs = {}
        self.lines_inputs = {}

        self.headers_grid = None
        self.lines_grid = None

        # sticky footer totals
        self._balance_label = None
        self._diff_label = None
        self._save_header_btn = None

        # cached exchange rate map (currency_id -> exchange_rate)
        self.currency_exchange_rates = {}   # currency_code/$|LBP -> exchange_rate (float)
        self.currency_ids_by_code = {}      # currency_code -> currencies.id (int)

        self.create_ui()
        self.refresh_headers_table()
        # Load last entry after a short delay so the grid is ready
        ui.timer(0.3, self._load_last_header, once=True)

    def create_ui(self):
        # Wrap content in ModernPageLayout only if standalone, otherwise just render the content
        if self.standalone:
            layout_container = ModernPageLayout("Journal Vouchers", standalone=True)
            layout_container.__enter__()

        try:
            # Preload currency exchange rates for header currency toggle + exchange rate field.
            currency_data = []
            connection.contogetrows("SELECT id, currency_code, exchange_rate FROM currencies", currency_data)
            for row in currency_data:
                if not row:
                    continue
                cur_id, cur_code, ex_rate = row
                if cur_code:
                    self.currency_exchange_rates[cur_code] = ex_rate or 1.0
                    self.currency_ids_by_code[cur_code] = cur_id

            with ui.row().classes('w-full gap-6 items-start p-4 animate-fade-in'):
                with ui.column().classes('flex-1 gap-8'):
                    with ModernCard(glass=True).classes('w-full p-6'):
                        ui.label('Voucher Header').classes('text-xl font-black mb-6 text-white')
                        with ui.row().classes('w-full gap-6'):
                            self.headers_grid = ui.aggrid({
                                'columnDefs': [
                                    {'headerName': 'ID', 'field': 'id', 'width': 80},
                                    {'headerName': 'Date', 'field': 'date', 'width': 120},
                                    {'headerName': 'Voucher #', 'field': 'voucher_number', 'width': 150},
                                    {'headerName': 'Subtype', 'field': 'subtype_code', 'width': 100},
                                    {'headerName': 'Ref', 'field': 'manual_reference', 'width': 150}
                                ],
                                'rowData': [],
                                'defaultColDef': MDS.get_ag_grid_default_def(),
                                'rowSelection': 'single',
                            }).classes('flex-1 h-64 ag-theme-quartz-dark')
                            self.headers_grid.on('cellClicked', lambda e: self.load_header_data(e.args['data']['id'] if isinstance(e.args, dict) and 'data' in e.args and e.args['data'] else None))

                            with ui.column().classes('w-80 gap-4'):
                                self.header_inputs['date'] = ui.input('Date').classes('w-full glass-input').props('dark rounded outlined type=date')
                                self.header_inputs['date'].value = str(datetime.now().date())
                                self.header_inputs['voucher_number'] = ui.input('Voucher #').classes('w-full glass-input').props('dark rounded outlined')
                                
                                subtype_data = []
                                try:
                                    connection.contogetrows("SELECT Id, Name FROM SubType", subtype_data)
                                    subtype_options = {str(row[0]): f"{row[0]} - {row[1]}" for row in subtype_data if row and row[0]}
                                except Exception as e:
                                    print("Error loading subtype: ", e)
                                    subtype_options = {}
                                
                                self.header_inputs['subtype'] = ui.select(subtype_options, label='Subtype').classes('w-full glass-input').props('dark rounded outlined')
                                self.header_inputs['manual_reference'] = ui.input('Reference').classes('w-full glass-input').props('dark rounded outlined')

                    # Lines Section (Detail)
                    with ModernCard(glass=True).classes('w-full p-6'):
                        ui.label('Voucher Lines').classes('text-xl font-black mb-6 text-white')
                        
                        # Inline Add Line Form
                        with ui.row().classes('w-full gap-4 items-end mb-6'):
                            self.lines_inputs['account'] = ui.input(
                                label='Account',
                                value='',
                                placeholder=''
                            ).classes('w-64 glass-input text-white').props('dark rounded outlined readonly').on(
                                'click', self.open_account_dialog
                            )

                            self.lines_inputs['account_auxiliary_id'] = None
                            self.lines_inputs['account_name_tmp'] = None
                            self.lines_inputs['account_aux_number_tmp'] = None
                            
                            currency_data = []
                            connection.contogetrows("SELECT currency_code FROM currencies", currency_data)
                            currency_options = [row[0] for row in currency_data if row and row[0]]
                            self.lines_inputs['currency'] = ui.select(currency_options, label='Cur').classes('w-24 glass-input').props('dark rounded outlined')
                            
                            self.lines_inputs['debit'] = ui.number('Debit', value=0.0).classes('w-32 glass-input').props('dark rounded outlined')
                            self.lines_inputs['credit'] = ui.number('Credit', value=0.0).classes('w-32 glass-input').props('dark rounded outlined')

                            self.lines_inputs['remark'] = ui.input('Remark', value='').classes('w-64 glass-input text-white').props('dark rounded outlined')

                            ModernButton('Add Line', icon='add', on_click=self.add_line, variant='primary').classes('h-14')

                        # Lines Grid
                        self.lines_grid = ui.aggrid({
                            'columnDefs': [
                                {'headerName': 'Account', 'field': 'account', 'width': 150},
                                {'headerName': 'Cur', 'field': 'currency_code', 'width': 80},
                                {'headerName': 'Debit', 'field': 'debit', 'width': 100, 'valueFormatter': "'$' + x.toLocaleString()"},
                                {'headerName': 'Credit', 'field': 'credit', 'width': 100, 'valueFormatter': "'$' + x.toLocaleString()"},
                                {'headerName': 'Remark', 'field': 'remark', 'width': 200, 'flex': 1},
                            ],
                            'rowData': [],
                            'defaultColDef': MDS.get_ag_grid_default_def(),
                            'rowSelection': 'single',
                        }).classes('w-full h-80 ag-theme-quartz-dark')
                        
                        async def delete_line():
                            selected = await self.lines_grid.get_selected_row()
                            if selected:
                                try:
                                    connection.deleterow("DELETE FROM journal_voucher_items WHERE Id=?", selected['id'])
                                    ui.notify('Line deleted', color='positive')
                                    self.refresh_lines_table()
                                except Exception as e:
                                    ui.notify(f'Error deleting line: {str(e)}', color='negative')
                        
                        with ui.row().classes('w-full justify-end mt-3 mb-2 gap-3'):
                            ui.label('Totals:').classes('text-sm text-white/70')
                            self._balance_label = ui.label('Debit=0.00 | Credit=0.00 | Diff=0.00').classes('text-sm font-bold')
                        
                        with ui.row().classes('w-full justify-end mt-2'):
                            ModernButton('Delete Selected Line', icon='delete', on_click=delete_line, variant='error').classes('text-white')

                # Action Bar
                with ui.column().classes('w-80px items-center'):
                    from modern_ui_components import ModernActionBar
                    ModernActionBar(
                        on_new=self.clear_all,
                        on_save=self.save_header,
                        on_delete=self.delete_header,
                        on_refresh=self.refresh_headers_table,
                        on_chatgpt=lambda: ui.run_javascript('window.open("https://chatgpt.com", "_blank");'),
                        button_class='h-16',
                        classes=' '
                    ).style('position: static; width: 80px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); margin-top: 0;')
        finally:
            if self.standalone:
                layout_container.__exit__(None, None, None)

    def clear_all(self):
        self.current_header_id = None
        self.header_inputs['date'].value = str(datetime.now().date())
        self.header_inputs['voucher_number'].value = ''
        self.header_inputs['subtype'].value = None
        self.header_inputs['manual_reference'].value = ''
        self.lines_grid.options['rowData'] = []
        self.lines_grid.update()
        self._update_balance_check([])
        if self.headers_grid:
            self.headers_grid.run_method('deselectAll')
        if 'debit' in self.lines_inputs:
            self.lines_inputs['debit'].value = 0
        if 'credit' in self.lines_inputs:
            self.lines_inputs['credit'].value = 0

        if 'account_auxiliary_id' in self.lines_inputs:
            self.lines_inputs['account_auxiliary_id'] = None
        if 'account_name_tmp' in self.lines_inputs:
            self.lines_inputs['account_name_tmp'] = None
        if 'account_aux_number_tmp' in self.lines_inputs:
            self.lines_inputs['account_aux_number_tmp'] = None

        if 'account' in self.lines_inputs:
            self.lines_inputs['account'].value = ''

        ui.notify('New voucher entry', color='info')

    def load_account_options(self, select_ref):
        try:
            data = []
            connection.contogetrows("SELECT auxiliary_id, account_name FROM auxiliary", data)
            options = {str(row[0]): f"{row[0]} - {row[1]}" for row in data }
            select_ref.options = options
            select_ref.update()
        except Exception as ex:
            print(f"Error loading ledger accounts: {ex}")

    def open_account_dialog(self):
        with ui.dialog() as dialog, ui.card().classes('w-full max-w-5xl glass p-6 border border-white/10').style(
            'background: rgba(15, 15, 25, 0.8); backdrop-filter: blur(20px); border-radius: 2rem;'
        ):
            ui.label().classes('text-2xl font-black mb-6 text-white').style(
                'font-family: "Outfit", sans-serif;'
            )

            search_input_holder = ui.row().classes('w-full items-center gap-3 bg-white/5 px-4 py-2 rounded-xl border border-white/10 mb-4')
            search_input_holder.clear()
            with search_input_holder:
                ui.icon('search', size='1.25rem').classes('text-purple-400')
                search_input = ui.input(
                    placeholder='Search by aux code or name...'
                ).props('borderless dense clearable dark').classes('flex-1 text-white text-sm')

            data = []
            try:
                connection.contogetrows(
                    "SELECT auxiliary_id, account_name, number FROM auxiliary ORDER BY auxiliary_id",
                    data
                )
            except Exception as ex:
                ui.notify(f'Error loading accounts: {ex}', color='negative')
                dialog.close()
                return

            rows = []
            for r in data:
                if not r:
                    continue
                aux_id = str(r[0] or '').strip()
                name = str(r[1] or '').strip()
                aux_number = str(r[2] or '').strip()
                if not aux_id:
                    continue
                code = f"{aux_id}{aux_number}" if aux_number else str(aux_id)
                rows.append({
                    'auxiliary_id': aux_id,
                    'account_name': name,
                    'aux_number': aux_number,
                    'type': 'Account',
                    'display': f"{code} {name}".strip()
                })

            filtered = list(rows)

            columns = [
                {'headerName': 'Auxiliary ID', 'field': 'auxiliary_id', 'width': 140},
                {'headerName': 'Number/Code', 'field': 'aux_number', 'width': 140},
                {'headerName': 'Name', 'field': 'account_name', 'flex': 1},
                {'headerName': 'Full Display', 'field': 'display', 'width': 260},
            ]

            grid = ui.aggrid({
                'columnDefs': columns,
                'rowData': filtered,
                'rowSelection': 'single',
                'domLayout': 'normal',
            }).classes('w-full h-72 ag-theme-quartz-dark shadow-inner').style('background: transparent; border: none;')

            def apply_filter(val):
                q = (val or '').strip().lower()
                if not q:
                    new_filtered = list(rows)
                else:
                    new_filtered = [
                        x for x in rows
                        if q in str(x.get('account_name', '')).lower()
                        or q in str(x.get('aux_number', '')).lower()
                        or q in str(x.get('display', '')).lower()
                    ]
                grid.options['rowData'] = new_filtered
                grid.update()

            search_input.on('keydown.enter', lambda e: apply_filter(search_input.value))

            def on_click(e):
                try:
                    selected = e.args.get('data') if isinstance(e.args, dict) else None
                    if not selected:
                        return

                    self.lines_inputs['account_auxiliary_id'] = selected['auxiliary_id']
                    self.lines_inputs['account_name_tmp'] = selected['account_name']
                    self.lines_inputs['account_aux_number_tmp'] = selected.get('aux_number')

                    aux_id = str(selected.get('auxiliary_id')).strip() if selected.get('auxiliary_id') is not None else ''
                    self.lines_inputs['account'].value = str(aux_id).strip()

                    dialog.close()
                except Exception as ex:
                    ui.notify(f'Account select error: {ex}', color='negative')

            grid.on('cellClicked', on_click)

            with ui.row().classes('w-full justify-end mt-6'):
                ui.button('Cancel', on_click=dialog.close).props('flat text-color=white').classes('px-6 rounded-xl hover:bg-white/5')
        dialog.open()

    def _load_last_header(self):
        try:
            data = []
            connection.contogetrows("SELECT TOP 1 NumberId FROM journal_voucher ORDER BY NumberId DESC", data)
            if data:
                self.load_header_data(data[0][0])
        except Exception as ex:
            print(f"Error loading last header: {ex}")

    def save_header(self):
        date = self.header_inputs['date'].value
        voucher_number = self.header_inputs['voucher_number'].value
        subtype_code = self.header_inputs['subtype'].value
        manual_reference = self.header_inputs['manual_reference'].value

        if not voucher_number or not subtype_code:
            ui.notify('Voucher # and Subtype are required', color='warning')
            return

        try:
            current_rows = []
            if hasattr(self.lines_grid, 'options') and self.lines_grid.options is not None:
                current_rows = self.lines_grid.options.get('rowData') or []
            elif hasattr(self.lines_grid, 'rowData'):
                current_rows = self.lines_grid.rowData or []

            total_debit = sum(float(r.get('debit') or 0) for r in current_rows or [])
            total_credit = sum(float(r.get('credit') or 0) for r in current_rows or [])
            diff = total_debit - total_credit

            if current_rows and abs(diff) > 0.01:
                ui.notify(
                    f'Cannot save: voucher not balanced. Debit={total_debit:,.2f} Credit={total_credit:,.2f} Diff={diff:,.2f}',
                    color='warning'
                )
                return
        except Exception:
            pass

        try:
            # 1. Update or Insert the Journal Voucher Header
            if self.current_header_id:
                sql = """
                    UPDATE journal_voucher
                    SET [Date]=?, Entry=?, SubTypeId=?, ManualReference=?, UpdateDate=GETDATE()
                    WHERE NumberId=?
                """
                values = (date, voucher_number, int(subtype_code) if str(subtype_code).isdigit() else None, manual_reference, self.current_header_id)
                connection.insertingtodatabase(sql, values)
            else:
                sql = """
                    INSERT INTO journal_voucher (Entry, SubTypeId, CurrencyId, ManualReference, [Date], [Status], UserId)
                    VALUES (?, ?, NULL, ?, ?, 1, NULL)
                """
                values = (voucher_number, int(subtype_code) if str(subtype_code).isdigit() else None, manual_reference, date)
                connection.insertingtodatabase(sql, values)

                id_data = []
                connection.contogetrows("SELECT CAST(SCOPE_IDENTITY() AS INT)", id_data)
                if not id_data or id_data[0][0] is None:
                    hid = []
                    connection.contogetrows("SELECT MAX(NumberId) FROM journal_voucher", hid)
                    self.current_header_id = hid[0][0] if hid else None
                else:
                    self.current_header_id = id_data[0][0]

            # 2. Sync entries to the real schema layout inside accounting_transactions
            if self.current_header_id:
                # Clear existing transactions recorded under this specific description identifier to handle overrides safely
                desc_identifier = f"JV #{voucher_number}"
                # Delete existing accounting entries + their lines for this JV description
                # accounting_transaction_lines references accounting_transactions by jv_id
                connection.insertingtodatabase(
                    "DELETE FROM accounting_transaction_lines WHERE jv_id IN (SELECT jv_id FROM accounting_transactions WHERE description=?)",
                    (desc_identifier,)
                )
                connection.insertingtodatabase(
                    "DELETE FROM accounting_transactions WHERE description=?",
                    (desc_identifier,)
                )

                # Fetch lines (including auxiliary number so we can persist correct account_number)
                lines_data = []
                connection.contogetrows(
                    """
                    SELECT
                        i.AuxiliaryId,
                        a.auxiliary_id as auxiliary_ui_id,
                        a.number as auxiliary_number,
                        i.Remark,
                        i.Debit,
                        i.Credit
                    FROM journal_voucher_items i
                    LEFT JOIN auxiliary a ON a.id = i.AuxiliaryId
                    WHERE i.VoucherId=?
                    """,
                    lines_data,
                    (self.current_header_id,)
                )

                for line in lines_data:
                    if not line:
                        continue
                    aux_db_id, auxiliary_ui_id, auxiliary_number, remark, debit, credit = line
                    
                    # Compute standard signed flat amount: Debit is (+), Credit is (-)
                    line_amount = float(debit or 0) - float(credit or 0)
                    
                    # Fallback text configuration
                    final_desc = desc_identifier
                    if remark and str(remark).strip():
                        final_desc = f"{desc_identifier} - {str(remark).strip()}"

                    # Persist double-entry into the real accounting schema:
                    # - accounting_transactions stores the header (reference_type/id, description, date)
                    # - accounting_transaction_lines stores debit/credit per account/aux
                    #
                    # Note: reference_id is set to the journal_voucher header DB id (self.current_header_id)
                    # so it's stable and can be filtered later.
                    #
                    # transaction_date is the JV date
                    # reference_type is a fixed label for Journal Vouchers
                    # reference_id ties all lines back to this JV header
                    #
                    # accounting_transactions was created earlier in this save_header() call.
                    # Here we only insert into accounting_transaction_lines.
                    # Persist full account_number AS-IS from auxiliary.number (auxiliary.number already contains the desired format)
                    account_number_as_is = None
                    if auxiliary_number is not None:
                        account_number_as_is = str(auxiliary_number).strip() or None

                    # accounting_transaction_lines.auxiliary_id should link to auxiliary.id (INT),
                    # so we persist aux_db_id from journal_voucher_items.AuxiliaryId

                    # Insert one line: debit/credit are stored separately
                    # Also persist auxiliary suffix-only into accounting_transaction_lines.number
                    atl_suffix = None
                    if auxiliary_number is not None:
                        aux_num_str = str(auxiliary_number).strip()
                        if aux_num_str:
                            atl_suffix = aux_num_str.split('.')[-1]
                    
                    line_sql = """
                        INSERT INTO accounting_transaction_lines
                        (jv_id, account_number, auxiliary_id, number, debit, credit)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """

                    # Ensure jv_id exists: create the accounting transaction header once per save_header()
                    # and reuse for all lines.
                    # We create it lazily on first iteration.
                    if 'jv_id_for_this_header' not in locals() or jv_id_for_this_header is None:
                        header_sql = """
                            INSERT INTO accounting_transactions (reference_type, reference_id, description, transaction_date)
                            VALUES (?, ?, ?, ?)
                        """
                        connection.insertingtodatabase(
                            header_sql,
                            ('Journal Voucher', int(self.current_header_id), final_desc, date)
                        )
                        data_id = []
                        connection.contogetrows("SELECT MAX(jv_id) FROM accounting_transactions", data_id)
                        jv_id_for_this_header = data_id[0][0] if data_id and data_id[0][0] else None

                    if jv_id_for_this_header is None:
                        raise Exception("Failed to retrieve new JV ID for accounting sync")

                    # debit is positive side, credit is positive side; we stored line_amount as debit-credit signed,
                    # but accounting_transaction_lines expects separate debit/credit.
                    debit_val = float(line_amount) if line_amount >= 0 else 0.0
                    credit_val = float(-line_amount) if line_amount < 0 else 0.0

                    # Contract: accounting_transaction_lines.auxiliary_id MUST reference auxiliary.id (INT),
                    # because auxiliaryui.py aggregates using: atl.auxiliary_id = auxiliary.id.
                    # Store suffix-only into accounting_transaction_lines.number
                    # (SQL expects: jv_id, account_number, auxiliary_id, number, debit, credit)
                    connection.insertingtodatabase(
                        line_sql,
                        (
                            jv_id_for_this_header,
                            account_number_as_is,
                            int(aux_db_id) if aux_db_id is not None else None,
                            atl_suffix,
                            debit_val,
                            credit_val
                        )
                    )

            ui.notify('Voucher and Transactions saved successfully', color='positive')
            self.refresh_headers_table()
            self.refresh_lines_table()
        except Exception as e:
            ui.notify(f'Error saving header: {str(e)}', color='negative')

    def load_auxiliary_options(self, select_ref):
        try:
            data = []
            connection.contogetrows(
                "SELECT auxiliary_id, account_name FROM auxiliary WHERE status=1 ORDER BY auxiliary_id",
                data
            )
            options = {}
            for row in data:
                if not row:
                    continue
                aux_code = row[0]
                name = row[1] or ''
                if aux_code:
                    options[str(aux_code)] = f"{aux_code} - {name}".strip()
            select_ref.options = options
            select_ref.update()
        except Exception as ex:
            print(f"Error loading auxiliary options: {ex}")

    def _update_balance_check(self, row_data):
        total_debit = sum(float(r.get('debit') or 0) for r in row_data or [])
        total_credit = sum(float(r.get('credit') or 0) for r in row_data or [])
        diff = total_debit - total_credit
        self._balance_label.set_text(f"Debit={total_debit:,.2f} | Credit={total_credit:,.2f} | Diff={diff:,.2f}")
        if abs(diff) < 0.01:
            self._balance_label.style('color: #34d399')
        else:
            self._balance_label.style('color: #fb7185')

    def add_line(self):
        if not self.current_header_id:
            ui.notify('Save Header first (click "Save Header")', color='warning')
            return

        selected_auxiliary_id = self.lines_inputs.get('account_auxiliary_id')
        selected_name_tmp = self.lines_inputs.get('account_name_tmp')
        selected_aux_number_tmp = self.lines_inputs.get('account_aux_number_tmp')
        currency = self.lines_inputs['currency'].value
        remark = self.lines_inputs.get('remark', None).value if self.lines_inputs.get('remark') else ''
        debit = float(self.lines_inputs['debit'].value or 0)
        credit = float(self.lines_inputs['credit'].value or 0)

        if not selected_auxiliary_id:
            ui.notify('Select an account', color='warning')
            return
        if debit == 0 and credit == 0:
            ui.notify('Either Debit or Credit must be greater than 0', color='warning')
            return

        try:
            aux_code_int = int(selected_auxiliary_id)

            # Resolve auxiliary row id (auxiliary.id) correctly by matching auxiliary.number
            # auxiliary.number is stored in DB as either:
            # - plain form: "1" (for auxiliary_id=6261, number='1')
            # - or dotted form: "6261.000001"
            aux_rows = []
            aux_number_raw = str(selected_aux_number_tmp).strip() if selected_aux_number_tmp is not None else ''
            aux_number_trim = aux_number_raw.strip()

            # Build candidate full numbers only.
            # NOTE: some auxiliaries are stored with number='0' (no dot / no suffix),
            # e.g. auxiliary_id=6260 has number=0.
            # In that case, if user selected "0", we must match number='0' directly,
            # not "6260.0".
            num_variants = []
            if aux_number_trim:
                # If DB stores '0' exactly, match it directly.
                if aux_number_trim == '0':
                    num_variants.append('0')
                else:
                    # 1) Always try the raw entered value as-is (covers DB storing auxiliary.number='1')
                    num_variants.append(aux_number_trim)

                    # 2) Also try common full/dotted formats
                    if aux_number_trim.startswith(f"{aux_code_int}."):
                        # already full form like "5300.000001"
                        num_variants.append(aux_number_trim)
                    elif aux_number_trim.startswith('.'):
                        # suffix-only like ".000001" => full "aux_code.suffix"
                        num_variants.append(f"{aux_code_int}{aux_number_trim}")
                    else:
                        # suffix-only like "000001" => full "aux_code.suffix"
                        num_variants.append(f"{aux_code_int}.{aux_number_trim}")

            # If the user didn't specify a suffix, try to resolve the only active row for this aux_code
            connection.contogetrows_with_params(
                "SELECT id, number, account_name FROM auxiliary WHERE auxiliary_id=? AND (status=1 OR status IS NULL OR status=0)",
                aux_rows,
                (aux_code_int,)
            )

            if aux_rows and len(aux_rows) == 1 and aux_rows[0][0] is not None and not num_variants:
                aux_id = aux_rows[0][0]
            else:
                if num_variants:
                    placeholders = ",".join(["?"] * len(num_variants))
                    params = [aux_code_int] + num_variants
                    narrowed = []
                    connection.contogetrows_with_params(
                        f"SELECT id, number, account_name FROM auxiliary WHERE auxiliary_id=? AND number IN ({placeholders}) AND (status=1 OR status IS NULL OR status=0)",
                        narrowed,
                        tuple(params)
                    )
                    aux_rows = narrowed

                if not aux_rows or aux_rows[0][0] is None:
                    ui.notify(f'Could not resolve Auxiliary for code {selected_auxiliary_id} ({aux_number_raw})', color='negative')
                    return
                aux_id = aux_rows[0][0]

            currency_id = None
            currency_code = self.lines_inputs['currency'].value
            if currency_code:
                cur_rows = []
                try:
                    connection.contogetrows("SELECT TOP 1 id FROM currencies WHERE currency_code=?", cur_rows, (currency_code,))
                    currency_id = cur_rows[0][0] if cur_rows and cur_rows[0] else None
                except Exception:
                    currency_id = None

            sql = """
                INSERT INTO journal_voucher_items
                (VoucherId, AuxiliaryId, [Date], Debit, Credit, CurrencyId, [Status], Remark, ValueDate)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
            """
            line_date = self.header_inputs['date'].value
            connection.insertingtodatabase(sql, (self.current_header_id, aux_id, line_date, debit, credit, currency_id, remark or '', line_date))

            ui.notify('Line added', color='positive')
            self.refresh_lines_table()

            if selected_auxiliary_id and selected_name_tmp is not None:
                self.lines_inputs['account'].value = str(selected_auxiliary_id).strip()

            self.lines_inputs['account_auxiliary_id'] = None
            self.lines_inputs['account_name_tmp'] = None
            self.lines_inputs['account_aux_number_tmp'] = None
            self.lines_inputs['debit'].value = 0
            self.lines_inputs['credit'].value = 0
        except Exception as e:
            ui.notify(f'Error adding line: {str(e)}', color='negative')

    def delete_header(self):
        if not self.current_header_id:
            ui.notify('No voucher selected', color='warning')
            return

        voucher_number = self.header_inputs['voucher_number'].value
        try:
            desc_identifier = None
            if voucher_number:
                desc_identifier = f"JV #{voucher_number}"

                # Delete both the header and its lines explicitly to ensure balances update immediately
                # (accounting_transaction_lines is what auxiliary/net_balance sums from).
                connection.insertingtodatabase(
                    "DELETE FROM accounting_transaction_lines WHERE jv_id IN (SELECT jv_id FROM accounting_transactions WHERE description LIKE ?)",
                    (f"{desc_identifier}%",)
                )
                connection.insertingtodatabase(
                    "DELETE FROM accounting_transactions WHERE description LIKE ?",
                    (f"{desc_identifier}%",)
                )

            connection.deleterow("DELETE FROM journal_voucher_items WHERE VoucherId=?", self.current_header_id)
            connection.deleterow("DELETE FROM journal_voucher WHERE NumberId=?", self.current_header_id)
            ui.notify('Voucher deleted', color='positive')
            self.clear_all()
            self.refresh_headers_table()
        except Exception as e:
            ui.notify(f'Error deleting: {str(e)}', color='negative')

    def refresh_headers_table(self):
        try:
            data = []
            connection.contogetrows(
                "SELECT NumberId, [Date], Entry, SubTypeId, ManualReference FROM journal_voucher ORDER BY NumberId DESC",
                data
            )
            rows = []
            for r in data:
                rows.append({
                    'id': r[0],
                    'date': str(r[1]),
                    'voucher_number': r[2],
                    'subtype_code': r[3],
                    'manual_reference': r[4] or ''
                })
            self.headers_grid.options['rowData'] = rows
            self.headers_grid.update()
        except Exception as e:
            ui.notify(f'Error refreshing headers: {str(e)}', color='negative')

    def refresh_lines_table(self):
        try:
            data = []
            connection.contogetrows(
                """
                SELECT
                    i.Id, a.auxiliary_id, a.number, a.account_name, i.CurrencyId, i.Debit, i.Credit, i.Remark
                FROM journal_voucher_items i
                LEFT JOIN auxiliary a ON a.id = i.AuxiliaryId
                WHERE i.VoucherId=?
                ORDER BY i.Id DESC
                """,
                data,
                (self.current_header_id,)
            )
            rows = []
            for r in data:
                aux_id = r[1] or ''
                aux_num = r[2] or ''
                aux_name = r[3] or ''

                aux_num_str = str(aux_num).strip()
                if aux_num_str != '':
                    suffix = aux_num_str if aux_num_str.startswith('.') else f".{aux_num_str}"
                    account_display = f"{str(aux_id).strip()}{suffix} {aux_name}".strip()
                else:
                    account_display = f"{str(aux_id).strip()} {aux_name}".strip()

                rows.append({
                    'id': r[0],
                    'account': account_display,
                    'currency_code': r[4],
                    'debit': float(r[5] or 0),
                    'credit': float(r[6] or 0),
                    'remark': r[7] or ''
                })
            self.lines_grid.options['rowData'] = rows
            self.lines_grid.update()
            self._update_balance_check(rows)
        except Exception as e:
            ui.notify(f'Error refreshing lines: {str(e)}', color='negative')

    def load_header_data(self, header_id):
        self.current_header_id = header_id
        try:
            data = []
            connection.contogetrows(
                "SELECT [Date], Entry, SubTypeId, ManualReference FROM journal_voucher WHERE NumberId=?",
                data,
                (header_id,)
            )
            if data:
                r = data[0]
                self.header_inputs['date'].value = str(r[0])
                self.header_inputs['voucher_number'].value = r[1] or ''
                self.header_inputs['subtype'].value = str(r[2]) if r[2] is not None else None
                self.header_inputs['manual_reference'].value = r[3] or ''
                self.refresh_lines_table()
        except Exception as e:
            ui.notify(f'Error loading voucher: {str(e)}', color='negative')