from nicegui import ui
from connection import connection
import datetime
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage

class CompanyUI:
    def __init__(self, show_navigation=True, show_footer=True):
        self.saving = False
        self.ui_created = False
        self.timer_set = False
        self.show_navigation = show_navigation
        self.show_footer = show_footer
        
        # Setup data and UI
        self.company_data = {}
        self.load_company_info()
        self.check_authentication_and_setup_ui()

    def check_authentication_and_setup_ui(self):
        # Prevent multiple UI creations
        if self.ui_created:
            return

        # Check if user is logged in
        user = session_storage.get('user')
        if not user:
            ui.notify('Please login to access this page', color='red')
            ui.run_javascript('window.location.href = "/login"')
            return

        # Get user permissions
        permissions = connection.get_user_permissions(user['role_id'])
        
        if self.show_navigation:
            # Create enhanced navigation instance
            navigation = EnhancedNavigation(permissions, user)
            navigation.create_navigation_drawer()  # Create drawer first
            navigation.create_navigation_header()  # Then create header with toggle button

        self.create_ui()
        self.ui_created = True  # Mark UI as created

    def load_company_info(self):
        """Load company information from database"""
        self.company_data = connection.get_company_info() or {}
        
    def save_company_info(self):
        """Save company information to database"""
        if self.saving:
            print("Save already in progress, ignoring duplicate request")
            return

        self.saving = True
        self.save_button.props('disabled=true')  # Disable button during save

        try:
            print("Starting company info save...")
            company_data = {
                'company_name': self.company_name_input.value,
                'address': self.address_input.value,
                'city': self.city_input.value,
                'state': self.state_input.value,
                'zip_code': self.zip_code_input.value,
                'phone': self.phone_input.value,
                'email': self.email_input.value,
                'website': self.website_input.value,
                'logo_path': self.logo_path_input.value
            }

            result = connection.save_company_info(company_data)
            print(f"Save result: {result}")
            ui.notify(result)
            self.load_company_info()  # Reload data

        except Exception as e:
            print(f"Error saving company information: {str(e)}")
            ui.notify(f'Error saving company information: {str(e)}')
        finally:
            self.saving = False
            self.save_button.props('disabled=false')  # Re-enable button

    def create_ui(self):
        """Create the company information management UI"""
        with ui.card().classes('w-full max-w-4xl mx-auto p-6'):
            ui.label('Company Details').classes('text-xl font-bold mb-6')
            
            with ui.grid(columns=2).classes('w-full gap-4'):
                # Company Name
                self.company_name_input = ui.input('Company Name', 
                    value=self.company_data.get('company_name', '')).classes('w-full')
                
                # Address
                self.address_input = ui.input('Address', 
                    value=self.company_data.get('address', '')).classes('w-full')
                
                # City
                self.city_input = ui.input('City', 
                    value=self.company_data.get('city', '')).classes('w-full')
                
                # State
                self.state_input = ui.input('State', 
                    value=self.company_data.get('state', '')).classes('w-full')
                
                # Zip Code
                self.zip_code_input = ui.input('Zip Code', 
                    value=self.company_data.get('zip_code', '')).classes('w-full')
                
                # Phone
                self.phone_input = ui.input('Phone', 
                    value=self.company_data.get('phone', '')).classes('w-full')
                
                # Email
                self.email_input = ui.input('Email', 
                    value=self.company_data.get('email', '')).classes('w-full')
                
                # Website
                self.website_input = ui.input('Website', 
                    value=self.company_data.get('website', '')).classes('w-full')
                
                # Logo Path (optional)
                self.logo_path_input = ui.input('Logo Path (optional)', 
                    value=self.company_data.get('logo_path', '')).classes('w-full')
            
            # Save button
            with ui.row().classes('w-full justify-center mt-6'):
                self.save_button = ui.button('Save Company Information',
                         on_click=self.save_company_info,
                         icon='save').props('color=primary size=lg')

        if self.show_footer:
            # Footer with system time, company name, and username
            with ui.footer().classes('flex justify-between items-center p-4 bg-gray-100 text-sm text-gray-600'):
                # System time
                def update_time():
                    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    time_label.set_text(f'System Time: {now}')
                time_label = ui.label()
                update_time()
                ui.timer(1.0, update_time)

                # Company name from database
                company_info = connection.get_company_info()
                company_name = company_info.get('company_name') if company_info else ''
                ui.label(f'Company: {company_name}')

                # Username from session
                user = session_storage.get('user')
                username = user.get('username') if user else 'Guest'
                ui.label(f'User: {username}')

@ui.page('/company')
def company_page_route():
    CompanyUI()
