from nicegui import ui
from connection import connection
from session_storage import session_storage
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput
from modern_design_system import ModernDesignSystem as MDS
import datetime

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
        self.create_ui()

    def fetch_data(self):
        try:
            # 1. Fetch Ledger Accounts
            ledger_data = []
            connection.contogetrows("SELECT Id, AccountNumber, Name_en, ParentId FROM Ledger ORDER BY AccountNumber", ledger_data)
            
            # 2. Fetch Auxiliary Accounts
            aux_data = []
            connection.contogetrows("""
                SELECT a.id, a.number, a.account_name, 
                       COALESCE(l.AccountNumber, a.auxiliary_id) as parent_ledger 
                FROM auxiliary a
                LEFT JOIN Ledger l ON a.ledger_id = l.Id
            """, aux_data)
            
            # 3. Fetch Balances (Summed from transaction lines)
            # We must JOIN with auxiliary to get the 'number' because l.auxiliary_id often stores the internal ID (int).
            balance_data = []
            sql_balances = """
                SELECT 
                    COALESCE(a.number, l.account_number) as code,
                    ISNULL(SUM(l.debit), 0) as total_debit,
                    ISNULL(SUM(l.credit), 0) as total_credit
                FROM accounting_transaction_lines l
                LEFT JOIN auxiliary a ON (l.auxiliary_id = CAST(a.id AS NVARCHAR(50)) OR l.auxiliary_id = a.number)
                INNER JOIN accounting_transactions t ON l.jv_id = t.jv_id
                WHERE CAST(t.transaction_date AS DATE) BETWEEN ? AND ?
                GROUP BY COALESCE(a.number, l.account_number)
            """
            connection.contogetrows_with_params(sql_balances, balance_data, (self.from_date, self.to_date))
            
            balances = {row[0]: {'debit': float(row[1]), 'credit': float(row[2])} for row in balance_data}
            
            return ledger_data, aux_data, balances
        except Exception as e:
            ui.notify(f"Error fetching data: {str(e)}", color='negative')
            return [], [], {}

    def build_tree(self):
        ledger_raw, aux_raw, balances = self.fetch_data()
        nodes = {}
        
        # 1. Create nodes for all known Ledger accounts
        for row in ledger_raw:
            id_val, code, name, parent_id = row
            code = str(code)
            nodes[code] = {
                'id': f"L_{code}",
                'code': code,
                'name': name,
                'debit': 0.0,
                'credit': 0.0,
                'children': [],
                'type': 'ledger'
            }

        # 2. Create nodes for all known Auxiliary accounts
        for row in aux_raw:
            id_val, aux_number, name, parent_ledger = row
            aux_number = str(aux_number)
            parent_ledger = str(parent_ledger) if parent_ledger else None
            
            # Auto-derive parent if missing but has dot
            if not parent_ledger and '.' in aux_number:
                parent_ledger = aux_number.split('.')[0]
                
            nodes[aux_number] = {
                'id': f"A_{aux_number}",
                'code': aux_number,
                'name': name,
                'debit': 0.0,
                'credit': 0.0,
                'children': [],
                'type': 'auxiliary',
                'parent_code': parent_ledger
            }

        # 3. Handle ghost accounts (codes in 'balances' that aren't in masters)
        for code in balances:
            if code not in nodes:
                nodes[code] = {
                    'id': f"M_{code}",
                    'code': code,
                    'name': f"Unmapped Account {code}",
                    'debit': 0.0,
                    'credit': 0.0,
                    'children': [],
                    'type': 'ledger'
                }

        # 4. Build Hierarchy
        final_roots = {}
        # Sorting by code ensures we process 1, then 10, then 100... mostly helpful for consistency
        for code in sorted(nodes.keys()):
            node = nodes[code]
            
            # Determine logic for finding parent
            p_code = None
            if node['type'] == 'auxiliary':
                p_code = node.get('parent_code')
            elif len(code) > 1:
                # For ledgers, look for parent by trimming last digit repeatedly
                temp_p = code[:-1]
                while temp_p:
                    if temp_p in nodes:
                        p_code = temp_p
                        break
                    temp_p = temp_p[:-1]

            # Attach to parent if found, otherwise it's a root
            if p_code and p_code in nodes:
                if node not in nodes[p_code]['children']:
                    nodes[p_code]['children'].append(node)
            else:
                final_roots[code] = node

        # 5. Recursive aggregation of totals
        def recursive_aggregate(node):
            code = node['code']
            # Start with direct balance posted precisely to this code
            d = balances.get(code, {}).get('debit', 0.0)
            c = balances.get(code, {}).get('credit', 0.0)
            
            # Add up all children
            for child in node['children']:
                cd, cc = recursive_aggregate(child)
                d += cd
                c += cc
            
            node['debit'] = d
            node['credit'] = c
            return d, c

        result_roots = sorted(list(final_roots.values()), key=lambda x: x['code'])
        for r in result_roots:
            recursive_aggregate(r)
            
        return [self.format_node(r) for r in result_roots]

    def format_node(self, node):
        def format_currency(val):
            return f"{val:,.2f}"
        
        d = node['debit']
        c = node['credit']
        bal = d - c
        
        label = f"{node['code']} - {node['name']}"
        
        # Add debit/credit to the label for the tree
        # We can use Q-Tree's slots for better formatting
        node['label'] = label
        node['debit_str'] = format_currency(d)
        node['credit_str'] = format_currency(c)
        node['balance_str'] = format_currency(bal)
        
        if node['children']:
            node['children'] = [self.format_node(c) for c in node['children']]
            
        return node

    def refresh_tree(self):
        self.tree_data = self.build_tree()
        if self.tree:
            self.tree._props['nodes'] = self.tree_data
            self.tree.update()

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
                    ui.button(icon='refresh', on_click=self.refresh_tree).props('flat round color=white')
                    ui.button('Print', icon='print', on_click=self.print_pdf).props('unelevated color=green')

            # Tree Content
            with ModernCard(glass=True).classes('w-full p-4 overflow-hidden'):
                # Custom Header for the Tree "Table"
                with ui.row().classes('w-full px-4 py-2 border-b border-white/10 mb-2'):
                    ui.label('Account Hierarchy').classes('flex-1 header-cell')
                    ui.label('Debit').classes('w-[100px] text-right header-cell')
                    ui.label('Credit').classes('w-[100px] text-right header-cell')
                    ui.label('Balance').classes('w-[120px] text-right header-cell')

                with ui.column().classes('w-full h-[700px] overflow-y-auto'):
                    self.tree = ui.tree([], label_key='label', children_key='children', node_key='id')\
                        .classes('w-full trial-tree text-white').props('dark')
                    
                    # Use slots for custom tree node content
                    self.tree.add_slot('default-header', '''
                        <div class="flex items-center w-full gap-4">
                            <span class="text-xs opacity-50 font-mono w-24">{{ props.node.code }}</span>
                            <span class="flex-1 font-bold">{{ props.node.name }}</span>
                            <span class="text-green-400 font-mono text-right w-[100px]">{{ props.node.debit_str }}</span>
                            <span class="text-red-400 font-mono text-right w-[100px]">{{ props.node.credit_str }}</span>
                            <span class="font-bold font-mono text-right w-[120px]" :class="props.node.debit - props.node.credit >= 0 ? 'text-white' : 'text-orange-400'">
                                {{ props.node.balance_str }}
                            </span>
                        </div>
                    ''')

            ui.timer(0.1, self.refresh_tree, once=True)

    def print_pdf(self):
        # We can reuse the existing hierarchical print from accounting_helpers but maybe customize it to show full page if requested
        import accounting_helpers
        accounting_helpers.print_hierarchical_trial_balance_pdf('', from_date=self.from_date, to_date=self.to_date)

