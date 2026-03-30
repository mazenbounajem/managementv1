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
        
        # Tab management state
        self.tabs_ui = None
        self.tab_panels_ui = None
        self.open_tabs = {} # name -> tab_obj
        self.tabbed_mode = False 
        self.split_view_callback = None

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
                    'modern-purchase': {'label': 'Modern Purchase',  'path': '/modern-purchase',  'icon': 'shopping_cart', 'shortcut': 'Alt+Y'},
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
        """Create premium navigation header with glassmorphism and dynamic tabs"""
        with ui.header().classes('ribbon-container').style('background: transparent; border: none;'):
            with ui.row().classes('w-full items-center justify-between px-6 py-2 glass shadow-lg').style('border-radius: 0 0 1.5rem 1.5rem; border: 1px solid rgba(255,255,255,0.1);'):
                # Left side - Logo & Path
                with ui.row().classes('items-center gap-4'):
                    # Custom Hamburger Toggle
                    self.toggle_button = ui.button(icon='menu').props('flat round').classes('text-gray-700 hover:text-[#7048E8] transition-all')
                    self.toggle_button.on('click', self.toggle_navigation_drawer)
                    
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('cloud_done', size='2rem', color='#7048E8')
                        ui.label('ManagementOS').classes('text-xl font-black tracking-tighter text-gray-900').style('font-family: "Outfit", sans-serif;')
                
                # Dynamic Tabs in the Header
                with ui.row().classes('flex-1 justify-center px-4'):
                    self.tabs_ui = ui.tabs().classes('text-gray-600')
                    self.tabs_ui.props('active-color=#7048E8 indicator-color=#7048E8 dense')
                
                # Right side - Actions & User (Search moved here for space)
                with ui.row().classes('items-center gap-3'):
                    # Split View Toggle
                    if self.tabbed_mode:
                        self.split_btn = ui.button(icon='vertical_split', on_click=self.toggle_split_view).props('flat round').classes('text-gray-500 hover:text-[#7048E8]')
                        self.split_btn.tooltip('Toggle Split View (Side-by-Side)')

                    with ui.row().classes('items-center px-3 py-1 rounded-full bg-gray-100/50 border border-gray-200/50 focus-within:bg-white focus-within:shadow-md transition-all').style('width: 150px;'):
                        ui.icon('search', size='1rem').classes('text-gray-400')
                        search_input = ui.input(placeholder='Search...').props('borderless dense').classes('flex-1 ml-2 text-xs')
                        search_input.on('input', lambda e: self.update_search_results(e.value))
                    
                    self.search_dropdown = ui.column().classes('absolute top-full mt-2 glass p-2 rounded-2xl hidden z-50 shadow-2xl').style('width: 300px; max-height: 400px; overflow-y: auto; right: 20px;')
                    
                    ui.button(icon='notifications').props('flat round').classes('text-gray-500 hover:text-[#7048E8]')
                    
                    # User Menu (existing)
                    with ui.button().props('flat round').classes('p-0 overflow-hidden border-2 border-purple-100 hover:border-[#7048E8] transition-all'):
                        ui.image('https://ui-avatars.com/api/?name=' + self.current_user.get("username", "U") + '&background=7048E8&color=fff').classes('w-8 h-8 rounded-full')
                        with ui.menu().classes('glass p-2 rounded-xl border border-white/50 shadow-2xl'):
                            ui.menu_item('My Account', lambda: self.navigate_to_page('profile', new_instance=True)).classes('rounded-lg font-bold text-sm')
                            ui.separator()
                            ui.menu_item('Sign Out', on_click=self.confirm_logout).classes('rounded-lg font-bold text-sm text-red-500')

        self.create_command_palette()

    def create_command_palette(self):
        """Creates the global command palette (Ctrl+K)"""
        with ui.dialog().classes('max-w-full') as dialog:
            # Set to 600px width card
            self.cmd_dialog = dialog
            with ui.card().classes('w-[600px] h-[400px] p-0 flex flex-col bg-white overflow-hidden').style('border-radius: 16px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);'):
                with ui.row().classes('w-full items-center p-4 border-b border-gray-100 bg-gray-50/50'):
                    ui.icon('search', size='1.5rem').classes('text-[#7048E8] mr-3')
                    self.cmd_input = ui.input(placeholder='Search modules, actions...').props('borderless autofocus').classes('flex-1 text-lg font-medium')
                    self.cmd_input.on('input', lambda e: self.update_cmd_results(e.value))
                    ui.label('ESC').classes('text-[10px] font-bold text-gray-400 bg-gray-200 px-2 py-1 rounded cursor-pointer').on('click', dialog.close).tooltip('Close')
                
                self.cmd_results_container = ui.column().classes('w-full flex-1 overflow-y-auto p-2 gap-1 bg-white')
        
        # Add global keyboard listener for Ctrl+K
        def handle_key(e):
            if e.key == 'k' and (e.modifiers.ctrl or e.modifiers.meta) and e.action.keydown:
                if self.cmd_dialog.value:
                    self.cmd_dialog.close()
                else:
                    self.cmd_dialog.open()
                    self.cmd_input.set_value('')
                    self.update_cmd_results('')
                
        ui.keyboard(on_key=handle_key)

    def update_cmd_results(self, query):
        self.cmd_results_container.clear()
        results = self.search_pages(query)
        
        with self.cmd_results_container:
            if not query:
                ui.label('Recent Pages').classes('text-xs font-bold text-gray-400 uppercase tracking-wider pl-4 pt-4 pb-2')
                for page_key in self.recent_pages[:5]:
                    page_info = None
                    for cat, data in self.navigation_categories.items():
                        if page_key in data['items']:
                            page_info = data['items'][page_key]
                            break
                    if page_info:
                        self.render_cmd_result(page_key, page_info['label'], page_info['icon'], 'Recent')
            elif not results:
                with ui.column().classes('w-full items-center justify-center p-8 opacity-50'):
                    ui.icon('search_off', size='3rem').classes('text-gray-300 mb-2')
                    ui.label('No matching pages found').classes('text-gray-400 font-medium text-center')
            else:
                ui.label('Navigation').classes('text-xs font-bold text-gray-400 uppercase tracking-wider pl-4 pt-4 pb-2')
                for r in results:
                    self.render_cmd_result(r['key'], r['label'], r['icon'], r['category'])

    def render_cmd_result(self, key, label, icon, category):
        with ui.row().classes('w-full items-center justify-between p-3 hover:bg-purple-50 rounded-xl cursor-pointer transition-all group').on('click', lambda: self.execute_cmd(key)):
            with ui.row().classes('items-center gap-4'):
                with ui.element('div').classes('w-10 h-10 rounded-xl bg-gray-50 flex items-center justify-center group-hover:bg-purple-100 group-hover:text-[#7048E8] border border-gray-100 group-hover:border-purple-200 transition-colors'):
                    ui.icon(icon, size='1.2rem').classes('text-gray-500 group-hover:text-[#7048E8] transition-colors')
                with ui.column().classes('gap-0'):
                    ui.label(label).classes('font-bold text-gray-800 text-sm')
                    ui.label(category).classes('text-[10px] text-gray-400 uppercase tracking-wider mt-0.5')
            
            with ui.row().classes('items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity'):
                ui.label('Open in Tab').classes('text-xs font-bold text-[#7048E8]')
                ui.icon('keyboard_return', size='1rem').classes('text-[#7048E8]')

    def execute_cmd(self, page_key):
        self.cmd_dialog.close()
        self.navigate_to_page(page_key, new_instance=True)


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
                        
                        with ui.row().classes(btn_classes):
                            # Main button for switching/opening (always new instance as requested by user)
                            with ui.row().classes('flex-1 items-center gap-3 py-2 px-3 rounded-lg hover:cursor-pointer').on('click', lambda p=page_key: self.navigate_to_page(p, new_instance=True)):
                                ui.icon(page_data['icon']).classes('drawer-button-icon')
                                ui.label(page_data['label']).classes('drawer-button-label flex-1')
                                if is_active:
                                    ui.element('div').classes('w-1.5 h-1.5 rounded-full bg-white animate-pulse')
                            
                            # Plus button for new instance
                            if self.tabbed_mode:
                                ui.button(icon='open_in_new').props('flat round dense size=xs').classes('text-gray-500 hover:text-white mr-2').on('click', lambda p=page_key: self.navigate_to_page(p, new_instance=True)).tooltip('Open duplicate tab')


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

    def toggle_split_view(self):
        """Toggle split view mode via callback"""
        if self.split_view_callback:
            is_split = self.split_view_callback()
            self.split_btn.props(f'color={"#7048E8" if is_split else "gray-500"}')
            self.split_btn.classes(add='text-[#7048E8]' if is_split else 'text-gray-500', remove='text-gray-500' if is_split else 'text-[#7048E8]')

    def navigate_to_page(self, page_key, new_instance=False):
        """Navigate to a page and update breadcrumbs/recent pages"""
        # Find page data
        for category, data in self.navigation_categories.items():
            if page_key in data['items']:
                page_data = data['items'][page_key]
                self.add_recent_page(page_key, page_data['label'])
                self.current_path = [category, page_data['label']]

                # Special handling for tabbed mode
                if self.tabbed_mode and hasattr(self, 'open_tab_callback') and self.open_tab_callback:
                    self.open_tab_callback(page_key, new_instance=new_instance)
                else:
                    ui.navigate.to(page_data['path'])

                # Hide search dropdown after navigation
                if hasattr(self, 'search_dropdown'):
                    self.search_dropdown.classes(add='hidden')
                break

    def navigate_to_search_result(self, result):
        """Navigate to a search result - always opens a new tab"""
        self.navigate_to_page(result['key'], new_instance=True)

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
