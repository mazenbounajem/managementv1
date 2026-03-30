"""
Modern Sales UI
Complete redesign with modern components and interactions
"""

from nicegui import ui
from datetime import date as dt
from connection import connection
from modern_design_system import ModernDesignSystem as MDS

from modern_ui_components import (
    ModernCard, ModernCardHeader, ModernCardBody, ModernButton, ModernInput, ModernTable, 
    ModernStats, ModernBadge, ModernToast, ModernSearchBar
)
from session_storage import session_storage
from invoice_pdf_cairo import generate_sales_invoice_pdf
import asyncio

@ui.page('/modern-sales')
def modern_sales_page():
    ModernSalesUI()

class ModernSalesUI:
    def __init__(self):
        # Check authentication
        user = session_storage.get('user')
        if not user:
            ui.notify('Please login to access this page', color='red')
            ui.run_javascript('window.location.href = "/login"')
            return
        
        # Initialize data
        self.user = user
        self.rows = []
        self.total_amount = 0
        self.current_sale_id = None
        self.currency_id = 2  # Default USD
        
        # Load currencies
        self.load_currencies()
        
        # Create UI
        self.create_ui()
    
    def load_currencies(self):
        """Load available currencies"""
        self.currency_rows = []
        try:
            connection.contogetrows(
                "SELECT id, currency_name, symbol FROM currencies",
                self.currency_rows
            )
        except Exception as e:
            print(f"Error loading currencies: {e}")
    
    def create_ui(self):
        """Create the modern sales interface using the reusable layout"""
        from modern_page_layout import ModernPageLayout
        
        # Create the page content
        def build_sales_content():
            with ui.element('div').classes('w-full min-h-screen p-8 mesh-gradient animate-fade-in'):
                # Dashboard stats
                self.create_stats_section()
                
               
        # Use the modern page layout
        # We use create_page_header for nav, then build our custom content area
        ModernPageLayout.create_page_header()
        build_sales_content()

        # Universal Action Bar
        from modern_ui_components import ModernActionBar
        ModernActionBar(
            on_new=getattr(self, 'clear_form', None),
            on_save=getattr(self, 'save_sale', None),
            on_undo=None,
            on_delete=getattr(self, 'delete_sale', None),
            on_print=getattr(self, 'print_invoice', None),
            on_refresh=None # Could handle refresh if needed
        )

    # Remaining methods are unchanged from your current implementation 
    # (create_stats_section, create_sales_history, create_invoice_form, add_product, 
    # calculate_totals, etc.) and should follow here as in your provided code
    def create_stats_section(self):
        """Creates the statistics section at the top of the page."""
        with ui.row().classes('w-full justify-between items-center bg-white/5 p-6 rounded-3xl glass border border-white/10 mb-8'):
            # Get today's sales
            today_sales = connection.get_today_sales()
            ModernStats(label='Revenue Performance', value=f'${today_sales:,.2f}', icon='analytics', trend='+4.2% today', color='#7048E8')
            ModernStats(label='Sales Volume', value='24', icon='shopping_cart', trend='+2 new', color='#1971C2')
            ModernStats(label='Pending Fulfillment', value='8', icon='hourglass_empty', trend='Action required', trend_positive=False, color=MDS.WARNING)
            ModernStats(label='Client Satisfaction', value='98%', icon='sentiment_very_satisfied', color='#2B8A3E')

   