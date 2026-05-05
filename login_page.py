from nicegui import ui
from connection import connection
import hashlib
from modern_design_system import ModernDesignSystem as MDS
from modern_ui_components import ModernInput, ModernButton

class LoginPage:
    def __init__(self):
        self.username_input = None
        self.password_input = None

    def build_ui(self):
        # Add global styles
        ui.add_head_html(MDS.get_global_styles())
        
        # Premium Background with Mesh-like Gradients
        ui.add_head_html('''
        <style>
            .login-container {
                min-height: 100vh;
                background: radial-gradient(circle at 0% 0%, #1a1b1e 0%, transparent 50%),
                            radial-gradient(circle at 100% 0%, #373a40 0%, transparent 50%),
                            radial-gradient(circle at 100% 100%, #5f3dc4 0%, transparent 50%),
                            radial-gradient(circle at 0% 100%, #1a202c 0%, transparent 50%);
                background-color: #1a1b1e;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 2rem;
                overflow: hidden;
                position: relative;
            }
            .login-container::before {
                content: "";
                position: absolute;
                width: 200%;
                height: 200%;
                background: url('https://www.transparenttextures.com/patterns/carbon-fibre.png');
                opacity: 0.1;
                animation: bg-rotate 60s linear infinite;
            }
            @keyframes bg-rotate {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }
            .login-card-wrapper {
                width: 100%;
                max-width: 480px;
                z-index: 10;
            }
            .feature-pill {
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
                padding: 0.5rem 1rem;
                border-radius: 9999px;
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                color: rgba(255, 255, 255, 0.8);
                font-size: 0.75rem;
                font-weight: 600;
                margin: 0.25rem;
                transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                backdrop-filter: blur(5px);
            }
            .feature-pill:hover {
                background: rgba(255, 255, 255, 0.15);
                transform: translateY(-3px) scale(1.05);
                color: white;
                border-color: rgba(255, 255, 255, 0.3);
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

        with ui.element('div').classes('w-full login-container mesh-gradient m-0'):
            with ui.column().classes('login-card-wrapper items-center gap-8'):
                
                # Header Section
                with ui.column().classes('text-center items-center w-full animate-fade-in'):
                    with ui.element('div').classes('os-logo-container p-4 rounded-3xl glass mb-4 hover-lift'):
                        ui.icon('cloud_done', size='3.5rem').style(f'color: {MDS.ACCENT}')
                    
                    company_info = connection.get_company_info()
                    company_name = company_info.get('company_name', 'ManagementOS') if company_info else 'ManagementOS'
                    ui.label(company_name).classes('text-5xl font-black text-white tracking-tighter mb-1 os-logo')
                    ui.label('Precision Management. Defined.').classes('text-sm text-gray-400 font-bold uppercase tracking-widest mb-6')
                    
                    # Feature pills
                    with ui.row().classes('justify-center flex-wrap gap-1 mb-2'):
                        features = [
                            ('inventory_2', 'Inventory'),
                            ('badge', 'Payroll'),
                            ('query_stats', 'Analytics'),
                            ('shopping_cart', 'Sourcing')
                        ]
                        for icon, label in features:
                            with ui.element('div').classes('feature-pill'):
                                ui.icon(icon, size='0.875rem').style(f'color: {MDS.ACCENT}')
                                ui.label(label)

                # Custom Glass Login Card
                with ui.column().classes('card glass p-10 w-full animate-slide-in').style('border-radius: 2rem;'):
                    ui.label('Welcome Back').style(f'color: {MDS.PRIMARY_DARK}; font-family: "Outfit", sans-serif;').classes('text-3xl font-black tracking-tight mb-2 text-center w-full')
                    ui.label('Access your secure enterprise portal').classes('text-gray-500 mb-8 text-center w-full font-medium')

                    # Form inputs
                    with ui.column().classes('w-full gap-5'):
                        self.username_input = ModernInput('Username', placeholder='Enter your username', icon='person').classes('w-full')
                        self.password_input = ModernInput('Password', placeholder='••••••••', input_type='password', icon='lock').classes('w-full')
                        
                        with ui.row().classes('w-full justify-between items-center px-1 mb-2'):
                            ui.checkbox('Secure Session').classes('text-xs text-gray-500 font-bold uppercase tracking-tight')
                            ui.link('Trouble signing in?', '#').style(f'color: {MDS.SECONDARY}').classes('text-xs font-bold uppercase tracking-tight hover:opacity-70 transition-opacity')

                        ModernButton('Initialize Dashboard', icon='rocket_launch', variant='primary', size='lg', on_click=self.login).classes('w-full py-4 text-lg shadow-xl shadow-purple-500/20')

                        with ui.row().classes('w-full justify-center pt-6 border-t border-gray-100 mt-4'):
                            ui.label("New to ManagementOS?").classes('text-gray-400 text-xs font-medium mr-1')
                            ui.link('Request Access', '/signup').style(f'color: {MDS.SECONDARY}').classes('text-xs font-black uppercase tracking-widest hover:opacity-70 transition-opacity cursor-pointer')



    def login(self):
        username = self.username_input.value
        password = self.password_input.value

        # Strip only if not None
        username = username.strip() if username else ""
        password = password.strip() if password else ""

        if not username or not password:
            ui.notify('Username and password are required', color='red', position='top')
            return

        # Use AuthService for robust authentication
        from auth_service import AuthService
        success, user_data = AuthService.authenticate_user(username, password)

        if success and user_data:
            from session_storage import session_storage
            # Store user info in session storage
            session_storage['user'] = user_data

            # Create user session entry using AuthService
            session_id = AuthService.create_user_session(user_data)
            if session_id:
                session_storage['session_id'] = session_id

            ui.notify(f'Login successful. Welcome {username}!', color='green', position='top-right')
            ui.run_javascript('window.location.href = "/tabbed-dashboard";')
        else:
            ui.notify('Invalid username or password, or user not approved', color='red', position='top')

def login_page():
    page = LoginPage()
    page.build_ui()
    return page
