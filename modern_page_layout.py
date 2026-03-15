"""
Modern Page Layout - Reusable page layout for all pages.
Provides a consistent single navigation (header + collapsible drawer)
across the entire application.
"""

from nicegui import ui
from connection import connection
from modern_design_system import ModernDesignSystem as MDS
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage

class ModernPageLayout:
    """
    Reusable page layout with header + collapsible sidebar navigation.
    Use this on every page to maintain consistent navigation.
    """
    
    def __init__(self, title="Management System"):
        self.title = title
        self.container = None

    def __enter__(self):
        # Create header and drawer navigation
        if not self.create_page_header():
            return self
        
        # Create content area
        self.container = ui.column().classes('w-full p-6 overflow-y-auto min-h-screen').style(
            'background: var(--bg-main); background-attachment: fixed;'
        )
        self.container.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.container:
            self.container.__exit__(exc_type, exc_val, exc_tb)

    @staticmethod
    def create_page_header():
        """
        Creates the standard page header with:
        - Top header bar (hamburger, logo, search, home button, user menu)
        - Collapsible left drawer with categorised navigation items

        Call this at the start of every page.
        Returns False and redirects to /login if user is not authenticated.
        """
        # Get current user
        user = session_storage.get('user')
        if not user:
            ui.notify('Please login to access this page', color='red')
            ui.navigate.to('/login')
            return False
        
        # Add global styles
        ui.add_head_html(MDS.get_global_styles())
        
        # Get user permissions
        permissions = connection.get_user_permissions(user['role_id'])
        
        # Create header and collapsible sidebar drawer (single navigation system)
        navigation = EnhancedNavigation(permissions, user)
        navigation.create_navigation_header()
        navigation.create_navigation_drawer()
        
        return True
    
    @staticmethod
    def create_page_content(content_builder):
        """
        Creates the main content area for the page
        
        Args:
            content_builder: A function that builds the page content
        
        Usage:
            def build_my_content():
                ui.label('My Page Content')
                # ... more content
            
            ModernPageLayout.create_page_content(build_my_content)
        """
        with ui.column().classes('w-full p-6 overflow-y-auto min-h-screen').style(
            'background: var(--bg-main); background-attachment: fixed;'
        ):
            content_builder()

    
    @staticmethod
    def create_full_page(content_builder):
        """
        Creates a complete page with header (nav drawer) and content
        
        Args:
            content_builder: A function that builds the page content
        
        Usage:
            def build_my_page():
                ui.label('My Page Title').classes('text-2xl font-bold mb-4')
                # ... more content
            
            if ModernPageLayout.create_full_page(build_my_page):
                # Page created successfully
                pass
        """
        # Create header and drawer navigation
        if not ModernPageLayout.create_page_header():
            return False
        
        # Create content area
        ModernPageLayout.create_page_content(content_builder)
        
        return True
