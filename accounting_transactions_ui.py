from nicegui import ui
from connection import connection
from modern_design_system import ModernDesignSystem as MDS
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput
from session_storage import session_storage
from datetime import datetime


ACCOUNT_CODES = {
    '4111': '4111 – Customers (AR)',
    '4011': '4011 – Suppliers (AP)',
    '6011': '6011 – Purchases',
    '7011': '7011 – Sales Revenue',
}


def accounting_transactions_content(standalone=False):
    """Content method for accounting transactions - usable in tabs"""
    if standalone:
        with ModernPageLayout("Accounting Transactions", standalone=standalone):
            AccountingTransactionsUI(standalone=False)
    else:
        AccountingTransactionsUI(standalone=False)


@ui.page('/accounting-transactions')
def accounting_transactions_page_route():
    accounting_transactions_content(standalone=True)


class AccountingTransactionsUI:
    def __init__(self, standalone=True):
        self.standalone = standalone
        self._ensure_table()
        self.create_ui()

    # ─────────────────── Table Setup ───────────────────

    def _ensure_table(self):
        """Create accounting_transactions table if not exists"""
        try:
            from database_manager import db_manager
            exists = db_manager.execute_scalar(
                "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'accounting_transactions'"
            )
            if not exists:
                sql = """
                CREATE TABLE accounting_transactions (
                    id            INT IDENTITY(1,1) PRIMARY KEY,
                    transaction_date DATETIME DEFAULT GETDATE(),
                    account_code  VARCHAR(20)    NOT NULL,
                    account_name  VARCHAR(100),
                    description   VARCHAR(500),
                    reference     VARCHAR(100),
                    debit         DECIMAL(18,2)  DEFAULT 0,
                    credit        DECIMAL(18,2)  DEFAULT 0,
                    entity_type   VARCHAR(20),
                    entity_id     INT,
                    created_at    DATETIME       DEFAULT GETDATE()
                )
                """
                db_manager.execute_update(sql)
                print("accounting_transactions table created.")
        except Exception as ex:
            print(f"Error ensuring accounting_transactions table: {ex}")

    # ─────────────────── UI ───────────────────

    def create_ui(self):
        with ui.row().classes('w-full gap-6 items-start p-2'):

            # ── Left: Form ──────────────────────────────
            with ui.column().classes('w-[340px] gap-4 flex-shrink-0'):
                with ModernCard(glass=True).classes('w-full p-6'):
                    ui.label('Transaction Entry').classes('text-lg font-black text-white mb-4')

                    self._id_input = ui.input('ID').props('readonly outlined dense dark').classes('hidden')

                    self._date_input = ui.input('Date').props('outlined dense dark type=date').classes('w-full')
                    self._date_input.value = datetime.now().strftime('%Y-%m-%d')

                    self._account_code_select = ui.select(
                        options=ACCOUNT_CODES,
                        label='Account Code',
                        value='7011',
                    ).props('outlined dense dark').classes('w-full mt-2')

                    self._description_input = ui.textarea('Description').props('outlined dense dark rows=2').classes('w-full mt-2')

                    self._reference_input = ui.input('Reference / Invoice No.').props('outlined dense dark').classes('w-full mt-2')

                    with ui.row().classes('w-full gap-3 mt-2'):
                        self._debit_input = ui.number('Debit', value=0, min=0).props('outlined dense dark').classes('flex-1')
                        self._credit_input = ui.number('Credit', value=0, min=0).props('outlined dense dark').classes('flex-1')

                    self._entity_type_select = ui.select(
                        options={'customer': 'Customer', 'supplier': 'Supplier',
                                 'purchase': 'Purchase', 'sale': 'Sale', 'other': 'Other'},
                        label='Entity Type',
                        value='sale',
                    ).props('outlined dense dark').classes('w-full mt-2')

                    self._entity_id_input = ui.number('Entity ID', value=None, min=0).props('outlined dense dark').classes('w-full mt-2')

            # ── Center: Grid ──────────────────────────────
            with ui.column().classes('flex-1 min-w-0'):
                with ModernCard(glass=True).classes('w-full p-4'):
                    with ui.row().classes('w-full items-center justify-between mb-3'):
                        ui.label('Accounting Transactions').classes('text-lg font-black text-white')
                        self._count_label = ui.label('').classes('text-xs text-gray-400')

                    cols = [
                        {'headerName': 'ID',          'field': 'id',           'width': 65},
                        {'headerName': 'Date',         'field': 'transaction_date', 'width': 110},
                        {'headerName': 'Account',      'field': 'account_code', 'width': 80},
                        {'headerName': 'Account Name', 'field': 'account_name', 'flex': 2},
                        {'headerName': 'Description',  'field': 'description',  'flex': 2},
                        {'headerName': 'Reference',    'field': 'reference',    'width': 120},
                        {'headerName': 'Debit',        'field': 'debit',        'width': 110,
                         'valueFormatter': '"$" + Number(params.value || 0).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2})'},
                        {'headerName': 'Credit',       'field': 'credit',       'width': 110,
                         'valueFormatter': '"$" + Number(params.value || 0).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2})'},
                        {'headerName': 'Entity Type',  'field': 'entity_type',  'width': 100},
                    ]

                    self._grid = ui.aggrid({
                        'columnDefs': cols,
                        'rowData': [],
                        'rowSelection': 'single',
                        'defaultColDef': {'resizable': True, 'sortable': True},
                        'pagination': True,
                        'paginationPageSize': 25,
                    }).classes('w-full ag-theme-quartz-dark').style('height: 600px;')

                    self._grid.on('cellClicked', self._on_row_click)

            # ── Right: Action Bar ──────────────────────────────
            with ui.column().classes('w-[80px] items-center flex-shrink-0'):
                from modern_ui_components import ModernActionBar
                ModernActionBar(
                    on_new=self._clear_form,
                    on_save=self._save_transaction,
                    on_undo=self._clear_form,
                    on_delete=self._delete_transaction,
                    on_chatgpt=lambda: ui.run_javascript('window.open("https://chatgpt.com", "_blank");'),
                    on_refresh=self._refresh_table,
                    button_class='h-16',
                    classes=' '
                ).style('position: static; width: 80px; border-radius: 16px; '
                        'box-shadow: 0 10px 40px rgba(0,0,0,0.15); margin-top: 0;')

        # Load table on open
        ui.timer(0.1, self._refresh_table, once=True)

    # ─────────────────── Data Methods ───────────────────

    def _refresh_table(self):
        try:
            data = []
            connection.contogetrows(
                """SELECT id, CONVERT(VARCHAR(10), transaction_date, 120) as transaction_date,
                          account_code, account_name, description, reference,
                          debit, credit, entity_type, entity_id
                   FROM accounting_transactions
                   ORDER BY id DESC""",
                data
            )
            headers = ['id', 'transaction_date', 'account_code', 'account_name',
                       'description', 'reference', 'debit', 'credit', 'entity_type', 'entity_id']
            rows = [dict(zip(headers, r)) for r in data]
            # Serialize
            for row in rows:
                row['debit'] = float(row['debit'] or 0)
                row['credit'] = float(row['credit'] or 0)

            self._grid.options['rowData'] = rows
            self._grid.update()
            self._count_label.set_text(f'{len(rows)} transactions')

            # Load last entry into form
            if rows:
                self._populate_form(rows[0])
        except Exception as ex:
            ui.notify(f'Error loading transactions: {ex}', color='red')
            print(f'Error loading accounting_transactions: {ex}')

    def _on_row_click(self, e):
        try:
            row = e.args.get('data', {})
            if row:
                self._populate_form(row)
        except Exception as ex:
            print(f'Row click error: {ex}')

    def _populate_form(self, row):
        try:
            self._id_input.set_value(str(row.get('id', '') or ''))
            t_date = row.get('transaction_date', '')
            if t_date and hasattr(t_date, 'strftime'):
                t_date = t_date.strftime('%Y-%m-%d')
            self._date_input.set_value(str(t_date)[:10] if t_date else datetime.now().strftime('%Y-%m-%d'))
            code = str(row.get('account_code', '7011') or '7011')
            if code in ACCOUNT_CODES:
                self._account_code_select.set_value(code)
            self._description_input.set_value(str(row.get('description', '') or ''))
            self._reference_input.set_value(str(row.get('reference', '') or ''))
            self._debit_input.set_value(float(row.get('debit', 0) or 0))
            self._credit_input.set_value(float(row.get('credit', 0) or 0))
            etype = str(row.get('entity_type', 'other') or 'other').lower()
            options = {'customer', 'supplier', 'purchase', 'sale', 'other'}
            self._entity_type_select.set_value(etype if etype in options else 'other')
            eid = row.get('entity_id')
            self._entity_id_input.set_value(int(eid) if eid else None)
        except Exception as ex:
            print(f'Populate form error: {ex}')

    def _get_account_name(self, code):
        mapping = {
            '4111': 'Accounts Receivable – Customers',
            '4011': 'Accounts Payable – Suppliers',
            '6011': 'Purchases',
            '7011': 'Sales Revenue',
        }
        return mapping.get(code, code)

    def _save_transaction(self):
        try:
            rec_id = self._id_input.value
            t_date = self._date_input.value or datetime.now().strftime('%Y-%m-%d')
            account_code = self._account_code_select.value or '7011'
            account_name = self._get_account_name(account_code)
            description = self._description_input.value or ''
            reference = self._reference_input.value or ''
            debit = float(self._debit_input.value or 0)
            credit = float(self._credit_input.value or 0)
            entity_type = self._entity_type_select.value or 'other'
            entity_id = self._entity_id_input.value
            entity_id = int(entity_id) if entity_id else None

            if rec_id:
                sql = """UPDATE accounting_transactions
                         SET transaction_date=?, account_code=?, account_name=?, description=?,
                             reference=?, debit=?, credit=?, entity_type=?, entity_id=?
                         WHERE id=?"""
                params = (t_date, account_code, account_name, description, reference,
                          debit, credit, entity_type, entity_id, int(rec_id))
            else:
                sql = """INSERT INTO accounting_transactions
                         (transaction_date, account_code, account_name, description, reference,
                          debit, credit, entity_type, entity_id)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"""
                params = (t_date, account_code, account_name, description, reference,
                          debit, credit, entity_type, entity_id)

            connection.insertingtodatabase(sql, params)
            ui.notify('Transaction saved successfully', color='positive')
            self._refresh_table()
        except Exception as ex:
            ui.notify(f'Error saving transaction: {ex}', color='negative')
            print(f'Save transaction error: {ex}')

    def _delete_transaction(self):
        rec_id = self._id_input.value
        if not rec_id:
            ui.notify('Select a transaction to delete', color='warning')
            return

        with ui.dialog() as dialog, ui.card().classes('p-6 rounded-2xl'):
            ui.label('Delete Transaction?').classes('text-xl font-bold text-red-500 mb-2')
            ui.label(f'This will permanently delete transaction ID {rec_id}.').classes('mb-6 text-gray-700')
            with ui.row().classes('w-full justify-end gap-3'):
                ui.button('Cancel', on_click=dialog.close).props('outline color=gray')
                def do_delete():
                    try:
                        connection.insertingtodatabase(
                            "DELETE FROM accounting_transactions WHERE id=?", (int(rec_id),)
                        )
                        ui.notify('Transaction deleted', color='positive')
                        self._clear_form()
                        self._refresh_table()
                        dialog.close()
                    except Exception as ex:
                        ui.notify(f'Error deleting: {ex}', color='negative')
                ui.button('Delete', color='red', on_click=do_delete)
        dialog.open()

    def _clear_form(self):
        self._id_input.set_value('')
        self._date_input.set_value(datetime.now().strftime('%Y-%m-%d'))
        self._account_code_select.set_value('7011')
        self._description_input.set_value('')
        self._reference_input.set_value('')
        self._debit_input.set_value(0)
        self._credit_input.set_value(0)
        self._entity_type_select.set_value('sale')
        self._entity_id_input.set_value(None)
        self._grid.run_method('deselectAll')
