from nicegui import ui
from connection import connection
from datetime import datetime
import json
import os
import asyncio
from modern_page_layout import ModernPageLayout
from modern_design_system import ModernDesignSystem as MDS
from modern_ui_components import ModernCard, ModernButton

def business_track_content(standalone=False):
    """Content method for Business Track that can be used in tabs or standalone"""
    if standalone:
        with ModernPageLayout("Business Track", standalone=standalone):
            BusinessTrackUI()
    else:
        BusinessTrackUI()

@ui.page('/business-track')
def business_track_page():
    business_track_content(standalone=True)

import json
import os
from datetime import datetime

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
        """Fetch potential ledger accounts directly from Ledger table based on account prefix"""
        # Fetch Sales accounts: all accounts starting with 7 (Revenue)
        sales_data = []
        sql_sales = "SELECT AccountNumber, Name_en FROM Ledger WHERE AccountNumber LIKE '7%' ORDER BY AccountNumber"
        connection.contogetrows(sql_sales, sales_data)
        self.sales_accounts = {str(row[0]): f"{row[0]} - {row[1]}" for row in sales_data}
        
        # Fetch Purchase accounts: all accounts starting with 6 (Expenses)
        purchase_data = []
        sql_purchase = "SELECT AccountNumber, Name_en FROM Ledger WHERE AccountNumber LIKE '6%' ORDER BY AccountNumber"
        connection.contogetrows(sql_purchase, purchase_data)
        self.purchase_accounts = {str(row[0]): f"{row[0]} - {row[1]}" for row in purchase_data}

    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
            except:
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
            with ui.row().classes('w-full justify-between items-center bg-white/5 p-4 rounded-3xl glass border border-white/10'):
                with ui.column().classes('gap-1'):
                    ui.label('Financial Analytics').classes('text-xs font-black uppercase tracking-[0.2em] text-purple-400')
                    ui.label('Business Track').classes('text-3xl font-black text-white').style('font-family: "Outfit", sans-serif;')
                
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
        with ui.dialog() as d, ui.card().classes('w-[500px] p-8 rounded-3xl glass border border-white/10').style('background: rgba(15, 15, 25, 0.85); backdrop-filter: blur(20px);'):
            ui.label('VAT Configuration').classes('text-2xl font-black text-white mb-6')
            
            # Current VAT
            vat_history = []
            connection.contogetrows("SELECT id, vat_percentage, effective_date FROM vat_settings ORDER BY effective_date DESC", vat_history)
            
            with ui.column().classes('w-full gap-4'):
                new_vat = ui.number('New VAT Percentage (%)', value=vat_history[0][1] if vat_history else 11.0).props('outlined dark color=purple stack-label').classes('w-full text-white')
                new_date = ui.input('Effective Date').props('type=date outlined dark color=purple stack-label').classes('w-full text-white').set_value(datetime.now().strftime('%Y-%m-%d'))
                
                def save_vat():
                    sql = "INSERT INTO vat_settings (vat_percentage, effective_date) VALUES (?, ?)"
                    connection.insertingtodatabase(sql, (new_vat.value, new_date.value))
                    ui.notify('VAT settings updated', color='green')
                    d.close()
                
                ModernButton('Add VAT Record', icon='add', on_click=save_vat).classes('w-full mt-4')
                
                ui.label('VAT History').classes('text-[10px] font-black text-purple-400 mt-6 uppercase tracking-widest pl-2')
                with ui.column().classes('w-full max-h-40 overflow-y-auto gap-2 pr-2 custom-scrollbar'):
                    if vat_history:
                        for row in vat_history:
                            with ui.row().classes('w-full justify-between items-center bg-white/5 p-3 rounded-xl border border-white/10'):
                                ui.label(f"{row[1]}%").classes('font-black text-white')
                                ds = str(row[2])[:10]
                                ui.label(ds).classes('text-xs text-gray-400 font-mono')
                    else:
                        ui.label('No history found').classes('text-gray-500 text-xs italic pl-2')
            
            with ui.row().classes('w-full justify-end mt-8'):
                ui.button('Close', on_click=d.close).props('flat text-color=white').classes('rounded-xl hover:bg-white/5')
        d.open()

    def refresh_data(self):
        # Fetch all sums for accounts in mapping
        all_accounts = []
        for tab in ['sales', 'purchase']:
            for row in self.mapping[tab]:
                for acc in row:
                    if acc: all_accounts.append(acc)
        
        if not all_accounts:
            self.ledger_summary = {}
        else:
            acc_sums = {}
            # Query in bulk for performance
            placeholders = ', '.join(['?'] * len(all_accounts))
            sql = f"""
                SELECT 
                    COALESCE(l.auxiliary_id, l.account_number) as acc,
                    SUM(ISNULL(l.credit, 0) - ISNULL(l.debit, 0)) as balance
                FROM accounting_transaction_lines l
                WHERE l.auxiliary_id IN ({placeholders}) OR l.account_number IN ({placeholders})
                GROUP BY COALESCE(l.auxiliary_id, l.account_number)
            """
            data = []
            connection.contogetrows_with_params(sql, data, tuple(all_accounts + all_accounts))
            acc_sums = {row[0]: float(row[1]) for row in data}
            
            # Map back to structural grid
            self.ledger_summary = {'sales': [[0.0, 0.0] for _ in range(12)], 'purchase': [[0.0, 0.0] for _ in range(12)]}
            for tab in ['sales', 'purchase']:
                for r in range(12):
                    for c in range(2):
                        acc = self.mapping[tab][r][c]
                        # For purchase, negate the balance (we want net debit effect)
                        val = acc_sums.get(acc, 0.0)
                        if tab == 'purchase': val = -val
                        self.ledger_summary[tab][r][c] = val

        self.sales_container.clear()
        with self.sales_container: self.create_grid_view('sales')
        self.purchase_container.clear()
        with self.purchase_container: self.create_grid_view('purchase')

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
                # Table Header
                with ui.row().classes('w-full bg-white/10 p-4 border-b border-white/10 items-center justify-between'):
                    ui.label('Metric / Indicator').classes('w-[25%] text-xs font-black uppercase tracking-widest text-purple-400')
                    ui.label(col1_label).classes('flex-1 text-center text-xs font-black uppercase tracking-widest text-white')
                    ui.label(col2_label).classes('flex-1 text-center text-xs font-black uppercase tracking-widest text-white')

                # Table Rows
                for i, (group, label, icon) in enumerate(row_labels):
                    bg_class = 'bg-white/5' if i % 2 == 0 else 'bg-transparent'
                    border_class = 'border-b-2 border-purple-500/30' if (i+1) % 4 == 0 else 'border-b border-white/5'
                    
                    with ui.row().classes(f'w-full p-4 items-center {bg_class} {border_class} hover:bg-white/10 transition-colors'):
                        with ui.row().classes('w-[25%] items-center gap-4'):
                            with ui.element('div').classes('w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center'):
                                ui.icon(icon, size='1rem').classes('text-purple-400')
                            with ui.column().classes('gap-0'):
                                if i % 4 == 0:
                                    ui.label(group).classes('text-[8px] font-black text-purple-400 uppercase tracking-tighter')
                                ui.label(label).classes('text-sm font-bold text-white')

                        # Build Columns with Dropdowns and Values
                        for c in range(2):
                            with ui.column().classes('flex-1 items-center gap-1'):
                                # Dropdown to select account
                                def on_change(e, r=i, col=c, t=tab_type):
                                    self.mapping[t][r][col] = e.value
                                
                                ui.select(
                                    self.sales_accounts if is_sales else self.purchase_accounts, 
                                    value=self.mapping[tab_type][i][c],
                                    on_change=on_change,
                                    with_input=True,
                                    label='Select Ledger'
                                ).props('dense outlined stand-alone dark hide-bottom-space').classes('w-full max-w-[200px] text-xs transition-all opacity-40 hover:opacity-100')
                                
                                val = data[i][c]
                                ui.label(f'{val:,.2f}').classes(f'text-lg font-black {"text-green-400" if val >= 0 else "text-red-400"}').style('font-family: "Outfit", sans-serif;')


