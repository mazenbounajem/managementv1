from nicegui import ui
from connection import connection
from modern_design_system import ModernDesignSystem as MDS
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput, ModernTable
from session_storage import session_storage
from datetime import datetime

def category_page(standalone=False):
    # Auth
    user = session_storage.get('user')
    if not user:
        if not standalone:
            ui.notify('Please login', color='negative')
            ui.navigate.to('/login')
        return

    # State
    input_refs = {}

    def refresh_table():
        data = []
        sql = "SELECT id, category_name, description, created_at FROM categories ORDER BY id DESC"
        connection.contogetrows(sql, data)
        rows = []
        cols = ['id', 'name', 'description', 'created_at']
        for r in data:
            rows.append({cols[i]: r[i] for i in range(len(cols))})
        table.options['rowData'] = rows
        table.update()

    def clear_inputs():
        for k, ref in input_refs.items():
            ref.set_value('')
        table.run_method('deselectAll')

    def save_category():
        try:
            name = input_refs['name'].value
            desc = input_refs['description'].value
            cid = input_refs['id'].value

            if not name:
                return ui.notify('Category name required', color='negative')

            if cid:
                sql = "UPDATE categories SET category_name=?, description=? WHERE id=?"
                params = (name, desc, cid)
            else:
                sql = "INSERT INTO categories (category_name, description, created_at) VALUES (?, ?, GETDATE())"
                params = (name, desc)

            connection.insertingtodatabase(sql, params)
            ui.notify('Category saved', color='positive')
            refresh_table()
        except Exception as e:
            ui.notify(f'Error: {e}', color='negative')

    def delete_category():
        cid = input_refs['id'].value
        if not cid: return ui.notify('Select a category', color='warning')
        connection.deleterow("DELETE FROM categories WHERE id=?", cid)
        ui.notify('Category deleted')
        clear_inputs()
        refresh_table()

    with ModernPageLayout("Category Management"):
        with ui.column().classes('w-full gap-6 p-4 animate-fade-in'):
            
            # Action Bar
            with ModernCard().classes('w-full p-4'):
                with ui.row().classes('w-full items-center justify-between'):
                    with ui.row().classes('items-center gap-4'):
                        ui.icon('category').classes('text-3xl text-accent')
                        ui.label('Category Catalog').classes('text-2xl font-black text-primary-dark')
                    
                    with ui.row().classes('gap-2'):
                        ModernButton.create('New', icon='add', on_click=clear_inputs, variant='primary')
                        ModernButton.create('Save', icon='save', on_click=save_category, variant='success')
                        ModernButton.create('Delete', icon='delete', on_click=delete_category, variant='error')

            with ui.row().classes('w-full gap-6 items-start'):
                # Left Column: Form
                with ui.column().classes('w-1/3 gap-4'):
                    with ModernCard().classes('w-full p-6'):
                        ui.label('Category Info').classes('text-lg font-bold mb-4')
                        input_refs['id'] = ui.input('ID').props('readonly outlined dense').classes('hidden')
                        input_refs['name'] = ModernInput('Category Name', icon='label')
                        input_refs['description'] = ui.textarea('Description').props('outlined dense').classes('w-full mt-2')

                # Right Column: List
                with ui.column().classes('flex-1'):
                    with ModernCard().classes('w-full p-4'):
                        ui.label('Available Categories').classes('text-lg font-bold mb-4 ml-2')
                        
                        cols = [
                            {'headerName': 'Name', 'field': 'name', 'flex': 1},
                            {'headerName': 'Description', 'field': 'description', 'flex': 2},
                            {'headerName': 'Created', 'field': 'created_at', 'width': 180}
                        ]
                        
                        table = ui.aggrid({
                            'columnDefs': cols,
                            'rowData': [],
                            'defaultColDef': {'sortable': True, 'filter': True},
                            'rowSelection': 'single',
                        }).classes('w-full h-[500px] ag-theme-quartz-dark')

                        async def on_row():
                            row = await table.get_selected_row()
                            if row:
                                input_refs['id'].set_value(row['id'])
                                input_refs['name'].set_value(row['name'])
                                input_refs['description'].set_value(row['description'])
                        table.on('cellClicked', on_row)

    ui.timer(0.1, refresh_table, once=True)

@ui.page('/category')
def category_page_route():
    category_page()

# Alias for legacy compatibility
category_content = lambda standalone=False, user=None: category_page(standalone)
