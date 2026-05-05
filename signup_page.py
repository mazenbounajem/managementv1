from nicegui import ui
from connection import connection
from modern_design_system import ModernDesignSystem as MDS
from modern_ui_components import ModernInput, ModernButton

class SignupPage:
    def __init__(self):
        self.username_input = None
        self.email_input = None
        self.password_input = None
        self.confirm_password_input = None

    def build_ui(self):
        # Add global styles
        ui.add_head_html(MDS.get_global_styles())
        
        # Share the same premium styles as login
        ui.add_head_html('''
        <style>
            .signup-container {
                min-height: 100vh;
                background: radial-gradient(circle at 100% 100%, #1a1b1e 0%, transparent 50%),
                            radial-gradient(circle at 0% 100%, #373a40 0%, transparent 50%),
                            radial-gradient(circle at 0% 0%, #5f3dc4 0%, transparent 50%),
                            radial-gradient(circle at 100% 0%, #1a202c 0%, transparent 50%);
                background-color: #1a1b1e;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 2rem;
                overflow-y: auto;
                position: relative;
            }
            .signup-card-wrapper {
                width: 100%;
                max-width: 520px;
                z-index: 10;
                padding: 2rem 0;
            }
            .os-logo {
                font-family: 'Outfit', sans-serif;
                background: linear-gradient(135deg, #fff 0%, #868e96 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                letter-spacing: -1px;
            }
        </style>
        ''')

        with ui.element('div').classes('w-full signup-container mesh-gradient m-0'):
            with ui.column().classes('signup-card-wrapper items-center gap-6'):
                
                # Header Section
                with ui.column().classes('text-center items-center w-full animate-fade-in'):
                    with ui.element('div').classes('p-3 rounded-2xl glass mb-4 hover-lift'):
                        ui.icon('person_add', size='2.5rem').style(f'color: {MDS.ACCENT}')
                    
                    company_info = connection.get_company_info()
                    company_name = company_info.get('company_name', 'ManagementOS') if company_info else 'ManagementOS'
                    ui.label(f'Join {company_name}').classes('text-4xl font-black text-white tracking-tighter mb-1 os-logo')
                    ui.label('Start your journey with precision.').classes('text-xs text-gray-400 font-bold uppercase tracking-widest mb-4')

                # Custom Glass Signup Card
                with ui.column().classes('card glass p-8 w-full animate-slide-in').style('border-radius: 2rem;'):
                    ui.label('Create Account').style(f'color: {MDS.PRIMARY_DARK}; font-family: "Outfit", sans-serif;').classes('text-2xl font-black tracking-tight mb-6 text-center w-full')

                    # Form inputs
                    with ui.column().classes('w-full gap-4'):
                        self.username_input = ModernInput('Username', placeholder='Choose a username', icon='person').classes('w-full')
                        self.email_input = ModernInput('Email', placeholder='your@email.com', icon='email').classes('w-full')
                        self.password_input = ModernInput('Password', placeholder='••••••••', input_type='password', icon='lock').classes('w-full')
                        self.confirm_password_input = ModernInput('Confirm Password', placeholder='••••••••', input_type='password', icon='verified_user').classes('w-full')
                        
                        with ui.row().classes('w-full items-center px-1 mb-2'):
                            ui.checkbox('').classes('mr-2')
                            ui.label('I agree to the Terms of Service').classes('text-xs text-gray-500 font-medium')

                        ModernButton('Register Enterprise', icon='how_to_reg', variant='primary', size='lg', on_click=self.signup).classes('w-full py-4 text-lg shadow-xl shadow-purple-500/20 mt-2')

                        with ui.row().classes('w-full justify-center pt-6 border-t border-gray-100/10 mt-4'):
                            ui.label("Already have an enterprise portal?").classes('text-gray-400 text-xs font-medium mr-1')
                            ui.link('Sign In', '/login').style(f'color: {MDS.SECONDARY}').classes('text-xs font-black uppercase tracking-widest hover:opacity-70 transition-opacity cursor-pointer')

    def signup(self):
        username = self.username_input.value
        email = self.email_input.value
        password = self.password_input.value
        confirm_password = self.confirm_password_input.value

        if not username or not password or not email:
            ui.notify('All fields are required', color='red', position='top')
            return

        if password != confirm_password:
            ui.notify('Passwords do not match', color='red', position='top')
            return

        from auth_service import AuthService
        success, message = AuthService.create_user(username, password, email=email, role_id=2) # Default to Employee/User role

        if success:
            ui.notify(f'Account created successfully! Welcome {username}. Please login.', color='green', position='top-right')
            ui.run_javascript('window.location.href = "/login";')
        else:
            ui.notify(message, color='red', position='top')

def signup_page():
    page = SignupPage()
    page.build_ui()
    return page
