from nicegui import ui
from connection import connection
from uiaggridtheme import uiAggridTheme
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage

def create_services_table():
    """Create services table if it doesn't exist"""
    sql = '''
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='services' AND xtype='U')
        CREATE TABLE services (
            id INT IDENTITY(1,1) PRIMARY KEY,
            service_name NVARCHAR(100) NOT NULL,
            description NVARCHAR(500),
            duration_minutes INT DEFAULT 30,
            price DECIMAL(10,2),
            is_active BIT DEFAULT 1,
            created_at DATETIME2 DEFAULT GETDATE(),
            updated_at DATETIME2 DEFAULT GETDATE()
        )
    '''
    connection.insertingtodatabase(sql)

def services_content():
    uiAggridTheme.addingtheme()

    services_data = []
    services_container = None
    service_dialog = None

    def load_services():
        """Load services from database"""
        nonlocal services_data
        query = "SELECT id, service_name, description, duration_minutes, price, is_active FROM services ORDER BY service_name"

        data = []
        connection.contogetrows(query, data)

        services_data = []
        for row in data:
            services_data.append({
                'id': row[0],
                'service_name': row[1],
                'description': row[2],
                'duration_minutes': row[3],
                'price': row[4],
                'is_active': row[5]
            })

    def create_service_dialog(service=None):
        """Create or edit service dialog"""
        nonlocal service_dialog

        service_dialog = ui.dialog()
        with service_dialog:
            with ui.card().classes('w-96'):
                ui.label('Add/Edit Service').classes('text-xl font-bold mb-4')

                # Form fields
                name_input = ui.input('Service Name', value=service['service_name'] if service else '').classes('mb-2')
                description_input = ui.textarea('Description', value=service['description'] if service else '').classes('mb-2')
                duration_input = ui.select(['15', '30', '45', '60', '90', '120'], value=str(service['duration_minutes']) if service else '30', label='Duration (minutes)').classes('mb-2')
                price_input = ui.input('Price', value=str(service['price']) if service else '', placeholder='0.00').classes('mb-2')
                active_input = ui.checkbox('Active', value=service['is_active'] if service else True).classes('mb-4')

                with ui.row().classes('w-full justify-end mt-4'):
                    ui.button('Cancel', on_click=service_dialog.close).classes('mr-2')
                    ui.button('Save', color='primary', on_click=lambda: save_service(
                        service['id'] if service else None,
                        name_input.value,
                        description_input.value,
                        duration_input.value,
                        price_input.value,
                        active_input.value
                    ))

        service_dialog.open()

    def save_service(service_id, name, description, duration, price, is_active):
        """Save service to database"""
        if not name:
            ui.notify('Service name is required', color='red')
            return

        try:
            if service_id:
                # Update existing service
                sql = '''
                    UPDATE services
                    SET service_name = ?, description = ?, duration_minutes = ?, price = ?, is_active = ?, updated_at = GETDATE()
                    WHERE id = ?
                '''
                values = (name, description, int(duration), float(price) if price else None, is_active, service_id)
            else:
                # Insert new service
                sql = '''
                    INSERT INTO services (service_name, description, duration_minutes, price, is_active)
                    VALUES (?, ?, ?, ?, ?)
                '''
                values = (name, description, int(duration), float(price) if price else None, is_active)

            connection.insertingtodatabase(sql, values)
            ui.notify('Service saved successfully', color='green')
            service_dialog.close()
            load_services()
            render_services()
        except Exception as e:
            ui.notify(f'Error saving service: {str(e)}', color='red')

    def delete_service(service_id):
        """Delete service from database"""
        try:
            sql = "DELETE FROM services WHERE id = ?"
            connection.insertingtodatabase(sql, (service_id,))
            ui.notify('Service deleted successfully', color='green')
            load_services()
            render_services()
        except Exception as e:
            ui.notify(f'Error deleting service: {str(e)}', color='red')

    def render_services():
        """Render services list"""
        nonlocal services_container

        if services_container:
            services_container.clear()

        with services_container:
            # Services grid
            with ui.grid(columns=1).classes('w-full gap-4'):
                for service in services_data:
                    with ui.card().classes('w-full'):
                        with ui.row().classes('w-full justify-between items-center'):
                            with ui.column().classes('flex-1'):
                                ui.label(service['service_name']).classes('text-lg font-semibold')
                                ui.label(service['description'] or 'No description').classes('text-sm text-gray-600')
                                with ui.row().classes('gap-4 mt-2'):
                                    ui.label(f"Duration: {service['duration_minutes']} min").classes('text-sm')
                                    ui.label(f"Price: ${service['price'] or 'N/A'}").classes('text-sm')
                                    ui.label(f"Status: {'Active' if service['is_active'] else 'Inactive'}").classes('text-sm')

                            with ui.column().classes('flex-shrink-0'):
                                with ui.row().classes('gap-2'):
                                    ui.button('Edit', on_click=lambda s=service: create_service_dialog(s)).classes('px-3 py-1')
                                    ui.button('Delete', on_click=lambda s=service: delete_service(s['id']), color='red').classes('px-3 py-1')

    # Main layout
    with ui.element('div').classes('flex w-full h-screen'):
        with ui.column().classes('w-48 p-4 bg-gray-100 flex-shrink-0'):
            ui.label('Services Management').classes('text-lg font-bold mb-4')
            ui.button('Add Service', icon='add', on_click=lambda: create_service_dialog()).classes('bg-blue-500 text-white w-full mb-2')
            ui.button('Refresh', icon='refresh', on_click=lambda: (load_services(), render_services())).classes('bg-purple-500 text-white w-full mb-2')

        with ui.column().classes('flex-1 p-4 overflow-y-auto'):
            ui.label('Services').classes('text-2xl font-bold mb-4')

            # Services container
            services_container = ui.element('div').classes('w-full')

            # Initial load
            load_services()
            render_services()

def services_page():
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

    # Create services table if it doesn't exist
    create_services_table()

    services_content()

@ui.page('/services')
def services_page_route():
    services_page()
