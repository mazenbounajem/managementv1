from nicegui import ui
from connection import connection
from uiaggridtheme import uiAggridTheme
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage
import datetime
import calendar

def appointments_content():
    uiAggridTheme.addingtheme()

    # Calendar state
    current_date = datetime.date.today()
    appointments_data = []
    calendar_container = None
    appointment_dialog = None
    time_slots_dialog = None
    date_selection_container = None
    date_selection_visible = False

    def load_appointments(date_range=None):
        """Load appointments from database"""
        nonlocal appointments_data
        query = """
            SELECT
                a.id,
                a.customer_id,
                c.customer_name,
                a.employee_id,
                CONCAT(e.first_name, ' ', e.last_name) as employee_name,
                s.service_name as service_type,
                a.service_id,
                a.appointment_date,
                a.appointment_time,
                a.status,
                a.notes,
                a.created_at,
                s.duration_minutes,
                s.price
            FROM appointments a
            LEFT JOIN customers c ON a.customer_id = c.id
            LEFT JOIN employees e ON a.employee_id = e.id
            LEFT JOIN services s ON a.service_id = s.id
            WHERE a.appointment_date >= ? AND a.appointment_date <= ?
        """

        # If no date range specified, load for current month +/- 2 months for broader coverage
        if date_range is None:
            # Load appointments for current month +/- 2 months to cover navigation
            year, month = current_date.year, current_date.month

            # Calculate start date (2 months before current month)
            start_year = year
            start_month = month - 2
            if start_month <= 0:
                start_year -= 1
                start_month += 12
            start_date = datetime.date(start_year, start_month, 1)

            # Calculate end date (2 months after current month)
            end_year = year
            end_month = month + 2
            if end_month > 12:
                end_year += 1
                end_month -= 12
            _, last_day = calendar.monthrange(end_year, end_month)
            end_date = datetime.date(end_year, end_month, last_day)
        else:
            start_date, end_date = date_range

        print(f"DEBUG: Loading appointments from {start_date} to {end_date}")

        data = []
        connection.contogetrows(query, data, (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))

        print(f"DEBUG: Found {len(data)} appointments in database")

        appointments_data = []
        for row in data:
            apt_dict = {
                'id': row[0],
                'customer_id': row[1],
                'customer_name': row[2] or 'N/A',
                'employee_id': row[3],
                'employee_name': row[4] or 'N/A',
                'service_type': row[5] or 'N/A',
                'service_id': row[6],
                'appointment_date': row[7],
                'appointment_time': row[8],
                'status': row[9],
                'notes': row[10],
                'created_at': row[11],
                'duration_minutes': row[12] or 30,
                'price': row[13] or 0
            }
            appointments_data.append(apt_dict)
            print(f"DEBUG: Loaded appointment - Date: {apt_dict['appointment_date']}, Time: {apt_dict['appointment_time']}, Duration: {apt_dict['duration_minutes']}")

        print(f"DEBUG: Total appointments loaded: {len(appointments_data)}")

    def get_occupied_slots(date_str):
        """Get dictionary of occupied time slots mapping to list of customer names for a given date"""
        print(f"DEBUG: get_occupied_slots called for date: {date_str}")
        print(f"DEBUG: Total appointments in memory: {len(appointments_data)}")

        occupied = {}
        # Convert date_str to date object for consistent comparison
        try:
            date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except Exception:
            date_obj = date_str  # fallback if already date object

        # Only consider active appointments (not canceled)
        day_appointments = [apt for apt in appointments_data if
                           (apt['appointment_date'] == date_obj or str(apt['appointment_date']) == date_str) and
                           apt['status'] != 'canceled']
        print(f"DEBUG: Found {len(day_appointments)} active appointments for date {date_str}")

        for apt in day_appointments:
            print(f"DEBUG: Processing appointment - Time: {apt['appointment_time']} (type: {type(apt['appointment_time'])}), Duration: {apt['duration_minutes']}")

            # Handle both string and time object formats
            if isinstance(apt['appointment_time'], str):
                start_time = datetime.datetime.strptime(apt['appointment_time'], "%H:%M:%S").time()
            else:
                start_time = apt['appointment_time']

            duration = apt['duration_minutes'] or 30
            print(f"DEBUG: Calculated start_time: {start_time}, duration: {duration}")

            # Generate slots from start to start + duration in 30-min increments
            # Use the actual date from the appointment, not today's date
            appointment_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            current = datetime.datetime.combine(appointment_date, start_time)
            end = current + datetime.timedelta(minutes=duration)
            print(f"DEBUG: Time range: {current} to {end}")

            while current < end:
                slot_str = current.strftime("%H:%M")
                if slot_str not in occupied:
                    occupied[slot_str] = []
                # Only add the customer name if the slot is not already occupied by the same customer
                if apt['customer_name'] not in occupied[slot_str]:
                    occupied[slot_str].append(apt['customer_name'])
                print(f"DEBUG: Added occupied slot: {slot_str} with customer {apt['customer_name']}")
                current += datetime.timedelta(minutes=30)

        print(f"DEBUG: Final occupied slots with customers: {occupied}")
        return occupied
    def create_appointment_dialog(selected_date=None, selected_time=None):
        """Create appointment dialog"""
        nonlocal appointment_dialog, time_slots_dialog

        # Close time slots dialog if it's open
        if time_slots_dialog:
            time_slots_dialog.close()
            time_slots_dialog = None

        # Get occupied slots for the selected date to disable reserved times
        occupied_slots = get_occupied_slots(selected_date or current_date.strftime('%Y-%m-%d'))

        appointment_dialog = ui.dialog()
        with appointment_dialog:
            with ui.card().classes('w-full max-w-lg mx-auto'):
                ui.label('New Appointment').classes('text-xl font-bold mb-6 text-center')

                # Center the form content
                with ui.column().classes('w-full items-center gap-4'):
                    # Load data first
                    services_data = []
                    connection.contogetrows("SELECT id, service_name, description, duration_minutes FROM services WHERE is_active = 1", services_data)
                    service_options = {row[0]: f"{row[1]} ({row[2] or 'No description'})" for row in services_data}

                    customers_data = []
                    connection.contogetrows("SELECT id, customer_name FROM customers", customers_data)
                    customer_options = {row[0]: row[1] for row in customers_data}

                    employees_data = []
                    connection.contogetrows("SELECT id, CONCAT(first_name, ' ', last_name) as name FROM employees", employees_data)
                    employee_options = {row[0]: row[1] for row in employees_data}

                    # Form fields with centered layout
                    service_select = ui.select(service_options, label='Service').classes('w-full max-w-sm')
                    customer_select = ui.select(customer_options, label='Customer').classes('w-full max-w-sm')
                    employee_select = ui.select(employee_options, label='Employee').classes('w-full max-w-sm')
                    date_input = ui.input('Date', value=selected_date or current_date.strftime('%Y-%m-%d')).classes('w-full max-w-sm')
                    time_input = ui.select(
                        [t for t in [f"{h:02d}:{m:02d}" for h in range(8, 20) for m in (0, 30)] if t not in occupied_slots],
                        label='Time',
                        value=selected_time or '09:00',
                    )

                    duration_input = ui.select(['30', '60', '90', '120'], value='30', label='Duration (minutes)').classes('w-full max-w-sm')
                    notes_input = ui.textarea('Notes').classes('w-full max-w-sm')

                    # Auto-fill duration when service is selected
                    def on_service_change():
                        if service_select.value:
                            selected_service = next((s for s in services_data if s[0] == service_select.value), None)
                            if selected_service:
                                duration_input.value = str(selected_service[3])

                    service_select.on('change', on_service_change)

                    # Buttons centered at bottom
                    with ui.row().classes('w-full justify-center mt-6 gap-4'):
                        ui.button('Cancel', on_click=appointment_dialog.close).classes('px-6 py-2')
                        ui.button('Save', color='primary', on_click=lambda: save_appointment(
                            service_select.value,
                            customer_select.value,
                            employee_select.value,
                            date_input.value,
                            time_input.value,
                            duration_input.value,
                            notes_input.value
                        )).classes('px-6 py-2')

        appointment_dialog.open()

    def show_date_selection_dialog():
        """Show date selection dialog for new appointment"""
        date_dialog = ui.dialog()
        with date_dialog:
            with ui.card().classes('w-full max-w-md mx-auto'):
                ui.label('Select Date for New Appointment').classes('text-xl font-bold mb-6 text-center')

                # Center the form content
                with ui.column().classes('w-full items-center gap-4'):
                    with ui.input('Select Date', value=current_date.strftime('%Y-%m-%d')) as date_input:
                        with ui.menu().props('no-parent-event') as menu:
                            with ui.date().bind_value(date_input):
                                with ui.row().classes('justify-end'):
                                    ui.button('Close', on_click=menu.close).props('flat')
                        with date_input.add_slot('append'):
                            ui.icon('edit_calendar').on('click', menu.open).classes('cursor-pointer')

                    # Buttons centered at bottom
                    with ui.row().classes('w-full justify-center mt-6 gap-4'):
                        ui.button('Cancel', on_click=date_dialog.close).classes('px-6 py-2')
                        ui.button('Continue', color='primary', on_click=lambda d=date_input, dlg=date_dialog: (ui.notify(f"Selected date: {d.value}"), proceed_to_time_slots(d.value, dlg))).classes('px-6 py-2')

        date_dialog.open()




    def proceed_to_time_slots(selected_date, date_dialog):
        """Proceed to time slots selection for the selected date"""
        print(f"DEBUG: proceed_to_time_slots called with date: {selected_date}")
        ui.notify(f"Closing date dialog for {selected_date}")
        date_dialog.close()

        # Parse the date
        try:
            parsed_date = datetime.datetime.strptime(selected_date, "%Y-%m-%d").date()
            print(f"DEBUG: Parsed date: {parsed_date}")
        except Exception as e:
            print(f"DEBUG: Error parsing date: {e}")
            ui.notify(f"Error parsing date: {e}", color='red')
            return

        # Open time slots dialog immediately for better user experience
        ui.notify(f"Opening time slots dialog for {selected_date}")

        # Call show_time_slots_dialog instead of show_day_time_slots to open the same dialog as clicking a day
        try:
            show_time_slots_dialog(selected_date)
            print(f"DEBUG: show_time_slots_dialog called successfully")
        except Exception as e:
            print(f"DEBUG: Error in show_time_slots_dialog: {e}")
            ui.notify(f"Error opening time slots: {e}", color='red')


    def show_time_slots_dialog(selected_date=None):
        """Show time slots dialog for the selected date with 30-minute intervals"""
        ui.notify(f"show_time_slots_dialog called with date: {selected_date}")
        nonlocal time_slots_dialog

        def on_available_click(ts, ds):
            create_appointment_dialog(ds, ts)

        def on_reserved_click(ts, ds):
            edit_appointment_from_slot(ds, ts)

        # Use current date if no date is provided
        if selected_date is None:
            selected_date = current_date.strftime('%Y-%m-%d')

        # Convert to date object for display
        try:
            display_date = datetime.datetime.strptime(selected_date, "%Y-%m-%d").date()
        except:
            display_date = current_date

        time_slots_dialog = ui.dialog()
        with time_slots_dialog:
            with ui.card().classes('w-full'):
                ui.label(f'Select Time Slot for {display_date.strftime("%B %d, %Y")}').classes('text-xl font-bold mb-4')

                # Date selector (pre-filled with selected date)
                date_selector = ui.input('Select Date', value=selected_date).classes('mb-4')

                # Time slots grid (8 AM to 8 PM with 30-minute intervals)
                time_slots = []
                for hour in range(8, 20):  # 8 AM to 8 PM
                    for minute in [0, 30]:
                        time_str = f"{hour:02d}:{minute:02d}"
                        time_slots.append(time_str)

                # Get occupied slots for the selected date
                occupied_slots = get_occupied_slots(selected_date)

                # Display time slots in a grid
                with ui.grid(columns=6).classes('w-full gap-2'):
                    for time_slot in time_slots:
                        # Determine if the slot is reserved
                        is_reserved = time_slot in occupied_slots

                        # Determine if the slot is in the past
                        slot_datetime = datetime.datetime.combine(display_date, datetime.datetime.strptime(time_slot, "%H:%M").time())
                        is_past = slot_datetime < datetime.datetime.now()

                        # Check if this slot has canceled appointments
                        has_canceled = False
                        canceled_customer_names = []
                        if is_reserved:
                            # Check if any of the appointments in this slot are canceled
                            date_obj = display_date
                            day_appointments = [apt for apt in appointments_data if
                                               (apt['appointment_date'] == date_obj or str(apt['appointment_date']) == selected_date)]

                            for apt in day_appointments:
                                if isinstance(apt['appointment_time'], str):
                                    start_time = datetime.datetime.strptime(apt['appointment_time'], "%H:%M:%S").time()
                                else:
                                    start_time = apt['appointment_time']

                                duration = apt['duration_minutes'] or 30
                                appointment_date = display_date
                                current = datetime.datetime.combine(appointment_date, start_time)
                                end = current + datetime.timedelta(minutes=duration)
                                slot_time = datetime.datetime.strptime(time_slot, "%H:%M").time()
                                slot_datetime_check = datetime.datetime.combine(appointment_date, slot_time)

                                if current <= slot_datetime_check < end:
                                    if apt['status'] == 'canceled':
                                        has_canceled = True
                                        if apt['customer_name'] not in canceled_customer_names:
                                            canceled_customer_names.append(apt['customer_name'])

                        if has_canceled:
                            # Show canceled appointment slot in orange with strikethrough
                            customer_names = ', '.join(canceled_customer_names)
                            ui.button(f"❌ {time_slot} - {customer_names}",
                                    on_click=lambda ts=time_slot: edit_appointment_from_slot(selected_date, ts)
                                   ).classes('w-full py-2 bg-orange-400 hover:bg-orange-500 text-sm text-white line-through').props('dense')
                        elif is_reserved:
                            # Show filled appointment slot in red with customer names
                            customer_names = ', '.join(occupied_slots[time_slot])
                            ui.button(f"{time_slot} - {customer_names}",
                                    on_click=lambda ts=time_slot: edit_appointment_from_slot(selected_date, ts)
                                   ).classes('w-full py-2 bg-red-400 hover:bg-red-500 text-sm text-white').props('dense')
                        elif is_past:
                            # Past time slots disabled and grayed out
                            ui.button(f"{time_slot} - Unavailable"
                                   ).classes('w-full py-2 bg-gray-300 text-sm text-gray-600').props('dense flat disabled')
                        else:
                            # Show available time slot
                            def create_apt_handler(ts=time_slot):
                                create_appointment_dialog(selected_date, ts)
                            ui.button(f"{time_slot} - Available",
                                    on_click=create_apt_handler
                                   ).classes('w-full py-2 bg-green-100 hover:bg-green-200 text-sm').props('dense flat')

                # Close button
                with ui.row().classes('w-full justify-end mt-4'):
                    ui.button('Close', on_click=time_slots_dialog.close).classes('px-4 py-2')


    def save_appointment(service_id, customer_id, employee_id, date, time, duration, notes):
        """Save appointment to database"""
        if not service_id or not customer_id or not employee_id or not date or not time:
            ui.notify('Please fill in all required fields', color='red')
            return

        try:
            sql = '''
                INSERT INTO appointments (customer_id, employee_id, service_id, appointment_date, appointment_time, status, notes, created_at, updated_at, duration_minutes)
                VALUES (?, ?, ?, ?, ?, 'filled', ?, GETDATE(), GETDATE(), ?)
            '''
            values = (customer_id, employee_id, service_id, date, time, notes, int(duration))

            connection.insertingtodatabase(sql, values)
            ui.notify('Appointment created successfully', color='green')
            appointment_dialog.close()
            load_appointments()
            render_calendar()
            # Reopen time slots dialog to show updated availability
            # Add a small delay to ensure DB commit before reloading slots
            import time
            time.sleep(0.5)
            show_time_slots_dialog()
        except Exception as e:
            ui.notify(f'Error creating appointment: {str(e)}', color='red')

    def update_appointment(appointment_id, service_id, customer_id, employee_id, date, time, duration, notes):
        """Update appointment in database"""
        if not service_id or not customer_id or not employee_id or not date or not time:
            ui.notify('Please fill in all required fields', color='red')
            return

        try:
            sql = '''
                UPDATE appointments
                SET customer_id = ?, employee_id = ?, service_id = ?, appointment_date = ?, appointment_time = ?, notes = ?, updated_at = GETDATE(), duration_minutes = ?
                WHERE id = ?
            '''
            values = (customer_id, employee_id, service_id, date, time, notes, int(duration), appointment_id)

            connection.insertingtodatabase(sql, values)
            ui.notify('Appointment updated successfully', color='green')
            appointment_dialog.close()
            load_appointments()
            render_calendar()
            # Reopen time slots dialog to show updated availability
            show_time_slots_dialog()
        except Exception as e:
            ui.notify(f'Error updating appointment: {str(e)}', color='red')

    def cancel_appointment(appointment_id):
        """Cancel appointment by updating status to 'canceled'"""
        try:
            sql = '''
                UPDATE appointments
                SET status = 'canceled', updated_at = GETDATE()
                WHERE id = ?
            '''
            connection.insertingtodatabase(sql, (appointment_id,))
            ui.notify('Appointment canceled successfully', color='orange')
            appointment_dialog.close()
            load_appointments()
            render_calendar()
            # Reopen time slots dialog to show updated availability
            show_time_slots_dialog()
        except Exception as e:
            ui.notify(f'Error canceling appointment: {str(e)}', color='red')

    def delete_appointment(appointment_id):
        """Delete appointment from database"""
        try:
            sql = 'DELETE FROM appointments WHERE id = ?'
            connection.insertingtodatabase(sql, (appointment_id,))
            ui.notify('Appointment deleted successfully', color='green')
            appointment_dialog.close()
            load_appointments()
            render_calendar()
            # Reopen time slots dialog to show updated availability
            show_time_slots_dialog()
        except Exception as e:
            ui.notify(f'Error deleting appointment: {str(e)}', color='red')

    def render_calendar():
        """Render the calendar view with all days and expandable time slots"""
        nonlocal calendar_container

        if calendar_container:
            calendar_container.clear()

        with calendar_container:
            # Calendar header
            with ui.row().classes('w-full justify-between items-center mb-4'):
                ui.button('<', on_click=previous_month).classes('px-3 py-1')
                ui.label(f'{calendar.month_name[current_date.month]} {current_date.year}').classes('text-xl font-bold')
                ui.button('>', on_click=next_month).classes('px-3 py-1')
                ui.button('Today', on_click=go_to_today).classes('px-3 py-1 ml-4')

            # Get all days in the current month
            year, month = current_date.year, current_date.month
            _, last_day = calendar.monthrange(year, month)

            # Create a grid of all days
            days_in_month = []
            for day in range(1, last_day + 1):
                days_in_month.append(day)

            # Display days in rows of 7
            for i in range(0, len(days_in_month), 7):
                week_days = days_in_month[i:i+7]
                with ui.row().classes('w-full mb-2'):
                    for day in week_days:
                        day_date = datetime.date(year, month, day)
                        # Convert day_date to date object for consistent comparison
                        day_appointments = [apt for apt in appointments_data if apt['appointment_date'] == day_date or str(apt['appointment_date']) == day_date.strftime('%Y-%m-%d')]

                        # Determine if the day is in the past
                        is_past = day_date < datetime.date.today()

                        # Day container with conditional background color
                        day_classes = 'w-1/7 border border-gray-300 p-2 min-h-24 '
                        if is_past:
                            day_classes += 'bg-red-100 text-gray-500'
                        else:
                            day_classes += 'bg-white hover:bg-gray-50'

                        with ui.column().classes(day_classes):
                            # Day header with date
                            with ui.row().classes('w-full justify-between items-center mb-1'):
                                ui.label(str(day)).classes('text-sm font-semibold')
                                if day_appointments:
                                    ui.badge(str(len(day_appointments)), color='blue').classes('text-xs')

                            # Show appointments for this day (limited preview)
                            if day_appointments:
                                for apt in day_appointments[:2]:  # Show max 2 appointments
                                    # Different styling for canceled appointments
                                    if apt['status'] == 'canceled':
                                        ui.button(f"❌ {apt['appointment_time']} - {apt['service_type'][:8]}...",
                                                on_click=lambda apt=apt: edit_appointment(apt)
                                               ).classes('w-full text-xs py-1 mb-1 bg-orange-100 hover:bg-orange-200 line-through text-gray-600').props('dense')
                                    else:
                                        ui.button(f"{apt['appointment_time']} - {apt['service_type'][:8]}...",
                                                on_click=lambda apt=apt: edit_appointment(apt)
                                               ).classes('w-full text-xs py-1 mb-1 bg-blue-100 hover:bg-blue-200').props('dense')

                                if len(day_appointments) > 2:
                                    ui.label(f"+{len(day_appointments) - 2} more").classes('text-xs text-gray-500')

                            # Clickable area to expand time slots
                            ui.button('View Times',
                                    on_click=lambda d=day_date: show_day_time_slots(d)
                                   ).classes('w-full text-xs py-1 mt-1 bg-gray-100 hover:bg-gray-200').props('dense flat')

    def show_day_time_slots(selected_date):
        """Show detailed time slots for a specific day with 30-minute intervals"""
        # Create a dialog to show the day's time slots
        day_dialog = ui.dialog()
        with day_dialog:
            with ui.card().classes('w-full max-w-4xl'):
                ui.label(f'Time Slots for {selected_date.strftime("%B %d, %Y")}').classes('text-xl font-bold mb-4')

                # Time slots grid (8 AM to 8 PM with 30-minute intervals)
                time_slots = []
                for hour in range(8, 20):  # 8 AM to 8 PM
                    for minute in [0, 30]:
                        time_str = f"{hour:02d}:{minute:02d}"
                        time_slots.append(time_str)

                # Get occupied slots for the selected date
                occupied_slots = get_occupied_slots(selected_date.strftime('%Y-%m-%d'))

                # Display time slots in a grid
                with ui.grid(columns=4).classes('w-full gap-2'):
                    for time_slot in time_slots:
                        # Determine if the slot is reserved
                        is_reserved = time_slot in occupied_slots

                        # Determine if the slot is in the past
                        slot_datetime = datetime.datetime.combine(selected_date, datetime.datetime.strptime(time_slot, "%H:%M").time())
                        is_past = slot_datetime < datetime.datetime.now()

                        # Check if this slot has canceled appointments
                        has_canceled = False
                        canceled_customer_names = []
                        if is_reserved:
                            # Check if any of the appointments in this slot are canceled
                            date_obj = selected_date
                            day_appointments = [apt for apt in appointments_data if
                                               (apt['appointment_date'] == date_obj or str(apt['appointment_date']) == selected_date.strftime('%Y-%m-%d'))]

                            for apt in day_appointments:
                                if isinstance(apt['appointment_time'], str):
                                    start_time = datetime.datetime.strptime(apt['appointment_time'], "%H:%M:%S").time()
                                else:
                                    start_time = apt['appointment_time']

                                duration = apt['duration_minutes'] or 30
                                appointment_date = selected_date
                                current = datetime.datetime.combine(appointment_date, start_time)
                                end = current + datetime.timedelta(minutes=duration)
                                slot_time = datetime.datetime.strptime(time_slot, "%H:%M").time()
                                slot_datetime_check = datetime.datetime.combine(appointment_date, slot_time)

                                if current <= slot_datetime_check < end:
                                    if apt['status'] == 'canceled':
                                        has_canceled = True
                                        if apt['customer_name'] not in canceled_customer_names:
                                            canceled_customer_names.append(apt['customer_name'])

                        if has_canceled:
                            # Show canceled appointment slot in orange with strikethrough
                            customer_names = ', '.join(canceled_customer_names)
                            ui.button(f"❌ {time_slot} - {customer_names}",
                                    on_click=lambda ts=time_slot: edit_appointment_from_slot(selected_date.strftime('%Y-%m-%d'), ts)
                                   ).classes('w-full py-2 bg-orange-400 hover:bg-orange-500 text-sm text-white line-through').props('dense')
                        elif is_reserved:
                            # Show filled appointment slot in red with customer names
                            customer_names = ', '.join(occupied_slots[time_slot])
                            ui.button(f"{time_slot} - {customer_names}",
                                    on_click=lambda ts=time_slot: edit_appointment_from_slot(selected_date.strftime('%Y-%m-%d'), ts)
                                   ).classes('w-full py-2 bg-red-400 hover:bg-red-500 text-sm text-white').props('dense')
                        elif is_past:
                            # Past time slots disabled and grayed out
                            ui.button(f"{time_slot} - Unavailable"
                                   ).classes('w-full py-2 bg-gray-300 text-sm text-gray-600').props('dense flat disabled')
                        else:
                            # Show available time slot
                            def create_apt_handler(ts=time_slot):
                                create_appointment_dialog(selected_date.strftime('%Y-%m-%d'), ts)
                            ui.button(f"{time_slot} - Available",
                                    on_click=create_apt_handler
                                   ).classes('w-full py-2 bg-green-100 hover:bg-green-200 text-sm').props('dense flat')

                # Close button
                with ui.row().classes('w-full justify-end mt-4'):
                    ui.button('Close', on_click=day_dialog.close).classes('px-4 py-2')

        day_dialog.open()

    def edit_appointment(appointment):
        """Edit existing appointment"""
        nonlocal appointment_dialog, time_slots_dialog

        # Close time slots dialog if it's open
        if time_slots_dialog:
            time_slots_dialog.close()
            time_slots_dialog = None

        appointment_dialog = ui.dialog()
        with appointment_dialog:
            with ui.card().classes('w-full max-w-lg mx-auto'):
                ui.label('Edit Appointment').classes('text-xl font-bold mb-6 text-center')

                # Center the form content
                with ui.column().classes('w-full items-center gap-4'):
                    # Load data first
                    services_data = []
                    connection.contogetrows("SELECT id, service_name, description, duration_minutes FROM services WHERE is_active = 1", services_data)
                    service_options = {row[0]: f"{row[1]} ({row[2] or 'No description'})" for row in services_data}

                    customers_data = []
                    connection.contogetrows("SELECT id, customer_name FROM customers", customers_data)
                    customer_options = {row[0]: row[1] for row in customers_data}

                    employees_data = []
                    connection.contogetrows("SELECT id, CONCAT(first_name, ' ', last_name) as name FROM employees", employees_data)
                    employee_options = {row[0]: row[1] for row in employees_data}

                    # Form fields with centered layout
                    service_select = ui.select(service_options, label='Service', value=appointment['service_id']).classes('w-full max-w-sm')
                    customer_select = ui.select(customer_options, label='Customer', value=appointment['customer_id']).classes('w-full max-w-sm')
                    employee_select = ui.select(employee_options, label='Employee', value=appointment['employee_id']).classes('w-full max-w-sm')
                    date_input = ui.input('Date', value=appointment['appointment_date']).classes('w-full max-w-sm')
                    time_input = ui.input('Time', value=appointment['appointment_time']).classes('w-full max-w-sm')
                    duration_input = ui.select(['30', '60', '90', '120'], value=str(appointment['duration_minutes']), label='Duration (minutes)').classes('w-full max-w-sm')
                    notes_input = ui.textarea('Notes', value=appointment['notes'] or '').classes('w-full max-w-sm')

                    # Auto-fill duration when service is selected
                    def on_service_change():
                        if service_select.value:
                            selected_service = next((s for s in services_data if s[0] == service_select.value), None)
                            if selected_service:
                                duration_input.value = str(selected_service[3])

                    service_select.on('change', on_service_change)

                    # Buttons centered at bottom
                    with ui.row().classes('w-full justify-center mt-6 gap-4'):
                        ui.button('Cancel', on_click=appointment_dialog.close).classes('px-6 py-2')
                        ui.button('Update', color='primary', on_click=lambda: update_appointment(
                            appointment['id'],
                            service_select.value,
                            customer_select.value,
                            employee_select.value,
                            date_input.value,
                            time_input.value,
                            duration_input.value,
                            notes_input.value
                        )).classes('px-6 py-2')
                        if appointment['status'] != 'canceled':
                            ui.button('Cancel Appointment', color='orange', on_click=lambda: cancel_appointment(appointment['id'])).classes('px-6 py-2')
                        ui.button('Delete', color='red', on_click=lambda: delete_appointment(appointment['id'])).classes('px-6 py-2')

        appointment_dialog.open()

    def edit_appointment_from_slot(date_str, time_str):
        """Edit appointment from time slot click"""
        # Find the appointment that occupies this slot
        # Convert date_str to date object for consistent comparison
        try:
            date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except Exception:
            date_obj = date_str  # fallback if already date object

        day_appointments = [apt for apt in appointments_data if apt['appointment_date'] == date_obj or str(apt['appointment_date']) == date_str]
        for apt in day_appointments:
            # Handle both string and time object formats
            if isinstance(apt['appointment_time'], str):
                start_time = datetime.datetime.strptime(apt['appointment_time'], "%H:%M:%S").time()
            else:
                start_time = apt['appointment_time']

            duration = apt['duration_minutes'] or 30
            # Use the actual date from the appointment, not today's date
            appointment_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            current = datetime.datetime.combine(appointment_date, start_time)
            end = current + datetime.timedelta(minutes=duration)
            slot_time = datetime.datetime.strptime(time_str, "%H:%M").time()
            slot_datetime = datetime.datetime.combine(appointment_date, slot_time)
            if current <= slot_datetime < end:
                edit_appointment(apt)
                return
        ui.notify("No appointment found for this time slot", color='orange')

    def previous_month():
        """Navigate to previous month"""
        nonlocal current_date
        if current_date.month == 1:
            current_date = current_date.replace(year=current_date.year - 1, month=12)
        else:
            current_date = current_date.replace(month=current_date.month - 1)
        load_appointments()
        render_calendar()

    def next_month():
        """Navigate to next month"""
        nonlocal current_date
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)
        load_appointments()
        render_calendar()

    def go_to_today():
        """Go to current month"""
        nonlocal current_date
        current_date = datetime.date.today()
        load_appointments()
        render_calendar()

    def show_print_dialog():
        """Show print dialog with appointments table for current month"""
        # Filter appointments for current month
        year, month = current_date.year, current_date.month
        month_appointments = [apt for apt in appointments_data if apt['appointment_date'].year == year and apt['appointment_date'].month == month]

        # Prepare table data
        table_data = []
        total_sum = 0
        for apt in month_appointments:
            date_time = f"{apt['appointment_date']} {apt['appointment_time']}"
            status = 'completed' if apt['appointment_date'] < datetime.date.today() and apt['status'] not in ['canceled', 'deleted'] else 'pending'
            value = apt['price'] or 0
            total_sum += value
            table_data.append({
                'Service': apt['service_type'],
                'Customer': apt['customer_name'],
                'Date & Time': date_time,
                'Status': status,
                'Value': f"${value:.2f}"
            })

        # Create dialog
        print_dialog = ui.dialog()
        with print_dialog:
            with ui.card().classes('w-full max-w-6xl'):
                ui.label(f'Appointments for {calendar.month_name[month]} {year}').classes('text-xl font-bold mb-4')

                # Table
                columns = [
                    {'name': 'Service', 'label': 'Service', 'field': 'Service'},
                    {'name': 'Customer', 'label': 'Customer', 'field': 'Customer'},
                    {'name': 'Date & Time', 'label': 'Date & Time', 'field': 'Date & Time'},
                    {'name': 'Status', 'label': 'Status', 'field': 'Status'},
                    {'name': 'Value', 'label': 'Value', 'field': 'Value'}
                ]

                ui.table(columns=columns, rows=table_data).classes('w-full')

                # Total
                ui.label(f'Total: ${total_sum:.2f}').classes('text-lg font-bold mt-4')

                # Buttons
                with ui.row().classes('w-full justify-between mt-4'):
                    ui.button('Print to PDF', on_click=lambda: ui.run_javascript('window.print()')).classes('px-4 py-2 bg-green-500 text-white')
                    ui.button('Close', on_click=print_dialog.close).classes('px-4 py-2')

        print_dialog.open()

    # Main layout
    with ui.element('div').classes('flex w-full h-screen'):
        with ui.column().classes('w-48 p-4 bg-gray-100 flex-shrink-0'):
            ui.label('Calendar Actions').classes('text-lg font-bold mb-4')
            ui.button('Print', icon='print', on_click=show_print_dialog).classes('bg-blue-500 text-white w-full mb-2')
            ui.button('Refresh', icon='refresh', on_click=lambda: (load_appointments(), render_calendar())).classes('bg-purple-500 text-white w-full mb-2')

        with ui.column().classes('flex-1 p-4 overflow-y-auto'):
            ui.label('Appointment Calendar').classes('text-2xl font-bold mb-4')

            # Calendar container
            calendar_container = ui.element('div').classes('w-full')

            # Initial load
            load_appointments()
            render_calendar()

def appointments_page():
    uiAggridTheme.addingtheme()

    user = session_storage.get('user')
    if not user:
        ui.notify('Please login to access this page', color='red')
        ui.navigate.to('/login')
        return

    permissions = connection.get_user_permissions(user['role_id'])
    allowed_pages = {page for page, can_access in permissions.items() if can_access}

    navigation = EnhancedNavigation(permissions, user)
    navigation.create_navigation_drawer()
    navigation.create_navigation_header()

    appointments_content()

@ui.page('/appointments')
def appointments_page_route():
    appointments_page()
