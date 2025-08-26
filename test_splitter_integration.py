"""
Test file to demonstrate Quasar splitter functionality with existing sales grids
"""

from nicegui import ui

class TestSplitterIntegration:
    """Test class to demonstrate splitter integration"""
    
    def __init__(self):
        self.create_test_ui()

    def create_test_ui(self):
        """Create test UI with splitter functionality"""
        with ui.element('div').classes('w-full h-screen flex flex-col'):
            # Header
            with ui.header().classes('items-center justify-between'):
                ui.label('Quasar Splitter Test').classes('text-2xl font-bold')
                ui.button('Back', on_click=lambda: ui.navigate.to('/dashboard')).props('flat color=white')

            # Main content with splitter
            with ui.splitter(horizontal=True, value=50).classes('w-full flex-grow') as splitter:
                with splitter.before:
                    ui.label('Top Grid').classes('text-lg font-bold mb-4')
                    ui.aggrid({
                        'columnDefs': [
                            {'headerName': 'ID', 'field': 'id'},
                            {'headerName': 'Name', 'field': 'name'},
                            {'headerName': 'Value', 'field': 'value'}
                        ],
                        'rowData': [
                            {'id': 1, 'name': 'Item 1', 'value': 100},
                            {'id': 2, 'name': 'Item 2', 'value': 200},
                            {'id': 3, 'name': 'Item 3', 'value': 300}
                        ]
                    }).classes('w-full h-full')

                with splitter.after:
                    ui.label('Bottom Grid').classes('text-lg font-bold mb-4')
                    ui.aggrid({
                        'columnDefs': [
                            {'headerName': 'Code', 'field': 'code'},
                            {'headerName': 'Description', 'field': 'description'},
                            {'headerName': 'Price', 'field': 'price'}
                        ],
                        'rowData': [
                            {'code': 'A001', 'description': 'Product A', 'price': 50},
                            {'code': 'A002', 'description': 'Product B', 'price': 75},
                            {'code': 'A003', 'description': 'Product C', 'price': 100}
                        ]
                    }).classes('w-full h-full')

            # Controls
            with ui.row().classes('mt-4 gap-2'):
                ui.button('Adjust Splitter', on_click=lambda: splitter.set_value(60))
                ui.button('Reset', on_click=lambda: splitter.set_value(50))

@ui.page('/test-splitter')
def test_splitter_page():
    """Test page for splitter functionality"""
    TestSplitterIntegration()

@ui.page('/quick-demo')
def quick_demo():
    """Quick demonstration of splitter with grids"""
    with ui.element('div').classes('w-full h-screen p-4'):
        ui.label('Quasar Splitter Demo').classes('text-2xl font-bold mb-4')
        
        # Horizontal splitter
        with ui.splitter(horizontal=True, value=40).classes('w-full h-96') as splitter:
            with splitter.before:
                ui.label('Top Grid').classes('text-lg font-bold')
                ui.aggrid({
                    'columnDefs': [
                        {'headerName': 'ID', 'field': 'id'},
                        {'headerName': 'Name', 'field': 'name'},
                        {'headerName': 'Value', 'field': 'value'}
                    ],
                    'rowData': [
                        {'id': 1, 'name': 'Item 1', 'value': 100},
                        {'id': 2, 'name': 'Item 2', 'value': 200},
                        {'id': 3, 'name': 'Item 3', 'value': 300}
                    ]
                }).classes('w-full h-full')

            with splitter.after:
                ui.label('Bottom Grid').classes('text-lg font-bold')
                ui.aggrid({
                    'columnDefs': [
                        {'headerName': 'Code', 'field': 'code'},
                        {'headerName': 'Description', 'field': 'description'},
                        {'headerName': 'Price', 'field': 'price'}
                    ],
                    'rowData': [
                        {'code': 'A001', 'description': 'Product A', 'price': 50},
                        {'code': 'A002', 'description': 'Product B', 'price': 75},
                        {'code': 'A003', 'description': 'Product C', 'price': 100}
                    ]
                }).classes('w-full h-full')

        # Controls
        with ui.row().classes('mt-4 gap-2'):
            ui.button('Adjust Splitter', on_click=lambda: splitter.set_value(60))
            ui.button('Reset', on_click=lambda: splitter.set_value(50))

if __name__ in {"__main__", "__mp_main__"}:
        ui.run()
