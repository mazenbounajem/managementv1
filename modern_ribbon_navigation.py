"""
Modern Ribbon Navigation Component
Microsoft Office-inspired ribbon interface for NiceGUI
"""

from nicegui import ui
from modern_design_system import ModernDesignSystem as MDS

class ModernRibbonNavigation:
    """
    Ribbon-style navigation component with tabs and grouped buttons
    """
    
    def __init__(self, user_info=None):
        self.user_info = user_info or {}
        self.current_tab = 'home'
        self.ribbon_tabs = {}
        self.ribbon_contents = {}
        
    def create_ribbon(self):
        """Create the complete ribbon navigation"""
        with ui.element('div').classes('ribbon-container'):
            # Company header with user info
            self._create_header()
            
            # Ribbon tabs
            self._create_tabs()
            
            # Ribbon content areas
            self._create_content_areas()
    
    def _create_header(self):
        """Create the header with company name and user info"""
        with ui.row().classes('w-full items-center justify-between p-4').style(
            f'background: {MDS.GRADIENT_HEADER}; color: {MDS.WHITE};'
        ):
            # Company name
            ui.label('Complete Business Management System').classes('text-2xl font-bold')
            
            # User info
            with ui.row().classes('items-center gap-4'):
                # User avatar
                with ui.element('div').style(
                    f'width: 40px; height: 40px; border-radius: {MDS.BORDER_RADIUS_FULL}; '
                    f'background: {MDS.ACCENT}; display: flex; align-items: center; '
                    f'justify-content: center; font-weight: {MDS.FONT_WEIGHT_BOLD};'
                ):
                    ui.label(self.user_info.get('initials', 'U')).style('color: white;')
                
                # User name and role
                with ui.column().classes('gap-0'):
                    ui.label(self.user_info.get('name', 'User')).classes('font-semibold')
                    ui.label(self.user_info.get('role', 'Admin')).classes('text-xs opacity-80')
    
    def _create_tabs(self):
        """Create ribbon tabs"""
        with ui.row().classes('ribbon-tabs'):
            tabs_config = [
                ('home', 'Home', '🏠'),
                ('sales', 'Sales', '💰'),
                ('purchases', 'Purchases', '🛒'),
                ('inventory', 'Inventory', '📦'),
                ('customers', 'Customers', '👥'),
                ('accounting', 'Accounting', '📊'),
                ('reports', 'Reports', '📈'),
                ('settings', 'Settings', '⚙️'),
            ]
            
            for tab_id, tab_label, tab_icon in tabs_config:
                tab_btn = ui.button(
                    f'{tab_icon} {tab_label}',
                    on_click=lambda t=tab_id: self._switch_tab(t)
                ).classes('ribbon-tab')
                
                if tab_id == self.current_tab:
                    tab_btn.classes(add='active')
                
                self.ribbon_tabs[tab_id] = tab_btn
    
    def _create_content_areas(self):
        """Create content areas for each tab"""
        # Home Tab
        with ui.element('div').classes('ribbon-content active') as home_content:
            self.ribbon_contents['home'] = home_content
            self._create_home_ribbon()
        
        # Sales Tab
        with ui.element('div').classes('ribbon-content') as sales_content:
            self.ribbon_contents['sales'] = sales_content
            self._create_sales_ribbon()
        
        # Purchases Tab
        with ui.element('div').classes('ribbon-content') as purchases_content:
            self.ribbon_contents['purchases'] = purchases_content
            self._create_purchases_ribbon()
        
        # Inventory Tab
        with ui.element('div').classes('ribbon-content') as inventory_content:
            self.ribbon_contents['inventory'] = inventory_content
            self._create_inventory_ribbon()
        
        # Customers Tab
        with ui.element('div').classes('ribbon-content') as customers_content:
            self.ribbon_contents['customers'] = customers_content
            self._create_customers_ribbon()
        
        # Accounting Tab
        with ui.element('div').classes('ribbon-content') as accounting_content:
            self.ribbon_contents['accounting'] = accounting_content
            self._create_accounting_ribbon()
        
        # Reports Tab
        with ui.element('div').classes('ribbon-content') as reports_content:
            self.ribbon_contents['reports'] = reports_content
            self._create_reports_ribbon()
        
        # Settings Tab
        with ui.element('div').classes('ribbon-content') as settings_content:
            self.ribbon_contents['settings'] = settings_content
            self._create_settings_ribbon()
    
    def _switch_tab(self, tab_id):
        """Switch between ribbon tabs"""
        # Update current tab
        self.current_tab = tab_id
        
        # Update tab buttons
        for tid, tab_btn in self.ribbon_tabs.items():
            if tid == tab_id:
                tab_btn.classes(add='active', remove='')
            else:
                tab_btn.classes(remove='active')
        
        # Update content visibility
        for cid, content in self.ribbon_contents.items():
            if cid == tab_id:
                content.classes(add='active', remove='')
            else:
                content.classes(remove='active')
    
    def _create_ribbon_group(self, label, buttons):
        """Helper to create a ribbon group"""
        with ui.element('div').classes('ribbon-group'):
            ui.label(label).classes('ribbon-group-label')
            with ui.element('div').classes('ribbon-buttons'):
                for btn_config in buttons:
                    self._create_ribbon_button(**btn_config)
    
    def _create_ribbon_button(self, icon, label, action=None, color=None):
        """Helper to create a ribbon button"""
        with ui.button(on_click=action).classes('ribbon-button'):
            ui.icon(icon).classes('ribbon-button-icon').style(
                f'color: {color or MDS.PRIMARY_DARK};'
            )
            ui.label(label).classes('ribbon-button-label')
    
    # ============= TAB CONTENT CREATORS =============
    
    def _create_home_ribbon(self):
        """Create Home tab ribbon content"""
        self._create_ribbon_group('Quick Access', [
            {'icon': 'dashboard', 'label': 'Dashboard', 'action': lambda: ui.navigate.to('/dashboard')},
            {'icon': 'notifications', 'label': 'Notifications', 'action': lambda: ui.notify('Notifications')},
            {'icon': 'search', 'label': 'Search', 'action': lambda: ui.notify('Search')},
        ])
        
        self._create_ribbon_group('Recent', [
            {'icon': 'history', 'label': 'Recent Items', 'action': lambda: ui.notify('Recent Items')},
            {'icon': 'bookmark', 'label': 'Favorites', 'action': lambda: ui.notify('Favorites')},
        ])
    
    def _create_sales_ribbon(self):
        """Create Sales tab ribbon content"""
        self._create_ribbon_group('New', [
            {'icon': 'add_shopping_cart', 'label': 'New Sale', 'action': lambda: ui.navigate.to('/sales'), 'color': MDS.SUCCESS},
            {'icon': 'receipt', 'label': 'New Invoice', 'action': lambda: ui.navigate.to('/sales')},
            {'icon': 'point_of_sale', 'label': 'POS', 'action': lambda: ui.navigate.to('/pos')},
        ])
        
        self._create_ribbon_group('Manage', [
            {'icon': 'list', 'label': 'Sales List', 'action': lambda: ui.navigate.to('/sales')},
            {'icon': 'receipt_long', 'label': 'Invoices', 'action': lambda: ui.navigate.to('/sales')},
            {'icon': 'payments', 'label': 'Payments', 'action': lambda: ui.navigate.to('/customerpayment')},
        ])
        
        self._create_ribbon_group('Reports', [
            {'icon': 'analytics', 'label': 'Sales Report', 'action': lambda: ui.navigate.to('/reports')},
            {'icon': 'trending_up', 'label': 'Performance', 'action': lambda: ui.navigate.to('/reports')},
        ])
    
    def _create_purchases_ribbon(self):
        """Create Purchases tab ribbon content"""
        self._create_ribbon_group('New', [
            {'icon': 'add_circle', 'label': 'New Purchase', 'action': lambda: ui.navigate.to('/purchase'), 'color': MDS.INFO},
            {'icon': 'shopping_cart', 'label': 'Purchase Order', 'action': lambda: ui.navigate.to('/purchase')},
        ])
        
        self._create_ribbon_group('Manage', [
            {'icon': 'list_alt', 'label': 'Purchase List', 'action': lambda: ui.navigate.to('/purchase')},
            {'icon': 'local_shipping', 'label': 'Suppliers', 'action': lambda: ui.navigate.to('/suppliers')},
            {'icon': 'payment', 'label': 'Payments', 'action': lambda: ui.navigate.to('/supplierpayment')},
        ])
        
        self._create_ribbon_group('Reports', [
            {'icon': 'assessment', 'label': 'Purchase Report', 'action': lambda: ui.navigate.to('/reports')},
            {'icon': 'inventory_2', 'label': 'Stock Report', 'action': lambda: ui.navigate.to('/reports')},
        ])
    
    def _create_inventory_ribbon(self):
        """Create Inventory tab ribbon content"""
        self._create_ribbon_group('Products', [
            {'icon': 'add_box', 'label': 'New Product', 'action': lambda: ui.navigate.to('/products'), 'color': MDS.SUCCESS},
            {'icon': 'inventory', 'label': 'Products List', 'action': lambda: ui.navigate.to('/products')},
            {'icon': 'category', 'label': 'Categories', 'action': lambda: ui.navigate.to('/products')},
        ])
        
        self._create_ribbon_group('Stock Operations', [
            {'icon': 'inventory_2', 'label': 'Stock Count', 'action': lambda: ui.navigate.to('/stockoperations')},
            {'icon': 'tune', 'label': 'Adjustment', 'action': lambda: ui.navigate.to('/stockoperations')},
            {'icon': 'warning', 'label': 'Defective', 'action': lambda: ui.navigate.to('/stockoperations')},
        ])
        
        self._create_ribbon_group('Reports', [
            {'icon': 'bar_chart', 'label': 'Stock Report', 'action': lambda: ui.navigate.to('/reports')},
            {'icon': 'low_priority', 'label': 'Low Stock', 'action': lambda: ui.navigate.to('/reports')},
        ])
    
    def _create_customers_ribbon(self):
        """Create Customers tab ribbon content"""
        self._create_ribbon_group('Manage', [
            {'icon': 'person_add', 'label': 'New Customer', 'action': lambda: ui.navigate.to('/customers'), 'color': MDS.SUCCESS},
            {'icon': 'people', 'label': 'Customers List', 'action': lambda: ui.navigate.to('/customers')},
            {'icon': 'business', 'label': 'Suppliers', 'action': lambda: ui.navigate.to('/suppliers')},
        ])
        
        self._create_ribbon_group('Transactions', [
            {'icon': 'receipt', 'label': 'Customer Receipt', 'action': lambda: ui.navigate.to('/customerreceipt')},
            {'icon': 'payment', 'label': 'Payments', 'action': lambda: ui.navigate.to('/customerpayment')},
            {'icon': 'account_balance', 'label': 'Balances', 'action': lambda: ui.navigate.to('/customers')},
        ])
        
        self._create_ribbon_group('Reports', [
            {'icon': 'description', 'label': 'Statement', 'action': lambda: ui.notify('Customer Statement')},
            {'icon': 'analytics', 'label': 'Analysis', 'action': lambda: ui.navigate.to('/reports')},
        ])
    
    def _create_accounting_ribbon(self):
        """Create Accounting tab ribbon content"""
        self._create_ribbon_group('Entries', [
            {'icon': 'book', 'label': 'Journal Entry', 'action': lambda: ui.navigate.to('/journal_voucher'), 'color': MDS.INFO},
            {'icon': 'account_balance_wallet', 'label': 'Cash Drawer', 'action': lambda: ui.navigate.to('/cash-drawer')},
            {'icon': 'receipt_long', 'label': 'Vouchers', 'action': lambda: ui.navigate.to('/voucher_subtype')},
        ])
        
        self._create_ribbon_group('Accounts', [
            {'icon': 'account_tree', 'label': 'Chart of Accounts', 'action': lambda: ui.navigate.to('/auxiliary')},
            {'icon': 'account_balance', 'label': 'Ledger', 'action': lambda: ui.navigate.to('/ledger')},
            {'icon': 'credit_card', 'label': 'Expenses', 'action': lambda: ui.navigate.to('/expenses')},
        ])
        
        self._create_ribbon_group('Reports', [
            {'icon': 'balance', 'label': 'Balance Sheet', 'action': lambda: ui.navigate.to('/reports')},
            {'icon': 'trending_up', 'label': 'P&L Statement', 'action': lambda: ui.navigate.to('/reports')},
            {'icon': 'summarize', 'label': 'Trial Balance', 'action': lambda: ui.navigate.to('/reports')},
        ])
    
    def _create_reports_ribbon(self):
        """Create Reports tab ribbon content"""
        self._create_ribbon_group('Sales Reports', [
            {'icon': 'point_of_sale', 'label': 'Sales Report', 'action': lambda: ui.navigate.to('/reports')},
            {'icon': 'receipt', 'label': 'Invoice Report', 'action': lambda: ui.navigate.to('/reports')},
            {'icon': 'trending_up', 'label': 'Performance', 'action': lambda: ui.navigate.to('/reports')},
        ])
        
        self._create_ribbon_group('Inventory Reports', [
            {'icon': 'inventory', 'label': 'Stock Report', 'action': lambda: ui.navigate.to('/reports')},
            {'icon': 'low_priority', 'label': 'Low Stock', 'action': lambda: ui.navigate.to('/reports')},
            {'icon': 'category', 'label': 'By Category', 'action': lambda: ui.navigate.to('/reports')},
        ])
        
        self._create_ribbon_group('Financial Reports', [
            {'icon': 'account_balance', 'label': 'Financial', 'action': lambda: ui.navigate.to('/reports')},
            {'icon': 'analytics', 'label': 'Analytics', 'action': lambda: ui.navigate.to('/reports')},
            {'icon': 'print', 'label': 'Print All', 'action': lambda: ui.notify('Printing Reports')},
        ])
    
    def _create_settings_ribbon(self):
        """Create Settings tab ribbon content"""
        self._create_ribbon_group('System', [
            {'icon': 'business', 'label': 'Company Info', 'action': lambda: ui.navigate.to('/company')},
            {'icon': 'settings', 'label': 'Preferences', 'action': lambda: ui.notify('Preferences')},
            {'icon': 'language', 'label': 'Language', 'action': lambda: ui.notify('Language Settings')},
        ])
        
        self._create_ribbon_group('Users', [
            {'icon': 'people', 'label': 'Users', 'action': lambda: ui.navigate.to('/employees')},
            {'icon': 'admin_panel_settings', 'label': 'Roles', 'action': lambda: ui.notify('Roles & Permissions')},
            {'icon': 'security', 'label': 'Security', 'action': lambda: ui.notify('Security Settings')},
        ])
        
        self._create_ribbon_group('Data', [
            {'icon': 'backup', 'label': 'Backup', 'action': lambda: ui.notify('Backup Database')},
            {'icon': 'restore', 'label': 'Restore', 'action': lambda: ui.notify('Restore Database')},
            {'icon': 'cloud_upload', 'label': 'Export', 'action': lambda: ui.notify('Export Data')},
        ])


class ModernActionDrawer:
    """
    Modern action drawer for page-specific actions
    """
    
    def __init__(self, actions=None):
        self.actions = actions or []
        self.is_expanded = False
        self.drawer_element = None
    
    def create_drawer(self):
        """Create the action drawer"""
        with ui.element('div').classes('drawer') as drawer:
            self.drawer_element = drawer
            
            # Toggle button
            with ui.button(
                icon='menu',
                on_click=self.toggle_drawer
            ).classes('drawer-button').style('margin-bottom: 2rem;'):
                ui.label('Menu').classes('drawer-button-label')
            
            # Action buttons
            for action in self.actions:
                self._create_action_button(**action)
    
    def toggle_drawer(self):
        """Toggle drawer expanded/collapsed state"""
        self.is_expanded = not self.is_expanded
        if self.is_expanded:
            self.drawer_element.classes(add='expanded')
        else:
            self.drawer_element.classes(remove='expanded')
    
    def _create_action_button(self, icon, label, action=None, color=None, tooltip=None):
        """Create an action button in the drawer"""
        with ui.button(on_click=action).classes('drawer-button').props(f'flat'):
            ui.icon(icon).classes('drawer-button-icon').style(
                f'color: {color or MDS.PRIMARY_LIGHT};'
            )
            ui.label(label).classes('drawer-button-label')
            
            if tooltip:
                ui.tooltip(tooltip)
