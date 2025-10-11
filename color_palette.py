"""
Centralized Color Palette Configuration
Color Scheme: #d3cae2 #e6c17a #f6ede3 #404041
"""

class ColorPalette:
    """
    Centralized color palette for the management system
    """
    
    # Main color palette
    PRIMARY_DARK = "#404041"      # Dark gray - for headers, primary text
    PRIMARY_LIGHT = "#f6ede3"     # Cream - for main backgrounds
    SECONDARY = "#d3cae2"         # Light purple - for alternating rows, secondary elements
    ACCENT = "#e6c17a"            # Golden yellow - for selections, hover states, highlights
    
    # Semantic color assignments
    HEADER_BG = PRIMARY_DARK
    HEADER_TEXT = PRIMARY_LIGHT
    
    MAIN_BG = PRIMARY_LIGHT
    MAIN_TEXT = PRIMARY_DARK
    
    ROW_ODD = SECONDARY
    ROW_EVEN = PRIMARY_LIGHT
    
    SELECTION_BG = ACCENT
    SELECTION_TEXT = PRIMARY_DARK
    
    HOVER_BG = ACCENT
    HOVER_TEXT = PRIMARY_DARK
    
    BORDER = PRIMARY_DARK
    BORDER_LIGHT = SECONDARY
    
    # Button colors
    BUTTON_PRIMARY_BG = PRIMARY_DARK
    BUTTON_PRIMARY_TEXT = PRIMARY_LIGHT
    
    BUTTON_SECONDARY_BG = SECONDARY
    BUTTON_SECONDARY_TEXT = PRIMARY_DARK
    
    BUTTON_ACCENT_BG = ACCENT
    BUTTON_ACCENT_TEXT = PRIMARY_DARK
    
    # Status colors (keeping some standard colors for notifications)
    SUCCESS = "#4CAF50"
    WARNING = "#FF9800"
    ERROR = "#F44336"
    INFO = "#2196F3"
    
    @classmethod
    def get_css_variables(cls):
        """
        Returns CSS custom properties for the color palette
        """
        return f"""
        :root {{
            --color-primary-dark: {cls.PRIMARY_DARK};
            --color-primary-light: {cls.PRIMARY_LIGHT};
            --color-secondary: {cls.SECONDARY};
            --color-accent: {cls.ACCENT};
            
            --color-header-bg: {cls.HEADER_BG};
            --color-header-text: {cls.HEADER_TEXT};
            
            --color-main-bg: {cls.MAIN_BG};
            --color-main-text: {cls.MAIN_TEXT};
            
            --color-row-odd: {cls.ROW_ODD};
            --color-row-even: {cls.ROW_EVEN};
            
            --color-selection-bg: {cls.SELECTION_BG};
            --color-selection-text: {cls.SELECTION_TEXT};
            
            --color-hover-bg: {cls.HOVER_BG};
            --color-hover-text: {cls.HOVER_TEXT};
            
            --color-border: {cls.BORDER};
            --color-border-light: {cls.BORDER_LIGHT};
        }}
        """
    
    @classmethod
    def get_tailwind_classes(cls):
        """
        Returns Tailwind CSS class mappings for the color palette
        """
        return {
            'bg-primary-dark': f'bg-[{cls.PRIMARY_DARK}]',
            'bg-primary-light': f'bg-[{cls.PRIMARY_LIGHT}]',
            'bg-secondary': f'bg-[{cls.SECONDARY}]',
            'bg-accent': f'bg-[{cls.ACCENT}]',
            
            'text-primary-dark': f'text-[{cls.PRIMARY_DARK}]',
            'text-primary-light': f'text-[{cls.PRIMARY_LIGHT}]',
            'text-secondary': f'text-[{cls.SECONDARY}]',
            'text-accent': f'text-[{cls.ACCENT}]',
            
            'border-primary-dark': f'border-[{cls.PRIMARY_DARK}]',
            'border-secondary': f'border-[{cls.SECONDARY}]',
        }
