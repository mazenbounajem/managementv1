# Modern Design System - Quick Start Guide

## 🚀 Getting Started in 5 Minutes

### 1. Import Required Modules
```python
from nicegui import ui
from modern_design_system import ModernDesignSystem as MDS
from modern_ribbon_navigation import ModernRibbonNavigation, ModernActionDrawer
from modern_ui_components import *
from session_storage import session_storage
```

### 2. Basic Page Template
```python
@ui.page('/your-page')
def your_page():
    # Check authentication
    user = session_storage.get('user')
    if not user:
        ui.notify('Please login', color='red')
        ui.run_javascript('window.location.href = "/login"')
        return
    
    # Add global styles
    ui.add_head_html(MDS.get_global_styles())
    
    # Create ribbon navigation
    ribbon = ModernRibbonNavigation(user_info={
        'name': user.get('username', 'User'),
        'role': user.get('role', 'Admin'),
        'initials': user.get('username', 'U')[0].upper()
    })
    ribbon.create_ribbon()
    
    # Main layout
    with ui.row().classes('w-full').style('height: calc(100vh - 160px);'):
        # Action drawer
        drawer = ModernActionDrawer(actions=[
            {'icon': 'add', 'label': 'New', 'action': create_new},
            {'icon': 'save', 'label': 'Save', 'action': save},
        ])
        drawer.create_drawer()
        
        # Main content
        with ui.column().classes('flex-1 p-6 overflow-y-auto').style(
            f'margin-left: {MDS.DRAWER_WIDTH_COLLAPSED}; background: {MDS.GRAY_50};'
        ):
            # Your content here
            create_stats()
            create_form()
            create_table()
```

### 3. Add Statistics Dashboard
```python
def create_stats():
    with ui.row().classes('w-full gap-4 mb-6'):
        ModernStats.create(
            label='Total Records',
            value='1,234',
            icon='inventory',
            trend='+12%',
            trend_positive=True,
            color=MDS.SUCCESS
        )
        
        ModernStats.create(
            label='Active Users',
            value='56',
            icon='people',
            trend='+5',
            trend_positive=True,
            color=MDS.INFO
        )
```

### 4. Create Modern Form
```python
def create_form():
    with ui.card().classes('p-6 mb-6').style(
        f'box-shadow: {MDS.SHADOW_LG}; border-radius: {MDS.BORDER_RADIUS_XL};'
    ):
        ui.label('Form Title').classes('text-xl font-bold mb-4')
        
        with ui.row().classes('w-full gap-4'):
            name_input = ModernInput.create(
                label='Name',
                placeholder='Enter name',
                required=True
            )
            
            email_input = ModernInput.create(
                label='Email',
                placeholder='Enter email',
                input_type='email',
                required=True
            )
        
        with ui.row().classes('gap-2 mt-4'):
            ModernButton.create(
                label='Save',
                icon='save',
                variant='success',
                on_click=save_form
            )
            
            ModernButton.create(
                label='Cancel',
                icon='close',
                variant='outline',
                on_click=cancel_form
            )
```

### 5. Create Modern Table
```python
def create_table():
    columns = [
        {'headerName': 'ID', 'field': 'id', 'width': 80},
        {'headerName': 'Name', 'field': 'name', 'width': 200},
        {'headerName': 'Email', 'field': 'email', 'width': 200},
        {'headerName': 'Status', 'field': 'status', 'width': 100},
    ]
    
    rows = [
        {'id': 1, 'name': 'John Doe', 'email': 'john@example.com', 'status': 'Active'},
        {'id': 2, 'name': 'Jane Smith', 'email': 'jane@example.com', 'status': 'Active'},
    ]
    
    table = ModernTable.create(
        columns=columns,
        rows=rows,
        selectable=True,
        sortable=True,
        filterable=True,
        pagination=True,
        on_row_click=handle_row_click
    )
```

### 6. Show Notifications
```python
def save_form():
    try:
        # Save logic here
        ModernToast.show('Saved successfully!', 'success')
    except Exception as e:
        ModernToast.show(f'Error: {str(e)}', 'error')
```

---

## 📚 Component Cheat Sheet

### Buttons
```python
# Primary button
ModernButton.create(label='Save', icon='save', variant='primary')

# Success button
ModernButton.create(label='Add', icon='add', variant='success')

# Danger button
ModernButton.create(label='Delete', icon='delete', variant='danger')

# Outline button
ModernButton.create(label='Cancel', icon='close', variant='outline')

# Small button
ModernButton.create(label='Edit', icon='edit', size='sm')
```

### Inputs
```python
# Text input
ModernInput.create(label='Name', placeholder='Enter name', required=True)

# Number input
ModernInput.create(label='Age', input_type='number', value='0')

# Email input
ModernInput.create(label='Email', input_type='email')

# Password input
ModernInput.create(label='Password', input_type='password')

# With error
ModernInput.create(label='Name', error='This field is required')

# With helper text
ModernInput.create(label='Name', helper='Enter your full name')
```

### Cards
```python
# Simple card
ModernCard.create(
    title='Card Title',
    content='<p>Card content here</p>'
)

# Card with actions
ModernCard.create(
    title='Confirm',
    content='<p>Are you sure?</p>',
    actions=[
        {'label': 'Yes', 'variant': 'primary', 'on_click': confirm},
        {'label': 'No', 'variant': 'outline', 'on_click': cancel}
    ]
)
```

### Stats Cards
```python
ModernStats.create(
    label='Total Sales',
    value='$12,450',
    icon='point_of_sale',
    trend='+12.5%',
    trend_positive=True,
    color=MDS.SUCCESS
)
```

### Badges
```python
ModernBadge.create(text='Active', variant='success')
ModernBadge.create(text='Pending', variant='warning')
ModernBadge.create(text='Error', variant='error')
ModernBadge.create(text='Info', variant='info')
```

### Toasts
```python
ModernToast.show('Success!', 'success')
ModernToast.show('Warning!', 'warning')
ModernToast.show('Error!', 'error')
ModernToast.show('Info!', 'info')
```

### Progress Bars
```python
ModernProgressBar.create(
    value=75,
    max_value=100,
    label='Upload Progress',
    show_percentage=True,
    color=MDS.SUCCESS
)
```

### Search Bar
```python
ModernSearchBar.create(
    placeholder='Search...',
    on_search=search_handler,
    with_filters=True
)
```

### Modals
```python
dialog = ModernModal.create(
    title='Confirm Action',
    content='<p>Are you sure you want to proceed?</p>',
    size='md',
    actions=[
        {'label': 'Cancel', 'variant': 'outline', 'on_click': lambda: dialog.close()},
        {'label': 'Confirm', 'variant': 'primary', 'on_click': confirm_action}
    ]
)
dialog.open()
```

---

## 🎨 Design Tokens Quick Reference

### Colors
```python
# Primary colors
MDS.PRIMARY_DARK      # #404041
MDS.PRIMARY_LIGHT     # #f6ede3
MDS.SECONDARY         # #d3cae2
MDS.ACCENT            # #e6c17a

# Semantic colors
MDS.SUCCESS           # #4CAF50
MDS.WARNING           # #FF9800
MDS.ERROR             # #F44336
MDS.INFO              # #2196F3

# Grays
MDS.GRAY_50           # Lightest
MDS.GRAY_100
MDS.GRAY_200
...
MDS.GRAY_900          # Darkest
```

### Typography
```python
# Font sizes
MDS.FONT_SIZE_TINY    # 10px
MDS.FONT_SIZE_SMALL   # 12px
MDS.FONT_SIZE_BASE    # 14px
MDS.FONT_SIZE_MEDIUM  # 16px
MDS.FONT_SIZE_LARGE   # 18px
MDS.FONT_SIZE_XL      # 20px
MDS.FONT_SIZE_2XL     # 24px
MDS.FONT_SIZE_3XL     # 32px

# Font weights
MDS.FONT_WEIGHT_NORMAL    # 400
MDS.FONT_WEIGHT_MEDIUM    # 500
MDS.FONT_WEIGHT_SEMIBOLD  # 600
MDS.FONT_WEIGHT_BOLD      # 700
```

### Spacing
```python
MDS.SPACE_1    # 4px
MDS.SPACE_2    # 8px
MDS.SPACE_3    # 12px
MDS.SPACE_4    # 16px
MDS.SPACE_6    # 24px
MDS.SPACE_8    # 32px
MDS.SPACE_12   # 48px
```

### Shadows
```python
MDS.SHADOW_SM    # Small shadow
MDS.SHADOW_MD    # Medium shadow
MDS.SHADOW_LG    # Large shadow
MDS.SHADOW_XL    # Extra large shadow
```

### Border Radius
```python
MDS.BORDER_RADIUS_SM    # 4px
MDS.BORDER_RADIUS_MD    # 6px
MDS.BORDER_RADIUS_LG    # 8px
MDS.BORDER_RADIUS_XL    # 12px
MDS.BORDER_RADIUS_FULL  # 9999px (circle)
```

---

## 🔧 Common Patterns

### Loading State
```python
with ui.row().classes('items-center gap-2'):
    ui.spinner(size='sm')
    ui.label('Loading...')
```

### Empty State
```python
with ui.column().classes('items-center justify-center p-12'):
    ui.icon('inbox').style('font-size: 64px; opacity: 0.3;')
    ui.label('No data available').classes('text-lg text-gray-600')
    ModernButton.create(
        label='Add New',
        icon='add',
        variant='primary',
        on_click=add_new
    )
```

### Confirmation Dialog
```python
def confirm_delete():
    dialog = ModernModal.create(
        title='Confirm Delete',
        content='<p>Are you sure you want to delete this item?</p>',
        actions=[
            {'label': 'Cancel', 'variant': 'outline', 'on_click': lambda: dialog.close()},
            {'label': 'Delete', 'variant': 'danger', 'on_click': lambda: [delete_item(), dialog.close()]}
        ]
    )
    dialog.open()
```

### Form Validation
```python
def validate_form():
    errors = []
    
    if not name_input.value:
        errors.append('Name is required')
    
    if not email_input.value:
        errors.append('Email is required')
    
    if errors:
        for error in errors:
            ModernToast.show(error, 'error')
        return False
    
    return True

def save_form():
    if validate_form():
        # Save logic
        ModernToast.show('Saved successfully!', 'success')
```

### Search and Filter
```python
def create_search_section():
    with ui.row().classes('w-full gap-4 mb-4'):
        search = ModernSearchBar.create(
            placeholder='Search records...',
            on_search=perform_search
        )
        
        with ui.row().classes('gap-2'):
            ui.select(
                ['All', 'Active', 'Inactive'],
                value='All',
                label='Status'
            ).on('change', filter_by_status)
            
            ui.date(label='From Date').on('change', filter_by_date)
```

---

## ⌨️ Keyboard Shortcuts

Add to your page:
```python
# Global shortcuts
ui.keyboard(lambda e: save_form() if e.key == 's' and e.action.keydown and e.modifiers.ctrl else None)
ui.keyboard(lambda e: new_record() if e.key == 'n' and e.action.keydown and e.modifiers.ctrl else None)
ui.keyboard(lambda e: print_page() if e.key == 'p' and e.action.keydown and e.modifiers.ctrl else None)
```

---

## 🐛 Common Issues & Solutions

### Issue: Styles not applying
**Solution**: Make sure to add global styles at the top of your page:
```python
ui.add_head_html(MDS.get_global_styles())
```

### Issue: Drawer overlapping content
**Solution**: Add left margin to main content:
```python
.style(f'margin-left: {MDS.DRAWER_WIDTH_COLLAPSED};')
```

### Issue: Table not updating
**Solution**: Update table data and call update():
```python
table.options['rowData'] = new_data
table.update()
```

### Issue: Toast not showing
**Solution**: Import and use ModernToast:
```python
from modern_ui_components import ModernToast
ModernToast.show('Message', 'success')
```

---

## 📖 Additional Resources

- **Full Documentation**: See `MODERN_DESIGN_IMPLEMENTATION.md`
- **TODO List**: See `MODERN_DESIGN_TODO.md`
- **Example Implementation**: See `modern_sales_ui.py`
- **NiceGUI Docs**: https://nicegui.io
- **AG Grid Docs**: https://www.ag-grid.com

---

## 💡 Tips & Best Practices

1. **Always use design tokens** instead of hardcoded values
2. **Use ModernToast** instead of ui.notify for consistency
3. **Add loading states** for async operations
4. **Validate forms** before submission
5. **Provide feedback** for all user actions
6. **Use keyboard shortcuts** for power users
7. **Test on different screen sizes**
8. **Keep components reusable**
9. **Document complex logic**
10. **Follow naming conventions**

---

**Happy Coding! 🚀**
