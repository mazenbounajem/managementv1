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
                    'sales-returns':   {'label': 'Sales Returns',    'path': '/salesreturn',      'icon': 'assignment_return', 'shortcut': 'Alt+R'},
                    'products':        {'label': 'Products',         'path': '/products',         'icon': 'inventory',     'shortcut': 'Alt+P'},
                    'purchase':        {'label': 'Purchase',         'path': '/purchase',         'icon': 'shopping_bag',  'shortcut': 'Alt+U'},
                    'purchase-returns': {'label': 'Purchase Returns', 'path': '/purchasereturn',   'icon': 'assignment_return', 'shortcut': 'Alt+T'},
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
                    'accounting-transactions': {'label': 'Acct. Transactions', 'path': '/accounting-transactions', 'icon': 'receipt_long', 'shortcut': 'Alt+Z'},
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
                    'business-track': {'label': 'Business Track', 'path': '/business-track', 'icon': 'insights'},
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
                    'backup': {'label': 'Database Backup', 'path': '/settings-backup', 'icon': 'backup', 'shortcut': 'Alt+Z'},
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
            with ui.row().classes('w-full items-center justify-between px-6 py-2 glass shadow-lg').style('border-radius: 0 0 1.5rem 1.5rem; border: 1px solid rgba(255,255,255,0.5);'):
                # Left side - Logo & Path
                with ui.row().classes('items-center gap-4'):
                    # Custom Hamburger Toggle
                    self.toggle_button = ui.button(icon='menu').props('flat round').classes('text-[#08CB00] hover:bg-[#08CB00]/10 transition-all')
                    self.toggle_button.on('click', self.toggle_navigation_drawer)
                    
                    with ui.row().classes('items-center gap-2'):
                        pass
                
                # Dynamic Tabs in the Header
                with ui.row().classes('flex-1 justify-center px-4'):
                    self.tabs_ui = ui.tabs().classes('text-[#08CB00]/70')
                    self.tabs_ui.props('active-color=#ffffff indicator-color=transparent dense')
                
                # Right side - Actions & User (Search moved here for space)
                with ui.row().classes('items-center gap-3'):
                    # Split View Toggle
                    if self.tabbed_mode:
                        self.split_btn = ui.button(icon='vertical_split', on_click=self.toggle_split_view).props('flat round').classes('text-[#08CB00]/60 hover:text-[#08CB00]')
                        self.split_btn.tooltip('Toggle Split View (Side-by-Side)')
                    
                    # Theme Switcher
                    def change_theme(e):
                        theme = e.value
                        themes = {
                            'Midnight': 'mesh-gradient',
                            'Ocean': 'mesh-gradient',
                            'Warm': 'mesh-gradient',
                            'Modern Light': 'bg-gray-50'
                        }
                        cls = themes.get(theme, 'mesh-gradient')
                        ui.run_javascript(f"document.body.className = '{cls}';")
                        ui.notify(f'Theme changed to {theme}', color='info')

                    ui.select(['Midnight', 'Ocean', 'Warm', 'Modern Light'], value='Midnight', on_change=change_theme).props('flat dense options-dark').classes('w-32 glass p-1 rounded-lg text-xs')

                    ui.button(icon='notifications').props('flat round').classes('text-[#08CB00]/60 hover:text-[#08CB00]')
                    
                    # User Menu (existing)
                    with ui.button().props('flat round').classes('p-0 overflow-hidden border-2 border-green-100 hover:border-[#08CB00] transition-all'):
                        ui.image('https://ui-avatars.com/api/?name=' + self.current_user.get("username", "U") + '&background=08CB00&color=fff').classes('w-8 h-8 rounded-full')
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
                    ui.icon('search', size='1.5rem').classes('text-[#08CB00] mr-3')
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
        with ui.row().classes('w-full items-center justify-between p-3 hover:bg-[#08CB00]/10 rounded-xl cursor-pointer transition-all group').on('click', lambda: self.execute_cmd(key)):
            with ui.row().classes('items-center gap-4'):
                with ui.element('div').classes('w-10 h-10 rounded-xl bg-gray-50 flex items-center justify-center group-hover:bg-[#08CB00]/10 group-hover:text-[#08CB00] border border-gray-100 group-hover:border-[#08CB00]/20 transition-colors'):
                    ui.icon(icon, size='1.2rem').classes('text-gray-500 group-hover:text-[#08CB00] transition-colors')
                with ui.column().classes('gap-0'):
                    ui.label(label).classes('font-bold text-gray-800 text-sm')
                    ui.label(category).classes('text-[10px] text-gray-400 uppercase tracking-wider mt-0.5')
            
            with ui.row().classes('items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity'):
                ui.label('Open in Tab').classes('text-xs font-bold text-[#08CB00]')
                ui.icon('keyboard_return', size='1rem').classes('text-[#08CB00]')

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
                    pass

                # Search in drawer
                with ui.row().classes('w-full items-center px-4 py-2 rounded-xl bg-white/5 border border-white/10 hover:border-white/20 transition-all focus-within:border-[#08CB00]/50'):
                    ui.icon('search', size='1rem').classes('text-gray-500')
                    
                    def handle_search(e):
                        self.filter_navigation(e.value)
                        
                    def on_enter(e):
                        # If user presses enter, try to navigate to the first result
                        query = self.drawer_search.value
                        if query:
                            # Use existing logic to find matches
                            allowed_pages = self.get_allowed_pages()
                            results = self.search_pages(query)
                            if results:
                                self.navigate_to_page(results[0]['key'], new_instance=True)

                    self.drawer_search = ui.input(placeholder='Jump to Page...')\
                        .props('borderless dense clearable')\
                        .classes('flex-1 ml-2 text-xs font-bold text-white uppercase tracking-wider')\
                        .on('update:model-value', handle_search)\
                        .on('keydown.enter', on_enter)
                    
                    ui.button(icon='close', on_click=lambda: self.drawer_search.set_value('')).props('flat round dense size=xs').classes('text-white/20 hover:text-white')

                # Navigation content
                self.nav_container = ui.column().classes('w-full gap-2 mt-4 drawer-scroll-container overflow-y-auto')
                with self.nav_container:
                    self.create_navigation_content()


    def create_navigation_content(self, search_filter=""):
        """Create navigation content with categories"""
        allowed_pages = self.get_allowed_pages()
        search_filter = search_filter.lower() if search_filter else ""

        if search_filter:
            # SEARCH RESULTS VIEW (Dedicated results list for better UX)
            self.render_search_results(search_filter, allowed_pages)
        else:
            # CATEGORY TREE VIEW (Standard browsing)
            self.render_category_tree(allowed_pages)

    def render_search_results(self, query, allowed_pages):
        """Render search results across modules and open tabs"""
        ui.label('Search Results').classes('text-[10px] font-black uppercase text-[#08CB00] mb-4 px-4')
        
        # 1. Matching Modules (Tabs that can be opened)
        matches = []
        for category, data in self.navigation_categories.items():
            for page_key, page_data in data['items'].items():
                if page_key in allowed_pages:
                    if query in page_data['label'].lower() or query in page_key.lower() or query in category.lower():
                        matches.append((page_key, page_data, category))
        
        if matches:
            ui.label('Modules').classes('text-[9px] font-bold text-gray-500 mb-2 px-4 uppercase')
            for page_key, page_data, category in matches:
                with ui.row().classes('drawer-button w-full items-center gap-3 py-2 px-3 rounded-lg hover:cursor-pointer animate-fade-in mb-1')\
                    .on('click', lambda p=page_key: self.navigate_to_page(p, new_instance=True)):
                    ui.icon(page_data['icon']).classes('drawer-button-icon')
                    with ui.column().classes('gap-0 flex-1'):
                        ui.label(page_data['label']).classes('drawer-button-label text-white leading-none')
                        ui.label(category).classes('text-[8px] text-gray-500 uppercase tracking-tighter mt-1')
                    ui.icon('add_circle', size='xs').classes('text-[#08CB00]/30 hover:text-[#08CB00]')
        
        # 2. Matching Open Tabs (Currently running instances)
        if self.tabbed_mode:
            tab_matches = [k for k in self.open_tabs.keys() if query in k.lower()]
            if tab_matches:
                if matches: ui.separator().classes('my-4 opacity-10')
                ui.label('Open Tab Instances').classes('text-[9px] font-bold text-[#08CB00] mb-2 px-4 uppercase')
                for tab_key in tab_matches:
                    with ui.row().classes('drawer-button w-full items-center gap-3 py-2 px-3 rounded-lg hover:cursor-pointer animate-fade-in mb-1')\
                        .on('click', lambda k=tab_key: self.navigate_to_page(k, new_instance=False)):
                        ui.icon('tab').classes('drawer-button-icon text-[#08CB00]')
                        ui.label(tab_key.replace('_', ' #').title()).classes('drawer-button-label flex-1 text-white')
                        ui.badge('Active', color='#08CB00').props('text-color=black size=xs')

        if not matches and (not self.tabbed_mode or not tab_matches):
            with ui.column().classes('w-full items-center justify-center p-8 opacity-40'):
                ui.icon('search_off', size='3rem').classes('text-gray-300 mb-2 text-center')
                ui.label('No matching pages found').classes('text-gray-400 text-xs text-center mt-2')

    def render_category_tree(self, allowed_pages):
        """Render the full category tree as a collapsible accordion"""
        for category, data in self.navigation_categories.items():
            category_items = [(k, v) for k, v in data['items'].items() if k in allowed_pages]

            if category_items:
                # Determine if this category should be expanded by default (if active page is inside)
                should_expand = any(v['path'] == self.active_path for k, v in category_items)
                
                with ui.expansion(category, icon=data.get('icon', 'folder'), value=should_expand).classes('w-full expansion-nav'):
                    # Customize expansion header styling via CSS or props
                    # Note: We styling the expansion component in modern_design_system or global CSS
                    
                    with ui.column().classes('w-full gap-1 pl-4 pb-2'):
                        for page_key, page_data in category_items:
                            is_active = (page_data['path'] == self.active_path)
                            btn_classes = 'drawer-button w-full ' + ('active ' if is_active else '')
                            
                            with ui.row().classes(btn_classes):
                                with ui.row().classes('flex-1 items-center gap-3 py-2 px-3 rounded-lg hover:cursor-pointer')\
                                    .on('click', lambda p=page_key: self.navigate_to_page(p, new_instance=True)):
                                    ui.icon(page_data['icon']).classes('drawer-button-icon')
                                    ui.label(page_data['label']).classes('drawer-button-label flex-1')
                                    if is_active:
                                        ui.element('div').classes('w-1.5 h-1.5 rounded-full bg-white animate-pulse')

                                if self.tabbed_mode:
                                    ui.button(icon='open_in_new').props('flat round dense size=xs').classes('text-gray-500 hover:text-white mr-2')\
                                        .on('click', lambda p=page_key: self.navigate_to_page(p, new_instance=True)).tooltip('Open duplicate tab')


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
            self.split_btn.props(f'color={"#08CB00" if is_split else "gray-500"}')
            self.split_btn.classes(add='text-[#08CB00]' if is_split else 'text-gray-500', remove='text-gray-500' if is_split else 'text-[#08CB00]')

    def navigate_to_page(self, page_key, new_instance=False):
        """Navigate to a page and update breadcrumbs/recent pages"""
        # Determine base module key (e.g., 'sales' from 'sales_1')
        base_key = page_key.split('_')[0] if '_' in page_key else page_key
        
        # Find page data using the base key
        page_data = None
        current_category = None
        for category, data in self.navigation_categories.items():
            if base_key in data['items']:
                page_data = data['items'][base_key]
                current_category = category
                break
        
        if page_data:
            self.add_recent_page(base_key, page_data['label'])
            self.current_path = [current_category, page_data['label']]

            # Special handling for tabbed mode
            if self.tabbed_mode and hasattr(self, 'open_tab_callback') and self.open_tab_callback:
                self.open_tab_callback(page_key, new_instance=new_instance)
            else:
                ui.navigate.to(page_data['path'])

            # Hide search dropdown after navigation
            if hasattr(self, 'search_dropdown'):
                self.search_dropdown.classes(add='hidden')
        elif self.tabbed_mode and (page_key in self.open_tabs or '_' in page_key):
            # Fallback for instance keys if not found in categories (shouldn't happen for base modules)
            if hasattr(self, 'open_tab_callback') and self.open_tab_callback:
                self.open_tab_callback(page_key, new_instance=new_instance)

    def navigate_to_search_result(self, result):
        """Navigate to a search result - always opens a new tab"""
        self.navigate_to_page(result['key'], new_instance=True)

    def open_report(self, page_key):
        """Open reports module filtered or specific to the module"""
        ui.notify(f'Opening specialized reports for {page_key}...', color='info')
        self.navigate_to_page('reports', new_instance=True)

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
