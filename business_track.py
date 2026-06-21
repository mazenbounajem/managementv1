from nicegui import ui
from connection import connection
from datetime import datetime
import json
import os

from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton


def business_track_content(standalone: bool = False):
    """Content method for Business Track that can be used in tabs or standalone."""
    if standalone:
        with ModernPageLayout("Business Track", standalone=standalone):
            BusinessTrackUI()
    else:
        BusinessTrackUI()


@ui.page('/business-track')
def business_track_page():
    business_track_content(standalone=True)


class BusinessTrackUI:
    def __init__(self):
        self.settings_file = 'business_track_settings.json'
        self.purchase_accounts = {}
        self.sales_accounts = {}
        self.mapping = self.load_settings()
        self.ledger_summary = {}

        self.load_accounts()
        self.create_ui()
        self.refresh_data()

    def load_accounts(self):
        """Fetch potential ledger accounts directly from Ledger table based on account prefix."""
        # Sales: all accounts starting with 7 (Revenue)
        sales_data = []
        sql_sales = "SELECT AccountNumber, Name_en FROM Ledger WHERE AccountNumber LIKE '7%' ORDER BY AccountNumber"
        connection.contogetrows(sql_sales, sales_data)
        self.sales_accounts = {str(row[0]): f"{row[0]} - {row[1]}" for row in sales_data}

        # Purchase: all accounts starting with 6 (Expenses)
        purchase_data = []
        sql_purchase = "SELECT AccountNumber, Name_en FROM Ledger WHERE AccountNumber LIKE '6%' ORDER BY AccountNumber"
        connection.contogetrows(sql_purchase, purchase_data)

        # Cash/GL: all accounts starting with 5 (e.g. 5300)
        cash_gl_data = []
        sql_cash_gl = "SELECT AccountNumber, Name_en FROM Ledger WHERE AccountNumber LIKE '5%' ORDER BY AccountNumber"
        connection.contogetrows(sql_cash_gl, cash_gl_data)

        # Merge 6% + 5% into purchase_accounts so 5300 is selectable.
        merged = purchase_data + cash_gl_data
        self.purchase_accounts = {str(row[0]): f"{row[0]} - {row[1]}" for row in merged}

    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass

        # Default empty mapping
        return {
            'sales': [['' for _ in range(2)] for _ in range(12)],
            'purchase': [['' for _ in range(2)] for _ in range(12)]
        }

    def save_settings(self):
        with open(self.settings_file, 'w') as f:
            json.dump(self.mapping, f)
        ui.notify('Settings saved successfully', color='green')
        self.refresh_data()

    def create_ui(self):
        with ui.column().classes('w-full gap-6 animate-fade-in'):
            # Header
            with ui.row().classes(
                'w-full justify-between items-center bg-white/5 p-4 rounded-3xl glass border border-white/10'
            ):
                with ui.column().classes('gap-1'):
                    ui.label('Financial Analytics').classes(
                        'text-xs font-black uppercase tracking-[0.2em] text-purple-400'
                    )
                    ui.label('Business Track').classes('text-3xl font-black text-white').style(
                        'font-family: "Outfit", sans-serif;'
                    )

                with ui.row().classes('items-center gap-4'):
                    ModernButton('VAT Settings', icon='percent', on_click=self.open_vat_settings, variant='outline').classes('px-4')
                    ModernButton('Save Mapping', icon='save', on_click=self.save_settings).classes('px-6')
                    ModernButton('Refresh', icon='refresh', on_click=self.refresh_data, variant='outline').classes('px-4')

                    with ui.tabs().classes('text-white') as self.tabs:
                        self.sales_tab = ui.tab('Sales')
                        self.purchase_tab = ui.tab('Purchase')

            with ui.tab_panels(self.tabs, value=self.sales_tab).classes('w-full bg-transparent'):
                with ui.tab_panel(self.sales_tab).classes('p-0'):
                    self.sales_container = ui.column().classes('w-full')

                with ui.tab_panel(self.purchase_tab).classes('p-0'):
                    self.purchase_container = ui.column().classes('w-full')

    def open_vat_settings(self):
        with ui.dialog() as d, ui.card().classes(
            'w-[500px] p-8 rounded-3xl glass border border-white/10'
        ).style('background: rgba(15, 15, 25, 0.85); backdrop-filter: blur(20px);'):
            ui.label('VAT Configuration').classes('text-2xl font-black text-white mb-6')

            vat_history = []
            connection.contogetrows(
                "SELECT id, vat_percentage, effective_date FROM vat_settings ORDER BY effective_date DESC",
                vat_history
            )

            with ui.column().classes('w-full gap-4'):
                new_vat = ui.number(
                    'New VAT Percentage (%)',
                    value=vat_history[0][1] if vat_history else 11.0
                ).props('outlined dark color=purple stack-label').classes('w-full text-white')

                new_date = ui.input('Effective Date').props(
                    'type=date outlined dark color=purple stack-label'
                ).classes('w-full text-white').set_value(datetime.now().strftime('%Y-%m-%d'))

                def save_vat():
                    sql = "INSERT INTO vat_settings (vat_percentage, effective_date) VALUES (?, ?)"
                    connection.insertingtodatabase(sql, (new_vat.value, new_date.value))
                    ui.notify('VAT settings updated', color='green')
                    d.close()

                ModernButton('Add VAT Record', icon='add', on_click=save_vat).classes('w-full mt-4')

                ui.label('VAT History').classes(
                    'text-[10px] font-black text-purple-400 mt-6 uppercase tracking-widest pl-2'
                )

                with ui.column().classes('w-full max-h-40 overflow-y-auto gap-2 pr-2 custom-scrollbar'):
                    if vat_history:
                        for row in vat_history:
                            with ui.row().classes(
                                'w-full justify-between items-center bg-white/5 p-3 rounded-xl border border-white/10'
                            ):
                                ui.label(f"{row[1]}%").classes('font-black text-white')
                                ds = str(row[2])[:10]
                                ui.label(ds).classes('text-xs text-gray-400 font-mono')
                    else:
                        ui.label('No history found').classes('text-gray-500 text-xs italic pl-2')

            with ui.row().classes('w-full justify-end mt-8'):
                ui.button('Close', on_click=d.close).props('flat text-color=white').classes('rounded-xl hover:bg-white/5')

        d.open()

    def refresh_data(self):
        all_accounts = []
        for tab in ['sales', 'purchase']:
            for row in self.mapping[tab]:
                for acc in row:
                    if acc:
                        all_accounts.append(str(acc).strip())

        self.ledger_summary = {
            'sales': [[0.0, 0.0] for _ in range(12)],
            'purchase': [[0.0, 0.0] for _ in range(12)]
        }

        if not all_accounts:
            self.sales_container.clear()
            with self.sales_container:
                self.create_grid_view('sales')

            self.purchase_container.clear()
            with self.purchase_container:
                self.create_grid_view('purchase')
            return

        exact_aux_codes = sorted({a for a in all_accounts if '.' in a})
        base_aux_codes = sorted({a for a in all_accounts if '.' not in a})

        acc_sums = {}

        # 1) Exact auxiliary.number sums (e.g. 44270.1)
        if exact_aux_codes:
            placeholders = ', '.join(['?'] * len(exact_aux_codes))
            sql_exact_aux = f"""
                SELECT
                    a.number as map_key,
                    SUM(ISNULL(l.credit, 0) - ISNULL(l.debit, 0)) as balance
                FROM accounting_transaction_lines l
                JOIN auxiliary a ON TRY_CAST(l.auxiliary_id AS INT) = a.id
                WHERE a.number IN ({placeholders})
                GROUP BY a.number
            """
            data = []
            connection.contogetrows_with_params(sql_exact_aux, data, tuple(exact_aux_codes))
            for row in data:
                acc_sums[str(row[0])] = float(row[1] or 0.0)

        # 2) Base auxiliary code sums (e.g. 5300 => sum all auxiliary.number LIKE '5300.%')
        base_aux_codes_for_cash = sorted([c for c in base_aux_codes if str(c).startswith('53')])

        if base_aux_codes_for_cash:
            for base_code in base_aux_codes_for_cash:
                data = []
                sql = """
                    SELECT
                        ? as map_key,
                        SUM(ISNULL(l.credit, 0) - ISNULL(l.debit, 0)) as balance
                    FROM accounting_transaction_lines l
                    JOIN auxiliary a ON TRY_CAST(l.auxiliary_id AS INT) = a.id
                    WHERE a.number LIKE ? + '.%'
                """
                connection.contogetrows_with_params(sql, data, (base_code, base_code))
                if data:
                    acc_sums[base_code] = float(data[0][1] or 0.0)

        # 3) Exact ledger code sums (e.g. 7111, 6011, 6019, 7090)
        ledger_codes_for_non_cash = sorted([c for c in base_aux_codes if not str(c).startswith('53')])

        if ledger_codes_for_non_cash:
            for ledger_code in ledger_codes_for_non_cash:
                data = []
                sql = """
                    SELECT
                        ? as map_key,
                        SUM(ISNULL(l.credit, 0) - ISNULL(l.debit, 0)) as balance
                    FROM accounting_transaction_lines l
                    WHERE CAST(l.account_number AS VARCHAR(50)) = CAST(? AS VARCHAR(50))
                """
                connection.contogetrows_with_params(sql, data, (ledger_code, ledger_code))
                if data and data[0]:
                    acc_sums[ledger_code] = float(data[0][1] or 0.0)

        # Map back to structural grid
        for tab in ['sales', 'purchase']:
            for r in range(12):
                for c in range(2):
                    acc = self.mapping[tab][r][c]
                    if not acc:
                        continue
                    acc = str(acc).strip()

                    val = float(acc_sums.get(acc, 0.0))
                    if tab == 'purchase':
                        val = -val
                    self.ledger_summary[tab][r][c] = val

        self.sales_container.clear()
        with self.sales_container:
            self.create_grid_view('sales')

        self.purchase_container.clear()
        with self.purchase_container:
            self.create_grid_view('purchase')

    def create_grid_view(self, tab_type):
        is_sales = tab_type == 'sales'
        row_labels = [
            ("LOCAL SALES" if is_sales else "LOCAL PURCHASE", "Value", "trending_up" if is_sales else "shopping_cart"),
            ("LOCAL SALES" if is_sales else "LOCAL PURCHASE", "Discount / Invoice", "money_off"),
            ("LOCAL SALES" if is_sales else "LOCAL PURCHASE", "Discount / Product", "local_offer"),
            ("LOCAL SALES" if is_sales else "LOCAL PURCHASE", "Charges", "add_business"),

            ("RETURN" if is_sales else "RETURN", "Value", "settings_backup_restore"),
            ("RETURN" if is_sales else "RETURN", "Discount / Invoice", "money_off"),
            ("RETURN" if is_sales else "RETURN", "Discount / Product", "local_offer"),
            ("RETURN" if is_sales else "RETURN", "Charges", "add_business"),

            ("EXPORT" if is_sales else "IMPORT", "Value", "public"),
            ("EXPORT" if is_sales else "IMPORT", "Discount / Invoice", "money_off"),
            ("EXPORT" if is_sales else "IMPORT", "Discount / Product", "local_offer"),
            ("EXPORT" if is_sales else "IMPORT", "Charges", "add_business"),
        ]

        col1_label = "Local VAT Sales" if is_sales else "With VAT"
        col2_label = "Local Non-VAT Sales" if is_sales else "Without VAT"

        data = self.ledger_summary.get(tab_type, [[0.0, 0.0] for _ in range(12)])

        with ModernCard(glass=True).classes('w-full p-8'):
            with ui.column().classes('w-full gap-0 border border-white/10 rounded-2xl overflow-hidden'):
                with ui.row().classes('w-full bg-white/10 p-4 border-b border-white/10 items-center justify-between'):
                    ui.label('Metric / Indicator').classes('w-[25%] text-xs font-black uppercase tracking-widest text-purple-400')
                    ui.label(col1_label).classes('flex-1 text-center text-xs font-black uppercase tracking-widest text-white')
                    ui.label(col2_label).classes('flex-1 text-center text-xs font-black uppercase tracking-widest text-white')

                for i, (group, label, icon) in enumerate(row_labels):
                    bg_class = 'bg-white/5' if i % 2 == 0 else 'bg-transparent'
                    border_class = 'border-b-2 border-purple-500/30' if (i + 1) % 4 == 0 else 'border-b border-white/5'

                    with ui.row().classes(f'w-full p-4 items-center {bg_class} {border_class} hover:bg-white/10 transition-colors'):
                        with ui.row().classes('w-[25%] items-center gap-4'):
                            with ui.element('div').classes('w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center'):
                                ui.icon(icon, size='1rem').classes('text-purple-400')
                            with ui.column().classes('gap-0'):
                                if i % 4 == 0:
                                    ui.label(group).classes('text-[8px] font-black text-purple-400 uppercase tracking-tighter')
                                ui.label(label).classes('text-sm font-bold text-white')

                        for c in range(2):
                            with ui.column().classes('flex-1 items-center gap-1'):
                                def on_change(e, r=i, col=c, t=tab_type):
                                    self.mapping[t][r][col] = e.value

                                options = dict(self.sales_accounts if is_sales else self.purchase_accounts)

                                # Always allow empty selection from saved mapping.
                                if '' not in options:
                                    options[''] = ''

                                current_value = self.mapping[tab_type][i][c]
                                if current_value is None:
                                    current_value = ''
                                current_value = str(current_value).strip()

                                safe_value = current_value if current_value in options else ''
                                ui.select(
                                    options,
                                    value=safe_value,
                                    on_change=on_change,
                                    with_input=True,
                                    label='Select Ledger'
                                ).props('dense outlined stand-alone dark hide-bottom-space').classes(
                                    'w-full max-w-[200px] text-xs transition-all opacity-40 hover:opacity-100'
                                )

                                val = data[i][c]
                                ui.label(f'{val:,.2f}').classes(
                                    f'text-lg font-black { "text-green-400" if val >= 0 else "text-red-400"}'
                                ).style('font-family: "Outfit", sans-serif;')
                # end for c
            # end for i
        # end container


