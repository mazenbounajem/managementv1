from nicegui import ui


class uiAggridTheme:
    ROW_HEIGHT = 20
    CELL_PADDING = 6
    CELL_LINE_HEIGHT = 20

    @staticmethod
    def addingtheme():
        ui.add_css("""
        .ag-theme-quartz-dark {
            --ag-row-height: 20px;
            --ag-cell-horizontal-padding: 6px;
            --ag-cell-vertical-padding: 1px;
            --ag-line-height: 20px;

            --ag-foreground-color: #f1f5f9;
            --ag-background-color: rgba(15, 15, 25, 0.6);

            --ag-header-background-color: rgba(46, 125, 50, 0.95);
            --ag-header-foreground-color: #ffffff;
            --ag-header-cell-hover-background-color: rgba(56, 142, 60, 0.8);
            --ag-header-cell-moving-background-color: rgba(76, 175, 80, 0.6);

            --ag-odd-row-background-color: rgba(20, 20, 35, 0.5);
            --ag-even-row-background-color: rgba(25, 25, 40, 0.5);
            --ag-row-hover-color: rgba(76, 175, 80, 0.25);
            --ag-row-border-color: rgba(255, 255, 255, 0.08);

            --ag-selected-row-background-color: rgba(76, 175, 80, 0.25);
            --ag-range-selection-background-color: rgba(56, 142, 60, 0.2);

            --ag-border-color: rgba(255, 255, 255, 0.12);
            --ag-secondary-border-color: rgba(255, 255, 255, 0.08);
            --ag-input-focus-border-color: rgba(76, 175, 80, 0.8);
            --ag-checkbox-background-color: rgba(30, 30, 50, 0.8);
            --ag-checkbox-checked-color: rgba(76, 175, 80, 0.9);
            --ag-menu-background-color: rgba(20, 20, 35, 0.95);
            --ag-menu-border-color: rgba(255, 255, 255, 0.12);
        }

        .ag-theme-quartz-dark .ag-header {
            background-color: rgba(46, 125, 50, 0.95) !important;
            color: #ffffff !important;
            font-weight: 600 !important;
            font-size: 12px !important;
            border-bottom: 1px solid rgba(255, 255, 255, 0.12) !important;
            visibility: visible !important;
            opacity: 1 !important;
        }

        .ag-theme-quartz-dark .ag-header-cell {
            background-color: rgba(46, 125, 50, 0.95) !important;
            color: #ffffff !important;
            border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
            border-bottom: 1px solid rgba(255, 255, 255, 0.12) !important;
        }

        .ag-theme-quartz-dark .ag-header-cell:hover {
            background-color: rgba(56, 142, 60, 0.7) !important;
            color: #ffffff !important;
        }

        .ag-theme-quartz-dark .ag-header-cell-label {
            display: flex;
            align-items: center;
        }

        .ag-theme-quartz-dark .ag-row {
            color: #f1f5f9 !important;
            border-bottom: 1px solid rgba(255, 255, 255, 0.06) !important;
            font-size: 13px !important;
        }

        .ag-theme-quartz-dark .ag-row-odd {
            background-color: rgba(20, 20, 35, 0.5) !important;
        }

        .ag-theme-quartz-dark .ag-row-even {
            background-color: rgba(25, 25, 40, 0.5) !important;
        }

        .ag-theme-quartz-dark .ag-row:hover {
            background-color: rgba(76, 175, 80, 0.15) !important;
            color: #ffffff !important;
        }

        .ag-theme-quartz-dark .ag-row-selected {
            background-color: rgba(76, 175, 80, 0.25) !important;
            color: #ffffff !important;
        }

        .ag-theme-quartz-dark .ag-cell {
            color: #f1f5f9 !important;
            border-right: 1px solid rgba(255, 255, 255, 0.04) !important;
            align-items: center !important;
        }

        .ag-theme-quartz-dark .ag-cell-focus {
            outline: 1px solid rgba(76, 175, 80, 0.6) !important;
            outline-offset: -1px;
        }

        .ag-theme-quartz-dark .ag-cell-range-selected {
            background-color: rgba(56, 142, 60, 0.15) !important;
        }
        """)
