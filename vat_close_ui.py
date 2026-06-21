from nicegui import ui
from datetime import datetime, date

from connection import connection
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput


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
                                label='Customer VAT source account (auto: starts with 44270)',
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

                        with ui.row().classes('w-full gap-3 mt-2'):
                            ui.button(
                                'Delete VAT Close',
                                icon='delete',
                                on_click=self.delete_vat_close
                            ).props('outlined color=negative').classes('w-full h-10')

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
**Posting rules:**

- `44270.*` children  →  **Sales VAT collected** (credit balance)
- `44210.*` children  →  **Purchase VAT paid** (debit balance)

**Scenario A — Sales VAT > Purchase VAT:**
  - Zero all children of `44270` and `44210` (reversing entry per child)
  - Difference → **CREDIT 44250** (VAT payable to tax authority)

**Scenario B — Purchase VAT > Sales VAT:**
  - Zero all children of `44270` and `44210` (reversing entry per child)
  - Difference → **DEBIT 44260** (VAT credit receivable from tax authority)

**Delete/Rollback:** removes the JV and all lines, restoring pre-close balances.
                        ''')

                        self._preview_grid = ui.table(
                            columns=[
                                {'name': 'period', 'label': 'Period', 'field': 'period', 'align': 'left'},
                                {'name': 'customer_vat', 'label': 'Sales VAT (44270 Credit)', 'field': 'customer_vat', 'align': 'right'},
                                {'name': 'supplier_vat', 'label': 'Purchase VAT (44210 Debit)', 'field': 'supplier_vat', 'align': 'right'},
                                {'name': 'net_vat', 'label': 'Net VAT', 'field': 'net_vat', 'align': 'right'},
                                {'name': 'clearing', 'label': 'Clearing Account', 'field': 'clearing', 'align': 'left'},
                            ],
                            rows=[],
                        ).classes('w-full h-[220px]').props('virtual-scroll flat bordered dense hide-pagination :pagination="{rowsPerPage: 0}"')

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

            # Ensure canonical VAT source accounts always exist in options
            all_opts.setdefault('44270', '44270 - VAT Customer')
            all_opts.setdefault('44210', '44210 - VAT Supplier')

            # Auto customer VAT source: prefer exact 44270
            customer_candidates = sorted(
                [a for a in all_opts.keys() if str(a) == '44270' or str(a).startswith('44270.')],
                key=lambda x: (len(x), x)
            )
            customer_source = customer_candidates[0] if customer_candidates else '44270'

            # Auto supplier VAT source: prefer exact 44210
            supplier_candidates = sorted(
                [a for a in all_opts.keys() if str(a) == '44210' or str(a).startswith('44210.')],
                key=lambda x: (len(x), x)
            )
            supplier_source = '44210' if '44210' in all_opts else (supplier_candidates[0] if supplier_candidates else '44210')

            self._customer_account_select.options = all_opts
            self._supplier_account_select.options = all_opts
            self._customer_account_select.value = customer_source
            self._supplier_account_select.value = supplier_source
            self._customer_account_select.update()
            self._supplier_account_select.update()

            # Auditor destination select: all ledger accounts
            self._transfer_account_select.options = all_opts
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
        """
        Preview: reads VAT from accounting_transaction_lines for accounts under 44210/44270.
        Also reads from sale_items/purchase_items as a secondary preview.
        """
        try:
            from_date, to_date = self._parse_dates()

            # -- Live accounting ledger totals (source of truth for posting) --
            ledger_data = []
            connection.contogetrows(
                """
                SELECT
                    CASE
                        WHEN l.account_number LIKE '44270%' THEN '44270'
                        WHEN l.account_number LIKE '44210%' THEN '44210'
                    END AS vat_group,
                    SUM(l.debit)  AS total_debit,
                    SUM(l.credit) AS total_credit
                FROM accounting_transaction_lines l
                INNER JOIN accounting_transactions t ON t.jv_id = l.jv_id
                WHERE (l.account_number LIKE '44270%' OR l.account_number LIKE '44210%')
                  AND CONVERT(date, t.transaction_date) >= ?
                  AND CONVERT(date, t.transaction_date) <= ?
                  AND t.description NOT LIKE 'Close VAT Period%'
                GROUP BY
                    CASE
                        WHEN l.account_number LIKE '44270%' THEN '44270'
                        WHEN l.account_number LIKE '44210%' THEN '44210'
                    END
                """,
                ledger_data,
                (from_date, to_date)
            )

            sales_vat_credit = 0.0   # 44270 credit = Sales VAT collected
            purchase_vat_debit = 0.0  # 44210 debit = Purchase VAT paid

            for row in ledger_data:
                group = row[0]
                total_debit = float(row[1] or 0)
                total_credit = float(row[2] or 0)
                if group == '44270':
                    sales_vat_credit = total_credit
                elif group == '44210':
                    purchase_vat_debit = total_debit

            self.customer_vat_total = sales_vat_credit
            self.supplier_vat_total = purchase_vat_debit
            self.net_vat = sales_vat_credit - purchase_vat_debit

            self._customer_total_label.set_text(f'Sales VAT (44270 Credit): ${self.customer_vat_total:,.2f}')
            self._supplier_total_label.set_text(f'Purchase VAT (44210 Debit): ${self.supplier_vat_total:,.2f}')
            self._net_total_label.set_text(f'Net VAT (Sales - Purchase): ${self.net_vat:,.2f}')

            if self.net_vat > 0:
                clearing_info = f'→ CREDIT 44250 with {self.net_vat:,.2f}'
            elif self.net_vat < 0:
                clearing_info = f'→ DEBIT 44260 with {abs(self.net_vat):,.2f}'
            else:
                clearing_info = '→ Balanced (no clearing line needed)'

            self._posting_preview.set_text(
                f'Post will zero all 44210/44270 children. {clearing_info}'
            )

            self._preview_grid.rows = [{
                'period': f'{from_date} to {to_date}',
                'customer_vat': f'${self.customer_vat_total:,.2f}',
                'supplier_vat': f'${self.supplier_vat_total:,.2f}',
                'net_vat': f'${self.net_vat:,.2f}',
                'clearing': '44250' if self.net_vat > 0 else ('44260' if self.net_vat < 0 else 'None'),
            }]

        except Exception as e:
            ui.notify(f'Error calculating VAT totals: {e}', color='negative')

    def _period_key(self, from_date, to_date):
        """Unique reference key for a VAT close period."""
        return f"{from_date}..{to_date}"

    def post_vat_close(self):
        """
        Post VAT period close:
        1. Aggregate all children of 44210 and 44270 from accounting_transaction_lines.
        2. Post reversing entries (per child auxiliary_id) to zero them out.
        3. Post difference to 44250 (CREDIT) or 44260 (DEBIT).
        4. Header description: 'Close VAT Period {period_key}'.
        """
        try:
            from_date, to_date = self._parse_dates()
            period_key = self._period_key(from_date, to_date)
            desc = f"Close VAT Period {period_key}"

            # Guard: check if already posted for this period
            existing = []
            connection.contogetrows_with_params(
                "SELECT jv_id FROM accounting_transactions WHERE description = ?",
                existing, (desc,)
            )
            if existing:
                ui.notify(
                    f'VAT Close already posted for this period (JV #{existing[0][0]}). Delete it first.',
                    color='warning'
                )
                return

            # ---------------------------------------------------------------
            # Step 1: Aggregate net balance per auxiliary_id for 44210 and 44270
            # ---------------------------------------------------------------
            child_data = []
            connection.contogetrows(
                """
                SELECT
                    l.account_number,
                    l.auxiliary_id,
                    SUM(l.debit)  AS total_debit,
                    SUM(l.credit) AS total_credit
                FROM accounting_transaction_lines l
                INNER JOIN accounting_transactions t ON t.jv_id = l.jv_id
                WHERE (l.account_number LIKE '44210%' OR l.account_number LIKE '44270%')
                  AND t.description NOT LIKE 'Close VAT Period%'
                GROUP BY l.account_number, l.auxiliary_id
                """,
                child_data
            )

            if not child_data:
                ui.notify('No VAT transaction lines found for 44210/44270. Nothing to close.', color='warning')
                return

            # ---------------------------------------------------------------
            # Step 2: Compute totals across all children
            # ---------------------------------------------------------------
            sales_vat_credit = 0.0    # 44270.* net credit
            purchase_vat_debit = 0.0  # 44210.* net debit

            for row in child_data:
                acct = str(row[0] or '')
                total_debit = float(row[2] or 0)
                total_credit = float(row[3] or 0)
                if acct.startswith('44270'):
                    sales_vat_credit += total_credit - total_debit
                elif acct.startswith('44210'):
                    purchase_vat_debit += total_debit - total_credit

            difference = sales_vat_credit - purchase_vat_debit

            # ---------------------------------------------------------------
            # Step 3: Create JV header in accounting_transactions
            # reference_id column is INT in the DB — use 0 as sentinel;
            # identification is done via the unique description string.
            # ---------------------------------------------------------------
            header_sql = """
                INSERT INTO accounting_transactions (reference_type, reference_id, description, transaction_date)
                VALUES (?, 0, ?, GETDATE());
            """
            connection.insertingtodatabase(
                header_sql,
                ('VAT Close', desc)
            )

            # Retrieve the new jv_id by the unique description
            id_rows = []
            connection.contogetrows_with_params(
                "SELECT MAX(jv_id) FROM accounting_transactions WHERE description = ?",
                id_rows, (desc,)
            )
            jv_id = id_rows[0][0] if id_rows and id_rows[0][0] else None
            if not jv_id:
                ui.notify('Failed to create JV header.', color='negative')
                return

            # ---------------------------------------------------------------
            # Step 4: Post reversing lines per child (zero each account)
            # ---------------------------------------------------------------
            line_sql = """
                INSERT INTO accounting_transaction_lines
                    (jv_id, account_number, auxiliary_id, debit, credit)
                VALUES (?, ?, ?, ?, ?)
            """

            for row in child_data:
                acct = str(row[0] or '')
                aux_id = row[1]
                total_debit = float(row[2] or 0)
                total_credit = float(row[3] or 0)
                net = total_debit - total_credit  # positive means debit-heavy; negative = credit-heavy

                if abs(net) < 0.001:
                    continue  # already balanced, skip

                # Reversing entry: if net > 0 (debit-heavy) → post CREDIT to zero it
                #                  if net < 0 (credit-heavy) → post DEBIT to zero it
                rev_debit = 0.0
                rev_credit = 0.0
                if net > 0:
                    rev_credit = net
                else:
                    rev_debit = abs(net)

                connection.insertingtodatabase(
                    line_sql,
                    (jv_id, acct, aux_id, rev_debit, rev_credit)
                )

            # ---------------------------------------------------------------
            # Step 5: Post the difference to clearing account
            # ---------------------------------------------------------------
            if abs(difference) >= 0.01:
                if difference > 0:
                    # Sales VAT > Purchase VAT → CREDIT 44250 (VAT payable to state)
                    connection.insertingtodatabase(
                        line_sql,
                        (jv_id, '44250', None, 0.0, round(difference, 2))
                    )
                    clearing_msg = f'CREDIT 44250 = {difference:,.2f}'
                else:
                    # Purchase VAT > Sales VAT → DEBIT 44260 (VAT credit receivable)
                    connection.insertingtodatabase(
                        line_sql,
                        (jv_id, '44260', None, round(abs(difference), 2), 0.0)
                    )
                    clearing_msg = f'DEBIT 44260 = {abs(difference):,.2f}'
            else:
                clearing_msg = 'Balanced — no clearing line needed'

            ui.notify(
                f'VAT Close posted (JV #{jv_id}). Children zeroed. {clearing_msg}.',
                color='positive'
            )

            # Refresh preview
            self.calculate_totals()

        except Exception as e:
            ui.notify(f'Error posting VAT close: {e}', color='negative')

    def delete_vat_close(self):
        """
        Rollback VAT period close:
        - Find the accounting_transactions row with description 'Close VAT Period {period_key}'.
        - Delete all accounting_transaction_lines for that jv_id.
        - Delete the accounting_transactions header.
        This restores all 44210/44270 balances to pre-close state.
        """
        try:
            from_date, to_date = self._parse_dates()
            period_key = self._period_key(from_date, to_date)
            desc = f"Close VAT Period {period_key}"

            # Find existing JV for this period
            existing = []
            connection.contogetrows_with_params(
                "SELECT jv_id FROM accounting_transactions WHERE description = ?",
                existing, (desc,)
            )

            if not existing:
                ui.notify('No VAT Close JV found for this period.', color='warning')
                return

            with ui.dialog() as confirm_dlg, ui.card().classes('p-6 w-96'):
                ui.label(f'Delete VAT Close: {period_key}?').classes('text-lg font-bold mb-2')
                ui.label('This will remove the closing JV and restore all 44210/44270 balances.').classes('text-sm text-gray-500 mb-4')

                jv_ids_to_delete = [row[0] for row in existing]

                def _confirm_delete():
                    try:
                        for jv_id in jv_ids_to_delete:
                            connection.deleterow(
                                "DELETE FROM accounting_transaction_lines WHERE jv_id = ?",
                                (jv_id,)
                            )
                            connection.deleterow(
                                "DELETE FROM accounting_transactions WHERE jv_id = ?",
                                (jv_id,)
                            )
                        ui.notify(
                            f'VAT Close rolled back ({len(jv_ids_to_delete)} JV(s) removed). Balances restored.',
                            color='positive'
                        )
                        confirm_dlg.close()
                        self.calculate_totals()
                    except Exception as ex:
                        ui.notify(f'Error rolling back VAT close: {ex}', color='negative')

                with ui.row().classes('w-full justify-end gap-2 mt-4'):
                    ui.button('Cancel', on_click=confirm_dlg.close).props('flat')
                    ui.button('Delete & Rollback', icon='delete', on_click=_confirm_delete).props('color=negative')

            confirm_dlg.open()

        except Exception as e:
            ui.notify(f'Error: {e}', color='negative')


__all__ = ['vat_close_content']
