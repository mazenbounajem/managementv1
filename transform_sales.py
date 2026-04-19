import re

def transform():
    with open('sales_returns_ui.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Class and Route renaming
    content = content.replace("class SalesUI:", "class SalesReturnsUI:")
    content = content.replace("def sales_page_route():", "def sales_return_route():")
    content = content.replace("@ui.page('/sales')", "@ui.page('/salesreturn')")
    content = content.replace("SalesUI()", "SalesReturnsUI()")

    # 2. UI Labelling
    content = content.replace("'Sales Invoice'", "'Sales Return Invoice'")
    content = content.replace("Sales Operations", "Sales Returns")
    content = content.replace("'Checkout'", "'Process Return'")
    content = content.replace("point_of_sale", "assignment_return")

    # 3. Database Table names
    # Safe replacements that won't break things like `sales_reports`
    content = content.replace("INTO sales (", "INTO sales_returns (")
    content = content.replace("INTO sale_items", "INTO sales_return_items")
    content = content.replace("UPDATE sales SET", "UPDATE sales_returns SET")
    content = content.replace("UPDATE sale_items", "UPDATE sales_return_items")
    content = content.replace("FROM sales ", "FROM sales_returns ")
    content = content.replace("FROM sale_items ", "FROM sales_return_items ")
    content = re.sub(r"DELETE FROM sales\b", "DELETE FROM sales_returns", content)
    content = content.replace("DELETE FROM sale_items", "DELETE FROM sales_return_items")
    content = content.replace("WHERE sales_id =", "WHERE sales_return_id =")

    # 4. Invert Stock Operations logic
    # In sales Checkout, we do: stock_quantity = stock_quantity - ?
    # In Return, we do:         stock_quantity = stock_quantity + ?
    # Let's replace 'stock_quantity - ?' with 'stock_quantity + ?'
    # Wait, there's also 'stock_quantity + ?' in undo/delete which needs to become '-'!
    # Let's do a trick: swap '+' and '-' for stock_quantity.
    content = content.replace("stock_quantity - ?", "TEMP_STOCK_OP")
    content = content.replace("stock_quantity + ?", "stock_quantity - ?")
    content = content.replace("TEMP_STOCK_OP", "stock_quantity + ?")

    # Also there might be expressions like `stock_quantity - {qty}`
    content = re.sub(r"stock_quantity\s*-\s*([a-zA-Z0-9_{}()]+)", r"TEMP_STOCK_OP \1", content)
    content = re.sub(r"stock_quantity\s*\+\s*([a-zA-Z0-9_{}()]+)", r"stock_quantity - \1", content)
    content = re.sub(r"TEMP_STOCK_OP\s*([a-zA-Z0-9_{}()]+)", r"stock_quantity + \1", content)

    # 5. Invert Accounting Debit/Credit dynamically
    # Look for the lines list creation in save_sale
    #                 {'account': '7011', 'debit': 0, 'credit': ht},
    #                 {'account': vat_aux, 'debit': 0, 'credit': total_vat},
    #                 {'account': pay_aux, 'debit': self.total_amount, 'credit': 0}
    # It might be spread over multiple lines.
    content = content.replace("'debit': 0, 'credit': ht", "'debit': ht, 'credit': 0")
    content = content.replace("'debit': 0, 'credit': total_vat", "'debit': total_vat, 'credit': 0")
    content = content.replace("'debit': self.total_amount, 'credit': 0", "'debit': 0, 'credit': self.total_amount")

    # Let's also check for perform_undo / delete accounting logic which reverses the reverse!
    # In perform_undo of sales:
    #                 {'account': '7011', 'debit': ht, 'credit': 0},
    #                 {'account': vat_aux, 'debit': total_vat, 'credit': 0},
    #                 {'account': pay_aux, 'debit': 0, 'credit': refund_amount}
    # This must become the reverse:
    content = content.replace("'debit': ht, 'credit': 0", "TEMP_DEBIT_HT")
    content = content.replace("'debit': 0, 'credit': ht", "'debit': ht, 'credit': 0")
    content = content.replace("TEMP_DEBIT_HT", "'debit': 0, 'credit': ht")

    content = content.replace("'debit': total_vat, 'credit': 0", "TEMP_DEBIT_VAT")
    content = content.replace("'debit': 0, 'credit': total_vat", "'debit': total_vat, 'credit': 0")
    content = content.replace("TEMP_DEBIT_VAT", "'debit': 0, 'credit': total_vat")

    # Note: self.total_amount isn't reversed perfectly above.
    # In perform_delete_sale:
    content = content.replace("'debit': 0, 'credit': refund_amount", "TEMP_DEBIT_REFUND")
    content = content.replace("'debit': refund_amount, 'credit': 0", "'debit': 0, 'credit': refund_amount")
    content = content.replace("TEMP_DEBIT_REFUND", "'debit': refund_amount, 'credit': 0")

    # In perform_undo:
    content = content.replace("'debit': 0, 'credit': total_amount", "TEMP_DEBIT_TOTAL")
    content = content.replace("'debit': total_amount, 'credit': 0", "'debit': 0, 'credit': total_amount")
    content = content.replace("TEMP_DEBIT_TOTAL", "'debit': total_amount, 'credit': 0")

    content = content.replace("'debit': 0, 'credit': self.total_amount", "TEMP_DEBIT_SELF_TOTAL")
    content = content.replace("'debit': self.total_amount, 'credit': 0", "'debit': 0, 'credit': self.total_amount")
    content = content.replace("TEMP_DEBIT_SELF_TOTAL", "'debit': self.total_amount, 'credit': 0")

    # Replace accounting reference
    content = content.replace('"Sale",', '"Sale Return",')
    content = content.replace('"Sale Delete",', '"Sale Return Delete",')
    content = content.replace('"Sale Undo",', '"Sale Return Undo",')

    with open('sales_returns_ui.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS")

if __name__ == "__main__":
    transform()
