from nicegui import ui
from connection import connection
from uiaggridtheme import uiAggridTheme
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput
from modern_design_system import ModernDesignSystem as MDS

def services_content(standalone=False):
    """Content method for services that can be used in tabs"""
    if standalone:
        with ModernPageLayout("Services Management", standalone=standalone):
            ServicesUI(standalone=False)
    else:
        ServicesUI(standalone=False)

@ui.page('/services')
def services_page_route():
    services_content(standalone=True)

class ServicesUI:
    def __init__(self, standalone=True):
        self.standalone = standalone
        self.services_data = []
        self.container = None
        self.create_ui()
        self.refresh_data()

    def load_services(self):
        query = "SELECT id, service_name, description, duration_minutes, price, is_active FROM services ORDER BY service_name"
        data = []
        connection.contogetrows(query, data)
        self.services_data = []
        for r in data:
            self.services_data.append({
                'id': r[0], 'name': r[1], 'desc': r[2] or '', 'duration': r[3], 'price': float(r[4]) if r[4] else 0.0, 'active': bool(r[5])
            })

    def refresh_data(self):
        self.load_services()
        self.render_list()

    def create_ui(self):
        # Wrap content in ModernPageLayout only if standalone, otherwise just render the content
        if self.standalone:
            layout_container = ModernPageLayout("Services Management", standalone=True)
            layout_container.__enter__()
        
        try:
            # Action Bar
            with ui.row().classes('w-full justify-between items-center mb-6 p-4 rounded-2xl bg-white/5 glass border border-white/10'):
                ui.label('Services Overview').classes('text-2xl font-black text-white')
                with ui.row().classes('gap-3'):
                    ModernButton('Add Service', icon='add', on_click=self.add_service, variant='primary')
                    ModernButton('Refresh', icon='refresh', on_click=self.refresh_data, variant='outline').classes('text-white border-white/20')

            self.container = ui.column().classes('w-full gap-4')
        finally:
            if self.standalone:
                layout_container.__exit__(None, None, None)

    def render_list(self):
        self.container.clear()
        with self.container:
            if not self.services_data:
                with ModernCard(glass=True).classes('w-full p-12 items-center justify-center'):
                    ui.icon('info', size='lg').classes('text-white/20 mb-4')
                    ui.label('No services found. Click "Add Service" to start.').classes('text-white/40')
                return

            for srv in self.services_data:
                with ModernCard(glass=srv['active']).classes('w-full p-6 transition-all hover:scale-[1.01] hover:shadow-xl'):
                    with ui.row().classes('w-full items-center justify-between gap-6'):
                        # Icon/Initial
                        with ui.element('div').classes('w-12 h-12 rounded-xl bg-primary/20 flex items-center justify-center border border-primary/30'):
                            ui.label(srv['name'][0].upper()).classes('text-xl font-black text-primary')
                        
                        # Info
                        with ui.column().classes('flex-1 gap-1'):
                            ui.label(srv['name']).classes('text-lg font-black text-white')
                            ui.label(srv['desc'] or 'No description provided.').classes('text-sm text-white/50 line-clamp-1')
                        
                        # Stats
                        with ui.row().classes('gap-8'):
                            with ui.column().classes('items-center'):
                                ui.label('Duration').classes('text-[10px] uppercase tracking-widest text-white/30')
                                ui.label(f"{srv['duration']}m").classes('text-sm font-bold text-white')
                            with ui.column().classes('items-center border-l border-white/10 pl-8'):
                                ui.label('Price').classes('text-[10px] uppercase tracking-widest text-white/30')
                                ui.label(f"${srv['price']:.2f}").classes('text-sm font-bold text-white')
                            with ui.column().classes('items-center border-l border-white/10 pl-8 w-24'):
                                ui.label('Status').classes('text-[10px] uppercase tracking-widest text-white/30')
                                color = 'primary' if srv['active'] else 'error'
                                with ui.row().classes('items-center gap-2'):
                                    ui.element('div').classes(f'w-2 h-2 rounded-full bg-{color}')
                                    ui.label('Active' if srv['active'] else 'Inactive').classes(f'text-xs font-bold text-{color}')

                        # Actions
                        with ui.row().classes('gap-2 border-l border-white/10 pl-6'):
                            ModernButton('', icon='edit', on_click=lambda s=srv: self.edit_service(s), variant='secondary').classes('w-10 h-10')
                            ModernButton('', icon='delete', on_click=lambda s=srv: self.delete_service(s), variant='error').classes('w-10 h-10')

    def add_service(self):
        self.show_dialog()

    def edit_service(self, srv):
        self.show_dialog(srv)

    def show_dialog(self, srv=None):
        dialog = ui.dialog()
        with dialog, ModernCard(glass=True).classes('w-[450px] p-8'):
            ui.label('Service Details').classes('text-2xl font-black mb-6 text-white')
            
            with ui.column().classes('w-full gap-4'):
                name_in = ui.input('Service Name', value=srv['name'] if srv else '').classes('w-full glass-input').props('dark rounded outlined')
                desc_in = ui.textarea('Description', value=srv['desc'] if srv else '').classes('w-full glass-input h-24').props('dark rounded outlined')
                
                with ui.row().classes('w-full gap-4'):
                    dur_in = ui.select(['15', '30', '45', '60', '90', '120'], label='Duration (min)', value=str(srv['duration'] if srv else '30')).classes('flex-1 glass-input').props('dark rounded outlined')
                    pri_in = ui.number('Price ($)', value=srv['price'] if srv else 0.0, format='%.2f').classes('flex-1 glass-input').props('dark rounded outlined')
                
                act_in = ui.switch('Active Status', value=srv['active'] if srv else True).classes('text-white')

                with ui.row().classes('w-full justify-end gap-3 mt-6'):
                    ModernButton('Cancel', on_click=dialog.close, variant='secondary')
                    ModernButton('Save Service', icon='save', on_click=lambda: self.perform_save(srv['id'] if srv else None, name_in.value, desc_in.value, dur_in.value, pri_in.value, act_in.value, dialog), variant='primary')
        dialog.open()

    def perform_save(self, s_id, name, desc, dur, pri, active, dialog):
        if not name:
            ui.notify('Name is required', color='warning')
            return
        
        try:
            if s_id:
                sql = "UPDATE services SET service_name=?, description=?, duration_minutes=?, price=?, is_active=?, updated_at=GETDATE() WHERE id=?"
                connection.insertingtodatabase(sql, (name, desc, int(dur), float(pri), 1 if active else 0, s_id))
            else:
                sql = "INSERT INTO services (service_name, description, duration_minutes, price, is_active) VALUES (?, ?, ?, ?, ?)"
                connection.insertingtodatabase(sql, (name, desc, int(dur), float(pri), 1 if active else 0))
            
            ui.notify('Service saved', color='positive')
            dialog.close()
            self.refresh_data()
        except Exception as e:
            ui.notify(f'Error: {str(e)}', color='negative')

    def delete_service(self, srv):
        async def confirm():
            try:
                # Check if service is used in appointments
                appointments = []
                connection.contogetrows("SELECT COUNT(*) FROM appointments WHERE service_id=?", appointments, (srv['id'],))
                if appointments and appointments[0][0] > 0:
                    ui.notify('Cannot delete: Service is used in appointments', color='warning')
                    return
                    
                connection.deleterow("DELETE FROM services WHERE id=?", srv['id'])
                ui.notify('Service removed', color='positive')
                self.refresh_data()
            except Exception as e:
                ui.notify(f'Error: {str(e)}', color='negative')
        
        ui.notify(f'Confirm deletion of {srv["name"]}?', close_button='Confirm', on_dismiss=confirm, timeout=5000)