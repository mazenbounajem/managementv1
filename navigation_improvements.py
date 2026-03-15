"""
Enhanced Navigation System for POS Management
Features: Organized categories, search, breadcrumbs, recent pages, keyboard shortcuts
"""

from nicegui import ui
from nicegui import context as ng_context


import json
from datetime import datetime
import os
from modern_design_system import ModernDesignSystem as MDS

# Import switch_to_tab function for tab switching
try:
    from tabbed_dashboard import switch_to_tab
except ImportError:
    switch_to_tab = None

class EnhancedNavigation:
    def __init__(self, user_permissions, current_user):
        self.user_permissions = user_permissions
        self.current_user = current_user
        self.recent_pages = self.load_recent_pages()
        self.current_path = []
        self.search_query = ""
        self.drawer = None
        # Detect current page path for active-item highlighting
        try:
            self.active_path = ng_context.client.page.path
        except Exception:
            self.active_path = ''
        self.setup_navigation_data()

    def setup_navigation_data(self):
        """Setup navigation structure with categories and icons"""
        self.navigation_categories = {
            'Dashboard': {
                'icon': 'dashboard',
                'items': {
                    'dashboard':  {'label': 'Home',               'path': '/dashboard',         'icon': 'home',                   'shortcut': 'Alt+H'},
                    'timespend':  {'label': 'Time Spend Analysis', 'path': '/timespend',          'icon': 'schedule',               'shortcut': 'Alt+T'},
                }
            },
            'Sales & Inventory': {
                'icon': 'shopping_cart',
                'items': {
                    'sales':           {'label': 'Sales',            'path': '/sales',            'icon': 'point_of_sale', 'shortcut': 'Alt+S'},
                    'products':        {'label': 'Products',         'path': '/products',         'icon': 'inventory',     'shortcut': 'Alt+P'},
                    'purchase':        {'label': 'Purchase',         'path': '/purchase',         'icon': 'shopping_bag',  'shortcut': 'Alt+U'},
                    'stockoperations': {'label': 'Stock Operations', 'path': '/stockoperations',  'icon': 'inventory_2',   'shortcut': 'Alt+K'},
                    'category':        {'label': 'Category',         'path': '/category',         'icon': 'category',      'shortcut': 'Alt+C'},
                }
            },
            'Customers & Suppliers': {
                'icon': 'people',
                'items': {
                    'customers':      {'label': 'Customers',        'path': '/customers',        'icon': 'person',    'shortcut': 'Alt+M'},
                    'customerreceipt':{'label': 'Customer Receipt', 'path': '/customerreceipt',  'icon': 'receipt',   'shortcut': 'Alt+Q'},
                    'suppliers':      {'label': 'Suppliers',        'path': '/suppliers',        'icon': 'business',  'shortcut': 'Alt+L'},
                    'supplierpayment':{'label': 'Supplier Payment', 'path': '/supplierpayment',  'icon': 'payment',   'shortcut': 'Alt+Y'},
                }
            },
            'Finance': {
                'icon': 'account_balance',
                'items': {
                    'expenses':       {'label': 'Expenses',             'path': '/expenses',        'icon': 'money_off',              'shortcut': 'Alt+E'},
                    'expensestype':   {'label': 'Expense Types',        'path': '/expensestype',    'icon': 'category',               'shortcut': 'Alt+X'},
                    'currencies':     {'label': 'Currencies',           'path': '/currencies',      'icon': 'currency_exchange',      'shortcut': 'Alt+W'},
                    'accounting':     {'label': 'Accounting & Finance', 'path': '/accounting',      'icon': 'account_balance',        'shortcut': 'Alt+A'},
                    'cash-drawer':    {'label': 'Cash Drawer',          'path': '/cash-drawer',     'icon': 'account_balance_wallet', 'shortcut': 'Alt+D'},
                    'ledger':         {'label': 'Ledger',               'path': '/ledger',          'icon': 'account_balance',        'shortcut': 'Alt+F'},
                    'auxiliary':      {'label': 'Auxiliary',            'path': '/auxiliary',       'icon': 'account_balance',        'shortcut': 'Alt+Aux'},
                    'journal_voucher':{'label': 'Journal Voucher',      'path': '/journal_voucher', 'icon': 'receipt_long',           'shortcut': 'Alt+J'},
                    'voucher_subtype':{'label': 'Voucher Subtype',      'path': '/voucher_subtype', 'icon': 'category',               'shortcut': 'Alt+V'},
                }
            },
            'Administration': {
                'icon': 'admin_panel_settings',
                'items': {
                    'employees':    {'label': 'Employees',    'path': '/employees',    'icon': 'badge',          'shortcut': 'Alt+O'},
                    'company':      {'label': 'Company',      'path': '/company',      'icon': 'business_center','shortcut': 'Alt+B'},
                    'roles':        {'label': 'Roles',        'path': '/roles',        'icon': 'group',          'shortcut': 'Alt+G'},
                    'appointments': {'label': 'Appointments', 'path': '/appointments', 'icon': 'event',          'shortcut': 'Alt+N'},
                    'services':     {'label': 'Services',     'path': '/services',     'icon': 'build',          'shortcut': 'Alt+I'},
                }
            },
            'Reports': {
                'icon': 'analytics',
                'items': {
                    'reports':             {'label': 'Reports',             'path': '/reports',             'icon': 'analytics', 'shortcut': 'Alt+R'},
                    'statistical-reports': {'label': 'Statistical Reports', 'path': '/statistical-reports', 'icon': 'bar_chart', 'shortcut': 'Alt+2'},
                }
            },
            'System': {
                'icon': 'settings',
                'items': {
                    'backup': {'label': 'Database Backup', 'path': '/tabbed-dashboard', 'icon': 'backup', 'shortcut': 'Alt+Z'},
                }
            }
        }

    def load_recent_pages(self):
        """Load recently visited pages from storage"""
        try:
            if os.path.exists('recent_pages.json'):
                with open('recent_pages.json', 'r') as f:
                    return json.load(f)
        except:
            pass
        return []

    def save_recent_pages(self):
        """Save recent pages to storage"""
        try:
            with open('recent_pages.json', 'w') as f:
                json.dump(self.recent_pages[:10], f)  # Keep only last 10
        except:
            pass

    def add_recent_page(self, page_key, label):
        """Add page to recent pages"""
        timestamp = datetime.now().isoformat()
        recent_item = {
            'key': page_key,
            'label': label,
            'timestamp': timestamp
        }

        # Remove if already exists
        self.recent_pages = [p for p in self.recent_pages if p['key'] != page_key]
        # Add to beginning
        self.recent_pages.insert(0, recent_item)
        self.save_recent_pages()

    def get_allowed_pages(self):
        """Get pages user has permission to access"""
        allowed = set()
        for category, data in self.navigation_categories.items():
            for page_key, page_data in data['items'].items():
                if page_key in self.user_permissions and self.user_permissions[page_key]:
                    allowed.add(page_key)
        return allowed

    def search_pages(self, query):
        """Search pages by label or key"""
        if not query:
            return []

        query = query.lower()
        results = []
        allowed_pages = self.get_allowed_pages()

        for category, data in self.navigation_categories.items():
            for page_key, page_data in data['items'].items():
                if page_key in allowed_pages:
                    if query in page_data['label'].lower() or query in page_key.lower():
                        results.append({
                            'key': page_key,
                            'label': page_data['label'],
                            'path': page_data['path'],
                            'icon': page_data['icon'],
                            'category': category
                        })

        return results

    def create_navigation_header(self):
        """Create premium navigation header with glassmorphism"""
        with ui.header().classes('ribbon-container').style('background: transparent; border: none;'):
            with ui.row().classes('w-full items-center justify-between px-6 py-2 glass').style('border-radius: 0 0 1.5rem 1.5rem; border-top: none;'):

                # Left side - Logo & Path
                with ui.row().classes('items-center gap-6'):
                    # Custom Hamburger Toggle
                    self.toggle_button = ui.button(icon='menu').props('flat round').classes('text-gray-700 hover:text-purple-600 transition-all')
                    self.toggle_button.on('click', self.toggle_navigation_drawer)

                    with ui.row().classes('items-center gap-2'):
                        ui.icon('cloud_done', size='2rem').style(f'color: {MDS.SECONDARY}')
                        ui.label('ManagementOS').classes('text-xl font-black tracking-tighter text-gray-900').style('font-family: "Outfit", sans-serif;')

                    # Animated Breadcrumbs
                    if self.current_path:
                        with ui.row().classes('items-center gap-2 ml-4 animate-fade-in'):
                            ui.label('/').classes('text-gray-300 font-light')
                            for i, crumb in enumerate(self.current_path):
                                if i > 0:
                                    ui.label('›').classes('text-gray-300 font-light')
                                ui.label(crumb).classes('text-xs font-bold uppercase tracking-widest text-gray-500 bg-gray-100/50 px-2 py-1 rounded-md')

                # Center - Global Quick Search
                with ui.row().classes('flex-1 justify-center max-w-xl mx-8'):
                    with ui.row().classes('w-full items-center px-4 py-1 rounded-full bg-gray-100/50 border border-gray-200/50 focus-within:bg-white focus-within:shadow-lg focus-within:border-purple-300 transition-all'):
                        ui.icon('search', size='1.25rem').classes('text-gray-400')
                        search_input = ui.input(placeholder='Search everything... (Alt+/)').props('borderless dense').classes('flex-1 ml-2 text-sm font-medium')
                        search_input.on('input', lambda e: self.update_search_results(e.value))

                    # Glass Search Results
                    self.search_dropdown = ui.column().classes('absolute top-full mt-2 left-0 right-0 glass p-2 rounded-2xl hidden z-50').style('max-height: 400px; overflow-y: auto;')

                # Right side - Actions & User
                with ui.row().classes('items-center gap-3'):
                    # Action Buttons
                    ui.button(icon='notifications').props('flat round').classes('text-gray-500 hover:text-purple-600')
                    
                    # User Profile Widget
                    with ui.row().classes('items-center gap-3 pl-4 border-l border-gray-200'):
                        with ui.column().classes('items-end gap-0'):
                            ui.label(self.current_user.get("username", "User")).classes('text-sm font-bold text-gray-900')
                            ui.label('Enterprise Admin').classes('text-[10px] font-black uppercase tracking-tighter text-purple-600')
                        
                        with ui.button().props('flat round').classes('p-0 overflow-hidden border-2 border-purple-100 hover:border-purple-500 transition-all'):
                            ui.image('https://ui-avatars.com/api/?name=' + self.current_user.get("username", "U") + '&background=7048E8&color=fff').classes('w-8 h-8 rounded-full')
                            
                            with ui.menu().classes('glass p-2 rounded-xl border border-white/50 shadow-2xl'):
                                ui.menu_item('My Account', lambda: self.navigate_to_page('profile')).classes('rounded-lg font-bold text-sm')
                                ui.menu_item('System Settings', lambda: self.navigate_to_page('settings')).classes('rounded-lg font-bold text-sm')
                                ui.separator().classes('my-2 opacity-50')
                                ui.menu_item('Sign Out', on_click=self.confirm_logout).classes('rounded-lg font-bold text-sm text-red-500')


    def confirm_logout(self):
        """Show confirmation dialog before logging out"""
        with ui.dialog() as dialog, ui.card().classes('p-6'):
            ui.label('Logout Confirmation').classes('text-xl font-bold mb-2')
            ui.label('Are you sure you want to logout of your session?').classes('text-gray-600 mb-6')
            with ui.row().classes('w-full justify-end gap-3 mt-4'):
                ui.button('Cancel', on_click=dialog.close).props('flat text-gray-600')
                ui.button('Logout', color='red', on_click=lambda: ui.navigate.to('/logout')).props('unelevated')
        dialog.open()

    def create_navigation_drawer(self):
        """Create premium navigation drawer"""
        with ui.left_drawer(value=True).classes('drawer p-4').props('width=280 breakpoint=0') as drawer:
            self.drawer = drawer
            
            with ui.column().classes('w-full gap-8'):
                # Branding / Logo
                with ui.row().classes('w-full items-center px-4 gap-3 mb-4'):
                    ui.icon('cloud_done', size='2.5rem').style(f'color: {MDS.ACCENT}')
                    ui.label('ManagementOS').classes('text-xl font-black text-white tracking-tighter')

                # Search in drawer
                with ui.row().classes('w-full items-center px-4 py-2 rounded-xl bg-white/5 border border-white/10 hover:border-white/20 transition-all'):
                    ui.icon('search', size='1rem').classes('text-gray-500')
                    self.drawer_search = ui.input(placeholder='Jump to Page...').props('borderless dense').classes('flex-1 ml-2 text-xs font-bold text-white uppercase tracking-wider')
                    self.drawer_search.on('input', lambda e: self.filter_navigation(e.value))

                # Navigation content
                self.nav_container = ui.column().classes('w-full gap-2 mt-4 drawer-scroll-container overflow-y-auto')
                with self.nav_container:
                    self.create_navigation_content()


    def create_navigation_content(self, search_filter=""):
        """Create navigation content with categories"""
        allowed_pages = self.get_allowed_pages()

        for category, data in self.navigation_categories.items():
            category_items = []
            for page_key, page_data in data['items'].items():
                if page_key in allowed_pages:
                    if not search_filter or search_filter.lower() in page_data['label'].lower():
                        category_items.append((page_key, page_data))

            if category_items:
                # Premium Category Section
                with ui.column().classes('w-full mb-6'):
                    ui.label(category).classes('text-[10px] font-black uppercase tracking-[0.2em] text-gray-400 mb-3 px-4')
                    
                    # Category items
                    for page_key, page_data in category_items:
                        is_active = (page_data['path'] == self.active_path)
                        
                        btn_classes = 'drawer-button w-full ' + ('active ' if is_active else '')
                        
                        with ui.element('div').classes(btn_classes).on('click', lambda p=page_key: self.navigate_to_page(p)):
                            ui.icon(page_data['icon']).classes('drawer-button-icon')
                            ui.label(page_data['label']).classes('drawer-button-label flex-1')
                            
                            if is_active:
                                ui.element('div').classes('w-1.5 h-1.5 rounded-full bg-white animate-pulse')


    def filter_navigation(self, query):
        """Filter navigation based on search query"""
        # Clear current content area only
        if hasattr(self, 'nav_container'):
            self.nav_container.clear()
            with self.nav_container:
                self.create_navigation_content(query)

    def update_search_results(self, query):
        """Update search results in header"""
        self.search_query = query

        # Clear previous results
        self.search_dropdown.clear()

        if query.strip():
            results = self.search_pages(query)
            if results:
                with self.search_dropdown:
                    for result in results[:8]:  # Limit to 8 results
                        ui.button(
                            f"{result['icon']} {result['label']}",
                            on_click=lambda r=result: self.navigate_to_search_result(r)
                        ).props('flat').classes('w-full text-left p-2 hover:bg-gray-100')

                # Show dropdown
                self.search_dropdown.classes(remove='hidden')
            else:
                # Hide dropdown if no results
                self.search_dropdown.classes(add='hidden')
        else:
            # Hide dropdown if query is empty
            self.search_dropdown.classes(add='hidden')

    def toggle_navigation_drawer(self):
        """Toggle the navigation drawer visibility"""
        if hasattr(self, 'drawer') and self.drawer:
            self.drawer.value = not self.drawer.value
        else:
            # If drawer is not yet created, create it now
            if not hasattr(self, 'drawer') or not self.drawer:
                self.create_navigation_drawer()
            if self.drawer:
                self.drawer.value = True

    def navigate_to_page(self, page_key):
        """Navigate to a page and update breadcrumbs/recent pages"""
        # Find page data
        for category, data in self.navigation_categories.items():
            if page_key in data['items']:
                page_data = data['items'][page_key]
                self.add_recent_page(page_key, page_data['label'])
                self.current_path = [category, page_data['label']]

                # Special handling for backup page - switch to tab instead of navigating
                if page_key == 'backup' and switch_to_tab:
                    switch_to_tab('Backup')
                else:
                    ui.navigate.to(page_data['path'])

                # Hide search dropdown after navigation
                if hasattr(self, 'search_dropdown'):
                    self.search_dropdown.classes(add='hidden')
                break

    def navigate_to_search_result(self, result):
        """Navigate to a search result"""
        self.navigate_to_page(result['key'])

    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for navigation"""
        allowed_pages = self.get_allowed_pages()

        shortcuts = {}
        for category, data in self.navigation_categories.items():
            for page_key, page_data in data['items'].items():
                if page_key in allowed_pages and 'shortcut' in page_data:
                    shortcuts[page_data['shortcut']] = lambda p=page_key: self.navigate_to_page(p)

        # Add shortcuts to the page
        for shortcut, action in shortcuts.items():
            ui.keyboard(shortcut, action)

    def get_navigation_ui(self):
        """Get the complete navigation UI"""
        self.create_navigation_header()
        self.create_navigation_drawer()
        self.setup_keyboard_shortcuts()

        return self.drawer
