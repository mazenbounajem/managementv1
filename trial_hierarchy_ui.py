from nicegui import ui
from connection import connection
from session_storage import session_storage
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput
from modern_design_system import ModernDesignSystem as MDS
import datetime

import reports

def trial_hierarchy_content(standalone=False):
    """Content method for Trial Hierarchy that can be used in tabs"""
    if standalone:
        with ModernPageLayout("Trial Balance Hierarchy", standalone=standalone):
            TrialHierarchyUI(standalone=False)
    else:
        TrialHierarchyUI(standalone=False)

@ui.page('/trial-hierarchy')
def trial_hierarchy_page_route():
    trial_hierarchy_content(standalone=True)

class TrialHierarchyUI:
    def __init__(self, standalone=True):
        self.standalone = standalone
        self.tree = None
        self.tree_data = []
        self.from_date = (datetime.date.today().replace(day=1)).strftime('%Y-%m-%d')
        self.to_date = datetime.date.today().strftime('%Y-%m-%d')

        # Trial Balance Hierarchy requirement:
        # By default show full hierarchy roots (1..7), including auxiliaries.
        # When ledger_prefix is '' (All), no filtering is applied in the UI.
        self.ledger_prefix = ''
        
        # When True, exclude 'Year-End Closing' transactions
        self.pre_closing_only = False

        self.create_ui()

    def fetch_data(self):
        """
        Fetch hierarchical trial balance from the backend so that:
        - debit/credit totals are computed consistently
        - auxiliaries are attached under the correct ledger prefix (e.g., 6011 under '6')
        """
        try:
            # Backend returns a hierarchical list of nodes with debit/credit and children already attached.
            return reports.Reports.fetch_hierarchical_trial_balance(
                ledger_prefix=self.ledger_prefix,
                from_date=self.from_date,
                to_date=self.to_date,
                exclude_reference='Year-End Closing' if self.pre_closing_only else None
            )
        except Exception as e:
            ui.notify(f"Error fetching data: {str(e)}", color='negative')
            return []

    def build_tree(self):
        roots = self.fetch_data() or []

        def format_currency(val):
            return f"{float(val):,.2f}"

        def to_tree_node(node, fallback_parent_code=None):
            # backend nodes:
            # {'code','name','debit','credit','balance','level','children',...}
            code = str(node.get('code', '') or '')
            name = node.get('name', '') or ''

            debit = float(node.get('debit', 0.0) or 0.0)
            credit = float(node.get('credit', 0.0) or 0.0)
            bal = float(node.get('balance', debit - credit) or (debit - credit))

            children_in = node.get('children', None)
            children = children_in if isinstance(children_in, list) else []

            # stable, collision-resistant id for tree node_key
            # backend may not provide id; build one deterministically
            level = node.get('level')
            level_part = str(level) if level is not None else 'NA'
            node_id = node.get('id', None)
            if not node_id:
                parent_part = str(fallback_parent_code) if fallback_parent_code else 'ROOT'
                node_id = f"{level_part}:{parent_part}:{code}"

            out = {
                'id': str(node_id),
                'label': f"{code} - {name}",
                'code': code,
                'name': name,
                'debit': debit,
                'credit': credit,
                'balance': bal,
                'debit_str': format_currency(debit),
                'credit_str': format_currency(credit),
                'balance_str': format_currency(bal),
                'children': [to_tree_node(c, fallback_parent_code=code) for c in children],
            }
            return out

        # Optional UI-side filter when ledger_prefix is set to a specific root (e.g., '6').
        filtered = []
        for r in roots:
            rc = str(r.get('code', '') or '')
            if not rc:
                continue
            if self.ledger_prefix and not rc.startswith(self.ledger_prefix) and rc != self.ledger_prefix:
                continue
            filtered.append(to_tree_node(r, fallback_parent_code=None))

        return filtered

    def flatten_tree_rows(self, nodes):
        """
        Flatten hierarchy into rows for AG Grid tree-table look.
        Returns list[dict] compatible with aggrid rowData.
        """
        rows = []

        def walk(node, level=0):
            code = str(node.get('code', '') or '')
            name = str(node.get('name', '') or '')
            debit = float(node.get('debit', 0.0) or 0.0)
            credit = float(node.get('credit', 0.0) or 0.0)
            balance = float(node.get('balance', debit - credit) or (debit - credit))

            rows.append({
                'level': int(node.get('level', level) or level),
                'indent': '  ' * int(level),
                'code': code,
                'name': name,
                'debit': f"{debit:,.2f}",
                'credit': f"{credit:,.2f}",
                'balance': f"{balance:+,.2f}",
            })

            for c in node.get('children', []) or []:
                walk(c, level=level + 1)

        for r in nodes or []:
            walk(r, level=0)
        return rows

    def refresh_tree(self):
        self.tree_data = self.build_tree()
        if hasattr(self, 'tree_table') and self.tree_table:
            flat_rows = self.flatten_tree_rows(self.tree_data)
            self.tree_table.options['rowData'] = flat_rows
            self.tree_table.update()

    def create_ui(self):
        ui.add_head_html('''
        <style>
            .trial-tree .q-tree__node-header {
                padding: 4px 8px;
                border-radius: 4px;
                border-bottom: 1px solid rgba(255,255,255,0.05);
            }
            .trial-tree .q-tree__node-header:hover {
                background: rgba(255,255,255,0.05);
            }
            .node-code { color: #aaa; font-family: monospace; }
            .node-name { font-weight: bold; }
            .node-debit { color: #4ade80; text-align: right; width: 100px; font-family: monospace; }
            .node-credit { color: #f87171; text-align: right; width: 100px; font-family: monospace; }
            .header-cell { font-size: 10px; font-weight: black; color: #4ade80; text-transform: uppercase; letter-spacing: 0.1em; }
        </style>
        ''')

        with ui.column().classes('w-full p-6 gap-6'):
            # Header Row
            with ui.row().classes('w-full justify-between items-center'):
                with ui.column().classes('gap-0'):
                    ui.label('Trial Balance Hierarchy').classes('text-3xl font-black text-white')
                    ui.label('Detailed hierarchical view including auxiliary accounts').classes('text-gray-400 text-sm')
                
                with ui.row().classes('gap-4 items-center glass p-4 rounded-2xl'):
                    ui.input('From', value=self.from_date).props('type=date outlined dark dense').classes('w-40')\
                        .on_value_change(lambda e: setattr(self, 'from_date', e.value))
                    ui.input('To', value=self.to_date).props('type=date outlined dark dense').classes('w-40')\
                        .on_value_change(lambda e: setattr(self, 'to_date', e.value))

                    # Ledger selector: business track is mostly under 6 (purchase) and 7 (sales).
                    # Provide an "All" option so we can include every account appearing in Business Track.
                    self.ledger_select = ui.select(
                        {'': 'All (1..7)'},
                        value=self.ledger_prefix if self.ledger_prefix is not None else '',
                        label='Ledger Root'
                    ).classes('w-40 glass-input text-white').props('dark rounded outlined')

                    # Extend options with 1..7
                    for i in range(1, 8):
                        self.ledger_select.options[str(i)] = f'Ledger {i}'

                    def _on_ledger_change(e):
                        # NiceGUI select may return empty string for "All"
                        self.ledger_prefix = '' if self.ledger_select.value in (None, '') else str(self.ledger_select.value)
                        self.refresh_tree()

                    self.ledger_select.on('update:model-value', _on_ledger_change)

                    ui.button(icon='refresh', on_click=self.refresh_tree).props('flat round color=white')
                    ui.button('Export CSV (Excel)', icon='download', on_click=self.export_csv_hierarchy).props('unelevated color=teal')
                    ui.button('Print', icon='print', on_click=self.print_pdf).props('unelevated color=green')

                    ui.button(
                        'Close',
                        icon='close',
                        on_click=lambda: ui.navigate.to('/tabbed-dashboard')
                    ).props('unelevated color=grey text-white')

                    with ui.row().classes('items-center gap-2 ml-4 px-3 py-1 rounded-lg bg-white/5 border border-white/10'):
                        ui.label('View:').classes('text-[10px] font-bold text-gray-400 uppercase')
                        def _toggle_pre_closing(e):
                            self.pre_closing_only = bool(e.value)
                            self.refresh_tree()
                        ui.toggle(
                            {False: 'Real-time', True: 'Pre-Closing'},
                            value=self.pre_closing_only,
                            on_change=_toggle_pre_closing
                        ).props('dark dense unelevated toggle-color=green-500').classes('text-xs')

            # Tree-table Content (flattened tree + hierarchy indent)
            with ModernCard(glass=True).classes('w-full p-4 overflow-hidden'):
                with ui.row().classes('w-full px-4 py-2 border-b border-white/10 mb-2'):
                    ui.label('Account Hierarchy (Tree Table)').classes('flex-1 header-cell')
                    ui.label('Debit').classes('w-[110px] text-right header-cell')
                    ui.label('Credit').classes('w-[110px] text-right header-cell')
                    ui.label('Balance').classes('w-[130px] text-right header-cell')

                with ui.column().classes('w-full h-[700px] overflow-y-auto'):
                    # AG Grid "tree table" style using indentation column
                    self.tree_table = ui.aggrid({
                        'columnDefs': [
                            {'headerName': 'Level', 'field': 'level', 'width': 70},
                            {
                                'headerName': 'Code',
                                'field': 'code',
                                'width': 110,
                                'cellRenderer': 'params => params.data.indent + params.value'
                            },
                            {'headerName': 'Name', 'field': 'name', 'flex': 1},
                            {'headerName': 'Debit', 'field': 'debit', 'width': 120},
                            {'headerName': 'Credit', 'field': 'credit', 'width': 120},
                            {'headerName': 'Balance', 'field': 'balance', 'width': 140, 'cellClass': 'text-right'},
                        ],
                        'rowData': [],
                        'defaultColDef': {
                            'resizable': True,
                            'sortable': True,
                            'filter': True,
                        }
                    }).classes('w-full h-full ag-theme-quartz-dark')

            ui.timer(0.1, self.refresh_tree, once=True)

    def export_csv_hierarchy(self):
        """
        Export the trial balance hierarchy as CSV (Excel-compatible).
        Uses backend hierarchical data (including auxiliaries) and flattens it row-by-row.
        """
        import base64
        import csv
        import io
        from reports import Reports

        try:
            tree_roots = Reports.fetch_hierarchical_trial_balance(
                ledger_prefix=self.ledger_prefix or '',
                from_date=self.from_date,
                to_date=self.to_date
            ) or []

            # Export the same "tree table" flattening (hierarchy + indentation)
            # so CSV matches what user sees.
            flat_rows = []
            for r in tree_roots or []:
                flat_rows.extend(self.flatten_tree_rows([r]))

            out = io.StringIO()
            writer = csv.writer(out, delimiter=';')
            writer.writerow(['Level', 'Code', 'Name', 'Debit', 'Credit', 'Balance'])

            for fr in flat_rows:
                writer.writerow([
                    fr.get('level', ''),
                    f"{fr.get('indent','')}{fr.get('code','')}",
                    fr.get('name', ''),
                    fr.get('debit', ''),
                    fr.get('credit', ''),
                    fr.get('balance', ''),
                ])

            csv_text = out.getvalue()
            csv_b64 = base64.b64encode(csv_text.encode('utf-8')).decode('ascii')
            filename = f"trial_balance_hierarchy_ledger_{self.ledger_prefix}_{self.from_date}_to_{self.to_date}.csv"

            # Trigger download via browser
            ui.run_javascript(
                f'''
                (function(){{
                    const b64 = "{csv_b64}";
                    const filename = "{filename}";
                    const link = document.createElement('a');
                    link.href = "data:text/csv;charset=utf-8;base64," + b64;
                    link.download = filename;
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                }})();
                '''
            )
        except Exception as e:
            ui.notify(f"CSV export error: {e}", color='negative')

    def print_pdf(self):
        # Keep existing behavior (dialog iframe), but now CSV export is available for printing/exporting externally.
        import accounting_helpers
        accounting_helpers.print_hierarchical_trial_balance_pdf(
            self.ledger_prefix or '',
            from_date=self.from_date,
            to_date=self.to_date
        )

