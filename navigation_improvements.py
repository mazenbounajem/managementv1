"""
Enhanced Navigation System for POS Management
Features: Organized categories, search, breadcrumbs, recent pages, keyboard shortcuts
"""

from nicegui import ui

ui.add_css('''
    body {
        border: 5px solid black;
    }
    .q-page-container {
        border: 5px solid blue;
    }
''')
import json
from datetime import datetime
import os

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
        self.setup_navigation_data()

    def setup_navigation_data(self):
        """Setup navigation structure with categories and icons"""
        self.navigation_categories = {
            'Dashboard': {
                'icon': 'dashboard',
                'items': {
                    'dashboard': {'label': 'Home', 'path': '/dashboard', 'icon': 'home', 'shortcut': 'Alt+H'},
                    'timespend': {'label': 'Time Spend Analysis', 'path': '/timespend', 'icon': 'schedule', 'shortcut': 'Alt+T'}
                }
            },
            'Sales & Inventory': {
                'icon': 'shopping_cart',
                'items': {
                    'sales': {'label': 'Sales', 'path': '/sales', 'icon': 'point_of_sale', 'shortcut': 'Alt+S'},
                    'products': {'label': 'Products', 'path': '/products', 'icon': 'inventory', 'shortcut': 'Alt+P'},
                    'purchase': {'label': 'Purchase', 'path': '/purchase', 'icon': 'shopping_bag', 'shortcut': 'Alt+U'},
                    'stockoperations': {'label': 'Stock Operations', 'path': '/stockoperations', 'icon': 'inventory_2', 'shortcut': 'Alt+K'},
                    'category': {'label': 'Category', 'path': '/category', 'icon': 'category', 'shortcut': 'Alt+C'}
                }
            },
            'Customers & Suppliers': {
                'icon': 'people',
                'items': {
                    'customers': {'label': 'Customers', 'path': '/customers', 'icon': 'person', 'shortcut': 'Alt+M'},
                    'customerreceipt': {'label': 'Customer Receipt', 'path': '/customerreceipt', 'icon': 'receipt', 'shortcut': 'Alt+R'},
                    'suppliers': {'label': 'Suppliers', 'path': '/suppliers', 'icon': 'business', 'shortcut': 'Alt+L'},
                    'supplierpayment': {'label': 'Supplier Payment', 'path': '/supplierpayment', 'icon': 'payment', 'shortcut': 'Alt+Y'}
                }
            },
            'Finance': {
                'icon': 'account_balance',
                'items': {
                    'expenses': {'label': 'Expenses', 'path': '/expenses', 'icon': 'money_off', 'shortcut': 'Alt+E'},
                    'expensestype': {'label': 'Expense Types', 'path': '/expensestype', 'icon': 'category', 'shortcut': 'Alt+X'},
                    'currencies': {'label': 'Currencies', 'path': '/currencies', 'icon': 'currency_exchange', 'shortcut': 'Alt+U'},
                    'accounting': {'label': 'Accounting & Finance', 'path': '/accounting', 'icon': 'account_balance', 'shortcut': 'Alt+A'},
                    'cash-drawer': {'label': 'Cash Drawer', 'path': '/cash-drawer', 'icon': 'account_balance_wallet', 'shortcut': 'Alt+D'},
                    'ledger': {'label': 'Ledger', 'path': '/ledger', 'icon': 'account_balance', 'shortcut': 'Alt+L'},
                    'auxiliary': {'label': 'Auxiliary', 'path': '/auxiliary', 'icon': 'account_balance', 'shortcut': 'Alt+Aux'}
                }
            },
            'Administration': {
                'icon': 'admin_panel_settings',
                'items': {
                    'employees': {'label': 'Employees', 'path': '/employees', 'icon': 'badge', 'shortcut': 'Alt+O'},
                    'company': {'label': 'Company', 'path': '/company', 'icon': 'business_center', 'shortcut': 'Alt+B'},
                    'roles': {'label': 'Roles', 'path': '/roles', 'icon': 'group', 'shortcut': 'Alt+G'},
                    'appointments': {'label': 'Appointments', 'path': '/appointments', 'icon': 'event', 'shortcut': 'Alt+N'},
                    'services': {'label': 'Services', 'path': '/services', 'icon': 'build', 'shortcut': 'Alt+V'}
                }
            },
            'Reports': {
                'icon': 'analytics',
                'items': {
                    'reports': {'label': 'Reports', 'path': '/reports', 'icon': 'analytics', 'shortcut': 'Alt+R'},
                    'statistical-reports': {'label': 'Statistical Reports', 'path': '/statistical-reports', 'icon': 'bar_chart', 'shortcut': 'Alt+S'}
                }
            },
            'System': {
                'icon': 'settings',
                'items': {
                    'backup': {'label': 'Database Backup', 'path': '/tabbed-dashboard', 'icon': 'backup', 'shortcut': 'Alt+K'}
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
        """Create enhanced navigation header"""
        with ui.header().classes('bg-white shadow-sm border-b'):
            with ui.row().classes('w-full items-center justify-between px-4'):

                # Left side - Toggle button, Logo and breadcrumbs
                with ui.row().classes('items-center gap-4'):
                    # Toggle button for navigation drawer
                    self.toggle_button = ui.button('', icon='menu').classes('text-gray-600 hover:text-gray-800').props('flat round')
                    self.toggle_button.on('click', self.toggle_navigation_drawer)

                    ui.icon('store').classes('text-2xl text-blue-600')
                    ui.label('POS System').classes('text-xl font-bold text-gray-800')

                    # Breadcrumbs
                    if self.current_path:
                        with ui.row().classes('items-center gap-2 ml-4'):
                            ui.icon('chevron_right').classes('text-gray-400 text-sm')
                            for i, crumb in enumerate(self.current_path):
                                if i > 0:
                                    ui.icon('chevron_right').classes('text-gray-400 text-sm')
                                ui.label(crumb).classes('text-sm text-gray-600')

                # Center - Search bar
                with ui.row().classes('flex-1 justify-center max-w-md relative'):
                    search_input = ui.input(placeholder='Search pages...').classes('w-full')
                    search_input.on('input', lambda e: self.update_search_results(e.value))

                    # Search results dropdown
                    self.search_dropdown = ui.column().classes('absolute top-full left-0 right-0 bg-white border border-gray-300 rounded-b shadow-lg z-50 max-h-64 overflow-y-auto hidden')

                # Right side - User info and actions
                with ui.row().classes('items-center gap-4'):
                    # Dashboard Home button
                    ui.button('Home', icon='home', on_click=lambda: self.navigate_to_page('dashboard')).props('flat').classes('text-blue-600')

                    # Recent pages dropdown
                    with ui.dropdown_button('Recent', icon='history').props('flat'):
                        if self.recent_pages:
                            for page in self.recent_pages[:5]:
                                ui.menu_item(page['label'], lambda p=page: self.navigate_to_page(p['key']))
                        else:
                            ui.menu_item('No recent pages', lambda: None).props('disabled')

                    # User menu
                    with ui.dropdown_button(f'Welcome, {self.current_user.get("username", "User")}', icon='person').props('flat'):
                        ui.menu_item('Profile', lambda: self.navigate_to_page('profile'))
                        ui.menu_item('Settings', lambda: self.navigate_to_page('settings'))
                        ui.menu_item('Logout', lambda: ui.navigate.to('/logout'))

                    # Add Appointments link if user has permission
                    if 'appointments' in self.get_allowed_pages():
                        ui.link('Appointments', '/appointments').classes('text-blue-600 hover:text-blue-800 ml-4')

    def create_navigation_drawer(self):
        """Create enhanced navigation drawer with categories"""
        with ui.left_drawer(value=False).classes('bg-gray-50 border-r').props('width=280') as drawer:
            self.drawer = drawer

            # Search in drawer
            with ui.row().classes('p-4 border-b'):
                ui.icon('search').classes('text-gray-400')
                self.drawer_search = ui.input(placeholder='Search navigation...').classes('flex-1 ml-2')
                self.drawer_search.on('input', lambda e: self.filter_navigation(e.value))

            # Navigation content
            with ui.column().classes('p-2'):
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
                # Category header
                with ui.expansion(category, icon=data['icon']).classes('w-full mb-1') as expansion:
                    expansion.props('header-class=text-sm font-semibold')

                    # Category items
                    for page_key, page_data in category_items:
                        with ui.row().classes('items-center p-2 rounded hover:bg-blue-50 cursor-pointer w-full').on('click', lambda p=page_key: self.navigate_to_page(p)):
                            ui.icon(page_data['icon']).classes('text-blue-600 mr-3')
                            with ui.column().classes('flex-1'):
                                ui.label(page_data['label']).classes('text-sm font-medium')
                                if 'shortcut' in page_data:
                                    ui.label(f'Shortcut: {page_data["shortcut"]}').classes('text-xs text-gray-500')

    def filter_navigation(self, query):
        """Filter navigation based on search query"""
        # Clear current content
        self.drawer.clear()

        # Recreate with filter
        with self.drawer:
            with ui.row().classes('p-4 border-b'):
                ui.icon('search').classes('text-gray-400')
                self.drawer_search = ui.input(placeholder='Search navigation...', value=query).classes('flex-1 ml-2')
                self.drawer_search.on('input', lambda e: self.filter_navigation(e.value))

            with ui.column().classes('p-2'):
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
