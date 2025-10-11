#/* AG Grid Custom Theme - New Color Palette */
#/* Colors: #d3cae2 #e6c17a #f6ede3 #404041 */

from nicegui import ui
from color_palette import ColorPalette

class uiAggridTheme:
    def addingtheme():
        # Add CSS variables first
        ui.add_css(ColorPalette.get_css_variables())
        
        ui.add_css(f'''
        .ag-theme-quartz-custom {{
            /* Base colors using new palette */
            --ag-foreground-color: {ColorPalette.MAIN_TEXT};
            --ag-background-color: {ColorPalette.MAIN_BG};
            --ag-header-background-color: {ColorPalette.HEADER_BG};
            --ag-header-foreground-color: {ColorPalette.HEADER_TEXT};
            --ag-header-cell-hover-background-color: {ColorPalette.HOVER_BG};
            --ag-header-cell-moving-background-color: {ColorPalette.ACCENT};
            
            /* Row colors */
            --ag-odd-row-background-color: {ColorPalette.ROW_ODD};
            --ag-even-row-background-color: {ColorPalette.ROW_EVEN};
            --ag-row-hover-color: {ColorPalette.HOVER_BG};
            --ag-row-border-color: {ColorPalette.BORDER_LIGHT};
            
            /* Selection colors */
            --ag-selected-row-background-color: {ColorPalette.SELECTION_BG};
            --ag-range-selection-background-color: rgba(230, 193, 122, 0.4);
            
            /* Border colors */
            --ag-border-color: {ColorPalette.BORDER_LIGHT};
            --ag-secondary-border-color: {ColorPalette.BORDER};
            
            /* Input colors */
            --ag-input-focus-border-color: {ColorPalette.ACCENT};
            
            /* Checkbox colors */
            --ag-checkbox-background-color: {ColorPalette.MAIN_BG};
            --ag-checkbox-checked-color: {ColorPalette.ACCENT};
            
            /* Menu colors */
            --ag-menu-background-color: {ColorPalette.MAIN_BG};
            --ag-menu-border-color: {ColorPalette.BORDER_LIGHT};
        }}

        /* Header styling */
        .ag-theme-quartz-custom .ag-header {{
            background-color: {ColorPalette.HEADER_BG} !important;
            color: {ColorPalette.HEADER_TEXT} !important;
            font-weight: bold;
            border-bottom: 2px solid {ColorPalette.BORDER};
        }}

        .ag-theme-quartz-custom .ag-header-cell {{
            background-color: {ColorPalette.HEADER_BG} !important;
            color: {ColorPalette.HEADER_TEXT} !important;
            border-right: 1px solid {ColorPalette.BORDER};
        }}

        .ag-theme-quartz-custom .ag-header-cell:hover {{
            background-color: {ColorPalette.HOVER_BG} !important;
            color: {ColorPalette.HOVER_TEXT} !important;
        }}

        /* Row styling */
        .ag-theme-quartz-custom .ag-row {{
            background-color: {ColorPalette.ROW_EVEN} !important;
            color: {ColorPalette.MAIN_TEXT} !important;
            border-bottom: 1px solid {ColorPalette.BORDER_LIGHT};
        }}

        .ag-theme-quartz-custom .ag-row-odd {{
            background-color: {ColorPalette.ROW_ODD} !important;
        }}

        .ag-theme-quartz-custom .ag-row-even {{
            background-color: {ColorPalette.ROW_EVEN} !important;
        }}

        .ag-theme-quartz-custom .ag-row:hover {{
            background-color: {ColorPalette.HOVER_BG} !important;
            color: {ColorPalette.HOVER_TEXT} !important;
        }}

        /* Selected row styling */
        .ag-theme-quartz-custom .ag-row-selected {{
            background-color: {ColorPalette.SELECTION_BG} !important;
            color: {ColorPalette.SELECTION_TEXT} !important;
            border: 2px solid {ColorPalette.BORDER} !important;
        }}

        /* Cell styling */
        .ag-theme-quartz-custom .ag-cell {{
            color: {ColorPalette.MAIN_TEXT} !important;
        }}

        /* Custom header classes */
        .blue-header {{
            background-color: {ColorPalette.HEADER_BG} !important;
            color: {ColorPalette.HEADER_TEXT} !important;
            font-weight: bold !important;
        }}
        
        .green-header {{
            background-color: {ColorPalette.HEADER_BG} !important;
            color: {ColorPalette.HEADER_TEXT} !important;
            font-weight: bold !important;
        }}
        
        .highlighted-row {{
            background-color: {ColorPalette.ACCENT} !important;
            color: {ColorPalette.MAIN_TEXT} !important;
            border: 2px solid {ColorPalette.BORDER} !important;
        }}
        
        /* Additional styling for better visual hierarchy */
        .ag-theme-quartz-custom .ag-cell-focus {{
            border: 2px solid {ColorPalette.ACCENT} !important;
        }}
        
        .ag-theme-quartz-custom .ag-cell-range-selected {{
            background-color: rgba(230, 193, 122, 0.3) !important;
        }}
        '''
        )
