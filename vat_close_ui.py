from nicegui import ui
from datetime import datetime, date

from connection import connection
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput
from modern_design_system import ModernDesignSystem as MDS


def vat_close_content(standalone: bool = False):
    """Content method for VAT close tab."""
    if standalone:
        with ModernPageLayout("VAT Close", standalone=standalone):
            VATCloseUI(standalone=False)
    else:
        VATCloseUI(standalone=False)


@ui.page('/vat-close')
def vat_close_page_route():
    vat_close_content(standalone=True)


class VATCloseUI:
    def __init__(self, standalone=True):
        self.standalone = standalone

        self.customer_vat_total = 0.0
        self.supplier_vat_total = 0.0
        self.net_vat = 0.0

        self.currency_code = None

        self.customer_vat_account = None
        self.supplier_vat_account = None

        self.transfer_account = None

        self.subtype_options = {}
        self.subtype_selected = None

        self._date_from = None
        self._date_to = None

        self._customer_total_label = None
        self._supplier_total_label = None
        self._net_total_label = None

        self._customer_account_select = None
        self._supplier_account_select = None
        self._transfer_account_select = None
        self._currency_select = None
        self._subtype_select = None
        self._voucher_ref_input = None

        self.create_ui()

    def create_ui(self):
        if self.standalone:
            layout_container = ModernPageLayout("VAT Close", standalone=True)
            layout_container.__enter__()

        try:
            with ui.row().classes('w-full gap-6 items-start p-4 animate-fade-in'):
                # Left: inputs
                with ui.column().classes('w-[360px] gap-4 flex-shrink-0'):
                    with ModernCard(glass=True).classes('w-full p-6'):
                        ui.label('VAT Close (date-to-date)').classes('text-lg font-black text-white mb-4')

                        with ui.column().classes('gap-3'):
                            self._date_from = ui.input('From Date').props('type=date dark').classes('w-full')
                            self._date_from.value = date.today().replace(day=1).strftime('%Y-%m-%d')

                            self._date_to = ui.input('To Date').props('type=date dark').classes('w-full')
                            self._date_to.value = date.today().strftime('%Y-%m-%d')

                            self._voucher_ref_input = ui.input('Reference (auditors)').classes('w-full').props('dark')

                            self._currency_select = ui.select(
                                {},
                                label='Currency',
                                value=None
                            ).props('outlined dense dark').classes('w-full')

                            # Source VAT accounts (fixed by accounting rules)
                            self._customer_account_select = ui.select(
                                {},
                                label='Customer VAT source account (auto: starts with 44270.00000x)',
                                value=None
                            ).props('outlined dense dark searchable readonly').classes('w-full')

                            self._supplier_account_select = ui.select(
                                {},
                                label='Supplier VAT source account (auto: 44210)',
                                value=None
                            ).props('outlined dense dark searchable readonly').classes('w-full')

                            # Auditor destination/transfer account
                            self._transfer_account_select = ui.select(
                                {},
                                label='Transfer (clearing) account (auditor selected)',
                                value=None
                            ).props('outlined dense dark searchable').classes('w-full')

                            # Journal subtype
                            self._subtype_select = ui.select(
                                {},
                                label='Journal Subtype',
                                value=None
                            ).props('outlined dense dark').classes('w-full')

                        with ui.row().classes('w-full gap-3 mt-4'):
                            ModernButton(
                                'Calculate',
                                icon='calculator',
                                on_click=self.calculate_totals
                            ).classes('flex-1 h-12')

                            ModernButton(
                                'Post VAT Close',
                                icon='upload',
                                on_click=self.post_vat_close
                            ).classes('flex-1 h-12')

                    with ModernCard(glass=True).classes('w-full p-6 mt-0'):
                        ui.label('Totals (selected period)').classes('text-sm font-black text-white/80 mb-3')

                        self._customer_total_label = ui.label('Customer VAT: $0.00').classes('text-white font-bold w-full')
                        self._supplier_total_label = ui.label('Supplier VAT: $0.00').classes('text-white font-bold mt-2 w-full')
                        self._net_total_label = ui.label('Net VAT (Customer - Supplier): $0.00').classes('text-white font-bold mt-2 w-full')

                        ui.separator().classes('my-4 bg-white/10')

                        ui.label('Posting preview').classes('text-sm font-black text-white/80 mb-2')
                        self._posting_preview = ui.label('- Calculate then choose accounts and Post.').classes('text-xs text-gray-300')

                        ui.button(
                            'Refresh Lists',
                            icon='refresh',
                            on_click=self.refresh_lookups
                        ).props('flat').classes('w-full mt-4 text-white border-white/20')

                # Right: breakdown (optional summary)
                with ui.column().classes('flex-1 min-w-0 gap-6'):
                    with ModernCard(glass=True).classes('w-full p-6'):
                        ui.label('VAT Calculation Details').classes('text-lg font-black text-white mb-2')
                        ui.markdown('''
- Customer VAT is summed from **sale_items.vat_amount** joined with **sales.sale_date** for `status='Sale'`.
- Supplier VAT is summed from **purchase_items.vat_amount** joined with **purchases.purchase_date**.
- Posting is done as journal lines:
  - **Customer VAT account = CREDIT**
  - **Supplier VAT account = DEBIT**
                        ''')

                        self._preview_grid = ui.aggrid({
                            'columnDefs': [
                                {'headerName': 'Period', 'field': 'period', 'flex': 1},
                                {'headerName': 'Customer VAT', 'field': 'customer_vat', 'width': 160},
                                {'headerName': 'Supplier VAT', 'field': 'supplier_vat', 'width': 160},
                                {'headerName': 'Net VAT', 'field': 'net_vat', 'width': 140},
                            ],
                            'rowData': [],
                            'defaultColDef': MDS.get_ag_grid_default_def(),
                            'pagination': False,
                        }).classes('w-full h-[220px] ag-theme-quartz-dark')

        finally:
            if self.standalone:
                layout_container.__exit__(None, None, None)

        self.refresh_lookups()
        self.calculate_totals()

    def refresh_lookups(self):
        # Currency
        currencies = []
        try:
            connection.contogetrows("SELECT currency_code FROM currencies", currencies)
            curr_list = [r[0] for r in currencies if r and r[0]]
            currency_options = {c: c for c in curr_list}
            self._currency_select.options = currency_options
            if curr_list and (self._currency_select.value is None):
                self._currency_select.value = curr_list[0]
            self._currency_select.update()
            self.currency_code = self._currency_select.value
        except Exception:
            # fallback
            self._currency_select.options = {'': ''}
            self.currency_code = None

        # Ledger accounts (fixed source + auditor destination)
        ledger_rows = []
        try:
            connection.contogetrows(
                "SELECT AccountNumber, Name_en FROM Ledger WHERE Status=1 ORDER BY AccountNumber",
                ledger_rows
            )

            all_opts = {}
            for r in ledger_rows:
                acct = str(r[0])
                name = str(r[1] or '')
                all_opts[acct] = f"{acct} - {name}"

            # Auto customer VAT source: startswith 44270
            customer_source = None
            for acct, label in all_opts.items():
                if acct.startswith('44270'):
                    customer_source = acct
                    break

            # Auto supplier VAT source: 44210
            supplier_source = '44210' if '44210' in all_opts else None

            # Set options and values for source selects (readonly, but still display)
            self._customer_account_select.options = all_opts
            self._supplier_account_select.options = all_opts
            self._customer_account_select.value = customer_source
            self._supplier_account_select.value = supplier_source
            self._customer_account_select.update()
            self._supplier_account_select.update()

            # Auditor destination select: all ledger accounts
            self._transfer_account_select.options = all_opts
            # leave value empty so auditor selects
            self._transfer_account_select.update()
        except Exception as e:
            ui.notify(f'Error loading ledger accounts: {e}', color='negative')

        # Journal subtype
        try:
            subtype_rows = []
            connection.contogetrows("SELECT code, name FROM subtype", subtype_rows)
            opts = {r[0]: f"{r[0]} - {r[1]}" for r in subtype_rows if r and r[0]}
            self.subtype_options = opts
            self._subtype_select.options = opts
            self._subtype_select.value = next(iter(opts.keys()), None)
            self._subtype_select.update()
        except Exception as e:
            ui.notify(f'Error loading journal subtype: {e}', color='negative')

    def _parse_dates(self):
        f = self._date_from.value
        t = self._date_to.value
        if not f or not t:
            raise ValueError('Select From and To dates.')
        if f > t:
            raise ValueError('From Date must be <= To Date.')
        return f, t

    def calculate_totals(self):
        try:
            from_date, to_date = self._parse_dates()

            customer_data = []
            # Customer VAT from sale_items.vat_amount
            connection.contogetrows(
                """
                SELECT
                    SUM(ISNULL(si.vat_amount, 0))
                FROM sales s
                INNER JOIN sale_items si ON si.sales_id = s.id
                WHERE s.status = 'Sale'
                  AND CONVERT(date, s.sale_date) >= ?
                  AND CONVERT(date, s.sale_date) <= ?
                """,
                customer_data,
                (from_date, to_date)
            )
            self.customer_vat_total = float(customer_data[0][0] or 0) if customer_data else 0.0

            supplier_data = []
            # Supplier VAT from purchase_items.vat_amount
            connection.contogetrows(
                """
                SELECT
                    SUM(ISNULL(pi.vat_amount, 0))
                FROM purchases p
                INNER JOIN purchase_items pi ON pi.purchase_id = p.id
                WHERE CONVERT(date, p.purchase_date) >= ?
                  AND CONVERT(date, p.purchase_date) <= ?
                """,
                supplier_data,
                (from_date, to_date)
            )
            self.supplier_vat_total = float(supplier_data[0][0] or 0) if supplier_data else 0.0

            self.net_vat = self.customer_vat_total - self.supplier_vat_total

            self._customer_total_label.set_text(f'Customer VAT: ${self.customer_vat_total:,.2f}')
            self._supplier_total_label.set_text(f'Supplier VAT: ${self.supplier_vat_total:,.2f}')
            self._net_total_label.set_text(f'Net VAT (Customer - Supplier): ${self.net_vat:,.2f}')

            self._posting_preview.set_text(
                f'If posted: Customer VAT CREDIT {self.customer_vat_total:,.2f}, '
                f'Supplier VAT DEBIT {self.supplier_vat_total:,.2f}.'
            )

            self._preview_grid.options['rowData'] = [{
                'period': f'{from_date} to {to_date}',
                'customer_vat': f'${self.customer_vat_total:,.2f}',
                'supplier_vat': f'${self.supplier_vat_total:,.2f}',
                'net_vat': f'${self.net_vat:,.2f}',
            }]
            self._preview_grid.update()

        except Exception as e:
            ui.notify(f'Error calculating VAT totals: {e}', color='negative')

    def post_vat_close(self):
        try:
            from_date, to_date = self._parse_dates()

            self.customer_vat_account = self._customer_account_select.value
            self.supplier_vat_account = self._supplier_account_select.value
            self.transfer_account = self._transfer_account_select.value

            if not self.customer_vat_account or not self.supplier_vat_account:
                ui.notify('Customer VAT source or Supplier VAT source account not found.', color='warning')
                return

            if not self.transfer_account:
                ui.notify('Select Transfer (clearing) account.', color='warning')
                return

            subtype_code = self._subtype_select.value
            if not subtype_code:
                ui.notify('Select Journal Subtype.', color='warning')
                return

            currency = self._currency_select.value
            currency = currency if currency else None

            voucher_ref = self._voucher_ref_input.value or f'VAT CLOSE {from_date}..{to_date}'

            # Create journal voucher header
            posting_date = to_date  # convention for close: date = To Date
            # generate voucher number: simple approach using MAX+1 pattern
            id_data = []
            connection.contogetrows("SELECT ISNULL(MAX(id),0) FROM journal_voucher_header", id_data)
            header_next_id = (id_data[0][0] if id_data and id_data[0] else 0) + 1
            voucher_number = f'VAT-{header_next_id}'

            header_insert_sql = """
                INSERT INTO journal_voucher_header (date, voucher_number, subtype_code, manual_reference)
                VALUES (?, ?, ?, ?)
            """
            connection.insertingtodatabase(
                header_insert_sql,
                (posting_date, voucher_number, subtype_code, voucher_ref)
            )

            # retrieve header_id
            hid = []
            connection.contogetrows("SELECT MAX(id) FROM journal_voucher_header", hid)
            header_id = hid[0][0] if hid else None
            if not header_id:
                ui.notify('Could not retrieve created voucher header id.', color='negative')
                return

            # VAT close based on your rule:
            # - Customer VAT is stored as DEBIT -> to empty it, we CREDIT 44270.* by customer_vat_total
            # - Supplier VAT is stored as CREDIT -> to empty it, we DEBIT 44210 by supplier_vat_total
            # - Remaining net (customer - supplier) is transferred to auditor-selected clearing account
            #
            # Source emptying:
            if self.customer_vat_total != 0:
                # Empty customer VAT debit: credit source
                connection.insertingtodatabase(
                    """
                    INSERT INTO journal_voucher_lines (header_id, account, currency_code, debit, credit, remark)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (header_id, str(self.customer_vat_account), currency, 0.0, self.customer_vat_total,
                     f'VAT close empty customer {from_date}..{to_date}')
                )

            if self.supplier_vat_total != 0:
                # Empty supplier VAT credit: debit source
                connection.insertingtodatabase(
                    """
                    INSERT INTO journal_voucher_lines (header_id, account, currency_code, debit, credit, remark)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (header_id, str(self.supplier_vat_account), currency, self.supplier_vat_total, 0.0,
                     f'VAT close empty supplier {from_date}..{to_date}')
                )

            # Transfer net to clearing to balance
            net = float(self.net_vat or 0)
            if net > 0:
                # customer debit > supplier credit => credits exceed debits by net => add DEBIT clearing
                connection.insertingtodatabase(
                    """
                    INSERT INTO journal_voucher_lines (header_id, account, currency_code, debit, credit, remark)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (header_id, str(self.transfer_account), currency, net, 0.0,
                     f'VAT close transfer net (customer - supplier) {from_date}..{to_date}')
                )
            elif net < 0:
                # customer debit < supplier credit => need CREDIT clearing
                connection.insertingtodatabase(
                    """
                    INSERT INTO journal_voucher_lines (header_id, account, currency_code, debit, credit, remark)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (header_id, str(self.transfer_account), currency, 0.0, abs(net),
                     f'VAT close transfer net (supplier - customer) {from_date}..{to_date}')
                )

            ui.notify(f'VAT Close posted successfully. Voucher: {voucher_number}', color='positive')

        except Exception as e:
            ui.notify(f'Error posting VAT close: {e}', color='negative')


__all__ = ['vat_close_content']
