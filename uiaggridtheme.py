#/* AG Grid Custom Theme - Multi-Color Design */
#/* Header: Green, Body: Black, Selection: Blue */

#/* Custom AG Grid Theme - ag-theme-quartz-custom */
from nicegui import ui
class uiAggridTheme:
    def addingtheme():
        ui.add_css('''
        .ag-theme-quartz-custom {
            /* Base colors */
            --ag-foreground-color: #ffffff;
            --ag-background-color: #000000;
            --ag-header-background-color: #2E7D32;
            --ag-header-foreground-color: #ffffff;
            --ag-header-cell-hover-background-color: #388E3C;
            --ag-header-cell-moving-background-color: #1B5E20;
            
            /* Row colors */
            --ag-odd-row-background-color: #111111;
            --ag-even-row-background-color: #0a0a0a;
            --ag-row-hover-color: #1976D2;
            --ag-row-border-color: #333333;
            
            /* Selection colors */
            --ag-selected-row-background-color: #1976D2;
            --ag-range-selection-background-color: rgba(25, 118, 210, 0.4);
            
            /* Border colors */
            --ag-border-color: #444444;
            --ag-secondary-border-color: #555555;
            
            /* Input colors */
            --ag-input-focus-border-color: #1976D2;
            
            /* Checkbox colors */
            --ag-checkbox-background-color: #000000;
            --ag-checkbox-checked-color: #1976D2;
            
            /* Menu colors */
            --ag-menu-background-color: #1a1a1a;
            --ag-menu-border-color: #444444;
        }

        /* Header styling */
        .ag-theme-quartz-custom .ag-header {
            background-color: #2E7D32 !important;
            color: #ffffff !important;
            font-weight: bold;
            border-bottom: 2 px solid #1B5E20;
        }

        .ag-theme-quartz-custom .ag-header-cell {
            background-color: #2E7D32 !important;
            color: #ffffff !important;
            border-right: 1px solid #1B5E20;
        }

        /* Row styling */
        .ag-theme-quartz-custom .ag-row {
            background-color: #000000 !important;
            color: #ffffff !important;
            border-bottom: 1px solid #333333;
        }

        .ag-theme-quartz-custom .ag-row-odd {
            background-color: #111111 !important;
        }

        .ag-theme-quartz-custom .ag-row-even {
            background-color: #0a0a0a !important;
        }

        .ag-theme-quartz-custom .ag-row:hover {
            background-color: #1976D2 !important;
        }

        /* Selected row styling */
        .ag-theme-quartz-custom .ag-row-selected {
            background-color: #1976D2 !important;
            color: #ffffff !important;
        }

        /* Cell styling */
        .ag-theme-quartz-custom .ag-cell {
            color: #ffffff !important;
        }

        /* Custom header classes */
        .green-header {
            background-color: #2E7D32 !important;
            color: #ffffff !important;
            font-weight: bold !important;
        }
        '''
        )