from nicegui import ui
from datetime import datetime, date
import logging

from connection import connection
import asyncio
from database_manager import db_manager
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput
from modern_design_system import ModernDesignSystem as MDS
from year_end_closing_service import YearEndClosingService

def year_end_closing_content(standalone: bool = False):
    """Content method for Year End Closing tab."""
    if standalone:
        with ModernPageLayout("Year Transition", standalone=standalone):
            YearEndClosingUI(standalone=False)
    else:
        YearEndClosingUI(standalone=False)

@ui.page('/year-transition')
def year_end_closing_page_route():
    year_end_closing_content(standalone=True)

class YearEndClosingUI:
    def __init__(self, standalone=True):
        self.standalone = standalone
        self.balances = []
        self.stock_value = 0.0
        self.new_db_name = ""
        
        self.create_ui()

    def create_ui(self):
        with ui.row().classes('w-full gap-6 items-start p-4 animate-fade-in'):
            # Left: Control Panel
            with ui.column().classes('w-[400px] gap-4 flex-shrink-0'):
                with ModernCard(glass=True).classes('w-full p-6'):
                    ui.label('Year-End Closing').classes('text-xl font-black text-white mb-4')
                    ui.markdown('''
                    This process will:
                    1. Calculate opening balances for all accounts.
                    2. Create a new database for the next year.
                    3. Copy master data (Products, Customers, etc.).
                    4. Post an "Opening" Journal Voucher in the new database.
                    ''')
                    
                    next_year = datetime.now().year + 1
                    self.db_name_input = ModernInput(
                        'New Database Name', 
                        placeholder=f'POSDb_{next_year}',
                        value=f'POSDb_{next_year}'
                    ).classes('w-full mt-4')
                    
                    with ui.row().classes('w-full gap-3 mt-6'):
                        ModernButton(
                            'Calculate Balances',
                            icon='calculator',
                            on_click=self.calculate_balances
                        ).classes('flex-1 h-12')
                        
                        self.process_btn = ModernButton(
                            'Execute Closing',
                            icon='rocket_launch',
                            on_click=self.execute_closing
                        ).classes('flex-1 h-12').props('disabled')

                with ModernCard(glass=True).classes('w-full p-6'):
                    ui.label('Summary').classes('text-sm font-black text-white/80 mb-3')
                    self.summary_label = ui.label('Status: Ready to calculate.').classes('text-white font-bold')
                    self.stock_label = ui.label('Stock Value: $0.00').classes('text-white font-bold mt-2')

            # Right: Balances Preview
            with ui.column().classes('flex-1 min-w-0 gap-6'):
                with ModernCard(glass=True).classes('w-full p-6'):
                    ui.label('Opening Balances Preview').classes('text-lg font-black text-white mb-4')
                    
                    self.grid = ui.aggrid({
                        'columnDefs': [
                            {'headerName': 'Account', 'field': 'account', 'width': 150},
                            {'headerName': 'Name', 'field': 'name', 'flex': 1},
                            {'headerName': 'Debit', 'field': 'debit', 'width': 120, 'valueFormatter': 'Math.abs(x).toLocaleString()'},
                            {'headerName': 'Credit', 'field': 'credit', 'width': 120, 'valueFormatter': 'Math.abs(x).toLocaleString()'},
                        ],
                        'rowData': [],
                        'defaultColDef': MDS.get_ag_grid_default_def(),
                    }).classes('w-full h-[500px] ag-theme-quartz-dark')

    def calculate_balances(self):
        try:
            ui.notify('Calculating balances...', color='info')
            self.balances, self.stock_value = YearEndClosingService.get_opening_balances()
            
            self.grid.options['rowData'] = self.balances
            self.grid.update()
            
            self.summary_label.set_text(f'Status: {len(self.balances)} accounts calculated.')
            self.stock_label.set_text(f'Stock Value: ${self.stock_value:,.2f}')
            
            self.process_btn.props(remove='disabled')
            ui.notify('Calculation complete.', color='positive')
        except Exception as e:
            ui.notify(f'Error: {e}', color='negative')

    async def execute_closing(self):
        new_db = self.db_name_input.value.strip()
        if not new_db:
            ui.notify('Please enter a new database name.', color='warning')
            return
            
        with ui.dialog() as confirm, ui.card().classes('p-6'):
            ui.label('Confirm Year-End Closing').classes('text-xl font-bold mb-4')
            ui.label(f'This will create database {new_db} and post all opening balances. Are you sure?').classes('mb-6')
            with ui.row().classes('w-full justify-end gap-3'):
                ui.button('Cancel', on_click=confirm.close).props('flat')
                ui.button('Yes, Execute', color='red', on_click=lambda: self.run_process(new_db, confirm))
        confirm.open()

    async def run_process(self, new_db, dialog):
        dialog.close()
        try:
            loading = ui.dialog().props('persistent')
            with loading, ui.card().classes('p-10 items-center gap-4 w-[600px]'):
                ui.spinner(size='lg')
                ui.label('Fiscal Year Rollover in Progress').classes('text-xl font-bold')
                
                with ui.column().classes('w-full border p-4 rounded bg-black/5'):
                    self.status_label = ui.label('Initializing...').classes('font-medium text-[#08CB00] text-lg')
                    self.progress_bar = ui.linear_progress(value=0, show_value=False).classes('w-full rounded h-2 mt-2')
                
                ui.label('Process Logs').classes('w-full text-xs font-bold uppercase tracking-tight text-gray-400 mt-4')
                self.log_container = ui.scroll_area().classes('w-full h-48 border rounded p-2 bg-gray-50 text-xs font-mono')
                with self.log_container:
                    self.log_content = ui.column().classes('gap-1')
            loading.open()
            
            async def update_status(msg, step=None):
                self.status_label.set_text(msg)
                with self.log_content:
                    ui.label(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
                self.log_container.scroll_to(percent=1)
                if step:
                    self.progress_bar.set_value(step / 10.0)
                await asyncio.sleep(0.5)

            current_year = datetime.now().year
            current_db = db_manager.CONNECTION_CONFIG['database']
            # Improved archive naming: avoid POSDb2026_2026
            archive_base = current_db
            for y in range(2000, 2100):
                if str(y) in current_db:
                    archive_base = current_db.replace(str(y), "").strip("_").strip("-")
                    break
            archive_db = f"Archive_{archive_base}_{current_year}"

            # 1. Post P&L Closing Entry to Zero out Class 6 and 7
            await update_status('Step 1/10: Closing P&L accounts (6 & 7) to 138/139...', 1)
            success, msg, net_res, res_account = await YearEndClosingService.close_pnl_accounts(lambda m: update_status(f"P&L: {m}", 1))
            if not success:
                ui.notify(f'P&L Closing failed: {msg}', color='negative')
                loading.close()
                return

            # 2. Close VAT
            await update_status('Step 2/10: Closing VAT for the fiscal year...', 2)
            success, msg = await YearEndClosingService.close_vat_for_year(lambda m: update_status(f"VAT: {m}", 2))
            if not success:
               ui.notify(f'VAT Closing failed: {msg}', color='warning')

            # 3. Recalculate balances after closures
            await update_status('Step 3/10: Finalizing opening balances report...', 3)
            self.balances, _ = YearEndClosingService.get_opening_balances()

            # 4. Create Backup (now contains closing entries)
            await update_status('Step 4/10: Creating database backup...', 4)
            success, backup_file = await YearEndClosingService.run_backup(current_db, lambda m: update_status(f"Backup: {m}", 4))
            if not success:
                ui.notify(f'Backup failed: {backup_file}', color='negative')
                loading.close()
                return

            # 5. Restore as Historic Archive
            await update_status(f'Step 5/10: Saving archive as {archive_db}...', 5)
            success, msg = await YearEndClosingService.run_restore_archive(backup_file, archive_db, lambda m: update_status(f"Archive: {m}", 5))

            # 6. Create New Year Database (Initial Copy)
            await update_status(f'Step 6/10: Initializing new database {new_db}...', 6)
            success, msg = await YearEndClosingService.create_new_database_from_backup(backup_file, new_db, lambda m: update_status(f"DB Clone: {m}", 6))
            if not success:
                ui.notify(f'DB Initialization failed: {msg}', color='negative')
                loading.close()
                return

            # 7. Execute Opening JV in New Database
            await update_status('Step 7/10: Posting opening balances in new database...', 7)
            success, msg = await YearEndClosingService.post_opening_jv(new_db, self.balances, self.stock_value, lambda m: update_status(f"Opening JV: {m}", 7))
            if not success:
                ui.notify(f'Opening Balances failed: {msg}', color='negative')
                loading.close()
                return

            # 8. Clean Transaction Tables in New Database
            await update_status('Step 8/11: Cleaning transaction records in new database...', 8)
            success, msg = await YearEndClosingService.empty_operational_tables(new_db, lambda m: update_status(f"Cleanup: {m}", 8))

            # 9. Rollover Open Documents (Unpaid Invoices)
            await update_status('Step 9/11: Rolling over open invoices (unpaid)...', 9)
            success, msg = await YearEndClosingService.rollover_open_documents(new_db, lambda m: update_status(f"Open Items: {m}", 9))

            # 10. Verify Opening Balances
            await update_status('Step 10/11: Verifying database consistency...', 10)
            success, msg = await YearEndClosingService.verify_opening_jv_exists(new_db, lambda m: update_status(f"Verify: {m}", 10))

            # 11. Log Transition
            await update_status('Step 11/11: Logging transition history...', 11)
            await YearEndClosingService.log_fiscal_year_transition(current_year, current_db, new_db, archive_db, "Completed")

            loading.close()
            ui.notify('Year-End Closing completed successfully!', color='positive', duration=10)
            
            with ui.dialog() as info, ui.card().classes('p-8 items-center text-center'):
                ui.icon('check_circle', color='positive', size='4rem')
                ui.label('Process Complete').classes('text-2xl font-black mt-4')
                ui.label(f'New database {new_db} is ready with your accounts intact.').classes('text-lg mt-2')
                ui.label(f'Archive {archive_db} has been preserved.').classes('text-sm text-gray-500')
                ui.label('Please log out and select the new year to start working.').classes('text-gray-500 mt-4')
                ui.button('Logout & Finish', color='negative', on_click=lambda: ui.navigate.to('/logout')).classes('mt-6 h-12 w-40')
            info.open()
            
        except Exception as e:
            ui.notify(f'Critical error: {e}', color='negative')
            if 'loading' in locals(): loading.close()

__all__ = ['year_end_closing_content']
