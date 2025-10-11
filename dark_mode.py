from nicegui import ui
from color_palette import ColorPalette

class DarkModeToggle:
    def __init__(self):
        self.dark_mode = False

    def toggle(self):
        self.dark_mode = not self.dark_mode
        if self.dark_mode:
            # Apply dark theme with new color palette
            ui.add_css(f'''
                :root {{
                    --color-primary-dark: {ColorPalette.PRIMARY_LIGHT};
                    --color-primary-light: {ColorPalette.PRIMARY_DARK};
                    --color-secondary: #9b8bb3;
                    --color-accent: {ColorPalette.ACCENT};
                    
                    --color-header-bg: {ColorPalette.PRIMARY_DARK};
                    --color-header-text: {ColorPalette.PRIMARY_LIGHT};
                    
                    --color-main-bg: {ColorPalette.PRIMARY_DARK};
                    --color-main-text: {ColorPalette.PRIMARY_LIGHT};
                    
                    --color-row-odd: #5a5a5b;
                    --color-row-even: {ColorPalette.PRIMARY_DARK};
                    
                    --color-selection-bg: {ColorPalette.ACCENT};
                    --color-selection-text: {ColorPalette.PRIMARY_DARK};
                    
                    --color-hover-bg: {ColorPalette.ACCENT};
                    --color-hover-text: {ColorPalette.PRIMARY_DARK};
                    
                    --color-border: {ColorPalette.PRIMARY_LIGHT};
                    --color-border-light: #9b8bb3;
                }}
            ''')
            ui.run_javascript('document.documentElement.classList.add("dark")')
        else:
            # Apply light theme with original color palette
            ui.add_css(ColorPalette.get_css_variables())
            ui.run_javascript('document.documentElement.classList.remove("dark")')

def add_dark_mode_toggle():
    toggle = DarkModeToggle()
    with ui.header().classes('flex justify-end p-2').style(f'background-color: {ColorPalette.SECONDARY}'):
        ui.button('Toggle Dark Mode', on_click=toggle.toggle).style(f'background-color: {ColorPalette.BUTTON_SECONDARY_BG}; color: {ColorPalette.BUTTON_SECONDARY_TEXT}')

def create_themed_button(text, on_click=None, icon=None, button_type='primary'):
    """
    Create a button with the new color palette
    """
    if button_type == 'primary':
        bg_color = ColorPalette.BUTTON_PRIMARY_BG
        text_color = ColorPalette.BUTTON_PRIMARY_TEXT
    elif button_type == 'secondary':
        bg_color = ColorPalette.BUTTON_SECONDARY_BG
        text_color = ColorPalette.BUTTON_SECONDARY_TEXT
    elif button_type == 'accent':
        bg_color = ColorPalette.BUTTON_ACCENT_BG
        text_color = ColorPalette.BUTTON_ACCENT_TEXT
    elif button_type == 'success':
        bg_color = ColorPalette.SUCCESS
        text_color = 'white'
    elif button_type == 'error':
        bg_color = ColorPalette.ERROR
        text_color = 'white'
    elif button_type == 'warning':
        bg_color = ColorPalette.WARNING
        text_color = 'white'
    else:
        bg_color = ColorPalette.BUTTON_PRIMARY_BG
        text_color = ColorPalette.BUTTON_PRIMARY_TEXT
    
    button = ui.button(text, on_click=on_click, icon=icon)
    button.style(f'background-color: {bg_color}; color: {text_color}')
    return button
