from nicegui import ui
from connection import connection
from uiaggridtheme import uiAggridTheme
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage
import datetime
import calendar
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput
from modern_design_system import ModernDesignSystem as MDS

@ui.page('/appointments')
def appointments_page_route():
    with ModernPageLayout("Appointment Calendar"):
        AppointmentsUI()

class AppointmentsUI:
    def __init__(self):
        self.current_date = datetime.date.today()
        self.appointments_data = []
        self.calendar_grid = None
        self.create_ui()
        self.refresh_data()

    def load_appointments(self):
        year, month = self.current_date.year, self.current_date.month
        start_date = datetime.date(year, month, 1) - datetime.timedelta(days=7)
        _, last_day = calendar.monthrange(year, month)
        end_date = datetime.date(year, month, last_day) + datetime.timedelta(days=7)

        query = """
            SELECT a.id, c.customer_name, e.first_name, e.last_name, s.service_name, 
                   a.appointment_date, a.appointment_time, a.status, s.duration_minutes
            FROM appointments a
            LEFT JOIN customers c ON a.customer_id = c.id
            LEFT JOIN employees e ON a.employee_id = e.id
            LEFT JOIN services s ON a.service_id = s.id
            WHERE a.appointment_date >= ? AND a.appointment_date <= ?
        """
        data = []
        connection.contogetrows(query, data, (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
        
        self.appointments_data = []
        for r in data:
            self.appointments_data.append({
                'id': r[0], 'customer': r[1], 'emp': f"{r[2]} {r[3]}", 'service': r[4],
                'date': r[5], 'time': r[6], 'status': r[7], 'duration': r[8] or 30
            })

    def refresh_data(self):
        self.load_appointments()
        self.render_calendar()

    def create_ui(self):
        with ui.row().classes('w-full gap-6 items-start'):
            # Left Column: Calendar Grid
            with ui.column().classes('flex-1 gap-4'):
                with ui.row().classes('w-full justify-between items-center mb-4 px-2'):
                    self.month_label = ui.label('').classes('text-3xl font-black text-white uppercase tracking-widest')
                    with ui.row().classes('items-baseline gap-2 opacity-50'):
                        ui.icon('calendar_today', size='sm').classes('text-white')
                        ui.label('Appointments').classes('text-lg font-bold text-white')

                self.calendar_grid = ui.grid(columns=7).classes('w-full gap-4')

            # Right Column: Action Bar
            with ui.column().classes('w-80px items-center'):
                from modern_ui_components import ModernActionBar
                ModernActionBar(
                    on_new=self.new_appointment,
                    on_save=self.go_today, # Mapping 'Today' to save icon temporarily as placeholder or just use custom buttons
                    # Custom mapping for calendar navigation
                    on_refresh=self.refresh_data,
                    on_chatgpt=lambda: ui.open('https://chatgpt.com', new_tab=True),
                    button_class='h-16',
                    classes=' '
                ).style('position: static; width: 80px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); margin-top: 0;')
                
                # Navigation Overrides/Additions
                with ui.column().classes('mt-4 gap-4 items-center'):
                    ModernButton('', icon='chevron_left', on_click=self.prev_month, variant='secondary').classes('w-14 h-14 rounded-2xl')
                    ModernButton('', icon='today', on_click=self.go_today, variant='primary').classes('w-14 h-14 rounded-2xl')
                    ModernButton('', icon='chevron_right', on_click=self.next_month, variant='secondary').classes('w-14 h-14 rounded-2xl')

    def render_calendar(self):
        self.month_label.text = f"{calendar.month_name[self.current_date.month]} {self.current_date.year}"
        self.calendar_grid.clear()
        
        with self.calendar_grid:
            # Days of week
            for day in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']:
                ui.label(day).classes('text-center text-white/40 font-bold uppercase text-xs tracking-widest mb-2')

            year, month = self.current_date.year, self.current_date.month
            cal = calendar.Calendar(firstweekday=0)
            
            for day_date in cal.itermonthdays4(year, month):
                d_date = datetime.date(day_date[0], day_date[1], day_date[2])
                is_current_month = d_date.month == month
                is_today = d_date == datetime.date.today()
                
                day_apts = [a for a in self.appointments_data if a['date'] == d_date or str(a['date']) == d_date.strftime('%Y-%m-%d')]
                
                with ModernCard(glass=is_current_month).classes(f'h-32 p-2 relative {"border-primary shadow-[0_0_15px_rgba(var(--primary-rgb),0.3)]" if is_today else "border-white/10"}'):
                    if not is_current_month:
                        ui.label(str(d_date.day)).classes('text-white/20 text-sm font-bold')
                    else:
                        ui.label(str(d_date.day)).classes(f'text-sm font-bold {"text-primary" if is_today else "text-white/60"}')
                        
                        with ui.column().classes('gap-1 mt-1 w-full overflow-hidden'):
                            for apt in day_apts[:2]:
                                status_color = 'primary' if apt['status'] == 'filled' else 'warning'
                                if apt['status'] == 'canceled': status_color = 'error'
                                
                                with ui.row().classes(f'w-full text-[10px] p-1 rounded bg-{status_color}/20 text-white truncate cursor-pointer hover:bg-{status_color}/40 transition-colors') \
                                    .on('click', lambda a=apt: self.edit_appointment(a)):
                                    ui.label(f"{apt['time'][:5]} {apt['customer'][:10]}").classes('truncate')
                            
                            if len(day_apts) > 2:
                                ui.label(f"+{len(day_apts)-2} more").classes('text-[9px] text-white/40 text-center w-full')

    def new_appointment(self):
        self.show_appointment_dialog()

    def edit_appointment(self, apt):
        self.show_appointment_dialog(apt)

    def show_appointment_dialog(self, apt=None):
        dialog = ui.dialog()
        with dialog, ModernCard(glass=True).classes('w-[500px] p-8'):
            ui.label('Appointment Details' if apt else 'New Appointment').classes('text-2xl font-black mb-8 text-white')
            
            # Form
            with ui.column().classes('w-full gap-4'):
                cust_data = []
                connection.contogetrows("SELECT id, customer_name FROM customers", cust_data)
                cust_opts = {r[0]: r[1] for r in cust_data}
                cust_sel = ui.select(cust_opts, label='Customer', value=apt['customer_id'] if apt else None).classes('w-full glass-input').props('dark rounded outlined')
                
                emp_data = []
                connection.contogetrows("SELECT id, first_name, last_name FROM employees", emp_data)
                emp_opts = {r[0]: f"{r[1]} {r[2]}" for r in emp_data}
                emp_sel = ui.select(emp_opts, label='Employee', value=apt['employee_id'] if apt else None).classes('w-full glass-input').props('dark rounded outlined')

                srv_data = []
                connection.contogetrows("SELECT id, service_name, duration_minutes FROM services", srv_data)
                srv_opts = {r[0]: r[1] for r in srv_data}
                srv_sel = ui.select(srv_opts, label='Service').classes('w-full glass-input').props('dark rounded outlined')

                with ui.row().classes('w-full gap-4'):
                    d_input = ui.input('Date').classes('flex-1 glass-input').props('dark rounded outlined type=date')
                    t_input = ui.input('Time').classes('w-32 glass-input').props('dark rounded outlined type=time')

                with ui.row().classes('w-full justify-end gap-3 mt-8'):
                    ModernButton('Cancel', on_click=dialog.close, variant='secondary')
                    ModernButton('Delete', icon='delete', on_click=lambda: self.delete_apt(apt['id'], dialog), variant='error') if apt else None
                    ModernButton('Save', icon='check', on_click=lambda: self.save_apt(apt['id'] if apt else None, dialog), variant='primary')
            
        dialog.open()

    def prev_month(self):
        m, y = (self.current_date.month - 1, self.current_date.year) if self.current_date.month > 1 else (12, self.current_date.year - 1)
        self.current_date = datetime.date(y, m, 1)
        self.refresh_data()

    def next_month(self):
        m, y = (self.current_date.month + 1, self.current_date.year) if self.current_date.month < 12 else (1, self.current_date.year + 1)
        self.current_date = datetime.date(y, m, 1)
        self.refresh_data()

    def go_today(self):
        self.current_date = datetime.date.today()
        self.refresh_data()

    def save_apt(self, apt_id, dialog):
        # Implementation of save logic...
        ui.notify('Save feature coming in next iteration', color='warning')
        dialog.close()

    def delete_apt(self, apt_id, dialog):
        # Implementation of delete logic...
        ui.notify('Delete feature coming in next iteration', color='warning')
        dialog.close()
