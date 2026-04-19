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

def appointments_content(standalone=False):
    """Content method for appointments that can be used in tabs"""
    if standalone:
        with ModernPageLayout("Appointment Calendar", standalone=standalone):
            AppointmentsUI(standalone=False)
    else:
        AppointmentsUI(standalone=False)

@ui.page('/appointments')
def appointments_page_route():
    appointments_content(standalone=True)

class AppointmentsUI:
    def __init__(self, standalone=True):
        self.standalone = standalone
        self.current_date = datetime.date.today()
        self.appointments_data = []
        self.calendar_grid = None
        self.month_label = None
        self.selected_date = None
        self.create_ui()
        self.refresh_data()

    def load_appointments(self):
        year, month = self.current_date.year, self.current_date.month
        start_date = datetime.date(year, month, 1) - datetime.timedelta(days=7)
        _, last_day = calendar.monthrange(year, month)
        end_date = datetime.date(year, month, last_day) + datetime.timedelta(days=7)

        # Updated query to match your table structure
        query = """
            SELECT a.id, a.customer_id, a.employee_id, a.service_id,
                   c.customer_name, e.first_name, e.last_name, ISNULL(s.service_name, 'N/A') as service_name, 
                   a.appointment_date, a.appointment_time, a.status, a.duration_minutes, a.notes
            FROM appointments a
            LEFT JOIN customers c ON a.customer_id = c.id
            LEFT JOIN employees e ON a.employee_id = e.id
            LEFT JOIN services s ON a.service_id = s.id
            WHERE a.appointment_date >= ? AND a.appointment_date <= ?
            ORDER BY a.appointment_date, a.appointment_time
        """
        data = []
        try:
            connection.contogetrows(query, data, (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
            print(f"Query executed successfully, got {len(data)} rows")
        except Exception as e:
            print(f"Error loading appointments: {e}")
            data = []
        
        self.appointments_data = []
        for r in data:
            date_str = r[8].strftime('%Y-%m-%d') if r[8] else ''
            time_str = r[9].strftime('%H:%M') if r[9] else '09:00'
            appointment = {
                'id': r[0], 
                'customer_id': r[1],
                'employee_id': r[2],
                'service_id': r[3],
                'customer': r[4], 
                'emp': f"{r[5]} {r[6]}", 
                'service': r[8],
                'date': date_str,
                'time': time_str, 
                'status': r[10], 
                'duration': r[11] or 30,
                'notes': r[12] or ''
            }
            self.appointments_data.append(appointment)
        
        print(f"Loaded {len(self.appointments_data)} appointments")

    def refresh_data(self):
        print("Refreshing data...")
        self.load_appointments()
        self.render_calendar()

    def create_ui(self):
        if self.standalone:
            layout_container = ModernPageLayout("Appointment Calendar", standalone=True)
            layout_container.__enter__()
        
        try:
            with ui.row().classes('w-full gap-6 items-start p-4'):
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
                        on_save=self.go_today,
                        on_refresh=self.refresh_data,
                        on_print=self.print_appointments_report,
                        on_chatgpt=lambda: ui.run_javascript('window.open("https://chatgpt.com", "_blank");'),
                        button_class='h-16',
                        classes=' '
                    ).style('position: static; width: 80px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); margin-top: 0;')
                    
                    with ui.column().classes('mt-4 gap-4 items-center'):
                        ModernButton('', icon='chevron_left', on_click=self.prev_month, variant='secondary').classes('w-14 h-14 rounded-2xl')
                        ModernButton('', icon='today', on_click=self.go_today, variant='primary').classes('w-14 h-14 rounded-2xl')
                        ModernButton('', icon='chevron_right', on_click=self.next_month, variant='secondary').classes('w-14 h-14 rounded-2xl')
        finally:
            if self.standalone:
                layout_container.__exit__(None, None, None)

    def render_calendar(self):
        if not self.month_label or not self.calendar_grid:
            return
            
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
                
                date_str = d_date.strftime('%Y-%m-%d')
                
                # Filter appointments for this day
                day_apts = []
                for a in self.appointments_data:
                    apt_date = a['date']
                    if isinstance(apt_date, datetime.date):
                        apt_date_str = apt_date.strftime('%Y-%m-%d')
                    else:
                        apt_date_str = str(apt_date)
                    
                    if apt_date_str == date_str:
                        day_apts.append(a)
                
                with ModernCard(glass=is_current_month).classes(f'h-32 p-2 relative cursor-pointer {"border-primary shadow-[0_0_15px_rgba(var(--primary-rgb),0.3)]" if is_today else "border-white/10"}') \
                    .on('dblclick', lambda d=d_date: self.open_new_appointment_dialog(d)):
                    
                    if not is_current_month:
                        ui.label(str(d_date.day)).classes('text-white/20 text-sm font-bold')
                    else:
                        ui.label(str(d_date.day)).classes(f'text-sm font-bold {"text-primary" if is_today else "text-white/60"}')
                        
                        with ui.column().classes('gap-1 mt-1 w-full overflow-hidden'):
                            for apt in day_apts[:2]:
                                status_color = 'primary' 
                                if apt['status'] == 'canceled':
                                    status_color = 'error'
                                elif apt['status'] == 'completed':
                                    status_color = 'success'
                                elif apt['status'] in ['scheduled', 'confirmed']:
                                    status_color = 'primary'
                                else:
                                    status_color = 'warning'
                                
                                time_str = apt['time'][:5] if apt['time'] else '00:00'
                                customer_name = apt['customer'][:15] if apt['customer'] else 'Unknown'
                                
                                with ui.row().classes(f'w-full text-[10px] p-1 rounded bg-{status_color}/20 text-white truncate') \
                                    .on('click.stop', lambda a=apt: self.edit_appointment(a)):
                                    ui.label(f"{time_str} {customer_name}").classes('truncate')
                            
                            if len(day_apts) > 2:
                                ui.label(f"+{len(day_apts)-2} more").classes('text-[9px] text-white/40 text-center w-full')

    def _validate_date_for_dialog(self, date_param):
        """Validate date for opening dialog - block past dates"""
        if isinstance(date_param, datetime.date):
            date_str = date_param.strftime('%Y-%m-%d')
        else:
            date_str = str(date_param)
        
        try:
            selected_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            if selected_date < datetime.date.today():
                ui.notify("you can't create or edit before today's date", color='warning')
                return False
        except ValueError:
            ui.notify('Invalid date format', color='warning')
            return False
        return True

    def open_new_appointment_dialog(self, date):
        """Open dialog for creating a new appointment on a specific date"""
        print(f"Double-clicked on date: {date}")
        if not self._validate_date_for_dialog(date):
            return
        self.show_appointment_dialog(date=date)

    def new_appointment(self):
        """Create new appointment with selected date or today's date"""
        date = self.selected_date if self.selected_date else datetime.date.today()
        if not self._validate_date_for_dialog(date):
            return
        self.show_appointment_dialog(date=date)

    def edit_appointment(self, apt):
        if not self._validate_date_for_dialog(apt['date']):
            return
        self.show_appointment_dialog(apt=apt)

    def show_appointment_dialog(self, apt=None, date=None):
        # Create dialog
        dialog = ui.dialog()
        
        with dialog, ModernCard(glass=True).classes('w-[550px] p-8'):
            title = 'Edit Appointment' if apt else 'New Appointment'
            ui.label(title).classes('text-2xl font-black mb-8 text-white')
            
            with ui.column().classes('w-full gap-4'):
                # Customers
                cust_data = []
                connection.contogetrows("SELECT id, customer_name FROM customers ORDER BY customer_name", cust_data)
                cust_opts = {r[0]: r[1] for r in cust_data}
                cust_select = ui.select(cust_opts, label='Customer *', value=apt.get('customer_id') if apt else None)
                cust_select.classes('w-full').props('dark outlined')
                
                # Employees
                emp_data = []
                connection.contogetrows("SELECT id, first_name, last_name FROM employees ORDER BY first_name", emp_data)
                emp_opts = {r[0]: f"{r[1]} {r[2]}" for r in emp_data}
                emp_select = ui.select(emp_opts, label='Employee *', value=apt.get('employee_id') if apt else None)
                emp_select.classes('w-full').props('dark outlined')
                
                # Services
                srv_data = []
                connection.contogetrows("SELECT id, service_name, duration_minutes FROM services ORDER BY service_name", srv_data)
                srv_opts = {r[0]: f"{r[1]} ({r[2]} min)" for r in srv_data}
                srv_select = ui.select(srv_opts, label='Service *', value=apt.get('service_id') if apt else None)
                srv_select.classes('w-full').props('dark outlined')
                
                # Date and Time
                with ui.row().classes('w-full gap-4'):
                    date_input = ui.input('Date *').classes('flex-1').props('dark outlined type=date')
                    time_input = ui.input('Time *').classes('w-32').props('dark outlined type=time')
                
                    if apt:
                        date_input.value = apt['date']
                        time_input.value = apt['time']
                    elif date:
                        date_input.value = date.strftime('%Y-%m-%d')
                        time_input.value = '09:00'
                    else:
                        date_input.value = datetime.date.today().strftime('%Y-%m-%d')
                        time_input.value = '09:00'
                
                # Status
                status_opts = {'scheduled': 'Scheduled', 'confirmed': 'Confirmed', 'completed': 'Completed', 'canceled': 'Canceled'}
                status_select = ui.select(status_opts, label='Status', value=apt.get('status') if apt else 'scheduled')
                status_select.classes('w-full').props('dark outlined')
                
                # Notes field (optional)
                notes_input = ui.textarea('Notes', value=apt.get('notes', '') if apt else '')
                notes_input.classes('w-full').props('dark outlined rows=2')
                
                with ui.row().classes('w-full justify-end gap-3 mt-8'):
                    ui.button('Cancel', on_click=dialog.close).props('flat').classes('text-white')
                    
                    if apt:
                        ui.button('Delete', icon='delete', on_click=lambda: self.delete_appointment(apt['id'], dialog)) \
                            .props('flat color=negative').classes('text-white')
                    
                    ui.button('Save', icon='save', on_click=lambda: self.save_appointment(
                        apt['id'] if apt else None,
                        dialog,
                        cust_select.value,
                        emp_select.value,
                        srv_select.value,
                        date_input.value,
                        time_input.value,
                        status_select.value,
                        notes_input.value
                    )).props('flat color=primary').classes('text-white')
        
        dialog.open()

    def save_appointment(self, apt_id, dialog, customer_id, employee_id, service_id, date, time, status, notes):
        """Save appointment to database"""
        # Validation
        if not all([customer_id, employee_id, service_id, date, time]):
            ui.notify('Please fill all required fields', color='warning')
            return
        
        try:
            selected_date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
            if selected_date < datetime.date.today():
                ui.notify('Cannot edit or create appointment for day that past', color='warning')
                return
        except ValueError:
            ui.notify('Invalid date format', color='warning')
            return
        
        try:
            print(f"\n=== SAVING APPOINTMENT ===")
            print(f"Data to save: customer_id={customer_id}, employee_id={employee_id}, service_id={service_id}")
            print(f"Date: {date}, Time: {time}, Status: {status}")
            print(f"Notes: {notes}")
            
            if apt_id:
                # Update existing appointment - using your table structure
                query = """
                    UPDATE appointments 
                    SET customer_id = ?, employee_id = ?, service_id = ?, 
                        appointment_date = ?, appointment_time = ?, status = ?, notes = ?,
                        updated_at = GETDATE()
                    WHERE id = ?
                """
                params = (customer_id, employee_id, service_id, date, time, status, notes, apt_id)
                print(f"UPDATE Query: {query}")
                print(f"Params: {params}")
                
                connection.insertingtodatabase(query, params)
                ui.notify('Appointment updated successfully!', color='positive')
                print("UPDATE successful")
            else:
                # Insert new appointment - matching your table structure
                query = """
                    INSERT INTO appointments (
                        customer_id, employee_id, service_id, 
                        appointment_date, appointment_time, status, notes,
                        created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, GETDATE(), GETDATE())
                """
                params = (customer_id, employee_id, service_id, date, time, status, notes)
                print(f"INSERT Query: {query}")
                print(f"Params: {params}")
                
                connection.insertingtodatabase(query, params)
                ui.notify('Appointment created successfully!', color='positive')
                print("INSERT successful")
            
            print("Appointment saved successfully!")
            print("========================\n")
            
            dialog.close()
            
            # Refresh data to show new appointment
            self.refresh_data()
            
            # Force UI update
            ui.update()
            
        except Exception as e:
            error_msg = f'Error saving appointment: {str(e)}'
            ui.notify(error_msg, color='negative')
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()

    def delete_appointment(self, apt_id, dialog):
        """Delete appointment from database"""
        try:
            print(f"\n=== DELETING APPOINTMENT {apt_id} ===")
            query = "DELETE FROM appointments WHERE id = ?"
            params = (apt_id,)
            
            connection.insertingtodatabase(query, params)
            ui.notify('Appointment deleted successfully!', color='positive')
            print("DELETE successful")
            print("========================\n")
            dialog.close()
            self.refresh_data()
            
        except Exception as e:
            ui.notify(f'Error deleting appointment: {str(e)}', color='negative')
            print(f"ERROR: {e}")

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

    def print_appointments_report(self):
        '''Print appointments report with date filter dialog'''
        dialog = ui.dialog()
        with dialog, ModernCard(glass=True).classes('w-96 p-8'):
            ui.label('Appointments Report').classes('text-2xl font-black mb-6 text-white')
            
            today = datetime.date.today()
            from_month_start = today.replace(day=1)
            from_date = ui.input('From Date', value=from_month_start.strftime('%Y-%m-%d')).props('type=date dark outlined')
            to_date = ui.input('To Date', value=today.strftime('%Y-%m-%d')).props('type=date dark outlined')
            
            with ui.row().classes('justify-end gap-3 mt-8'):
                ui.button('Cancel', on_click=dialog.close).props('flat').classes('text-white')
            with ui.row().classes('justify-end gap-3 mt-8'):
                ui.button('Preview', on_click=lambda: self._preview_appointments_report(
                    from_date.value, to_date.value
                )).props('flat').classes('text-white')
                ui.button('Download PDF', on_click=lambda: self._generate_appointments_pdf(
                    from_date.value, to_date.value, dialog
                )).props('color=primary flat').classes('text-white')
        
        dialog.open()

    def _preview_appointments_report(self, from_date_str, to_date_str):
        try:
            # Validate dates
            from_date = datetime.datetime.strptime(from_date_str, '%Y-%m-%d').date()
            to_date = datetime.datetime.strptime(to_date_str, '%Y-%m-%d').date()
            
            # Get appointments data
            data = []
            query = """
                SELECT 
                    a.appointment_date, a.appointment_time, 
                    ISNULL(c.customer_name, 'N/A') as customer_name, 
                    ISNULL(e.first_name + ' ' + ISNULL(e.last_name, ''), 'N/A') as employee_name, 
                    ISNULL(s.service_name, 'N/A') as service_name, ISNULL(a.status, 'N/A') as status, ISNULL(a.duration_minutes, 0) as duration_minutes
                FROM appointments a
                LEFT JOIN customers c ON a.customer_id = c.id
                LEFT JOIN employees e ON a.employee_id = e.id
                LEFT JOIN services s ON a.service_id = s.id
                WHERE a.appointment_date BETWEEN ? AND ?
                ORDER BY a.appointment_date, a.appointment_time
            """
            connection.contogetrows(query, data, (from_date_str, to_date_str))
            print(f"[DEBUG] Preview report: {len(data)} rows fetched for {from_date_str} to {to_date_str}")
            
            # Process data for table
            report_data = []
            total_duration = 0
            for r in data:
                row = {
                    'date': r[0].strftime('%Y-%m-%d') if r[0] else '',
                    'time': r[1].strftime('%H:%M') if r[1] else '',
                    'customer': r[2] or 'N/A',
                    'employee': r[3] or 'N/A',
                    'service': r[4] or 'N/A',
                    'status': r[5] or 'N/A',
                    'duration': f"{r[6] or 0} min"
                }
                report_data.append(row)
                total_duration += r[6] or 0
            
            # Preview dialog
            preview_dialog = ui.dialog()
            with preview_dialog, ModernCard(glass=True).classes('w-[90vw] max-w-7xl h-[80vh] p-6 overflow-auto'):
                ui.label(f'Appointments Preview - {from_date_str} to {to_date_str}').classes('text-2xl font-black mb-6 text-white')
                
                ui.aggrid({
                    'columnDefs': [
                        {'field': 'date', 'headerName': 'Date'},
                        {'field': 'time', 'headerName': 'Time'},
                        {'field': 'customer', 'headerName': 'Customer'},
                        {'field': 'employee', 'headerName': 'Employee'},
                        {'field': 'service', 'headerName': 'Service'},
                        {'field': 'status', 'headerName': 'Status'},
                        {'field': 'duration', 'headerName': 'Duration'},
                    ],
                    'rowData': report_data,
                    'defaultColDef': {'flex': 1, 'minWidth': 120},
                    'pagination': True,
                    'paginationPageSize': 20,
                }).classes('w-full h-[60vh] my-4')
                
                with ui.row().classes('justify-center gap-4 mt-4'):
                    ui.label(f'Total: {len(report_data)} appointments, {total_duration} minutes').classes('text-lg font-bold text-white')
                
                with ui.row().classes('justify-end gap-3 mt-6'):
                    ui.button('Close', on_click=preview_dialog.close).props('flat').classes('text-white')
                    ui.button('Download PDF', on_click=lambda: (self._generate_appointments_pdf(from_date_str, to_date_str, None), preview_dialog.close())).props('color=primary flat').classes('text-white')
            
            preview_dialog.open()
            
        except Exception as e:
            ui.notify(f'Preview error: {str(e)}', color='negative')

    def _generate_appointments_pdf(self, from_date_str, to_date_str, dialog=None):
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors
            from reportlab.lib.units import inch
            import io
            
            # Validate dates
            from_date = datetime.datetime.strptime(from_date_str, '%Y-%m-%d').date()
            to_date = datetime.datetime.strptime(to_date_str, '%Y-%m-%d').date()
            
            # Get appointments data
            data = []
            query = """
                SELECT 
                    a.appointment_date, a.appointment_time, 
                    ISNULL(c.customer_name, 'N/A') as customer_name, 
                    ISNULL(e.first_name + ' ' + ISNULL(e.last_name, ''), 'N/A') as employee_name, 
                    ISNULL(s.service_name, 'N/A') as service_name, ISNULL(a.status, 'N/A') as status, ISNULL(a.duration_minutes, 0) as duration_minutes
                FROM appointments a
                LEFT JOIN customers c ON a.customer_id = c.id
                LEFT JOIN employees e ON a.employee_id = e.id
                LEFT JOIN services s ON a.service_id = s.id
                WHERE a.appointment_date BETWEEN ? AND ?
                ORDER BY a.appointment_date, a.appointment_time
            """
            connection.contogetrows(query, data, (from_date_str, to_date_str))
            print(f"[DEBUG] PDF report: {len(data)} rows fetched for {from_date_str} to {to_date_str}")
            
            # Process data
            report_data = [['Date', 'Time', 'Customer', 'Employee', 'Service', 'Status', 'Duration']]
            total_duration = 0
            for r in data:
                row = [
                    r[0].strftime('%Y-%m-%d') if r[0] else '',
                    r[1].strftime('%H:%M') if r[1] else '',
                    r[2] or 'N/A',
                    r[3] or 'N/A',
                    r[4] or 'N/A',
                    r[5] or 'N/A',
                    f"{r[6] or 0} min"
                ]
                report_data.append(row)
                total_duration += r[6] or 0
            
            # Create PDF
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            styles = getSampleStyleSheet()
            
            story = []
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=30,
                alignment=1,  # center
                textColor=colors.darkblue
            )
            
            story.append(Paragraph('Appointments Report', title_style))
            story.append(Paragraph(f'From: {from_date_str}  To: {to_date_str}', styles['Normal']))
            story.append(Spacer(1, 12))
            
            table = Table(report_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 10)
            ]))
            
            story.append(table)
            
            # Summary
            summary_style = ParagraphStyle(
                'Summary',
                parent=styles['Normal'],
                fontSize=12,
                spaceBefore=20,
                leftIndent=36
            )
            story.append(Spacer(1, 12))
            story.append(Paragraph(f'Total Appointments: {len(data)}', summary_style))
            story.append(Paragraph(f'Total Duration: {total_duration} minutes', summary_style))
            story.append(Paragraph(f'Generated: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}', summary_style))
            
            doc.build(story)
            buffer.seek(0)
            
            filename = f"Reports/appointments_report_{from_date_str.replace('-','')}_to_{to_date_str.replace('-','')}.pdf"
            ui.download(filename, buffer.getvalue())
            
            ui.notify('Appointments report downloaded!', color='positive')
            if dialog:
                dialog.close()
            
        except Exception as e:
            ui.notify(f'Error generating PDF: {str(e)}', color='negative')
            print(f'Report error: {e}')
            import traceback
            traceback.print_exc()
