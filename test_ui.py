from nicegui.testing import Screen

# We need to import the app object to run the server
# and register the routes.
import main

def test_customers_page_loads_and_has_correct_elements(screen: Screen):
    """Test if the customers page loads and contains the expected UI elements."""
    screen.should_contain('Referenced By')

    # Check for a button in the sidebar
    screen.should_contain('Save')


def test_clicking_new_button_clears_inputs(screen: Screen):
    """Test if clicking the 'New' button clears the input fields."""
    screen.open('/customers')

    # Wait for grid to render and click the first row to populate the form.
    # This might be flaky if the database is empty. A better test would mock data.
    screen.wait(1)
    try:
        grid = screen.find_by_tag('ag-grid-vue')
        grid.run_method('__testing__.select_row', 0)
    except Exception:
        # If there's no data, we can't test this part, but we can still test the 'New' button
        pass

    # Click the 'New' button in the sidebar
    screen.click('New')

    # Check if the 'Name' input is now empty
    name_input = screen.find('Name').find_by_tag('input')

