from nicegui import ui
from connection import connection
from modern_design_system import ModernDesignSystem as MDS
from modern_page_layout import ModernPageLayout
from modern_ui_components import ModernCard, ModernButton, ModernInput, ModernTable
from session_storage import session_storage
from datetime import datetime
import base64
import io

def customer_page(standalone=False):
    # Auth
    user = session_storage.get('user')
    if not user:
        if not standalone:
            ui.notify('Please login', color='negative')
            ui.navigate.to('/login')
        return

    # State
    input_refs = {}
    # Removed customer_photos cache to keep memory lightweight

    def handle_photo_upload(e):
        try:
            content = e.content.read()
            # Determine mime type or just assume png/jpeg
            base64_str = base64.b64encode(content).decode('ascii')
            mime_type = "image/png" # Default, could be refined
            input_refs['photo'].set_value(f"data:{mime_type};base64,{base64_str}")
            photo_preview.set_source(f"data:{mime_type};base64,{base64_str}")
            ui.notify('Photo uploaded', color='positive')
        except Exception as ex:
            ui.notify(f'Upload error: {ex}', color='negative')

    def refresh_table():
        data = []
        # Query metadata and photo existence flag
        sql = """SELECT id, customer_name, email, phone, address, city, balance, is_active, 
                 CASE WHEN photo IS NOT NULL AND photo != '' THEN 1 ELSE 0 END as has_photo,
                 instagram, facebook, twitter, tiktok,
                 COALESCE((SELECT SUM(ISNULL(s.total_amount, 0)) FROM sales s WHERE s.customer_id = c.id AND s.payment_status = 'pending'), 0) as pending_sales
                 FROM customers c ORDER BY id DESC"""
        connection.contogetrows(sql, data)
        rows = []
        
        for r in data:
            rows.append({
                'id': r[0], 'customer_name': r[1], 'email': r[2], 'phone': r[3], 'address': r[4], 
                'city': r[5], 'balance': r[6], 'is_active': r[7], 'has_photo': bool(r[8]),
                'instagram': r[9], 'facebook': r[10], 'twitter': r[11], 'tiktok': r[12], 'pending_sales': to_float(r[13])
            })
        table.options['rowData'] = rows
        table.update()

    def clear_inputs():
        for k, ref in input_refs.items():
            if k == 'is_active': ref.set_value(True)
            elif k == 'balance': ref.set_value(0)
            else: ref.set_value('')
        photo_preview.set_source('https://via.placeholder.com/150')
        table.run_method('deselectAll')

    def save_customer():
        try:
            c_data = {k: ref.value for k, ref in input_refs.items()}
            if not c_data['customer_name']:
                return ui.notify('Customer name required', color='negative')

            if c_data['id']:
                sql = """UPDATE customers SET customer_name=?, email=?, phone=?, address=?, 
                         city=?, balance=?, is_active=?, photo=?, instagram=?, facebook=?, twitter=?, tiktok=? WHERE id=?"""
                params = (c_data['customer_name'], c_data['email'], c_data['phone'], c_data['address'],
                          c_data['city'], float(c_data['balance'] or 0), bool(c_data['is_active']), 
                          c_data['photo'], c_data['instagram'], c_data['facebook'], c_data['twitter'], c_data['tiktok'],
                          c_data['id'])
            else:
                sql = """INSERT INTO customers (customer_name, email, phone, address, city, balance, 
                         created_at, is_active, photo, instagram, facebook, twitter, tiktok) 
                         VALUES (?, ?, ?, ?, ?, ?, GETDATE(), ?, ?, ?, ?, ?, ?)"""
                params = (c_data['customer_name'], c_data['email'], c_data['phone'], c_data['address'],
                          c_data['city'], float(c_data['balance'] or 0), bool(c_data['is_active']),
                          c_data['photo'], c_data['instagram'], c_data['facebook'], c_data['twitter'], c_data['tiktok'])

            connection.insertingtodatabase(sql, params)
            ui.notify('Customer saved', color='positive')
            refresh_table()
        except Exception as e:
            ui.notify(f'Error: {e}', color='negative')

    with ModernPageLayout("Customer Management", standalone=standalone):
        with ui.column().classes('w-full gap-6 p-4 animate-fade-in'):
            
            with ui.row().classes('w-full gap-6 items-start'):
                # Form
                with ui.column().classes('w-[400px] gap-4'):
                    # Photo Card
                    with ModernCard().classes('w-full p-6 flex flex-col items-center'):
                        ui.label('Photo Profile').classes('text-lg font-bold mb-4 w-full text-center')
                        photo_preview = ui.image('https://via.placeholder.com/150').classes('w-40 h-40 rounded-full border-4 border-accent shadow-xl object-cover mb-4')
                        input_refs['photo'] = ui.input().classes('hidden') # State holder
                        ui.upload(on_upload=handle_photo_upload, auto_upload=True).props('flat bordered dense label="Upload Photo" accept=".jpg,.png,.jpeg"').classes('w-full')
                        ui.label('Click above to change').classes('text-xs text-gray-500 mt-1 uppercase tracking-widest')

                    with ModernCard().classes('w-full p-6'):
                        ui.label('Client Details').classes('text-lg font-bold mb-4')
                        input_refs['id'] = ui.input('ID').props('readonly outlined dense').classes('hidden')
                        input_refs['customer_name'] = ModernInput('Full Name', icon='person')
                        input_refs['email'] = ModernInput('Email', icon='email')
                        input_refs['phone'] = ModernInput('Phone', icon='phone')

                    with ModernCard().classes('w-full p-6'):
                        ui.label('Social Accounts').classes('text-lg font-bold mb-4')
                        input_refs['instagram'] = ModernInput('Instagram', icon='camera_alt', placeholder='@username')
                        input_refs['facebook'] = ModernInput('Facebook', icon='facebook')
                        input_refs['twitter'] = ModernInput('X (Twitter)', icon='close')
                        input_refs['tiktok'] = ModernInput('TikTok', icon='music_note')

                    with ModernCard().classes('w-full p-6'):
                        ui.label('Profile Settings').classes('text-lg font-bold mb-4')
                        input_refs['address'] = ui.input('Address').props('outlined dense').classes('w-full')
                        input_refs['city'] = ui.input('City').props('outlined dense').classes('w-full mt-2')
                        input_refs['balance'] = ui.number('Account Balance').props('outlined dense').classes('w-full mt-2')
                        input_refs['is_active'] = ui.checkbox('Active', value=True).classes('mt-2')

                # List
                with ui.column().classes('flex-1'):
                    with ModernCard().classes('w-full p-4'):
                        ui.label('Client Repository').classes('text-lg font-bold mb-4 ml-2')
                        
                        cols = [
                            {'headerName': 'Photo', 'field': 'photo', 'width': 70, 'cellRenderer': 'img_renderer'}, # Placeholder for custom renderer if needed
                            {'headerName': 'Name', 'field': 'customer_name', 'flex': 2},
                            {'headerName': 'Email', 'field': 'email', 'flex': 1.5},
                            {'headerName': 'Phone', 'field': 'phone', 'width': 130},
                            {'headerName': 'Pending Sales', 'field': 'pending_sales', 'width': 110},
                            {'headerName': 'Balance', 'field': 'balance', 'width': 120},
                            {'headerName': 'Status', 'field': 'is_active', 'cellRenderer': 'agCheckboxRenderer'}
                        ]
                        
                        # Custom renderer script for images in ag-grid if base64
                        ui.add_body_html('''
                        <script>
                        window.img_renderer = (params) => {
                            if (!params.data.has_photo) return "";
                            return `<div style="width: 24px; height: 24px; border-radius: 50%; background: var(--primary); display: flex; align-items: center; justify-content: center;">
                                <span style="font-size: 8px; color: white;">P</span>
                            </div>`;
                        };
                        </script>
                        ''')

                        table = ui.aggrid({
                            'columnDefs': cols,
                            'rowData': [],
                            'defaultColDef': {'sortable': True, 'filter': True},
                            'rowSelection': 'single',
                        }).classes('w-full h-[600px] ag-theme-quartz-dark')

                        def on_row(e):
                            try:
                                # Instant response from click event data
                                row = e.args.get('data')
                                if not row: return
                                
                                cid = row.get('id')
                                if cid is None: return
                                
                                # Update inputs immediately
                                input_refs['id'].set_value(str(cid))
                                for k in ['customer_name', 'email', 'phone', 'address', 'city', 'balance', 'is_active', 'instagram', 'facebook', 'twitter', 'tiktok']:
                                    if k in row: input_refs[k].set_value(row[k])
                                
                                # Fetch high-res photo on-demand from database
                                photo_data = []
                                connection.contogetrows(f"SELECT photo FROM customers WHERE id = {cid}", photo_data)
                                full_photo = photo_data[0][0] if photo_data else None
                                
                                input_refs['photo'].set_value(full_photo or '')
                                if full_photo:
                                    photo_preview.set_source(full_photo)
                                else:
                                    photo_preview.set_source('https://via.placeholder.com/150')
                            except Exception as ex:
                                print(f"Customer selection error: {ex}")
                                ui.notify(f'Display error: {ex}', color='warning')

                        table.on('cellClicked', on_row)

                # Action Bar Panel (Right Side of Editor)
                with ui.column().classes('w-80px items-center'):
                    from modern_ui_components import ModernActionBar
                    ModernActionBar(
                        on_new=clear_inputs,
                        on_save=save_customer,
                        on_undo=lambda: ui.notify('Undo not implemented for customers'),
                        on_delete=lambda: ui.notify('Delete currently disabled'),
                        on_chatgpt=lambda: ui.open('https://chatgpt.com', new_tab=True),
                        on_refresh=refresh_table,
                        button_class='h-16',
                        classes=' '
                    ).style('position: static; width: 80px; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.15); margin-top: 0;')

    ui.timer(0.1, refresh_table, once=True)


@ui.page('/customers')
def customer_page_route():
    customer_page()
