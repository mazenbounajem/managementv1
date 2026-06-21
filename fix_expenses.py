with open('expenses.py', 'r') as f:
    lines = f.readlines()

# Remove the header from __init__
in_init = False
new_lines = []
for line in lines:
    if 'def __init__(self):' in line:
        in_init = True
        new_lines.append(line)
        continue
    if in_init:
        if 'with ui.header().classes(' in line:
            continue
        if "ui.label('Expenses Management')" in line:
            continue
        if "ui.button('Back to Dashboard'" in line:
            continue
        if line.strip() == '' and len(new_lines) > 0 and new_lines[-1].strip() == '':
            continue  # Skip extra blank lines
        if 'self.create_ui()' in line:
            in_init = False
    new_lines.append(line)

# Update the page route
in_page_route = False
final_lines = []
for line in new_lines:
    if "@ui.page('/expenses')" in line:
        in_page_route = True
        final_lines.append(line)
        continue
    if in_page_route:
        if 'def expenses_page_route():' in line:
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
            final_lines.append('    ExpensesUI()\n')
            in_page_route = False
            continue
        else:
            continue
    final_lines.append(line)

with open('expenses.py', 'w') as f:
    f.writelines(final_lines)

print('Updated expenses.py')
