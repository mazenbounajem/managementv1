"""
Modern UI Components Library
Reusable components for the management system
"""

from nicegui import ui
from modern_design_system import ModernDesignSystem as MDS
from typing import Optional, Callable, List, Dict, Any

class ModernCard(ui.card):
    """Modern card component with elevation and hover effects"""
    
    def __init__(self, elevated: bool = True, hoverable: bool = True, glass: bool = True):
        super().__init__()
        self.classes('card')
        if glass:
            self.classes('glass')
        if hoverable:
            self.classes('hover-lift')

    @staticmethod
    def create(*args, **kwargs):
        return ModernCard(*args, **kwargs)



class ModernCardHeader(ui.label):
    def __init__(self, title: str):
        super().__init__(title)
        self.classes('card-header')

class ModernCardBody(ui.element):
    def __init__(self):
        super().__init__('div')
        self.classes('card-body')

class ModernCardActions(ui.row):
    def __init__(self):
        super().__init__()
        self.classes('gap-2 mt-4 justify-end')
                        


class ModernButton(ui.button):
    """Modern button component with variants"""
    
    def __init__(self, label: str,
                 icon: Optional[str] = None,
                 variant: str = 'primary',
                 size: str = 'md',
                 on_click: Optional[Callable] = None,
                 disabled: bool = False,
                 loading: bool = False):
        super().__init__(label, on_click=on_click, icon=icon)
        
        btn_classes = f'btn btn-{variant} btn-{size}'
        self.classes(btn_classes)
        
        if variant == 'outline':
            self.props('flat')
            
        if disabled:
            self.props('disabled')

    @staticmethod
    def create(*args, **kwargs):
        return ModernButton(*args, **kwargs)




def ModernInput(label: str,
                placeholder: str = '',
                value: str = '',
                input_type: str = 'text',
                icon: Optional[str] = None,
                required: bool = False,
                disabled: bool = False,
                error: Optional[str] = None,
                helper: Optional[str] = None,
                on_change: Optional[Callable] = None):
    """
    Create a modern input field returning the nicegui element.
    """
    with ui.element('div').classes('input-group w-full'):
        # Label
        label_classes = 'input-label mb-1 ml-1'
        if required:
            label_classes += ' required'
        ui.label(label).classes(label_classes).style(f'color: {MDS.GRAY_700}; font-weight: {MDS.FONT_WEIGHT_BOLD}')
        
        # Input field
        input_classes = 'input-field w-full'
        if error:
            input_classes += ' error'
        
        if input_type == 'number':
            input_field = ui.number(
                placeholder=placeholder,
                value=float(value) if value else 0
            ).classes(input_classes).props('outlined dense')
        else:
            input_field = ui.input(
                placeholder=placeholder,
                value=value
            ).classes(input_classes).props('outlined dense')
            if input_type == 'password':
                input_field.props('type=password')
            elif input_type == 'email':
                input_field.props('type=email')
        
        if icon:
            with input_field.add_slot('prepend'):
                ui.icon(icon).classes('text-gray-400')
        
        if disabled:
            input_field.props('disabled')
        
        if on_change:
            input_field.on_value_change(on_change)
        
        # Helper or error text
        if error:
            ui.label(error).classes('input-error text-xs mt-1 ml-1')
        elif helper:
            ui.label(helper).classes('input-helper text-xs mt-1 ml-1')
        
        return input_field

# Add static create method to the function for consistency
ModernInput.create = ModernInput




class ModernTable(ui.aggrid):
    """Modern table component with sorting and filtering"""
    
    def __init__(self, columns: List[Dict],
                 rows: List[Dict],
                 selectable: bool = True,
                 sortable: bool = True,
                 filterable: bool = True,
                 pagination: bool = True,
                 page_size: int = 10,
                 on_row_click: Optional[Callable] = None):
                 
        grid_options = {
            'columnDefs': columns,
            'rowData': rows,
            'defaultColDef': {
                'flex': 1,
                'minWidth': 100,
                'sortable': sortable,
                'filter': filterable,
                'resizable': True
            },
            'rowSelection': 'single' if selectable else None,
            'pagination': pagination,
            'paginationPageSize': page_size,
            'domLayout': 'autoHeight',
            'animateRows': True,
            'rowClassRules': {
                'selected': 'data.selected === true'
            }
        }
        
        # nicegui.ui.aggrid needs to be wrapped manually to simulate the div
        # however extending aggrid is more flexible
        super().__init__(grid_options)
        self.classes('w-full ag-theme-quartz-custom')
        
        if on_row_click:
            self.on('cellClicked', on_row_click)

    @staticmethod
    def create(*args, **kwargs):
        return ModernTable(*args, **kwargs)



class ModernModal:
    """Modern modal dialog component"""
    
    @staticmethod
    def create(title: str,
               content: Optional[str] = None,
               size: str = 'md',
               actions: Optional[List[Dict]] = None,
               on_close: Optional[Callable] = None):
        """
        Create a modern modal
        
        Args:
            title: Modal title
            content: Modal content
            size: Modal size (sm, md, lg, xl)
            actions: Action buttons
            on_close: Close handler
        """
        with ui.dialog() as dialog:
            with ui.card().classes(f'modal modal-{size}'):
                # Header
                with ui.row().classes('modal-header'):
                    ui.label(title).classes('modal-title')
                    ui.button(
                        icon='close',
                        on_click=lambda: dialog.close()
                    ).props('flat round')
                
                # Body
                if content:
                    with ui.element('div').classes('modal-body'):
                        ui.html(content)
                
                # Footer
                if actions:
                    with ui.row().classes('modal-footer'):
                        for action in actions:
                            ModernButton.create(**action)
        
        return dialog


class ModernStats(ui.card):
    """Modern statistics card component"""
    
    def __init__(self, label: str,
                 value: str,
                 icon: str,
                 trend: Optional[str] = None,
                 trend_positive: bool = True,
                 color: str = MDS.SECONDARY):
        super().__init__()
        
        self.classes('p-6 glass hover-lift transition-all overflow-hidden').style(
            f'border-top: 4px solid {color};'
        )
        
        # Add decorative background icon
        with ui.row().classes('items-center justify-between w-full relative z-10'):
            with ui.column().classes('gap-1'):
                ui.label(label).classes('text-xs text-gray-500 font-bold uppercase tracking-wider')
                self.value_label = ui.label(value).classes('text-3xl font-black').style(
                    f'color: {MDS.PRIMARY_DARK}; font-family: "Outfit", sans-serif;'
                )
                
                if trend:
                    trend_color = MDS.SUCCESS if trend_positive else MDS.ERROR
                    trend_icon = 'trending_up' if trend_positive else 'trending_down'
                    with ui.row().classes('items-center gap-1 bg-white/50 px-2 py-0.5 rounded-full'):
                        ui.icon(trend_icon).style(f'color: {trend_color}; font-size: 14px;')
                        self.trend_label = ui.label(trend).classes('text-sm font-bold').style(f'color: {trend_color};')
            
            with ui.element('div').classes('p-3 rounded-2xl').style(f'background: {color}20'):
                ui.icon(icon).style(
                    f'font-size: 32px; color: {color};'
                )

    @staticmethod
    def create(*args, **kwargs):
        return ModernStats(*args, **kwargs)


            
    def update_value(self, new_value: str):
         self.value_label.set_text(new_value)


class ModernBadge(ui.label):
    """Modern badge component"""
    
    def __init__(self, text: str,
                 variant: str = 'default',
                 size: str = 'md'):
        super().__init__(text)
        
        colors = {
            'default': (MDS.GRAY_200, MDS.GRAY_800),
            'success': (MDS.SUCCESS_LIGHT, MDS.WHITE),
            'warning': (MDS.WARNING_LIGHT, MDS.WHITE),
            'error': (MDS.ERROR_LIGHT, MDS.WHITE),
            'info': (MDS.INFO_LIGHT, MDS.WHITE),
        }
        
        sizes = {
            'sm': ('0.625rem', '0.25rem 0.5rem'),
            'md': ('0.75rem', '0.375rem 0.75rem'),
            'lg': ('0.875rem', '0.5rem 1rem'),
        }
        
        bg_color, text_color = colors.get(variant, colors['default'])
        font_size, padding = sizes.get(size, sizes['md'])
        
        self.style(
            f'background: {bg_color}; color: {text_color}; '
            f'padding: {padding}; border-radius: {MDS.BORDER_RADIUS_FULL}; '
            f'font-size: {font_size}; font-weight: {MDS.FONT_WEIGHT_SEMIBOLD}; '
            f'display: inline-block;'
        )

    @staticmethod
    def create(*args, **kwargs):
        return ModernBadge(*args, **kwargs)



class ModernToast:
    """Modern toast notification"""
    
    @staticmethod
    def show(message: str,
             variant: str = 'info',
             duration: int = 3000,
             position: str = 'top-right'):
        """
        Show a toast notification
        
        Args:
            message: Toast message
            variant: Toast variant (success, warning, error, info)
            duration: Duration in milliseconds
            position: Toast position
        """
        colors = {
            'success': MDS.SUCCESS,
            'warning': MDS.WARNING,
            'error': MDS.ERROR,
            'info': MDS.INFO,
        }
        
        icons = {
            'success': 'check_circle',
            'warning': 'warning',
            'error': 'error',
            'info': 'info',
        }
        
        color = colors.get(variant, colors['info'])
        icon = icons.get(variant, icons['info'])
        
        ui.notify(
            message,
            type=variant,
            position=position,
            close_button=True,
            timeout=duration,
            icon=icon,
            color=color
        )


class ModernProgressBar(ui.column):
    """Modern progress bar component"""
    
    def __init__(self, value: float,
                 max_value: float = 100,
                 label: Optional[str] = None,
                 show_percentage: bool = True,
                 color: str = MDS.ACCENT):
        super().__init__()
        
        self.max_value = max_value
        self.color = color
        self.show_percentage = show_percentage
        self.classes('w-full gap-2')
        
        percentage = (value / max_value) * 100
        
        if label or show_percentage:
            with ui.row().classes('justify-between items-center w-full'):
                if label:
                    ui.label(label).classes('text-sm font-medium')
                if show_percentage:
                    self.percent_label = ui.label(f'{percentage:.0f}%').classes('text-sm font-bold')
        
        with ui.element('div').style(
            f'width: 100%; height: 8px; background: {MDS.GRAY_200}; '
            f'border-radius: {MDS.BORDER_RADIUS_FULL}; overflow: hidden;'
        ):
            self.bar_element = ui.element('div').style(
                f'width: {percentage}%; height: 100%; background: {color}; '
                f'transition: width {MDS.TRANSITION_BASE} ease-in-out;'
            )

    @staticmethod
    def create(*args, **kwargs):
        return ModernProgressBar(*args, **kwargs)

            
    def set_value(self, new_value: float):
        percentage = (new_value / self.max_value) * 100
        self.bar_element.style(f'width: {percentage}%;')
        if self.show_percentage:
             self.percent_label.set_text(f'{percentage:.0f}%')


class ModernTabs(ui.column):
    """Modern tabs component"""
    
    def __init__(self, tabs: List[Dict],
                 default_tab: int = 0):
        super().__init__()
        
        self.classes('w-full gap-4')
        self.tab_buttons = []
        self.tab_contents = []
        
        # Tab buttons
        with ui.row().classes('gap-2 border-b-2').style(
            f'border-color: {MDS.GRAY_200};'
        ):
            for i, tab in enumerate(tabs):
                btn = ui.button(
                    f"{tab.get('icon', '')} {tab['label']}",
                    on_click=lambda idx=i: self.switch_tab(idx)
                ).props('flat').style(
                    f'border-bottom: 3px solid {"transparent" if i != default_tab else MDS.ACCENT};'
                )
                self.tab_buttons.append(btn)
        
        # Tab contents
        for i, tab in enumerate(tabs):
            with ui.element('div').classes('tab-content') as content:
                if i != default_tab:
                    content.style('display: none;')
                ui.html(tab.get('content', ''))
                self.tab_contents.append(content)
        
    def switch_tab(self, index):
        for i, (btn, content) in enumerate(zip(self.tab_buttons, self.tab_contents)):
            if i == index:
                btn.style(f'border-bottom: 3px solid {MDS.ACCENT};')
                content.style('display: block;')
            else:
                btn.style('border-bottom: 3px solid transparent;')
                content.style('display: none;')


def ModernSearchBar(placeholder: str = 'Search...',
                    on_search: Optional[Callable] = None,
                    with_filters: bool = False):
    """
    Create a search bar returning the nicegui element.
    """
    with ui.row().classes('items-center gap-2 w-full').style(
        f'background: {MDS.WHITE}; padding: {MDS.SPACE_2}; '
        f'border-radius: {MDS.BORDER_RADIUS_LG}; '
        f'box-shadow: {MDS.SHADOW_MD};'
    ):
        ui.icon('search').style(f'color: {MDS.GRAY_500};')
        
        search_input = ui.input(placeholder=placeholder).classes(
            'flex-1'
        ).props('borderless')
        
        if on_search:
            search_input.on('keydown.enter', lambda e: on_search(e.sender.value))
        
        if with_filters:
            ui.button(icon='filter_list').props('flat round')
        
        return search_input

# Add static create method to the function for consistency
ModernSearchBar.create = ModernSearchBar



class ModernTimeline(ui.column):
    """Modern timeline component"""
    
    def __init__(self, items: List[Dict]):
        super().__init__()
        
        self.classes('gap-4')
        for i, item in enumerate(items):
            with ui.row().classes('gap-4 items-start'):
                # Timeline dot
                with ui.column().classes('items-center gap-2'):
                    with ui.element('div').style(
                        f'width: 40px; height: 40px; border-radius: {MDS.BORDER_RADIUS_FULL}; '
                        f'background: {MDS.ACCENT}; display: flex; align-items: center; '
                        f'justify-content: center; box-shadow: {MDS.SHADOW_MD};'
                    ):
                        ui.icon(item.get('icon', 'circle')).style('color: white;')
                    
                    if i < len(items) - 1:
                        ui.element('div').style(
                            f'width: 2px; height: 60px; background: {MDS.GRAY_300};'
                        )
                
                # Timeline content
                with ui.column().classes('flex-1 gap-1'):
                    ui.label(item['title']).classes('font-bold text-lg')
                    ui.label(item.get('description', '')).classes('text-gray-600')
                    ui.label(item.get('date', '')).classes('text-sm text-gray-500')
