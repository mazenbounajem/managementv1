with open('customer_receipt_ui_fixed_v2.py', 'r') as f:
    lines = f.readlines()

# Find the setup_ui method and remove the header lines
in_setup_ui = False
new_lines = []
for line in lines:
    if 'def setup_ui(self):' in line:
        in_setup_ui = True
        new_lines.append(line)
        continue
    if in_setup_ui:
        if 'uiAggridTheme.addingtheme()' in line:
            continue
        if 'with ui.header().classes(' in line:
            continue
        if "ui.label('Customer Receipt Management')" in line:
            continue
        if "ui.button('Back to Dashboard'" in line:
            continue
        if line.strip() == '' and len(new_lines) > 0 and new_lines[-1].strip() == '':
            continue  # Skip extra blank lines
        if "with ui.element('div').classes('flex w-full h-screen'):" in line:
            in_setup_ui = False
    new_lines.append(line)

# Now update the page route
in_page_route = False
final_lines = []
for line in new_lines:
    if "@ui.page('/customerreceipt')" in line:
        in_page_route = True
        final_lines.append(line)
        continue
    if in_page_route:
        if 'def customer_receipt_page_route():' in line:
            final_lines.append(line)
            final_lines.append('    uiAggridTheme.addingtheme()\n')
            final_lines.append('\n')
            final_lines.append('    # Check if user is logged in\n')
            final_lines.append("    user = session_storage.get('user')\n")
            final_lines.append('    if not user:\n')
            final_lines.append("        ui.notify('Please login to access this page', color='red')\n")
            final_lines.append('        ui.run_javascript(\'window.location.href = "/login"\')\n')
            final_lines.append('        return\n')
            final_lines.append('\n')
            final_lines.append('    # Get user permissions\n')
            final_lines.append("    permissions = connection.get_user_permissions(user['role_id'])\n")
            final_lines.append('    allowed_pages = {page for page, can_access in permissions.items() if can_access}\n')
            final_lines.append('\n')
            final_lines.append('    # Create enhanced navigation instance\n')
            final_lines.append('    navigation = EnhancedNavigation(permissions, user)\n')
            final_lines.append('    navigation.create_navigation_drawer()  # Create drawer first\n')
            final_lines.append('    navigation.create_navigation_header()  # Then create header with toggle button\n')
            final_lines.append('\n')
            final_lines.append('    CustomerReceipt()\n')
            in_page_route = False
            continue
        else:
            continue
    final_lines.append(line)

with open('customer_receipt_ui_fixed_v2.py', 'w') as f:
    f.writelines(final_lines)

print('Updated customer_receipt_ui_fixed_v2.py')
