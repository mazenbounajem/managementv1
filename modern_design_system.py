"""
Modern Design System for Management System
Inspired by Microsoft Office Ribbon UI with enhanced components
"""

class ModernDesignSystem:
    """
    Complete modern design system with ribbon interface
    """
    
    # ============= COLOR PALETTE =============
    # Primary Colors (keeping existing palette but enhanced)
    PRIMARY_DARK = "#404041"
    PRIMARY_LIGHT = "#f6ede3"
    SECONDARY = "#d3cae2"
    ACCENT = "#e6c17a"
    
    # Extended Color Shades
    PRIMARY_DARK_LIGHT = "#5a5a5b"
    PRIMARY_DARK_LIGHTER = "#707071"
    PRIMARY_LIGHT_DARK = "#e8dfd1"
    PRIMARY_LIGHT_DARKER = "#d9cfbe"
    SECONDARY_LIGHT = "#e0d7ed"
    SECONDARY_DARK = "#c0b5d5"
    ACCENT_LIGHT = "#f0d49a"
    ACCENT_DARK = "#dcb05a"
    
    # Semantic Colors
    SUCCESS = "#4CAF50"
    SUCCESS_LIGHT = "#81C784"
    SUCCESS_DARK = "#388E3C"
    
    WARNING = "#FF9800"
    WARNING_LIGHT = "#FFB74D"
    WARNING_DARK = "#F57C00"
    
    ERROR = "#F44336"
    ERROR_LIGHT = "#E57373"
    ERROR_DARK = "#D32F2F"
    
    INFO = "#2196F3"
    INFO_LIGHT = "#64B5F6"
    INFO_DARK = "#1976D2"
    
    # Neutral Colors
    WHITE = "#FFFFFF"
    BLACK = "#000000"
    GRAY_50 = "#FAFAFA"
    GRAY_100 = "#F5F5F5"
    GRAY_200 = "#EEEEEE"
    GRAY_300 = "#E0E0E0"
    GRAY_400 = "#BDBDBD"
    GRAY_500 = "#9E9E9E"
    GRAY_600 = "#757575"
    GRAY_700 = "#616161"
    GRAY_800 = "#424242"
    GRAY_900 = "#212121"
    
    # Gradients
    GRADIENT_PRIMARY = f"linear-gradient(135deg, {PRIMARY_DARK} 0%, {PRIMARY_DARK_LIGHT} 100%)"
    GRADIENT_ACCENT = f"linear-gradient(135deg, {ACCENT} 0%, {ACCENT_LIGHT} 100%)"
    GRADIENT_SUCCESS = f"linear-gradient(135deg, {SUCCESS} 0%, {SUCCESS_LIGHT} 100%)"
    GRADIENT_HEADER = f"linear-gradient(135deg, {PRIMARY_DARK} 0%, {SECONDARY_DARK} 100%)"
    
    # ============= TYPOGRAPHY =============
    FONT_FAMILY = "'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif"
    FONT_FAMILY_MONO = "'Consolas', 'Monaco', 'Courier New', monospace"
    
    # Font Sizes
    FONT_SIZE_TINY = "0.625rem"      # 10px
    FONT_SIZE_SMALL = "0.75rem"      # 12px
    FONT_SIZE_BASE = "0.875rem"      # 14px
    FONT_SIZE_MEDIUM = "1rem"        # 16px
    FONT_SIZE_LARGE = "1.125rem"     # 18px
    FONT_SIZE_XL = "1.25rem"         # 20px
    FONT_SIZE_2XL = "1.5rem"         # 24px
    FONT_SIZE_3XL = "2rem"           # 32px
    FONT_SIZE_4XL = "2.5rem"         # 40px
    
    # Font Weights
    FONT_WEIGHT_LIGHT = "300"
    FONT_WEIGHT_NORMAL = "400"
    FONT_WEIGHT_MEDIUM = "500"
    FONT_WEIGHT_SEMIBOLD = "600"
    FONT_WEIGHT_BOLD = "700"
    FONT_WEIGHT_EXTRABOLD = "800"
    
    # Line Heights
    LINE_HEIGHT_TIGHT = "1.2"
    LINE_HEIGHT_NORMAL = "1.5"
    LINE_HEIGHT_RELAXED = "1.75"
    
    # ============= SPACING =============
    SPACE_0 = "0"
    SPACE_1 = "0.25rem"    # 4px
    SPACE_2 = "0.5rem"     # 8px
    SPACE_3 = "0.75rem"    # 12px
    SPACE_4 = "1rem"       # 16px
    SPACE_5 = "1.25rem"    # 20px
    SPACE_6 = "1.5rem"     # 24px
    SPACE_8 = "2rem"       # 32px
    SPACE_10 = "2.5rem"    # 40px
    SPACE_12 = "3rem"      # 48px
    SPACE_16 = "4rem"      # 64px
    SPACE_20 = "5rem"      # 80px
    
    # ============= BORDERS =============
    BORDER_RADIUS_NONE = "0"
    BORDER_RADIUS_SM = "0.25rem"    # 4px
    BORDER_RADIUS_MD = "0.375rem"   # 6px
    BORDER_RADIUS_LG = "0.5rem"     # 8px
    BORDER_RADIUS_XL = "0.75rem"    # 12px
    BORDER_RADIUS_2XL = "1rem"      # 16px
    BORDER_RADIUS_FULL = "9999px"
    
    BORDER_WIDTH_THIN = "1px"
    BORDER_WIDTH_MEDIUM = "2px"
    BORDER_WIDTH_THICK = "4px"
    
    # ============= SHADOWS =============
    SHADOW_NONE = "none"
    SHADOW_SM = "0 1px 2px 0 rgba(0, 0, 0, 0.05)"
    SHADOW_MD = "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)"
    SHADOW_LG = "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)"
    SHADOW_XL = "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)"
    SHADOW_2XL = "0 25px 50px -12px rgba(0, 0, 0, 0.25)"
    SHADOW_INNER = "inset 0 2px 4px 0 rgba(0, 0, 0, 0.06)"
    
    # ============= TRANSITIONS =============
    TRANSITION_FAST = "150ms"
    TRANSITION_BASE = "200ms"
    TRANSITION_SLOW = "300ms"
    TRANSITION_SLOWER = "500ms"
    
    TRANSITION_ALL = f"all {TRANSITION_BASE} ease-in-out"
    TRANSITION_COLORS = f"color {TRANSITION_BASE} ease-in-out, background-color {TRANSITION_BASE} ease-in-out, border-color {TRANSITION_BASE} ease-in-out"
    TRANSITION_TRANSFORM = f"transform {TRANSITION_BASE} ease-in-out"
    
    # ============= Z-INDEX LAYERS =============
    Z_INDEX_DROPDOWN = "1000"
    Z_INDEX_STICKY = "1020"
    Z_INDEX_FIXED = "1030"
    Z_INDEX_MODAL_BACKDROP = "1040"
    Z_INDEX_MODAL = "1050"
    Z_INDEX_POPOVER = "1060"
    Z_INDEX_TOOLTIP = "1070"
    
    # ============= RIBBON SPECIFIC =============
    RIBBON_HEIGHT = "120px"
    RIBBON_TAB_HEIGHT = "32px"
    RIBBON_CONTENT_HEIGHT = "88px"
    RIBBON_GROUP_MIN_WIDTH = "100px"
    
    # ============= DRAWER SPECIFIC =============
    DRAWER_WIDTH_COLLAPSED = "64px"
    DRAWER_WIDTH_EXPANDED = "240px"
    DRAWER_ICON_SIZE = "24px"
    
    @classmethod
    def get_ag_grid_default_def(cls):
        """Returns the default column definition for AG Grid"""
        return {
            'sortable': True,
            'filter': True,
            'resizable': True,
            'flex': 1,
            'minWidth': 100
        }

    @classmethod
    def get_global_styles(cls):
        """Returns global CSS styles for the application with Premium Dark Mode and Glassmorphism"""
        return f"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;600;700;900&display=swap');

            :root {{
                /* Premium Palette - Light Mode */
                --primary-dark: {cls.PRIMARY_DARK};
                --primary-light: {cls.PRIMARY_LIGHT};
                --secondary: {cls.SECONDARY};
                --accent: {cls.ACCENT};
                --accent-dark: {cls.ACCENT_DARK};
                
                --bg-main: #f8fafc;
                --bg-card: rgba(255, 255, 255, 0.7);
                --text-main: #1e293b;
                --text-muted: #64748b;
                --border-color: rgba(226, 232, 240, 0.8);
                
                --glass-bg: rgba(255, 255, 255, 0.4);
                --glass-border: rgba(255, 255, 255, 0.5);
                --glass-shadow: rgba(0, 0, 0, 0.05);
                
                --gradient-premium: radial-gradient(at 0% 0%, hsla(253,16%,7%,1) 0, transparent 50%), 
                                   radial-gradient(at 50% 0%, hsla(225,39%,30%,1) 0, transparent 50%), 
                                   radial-gradient(at 100% 0%, hsla(339,49%,30%,1) 0, transparent 50%);
            }}

            @media (prefers-color-scheme: dark) {{
                :root {{
                    --bg-main: #0f172a;
                    --bg-card: rgba(30, 41, 59, 0.7);
                    --text-main: #f1f5f9;
                    --text-muted: #94a3b8;
                    --border-color: rgba(51, 65, 85, 0.8);
                    
                    --primary-dark: #f1f5f9;
                    --glass-bg: rgba(15, 23, 42, 0.6);
                    --glass-border: rgba(255, 255, 255, 0.1);
                    --glass-shadow: rgba(0, 0, 0, 0.3);
                }}
            }}

            /* ============= GLOBAL RESET ============= */
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            html, body {{
                height: 100%;
                font-family: 'Inter', sans-serif;
                font-size: 16px;
                line-height: {cls.LINE_HEIGHT_NORMAL};
                color: var(--text-main);
                background-color: var(--bg-main);
                -webkit-font-smoothing: antialiased;
            }}

            h1, h2, h3, .heading-premium {{
                font-family: 'Outfit', sans-serif;
            }}

            /* ============= PREMIUM EFFECTS ============= */
            .glass {{
                background: var(--glass-bg);
                backdrop-filter: blur(12px) saturate(180%);
                -webkit-backdrop-filter: blur(12px) saturate(180%);
                border: 1px solid var(--glass-border);
                box-shadow: 0 8px 32px 0 var(--glass-shadow);
            }}

            .mesh-gradient {{
                background-color: hsla(225, 39%, 30%, 1);
                background-image: var(--gradient-premium);
                background-attachment: fixed;
            }}

            .hover-lift {{
                transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.3s ease;
            }}

            .hover-lift:hover {{
                transform: translateY(-5px) scale(1.01);
                box-shadow: 0 12px 40px rgba(0, 0, 0, 0.12);
            }}

            /* ============= NICHGUI OVERRIDES ============= */
            .q-card {{
                background: var(--bg-card) !important;
                color: var(--text-main) !important;
                border-radius: 16px !important;
                border: 1px solid var(--border-color);
            }}

            /* ============= COMPONENT STYLES ============= */
            .card-header {{
                font-family: 'Outfit', sans-serif;
                font-size: 1.25rem;
                font-weight: 700;
                letter-spacing: -0.02em;
                color: var(--text-main);
                margin-bottom: 1rem;
            }}

            .input-field {{
                background: var(--bg-card) !important;
                border-radius: 12px !important;
            }}
            
            .q-field--outlined .q-field__control {{
                border-radius: 12px !important;
            }}

            .btn {{
                border-radius: 12px !important;
                text-transform: none !important;
                font-weight: 600 !important;
                letter-spacing: 0.2px;
                transition: all 0.2s ease !important;
            }}

            .btn-primary {{
                background: {cls.ACCENT} !important;
                color: {cls.PRIMARY_DARK} !important;
            }}

            .btn-primary:hover {{
                filter: brightness(1.1);
                box-shadow: 0 4px 15px rgba(230, 193, 122, 0.4) !important;
            }}

            /* ============= ANIMATIONS ============= */
            @keyframes fadeIn {{
                from {{ opacity: 0; transform: translateY(10px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}
            
            .animate-fade-in {{
                animation: fadeIn 0.6s cubic-bezier(0.22, 1, 0.36, 1) forwards;
            }}

            /* ============= DRAWER STYLES ============= */
            .drawer {{
                background: rgba(15, 23, 42, 0.8) !important;
                backdrop-filter: blur(20px);
                border-right: 1px solid rgba(255, 255, 255, 0.1);
            }}

            .q-drawer {{
                background: rgba(15, 23, 42, 0.8) !important;
            }}

            .drawer-button {{
                display: flex;
                align-items: center;
                padding: 0.75rem 1rem;
                margin: 0.25rem 0.5rem;
                border-radius: 12px;
                cursor: pointer;
                transition: all 0.2s ease;
                color: #94a3b8;
                gap: 1rem;
            }}

            .drawer-button:hover {{
                background: rgba(255, 255, 255, 0.05);
                color: white;
            }}

            .drawer-button.active {{
                background: linear-gradient(135deg, #7048E8 0%, #4c2fb3 100%);
                color: white;
                box-shadow: 0 4px 15px rgba(112, 72, 232, 0.3);
            }}

            .drawer-button-icon {{
                font-size: 1.25rem;
            }}

            .drawer-button-label {{
                font-size: 0.875rem;
                font-weight: 600;
                letter-spacing: 0.01em;
            }}

            /* ============= AG-GRID PREMIUM OVERRIDES ============= */
            .ag-theme-quartz-dark, .ag-theme-quartz-custom {{
                --ag-background-color: transparent !important;
                --ag-header-background-color: rgba(255, 255, 255, 0.05) !important;
                --ag-row-hover-color: rgba(255, 255, 255, 0.05) !important;
                --ag-selected-row-background-color: rgba(112, 72, 232, 0.2) !important;
                --ag-odd-row-background-color: transparent !important;
                --ag-border-color: rgba(255, 255, 255, 0.1) !important;
                --ag-foreground-color: #f1f5f9 !important;
                --ag-header-foreground-color: #94a3b8 !important;
                --ag-header-cell-hover-background-color: rgba(255, 255, 255, 0.1) !important;
                --ag-header-cell-moving-background-color: #7048E8 !important;
                border: none !important;
            }}

            .ag-theme-quartz-custom .ag-header, 
            .ag-theme-quartz-custom .ag-row,
            .ag-theme-quartz-custom .ag-cell {{
                background-color: transparent !important;
                color: #f1f5f9 !important;
                border: none !important;
            }}

            /* ============= LEGACY COMPATIBILITY OVERRIDES ============= */
            .bg-\[\#f6ede3\] {{ background-color: #0f172a !important; }}
            .text-\[\#404041\] {{ color: #f1f5f9 !important; }}
            .bg-\[\#d3cae2\] {{ background-color: rgba(30, 41, 59, 0.5) !important; }}
            .border-\[\#404041\] {{ border-color: rgba(255, 255, 255, 0.1) !important; }}
            
            /* High contrast for white-on-white text issues */
            .text-white {{ color: #ffffff !important; }}
            .q-table__card {{ background: var(--bg-card) !important; color: var(--text-main) !important; }}
            .q-table th {{ color: var(--accent) !important; }}
            .q-table td {{ color: var(--text-main) !important; }}

            /* Fix for input text visibility in whole software */
            .q-input input, .q-field__native, .q-field__prefix, .q-field__suffix, .q-field__native span {{
                color: #f1f5f9 !important;
                -webkit-text-fill-color: #f1f5f9 !important;
            }}

            /* Ensure placeholder is visible */
            .q-placeholder, .q-field__label {{
                color: #94a3b8 !important;
            }}

            /* Dropdown boxes visibility */
            .q-select .q-field__native {{
                color: #f1f5f9 !important;
            }}
            .q-menu {{
                background-color: #1e293b !important;
                color: #f1f5f9 !important;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}

            /* ============= SCROLLBAR ============= */
            ::-webkit-scrollbar {{
                width: 8px;
            }}
            ::-webkit-scrollbar-track {{
                background: transparent;
            }}
            ::-webkit-scrollbar-thumb {{
                background: var(--border-color);
                border-radius: 10px;
            }}
            ::-webkit-scrollbar-thumb:hover {{
                background: var(--text-muted);
            }}
        </style>
        """
