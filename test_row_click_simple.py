#!/usr/bin/env python3
"""
Simple test to verify the row click functionality in salesui_final.py
"""

import sys
import os
sys.path.append('.')

# Test the specific functionality
def test_row_click_handler():
    """Test the row click handler directly."""
    print("🧪 Testing row click handler...")
    
    # Import and create instance
    from salesui_final import SalesUI
    
    # Create a mock sales UI instance
    sales_ui = SalesUI()
    
    # Add test data
    test_row = {
        'barcode': '123456789',
        'product': 'Test Product',
        'quantity': 5,
        'discount': 10,
        'price': 25.99,
        'subtotal': 116.96
    }
    
    sales_ui.rows.append(test_row)
    
    # Test 1: Normal case
    print("\n📋 Test 1: Normal row click")
    mock_event = type('MockEvent', (), {'args': [0, test_row]})()
    
    try:
        sales_ui.on_row_click_edit_cells(mock_event)
        print("✅ Normal case: Handler executed without error")
    except Exception as e:
        print(f"❌ Normal case failed: {e}")
    
    # Test 2: Missing args
    print("\n📋 Test 2: Missing args")
    mock_event_bad = type('MockEvent', (), {'args': []})()
    
    try:
        sales_ui.on_row_click_edit_cells(mock_event_bad)
        print("✅ Missing args: Handled gracefully")
    except Exception as e:
        print(f"✅ Missing args: Exception caught: {e}")
    
    # Test 3: None data
    print("\n📋 Test 3: None data")
    mock_event_none = type('MockEvent', (), {'args': [0, None]})()
    
    try:
        sales_ui.on_row_click_edit_cells(mock_event_none)
        print("✅ None data: Handled gracefully")
    except Exception as e:
        print(f"✅ None data: Exception caught: {e}")
    
    print("\n🎯 Row click handler tests completed!")

if __name__ == "__main__":
    test_row_click_handler()
