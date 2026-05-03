from nicegui import ui
from connection import connection
from navigation_improvements import EnhancedNavigation
from session_storage import session_storage
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput
from modern_design_system import ModernDesignSystem as MDS
import accounting_helpers

def ledger_content(standalone=False):
    """Content method for ledger that can be used in tabs"""
    if standalone:
        with ModernPageLayout("Ledger Management", standalone=standalone):
            LedgerUI(standalone=False)
    else:
        LedgerUI(standalone=False)

@ui.page('/ledger')
def ledger_page_route():
    ledger_content(standalone=True)

class LedgerUI:
    def __init__(self, standalone=True):
        self.standalone = standalone
        self.input_refs = {}
        self.initial_values = {}
        self.row_data = []
        self.tree = None
        self.search_input = None
        self.tree_data = []
        self.create_ui()

    def clear_input_fields(self):
        self.input_refs['account_number'].value = ''
        self.input_refs['sub_number'].value = ''
        self.input_refs['parent_id'].value = None
        self.input_refs['name_en'].value = ''
        self.input_refs['name_fr'].value = ''
        self.input_refs['name_ar'].value = ''
        self.input_refs['status'].value = 1
        self.input_refs['id'].value = ''
        ui.notify('Ready for new ledger entry', color='info')

    def _load_last_row(self):
        """Load the first row into form fields"""
        if not self.row_data:
            return
        row = self.row_data[0]
        self.input_refs['id'].value = str(row['Id'])
        self.input_refs['account_number'].value = row['AccountNumber'] or ''
        self.input_refs['sub_number'].value = row['SubNumber'] or ''
        self.input_refs['parent_id'].value = str(row['ParentId']) if row['ParentId'] else ''
        self.input_refs['name_en'].value = row['Name_en'] or ''
        self.input_refs['name_fr'].value = row['Name_fr'] or ''
        self.input_refs['name_ar'].value = row['Name_ar'] or ''
        self.input_refs['status'].value = row['Status']
        self.initial_values = {
            'account_number': row['AccountNumber'] or '',
            'sub_number': row['SubNumber'] or '',
            'parent_id': str(row['ParentId']) if row['ParentId'] else '',
            'name_en': row['Name_en'] or '',
            'name_fr': row['Name_fr'] or '',
            'name_ar': row['Name_ar'] or '',
            'status': row['Status'],
            'id': str(row['Id'])
        }

    def save_ledger(self):
        account_number = self.input_refs['account_number'].value
        sub_number = self.input_refs['sub_number'].value
        parent_id = self.input_refs['parent_id'].value
        name_en = self.input_refs['name_en'].value
        name_fr = self.input_refs['name_fr'].value
        name_ar = self.input_refs['name_ar'].value
        status = self.input_refs['status'].value
        id_value = self.input_refs['id'].value

        if not account_number or not name_en:
            ui.notify('Account Number and English Name are required', color='warning')
            return

        # Constraint: Only accounts starting with 1-7 are allowed
        if account_number[0] not in '1234567':
            ui.notify('Invalid Account: Only root accounts 1-7 and their children are allowed', color='negative')
            return

        # Constraint: Cannot add a new single-digit root (1-7 already exist)
        if not id_value and len(account_number) == 1:
            existing = [r for r in self.row_data if r['AccountNumber'] == account_number]
            if existing:
                ui.notify(f'Root account {account_number} already exists. Add children under it instead.', color='warning')
                return

        try:
            if id_value:
                sql = "UPDATE Ledger SET AccountNumber=?, SubNumber=?, ParentId=?, Name_en=?, Name_fr=?, Name_ar=?, UpdateDate=GETDATE(), Status=? WHERE Id=?"
                values = (account_number, sub_number, parent_id, name_en, name_fr, name_ar, status, id_value)
            else:
                sql = "INSERT INTO Ledger (AccountNumber, SubNumber, ParentId, Name_en, Name_fr, Name_ar, UpdateDate, Status) VALUES (?, ?, ?, ?, ?, ?, GETDATE(), ?)"
                values = (account_number, sub_number, parent_id, name_en, name_fr, name_ar, status)

            connection.insertingtodatabase(sql, values)
            ui.notify('Ledger saved successfully', color='positive')
            self.refresh_table()
        except Exception as e:
            ui.notify(f'Error saving ledger: {str(e)}', color='negative')

    def undo_changes(self):
        for field in ['account_number', 'sub_number', 'parent_id', 'name_en', 'name_fr', 'name_ar', 'status', 'id']:
            if field in self.initial_values:
                self.input_refs[field].value = self.initial_values[field]
        ui.notify('Changes reverted', color='info')

    def delete_ledger(self):
        id_value = self.input_refs['id'].value
        if not id_value:
            ui.notify('Please select a ledger to delete', color='warning')
            return

        try:
            # Check if ledger is used in any transactions
            data = []
            connection.contogetrows("SELECT COUNT(*) FROM journal_voucher_lines WHERE account=?", data, (self.input_refs['account_number'].value,))
            if data and data[0][0] > 0:
                ui.notify('Cannot delete: Ledger account is in use by journal vouchers', color='warning')
                return

            # Check if account has children in the tree
            acc_num = self.input_refs['account_number'].value
            children = [r for r in self.row_data if r['AccountNumber'] != acc_num and r['AccountNumber'].startswith(acc_num)]
            if children:
                ui.notify('Cannot delete: This account has child accounts. Delete children first.', color='warning')
                return

            sql = "DELETE FROM Ledger WHERE Id=?"
            connection.deleterow(sql, id_value)
            ui.notify('Ledger deleted successfully', color='positive')
            self.clear_input_fields()
            self.refresh_table()
        except Exception as e:
            ui.notify(f'Error deleting ledger: {str(e)}', color='negative')

    def refresh_table(self):
        try:
            data = []
            connection.contogetrows("SELECT Id, AccountNumber, SubNumber, ParentId, Name_en, Name_fr, Name_ar, UpdateDate, Status FROM Ledger ORDER BY AccountNumber", data)

            self.row_data = []
            for row in data:
                self.row_data.append({
                    'Id': row[0],
                    'AccountNumber': str(row[1]) if row[1] else '',
                    'SubNumber': row[2],
                    'ParentId': row[3],
                    'Name_en': row[4],
                    'Name_fr': row[5],
                    'Name_ar': row[6],
                    'UpdateDate': str(row[7]),
                    'Status': row[8]
                })

            self.tree_data = self.build_account_tree(self.row_data)
            if self.tree:
                self.tree._props['nodes'] = self.tree_data
                self.tree.update()

            self.update_parent_options()
            self._load_last_row()
        except Exception as e:
            ui.notify(f'Error refreshing data: {str(e)}', color='negative')

    def build_account_tree(self, accounts):
        """Build hierarchical tree from flat account list based on account number prefix."""
        sorted_accs = sorted(accounts, key=lambda x: (len(x['AccountNumber']), x['AccountNumber']))

        nodes = {}
        for acc in sorted_accs:
            acc_num = acc['AccountNumber']
            if not acc_num:
                continue

            status_icon = '🟢' if acc.get('Status') == 1 else '🔴'
            label = f"{status_icon} {acc_num} - {acc['Name_en'] or ''}"
            nodes[acc_num] = {
                'id': str(acc['Id']),
                'label': label,
                'account_number': acc_num,
                'children': [],
                'data': acc
            }

        roots = []
        for acc_num, node in nodes.items():
            if len(acc_num) == 1 and acc_num in '1234567':
                roots.append(node)
                continue

            # Walk up the prefix chain to find a parent
            parent_num = acc_num[:-1]
            found_parent = False
            while parent_num:
                if parent_num in nodes:
                    nodes[parent_num]['children'].append(node)
                    found_parent = True
                    break
                parent_num = parent_num[:-1]

            if not found_parent:
                # Orphan account under 1-7, attach as root-level
                if acc_num and acc_num[0] in '1234567':
                    roots.append(node)

        return sorted(roots, key=lambda n: n['account_number'])

    def update_parent_options(self):
        try:
            ledger_data = []
            connection.contogetrows("SELECT Id, AccountNumber, Name_en FROM Ledger WHERE Status = 1 ORDER BY AccountNumber", ledger_data)
            options = {'': 'None (Root Level)'}
            for row in ledger_data:
                if row[0] != int(self.input_refs['id'].value) if self.input_refs['id'].value else True:
                    options[str(row[0])] = f"{row[1]} - {row[2]} (ID: {row[0]})"
            self.input_refs['parent_id'].options = options
            self.input_refs['parent_id'].update()
        except Exception as e:
            print(f"Error updating parent options: {e}")

    def create_ui(self):
        if self.standalone:
            layout_container = ModernPageLayout("Ledger Management", standalone=True)
            layout_container.__enter__()

        try:
            # Custom CSS for the tree
            ui.add_head_html('''
            <style>
                .ledger-tree .q-tree__node-header {
                    padding: 6px 8px;
                    border-radius: 8px;
                    transition: background 0.2s;
                }
                .ledger-tree .q-tree__node-header:hover {
                    background: rgba(255,255,255,0.08);
                }
                .ledger-tree .q-tree__node-header--active {
                    background: rgba(59, 130, 246, 0.25) !important;
                }
                .ledger-tree .q-tree__node--child > .q-tree__node-header {
                    padding-left: 12px;
                }
                .ledger-tree .q-icon {
                    color: rgba(255,255,255,0.7);
                }
                .ledger-tree .q-tree__arrow {
                    color: rgba(255,255,255,0.5);
                }
            </style>
            ''')

            with ui.row().classes('w-full gap-6 items-start p-4 animate-fade-in'):
                # Left Column: Details Form
                with ui.column().classes('w-1/3 gap-6'):
                    with ModernCard(glass=True).classes('w-full p-6'):
                        ui.label('Ledger Details').classes('text-lg font-black mb-6 text-white')
                        with ui.column().classes('w-full gap-4'):
                            self.input_refs['account_number'] = ui.input('Account Number').classes('w-full glass-input text-white').props('dark rounded outlined')
                            self.input_refs['sub_number'] = ui.input('Sub Number').classes('w-full glass-input text-white').props('dark rounded outlined')
                            self.input_refs['parent_id'] = ui.select({}, label='Parent Account').classes('w-full glass-input text-white').props('dark rounded outlined')
                            self.input_refs['status'] = ui.select({1: 'Active', 0: 'Inactive'}, label='Status').classes('w-full glass-input text-white').props('dark rounded outlined')
                            self.input_refs['id'] = ui.input('ID (Auto)').classes('w-full glass-input text-white').props('dark rounded outlined readonly')

                    with ModernCard(glass=True).classes('w-full p-6'):
                        ui.label('Name Aliases').classes('text-lg font-black mb-6 text-white')
                        with ui.column().classes('w-full gap-4'):
                            self.input_refs['name_en'] = ui.input('Name (English)').classes('w-full glass-input text-white').props('dark rounded outlined')
                            self.input_refs['name_fr'] = ui.input('Name (French)').classes('w-full glass-input text-white').props('dark rounded outlined')
                            self.input_refs['name_ar'] = ui.input('Name (Arabic)').classes('w-full glass-input text-white').props('dark rounded outlined')

                # Middle Column: Tree
                with ui.column().classes('flex-1 gap-6'):
                    with ModernCard(glass=True).classes('w-full p-6'):
                        with ui.row().classes('w-full justify-between items-center mb-4'):
                            ui.label('Chart of Accounts').classes('text-xl font-black text-white')
                            with ui.row().classes('gap-2 items-center'):
                                self.search_input = ui.input(placeholder='Search accounts...').classes('w-64 glass-input text-white text-sm').props('dark rounded outlined dense')
                                self.search_input.on('input', lambda e: self.filter_rows(e.value))
                                ui.button(icon='unfold_more', on_click=self._expand_all).props('flat dense color=white').tooltip('Expand All')
                                ui.button(icon='unfold_less', on_click=self._collapse_all).props('flat dense color=white').tooltip('Collapse All')

                        with ui.column().classes('w-full h-[600px] overflow-auto').style(
                            'background: rgba(255,255,255,0.04); border-radius: 12px; padding: 12px; '
                            'border: 1px solid rgba(255,255,255,0.08);'
                        ):
                            self.tree = ui.tree(
                                self.tree_data,
                                label_key='label',
                                children_key='children',
                                node_key='id',
                                on_select=lambda e: self.on_tree_select(e)
                            ).classes('w-full text-white ledger-tree').props('dark dense')

                # Right Column: Action Bar
                with ui.column().classes('w-80px items-center'):
                    from modern_ui_components import ModernActionBar
                    ModernActionBar(
                        on_new=self.clear_input_fields,
                        on_save=self.save_ledger,
                        on_undo=self.undo_changes,
                        on_delete=self.delete_ledger,
                        on_refresh=self.refresh_table,
                        on_chatgpt=lambda: ui.run_javascript('window.open("https://chatgpt.com", "_blank");'),
                        button_class='h-16',
                        target_table=None,
                        classes=' '
                    ).style('position: static; width: 80px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); margin-top: 0;')
                    
                    with ModernCard(glass=True).classes('w-full p-4 mt-4'):
                        ui.label('Reports').classes('text-sm font-bold mb-2 text-white')
                        ui.button('Full Trial Balance', icon='account_balance', on_click=lambda: accounting_helpers.print_trial_balance()).props('flat full-width color=green')
                        ui.button('Hierarchical TB', icon='account_tree', on_click=lambda: accounting_helpers.print_hierarchical_trial_balance_pdf(self.input_refs['account_number'].value)).props('flat full-width color=orange')

            ui.timer(0.1, self.refresh_table, once=True)
        finally:
            if self.standalone:
                layout_container.__exit__(None, None, None)

    def on_tree_select(self, e):
        try:
            if not e.value:
                return

            def find_node(nodes, target_id):
                for n in nodes:
                    if n['id'] == target_id:
                        return n
                    res = find_node(n.get('children', []), target_id)
                    if res:
                        return res
                return None

            selected_node = find_node(self.tree_data, e.value)
            if selected_node:
                data = selected_node['data']
                self.input_refs['id'].value = str(data['Id'])
                self.input_refs['account_number'].value = data['AccountNumber'] or ''
                self.input_refs['sub_number'].value = data['SubNumber'] or ''
                self.input_refs['parent_id'].value = str(data['ParentId']) if data.get('ParentId') else ''
                self.input_refs['name_en'].value = data['Name_en'] or ''
                self.input_refs['name_fr'].value = data['Name_fr'] or ''
                self.input_refs['name_ar'].value = data['Name_ar'] or ''
                self.input_refs['status'].value = data['Status']

                self.initial_values = {
                    'account_number': data['AccountNumber'] or '',
                    'sub_number': data['SubNumber'] or '',
                    'parent_id': str(data['ParentId']) if data.get('ParentId') else '',
                    'name_en': data['Name_en'] or '',
                    'name_fr': data['Name_fr'] or '',
                    'name_ar': data['Name_ar'] or '',
                    'status': data['Status'],
                    'id': str(data['Id'])
                }
                self.update_parent_options()
        except Exception as e:
            ui.notify(f'Error selecting tree node: {str(e)}', color='negative')

    def filter_rows(self, search_text):
        if not search_text:
            if self.tree:
                self.tree._props['nodes'] = self.tree_data
                self.tree.update()
        else:
            search_text = search_text.lower()

            def filter_nodes(nodes):
                filtered = []
                for n in nodes:
                    matches = search_text in n['label'].lower()
                    child_matches = filter_nodes(n.get('children', []))
                    if matches or child_matches:
                        new_node = {**n, 'children': child_matches}
                        filtered.append(new_node)
                return filtered

            filtered_data = filter_nodes(self.tree_data)
            if self.tree:
                self.tree._props['nodes'] = filtered_data
                self.tree.update()
                self.tree.run_method('expandAll')

    def _expand_all(self):
        if self.tree:
            self.tree.run_method('expandAll')

    def _collapse_all(self):
        if self.tree:
            self.tree.run_method('collapseAll')