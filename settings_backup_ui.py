
from nicegui import ui
from connection import connection
import os
import pyodbc
from datetime import datetime
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput
from modern_design_system import ModernDesignSystem as MDS

def get_config(key, default=''):
    try:
        data = []
        connection.contogetrows(f"SELECT setting_value FROM configuration WHERE setting_key = '{key}'", data)
        return data[0][0] if data else default
    except expression as identifier:
        return default

def set_config(key, value, description=''):
    try:
        data = []
        connection.contogetrows(f"SELECT id FROM configuration WHERE setting_key = '{key}'", data)
        if data:
            sql = "UPDATE configuration SET setting_value=?, updated_at=GETDATE() WHERE setting_key=?"
            connection.insertingtodatabase(sql, (value, key))
        else:
            sql = "INSERT INTO configuration (setting_key, setting_value, description, updated_at) VALUES (?, ?, ?, GETDATE())"
            connection.insertingtodatabase(sql, (key, value, description))
    except Exception as e:
        print(f"Error setting config: {e}")

async def perform_backup(directory):
    if not directory:
        ui.notify('Backup directory is not set.', color='negative')
        return

    def _do_backup():
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"POSDB_Backup_{timestamp}.bak"
        filepath = os.path.join(directory, filename)
        
        conn_str = (
            "Driver={SQL Server Native Client 11.0};"
            "Server=DESKTOP-Q7U1STD\\SQLEXPRESS02;"
            "Database=master;" # Need to be on master or use different DB to back up POSDB safely
            "Trusted_Connection=yes;"
        )
        conn = pyodbc.connect(conn_str, autocommit=True)
        cursor = conn.cursor()
        
        backup_query = f"BACKUP DATABASE [POSDB] TO DISK = '{filepath}' WITH FORMAT, MEDIANAME = 'SQLServerBackups', NAME = 'Full Backup of POSDB';"
        cursor.execute(backup_query)
        while cursor.nextset():
            pass
            
        cursor.close()
        conn.close()
        return filename

    try:
        ui.notify('Starting backup (this may take a moment)...', color='info', timeout=5000)
        from nicegui import run
        filename = await run.io_bound(_do_backup)
        ui.notify(f'Backup completed successfully: {filename}', color='positive', timeout=10000)
    except Exception as e:
        ui.notify(f'Backup failed: {str(e)}', color='negative', multi_line=True, timeout=10000)


def settings_backup_content(standalone=False):
    if standalone:
        with ModernPageLayout("Settings & Backup", standalone=standalone):
            SettingsBackupUI(standalone=False)
    else:
        SettingsBackupUI(standalone=False)

@ui.page('/settings-backup')
def settings_backup_page_route():
    settings_backup_content(standalone=True)

class SettingsBackupUI:
    def __init__(self, standalone=True):
        self.standalone = standalone
        self.directory_input = None
        self.auto_backup_switch = None
        self.create_ui()
        self.load_settings()

    def create_ui(self):
        if self.standalone:
            layout_container = ModernPageLayout("Settings & Backup", standalone=True)
            layout_container.__enter__()
        try:
            with ui.row().classes('w-full justify-center mt-6'):
                with ModernCard(glass=True).classes('w-full max-w-2xl p-8 gap-6 flex flex-col'):
                    ui.label('Database Backup Configuration').classes('text-2xl font-black text-white mb-2 uppercase tracking-widest opacity-80')
                    
                    self.directory_input = ui.input('Backup Directory Path').classes('w-full glass-input text-white text-lg').props('dark rounded outlined')
                    ui.label('Example: C:\\dbbackup\\backups').classes('text-xs text-gray-400 mt-[-1rem] mb-2')
                    
                    self.auto_backup_switch = ui.switch('Enable Automatic Backups').classes('text-white text-lg mb-4')
                    
                    with ui.row().classes('w-full justify-end gap-4 mt-6'):
                        ui.button('Save Settings', on_click=self.save_settings).classes('h-12 w-48 bg-[#08CB00] text-black font-bold uppercase tracking-wider rounded-xl hover:bg-white transition-all')
                    
                    ui.separator().classes('my-6 opacity-30')
                    
                    ui.label('Manual Tools').classes('text-lg font-bold text-white mb-2 uppercase tracking-widest opacity-70')
                    with ui.row().classes('w-full gap-4'):
                        ui.button('Run Manual Backup', on_click=self.run_manual_backup, icon='backup').classes('h-12 flex-1 bg-blue-600 text-white font-bold uppercase tracking-wider rounded-xl hover:bg-blue-500 transition-all')
        finally:
            if self.standalone:
                layout_container.__exit__(None, None, None)

    def load_settings(self):
        dir_val = get_config('backup_directory', 'C:\\dbbackup\\backups')
        self.directory_input.value = dir_val
        auto_val = get_config('auto_backup_enabled', 'false')
        self.auto_backup_switch.value = (auto_val.lower() == 'true')

    def save_settings(self):
        dir_val = self.directory_input.value
        auto_val = 'true' if self.auto_backup_switch.value else 'false'
        
        set_config('backup_directory', dir_val, 'Directory where database backups are saved.')
        set_config('auto_backup_enabled', auto_val, 'Enable or disable automatic daily backups.')
        
        ui.notify('Settings saved successfully.', color='positive')

    async def run_manual_backup(self):
        dir_val = self.directory_input.value
        await perform_backup(dir_val)
