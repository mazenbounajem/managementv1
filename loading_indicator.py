from nicegui import ui
import asyncio
from contextlib import asynccontextmanager

class LoadingIndicator:
    """Reusable loading indicator component for database operations and UI feedback"""

    def __init__(self):
        self.loading_elements = {}
        self.spinner = None

    def create_spinner(self, message="Loading...", size="md"):
        """Create a loading spinner with message"""
        with ui.element('div').classes('flex items-center justify-center p-4') as container:
            with ui.element('div').classes('flex flex-col items-center gap-2'):
                ui.spinner(size=size).classes('text-blue-500')
                ui.label(message).classes('text-sm text-gray-600')
        return container

    def create_overlay_spinner(self, message="Loading...", size="lg"):
        """Create a full-screen overlay loading spinner"""
        overlay = ui.element('div').classes('fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50')
        with overlay:
            with ui.element('div').classes('bg-white rounded-lg p-6 flex flex-col items-center gap-4 shadow-lg'):
                ui.spinner(size=size).classes('text-blue-500')
                ui.label(message).classes('text-lg font-medium text-gray-700')
        return overlay

    def create_progress_bar(self, message="Processing..."):
        """Create a progress bar for long operations"""
        with ui.element('div').classes('w-full p-4') as container:
            ui.label(message).classes('text-sm text-gray-600 mb-2')
            progress = ui.linear_progress(value=0).classes('w-full')
        return container, progress

    @asynccontextmanager
    async def show_loading(self, element_id, message="Loading...", overlay=False):
        """Context manager for showing loading indicator during async operations"""
        if overlay:
            spinner = self.create_overlay_spinner(message)
        else:
            spinner = self.create_spinner(message)

        self.loading_elements[element_id] = spinner

        try:
            yield
        finally:
            if element_id in self.loading_elements:
                self.loading_elements[element_id].delete()
                del self.loading_elements[element_id]

    async def show_loading_for_duration(self, duration=2.0, message="Loading...", overlay=False):
        """Show loading indicator for a specific duration"""
        if overlay:
            spinner = self.create_overlay_spinner(message)
        else:
            spinner = self.create_spinner(message)

        await asyncio.sleep(duration)
        spinner.delete()

    def show_notification_loading(self, message="Processing..."):
        """Show loading notification"""
        return ui.notification(message, type='ongoing', position='top', close_button=False)

    def update_progress(self, progress_element, value):
        """Update progress bar value"""
        if hasattr(progress_element, 'value'):
            progress_element.value = value

# Global instance for easy access
loading_indicator = LoadingIndicator()

# Convenience functions
async def with_loading(func, message="Loading...", overlay=False):
    """Decorator to wrap async functions with loading indicator"""
    async def wrapper(*args, **kwargs):
        element_id = f"loading_{id(func)}"
        async with loading_indicator.show_loading(element_id, message, overlay):
            return await func(*args, **kwargs)
    return wrapper

def show_quick_loading(message="Loading...", duration=1.0):
    """Show a quick loading indicator"""
    ui.timer(duration, lambda: None, once=True)  # Just to create a timer
    spinner = loading_indicator.create_spinner(message)
    ui.timer(duration, spinner.delete, once=True)
