import re

def transform():
    with open('purchase_returns_ui.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Class and Route renaming
    content = content.replace("class PurchaseUI:", "class PurchaseReturnsUI:")
    content = content.replace("def purchase_page_route():", "def purchase_return_route():")
    content = content.replace("@ui.page('/purchase')", "@ui.page('/purchasereturn')")
    content = content.replace("PurchaseUI()", "PurchaseReturnsUI()")

    # 2. UI Labelling
    content = content.replace("'Purchase Invoice'", "'Purchase Return Invoice'")
    content = content.replace("Purchase Operations", "Purchase Returns")
    content = content.replace("'Save and Print'", "'Process Supplier Return'")
    # Note: shopping_bag -> assignment_return (already assignment_return in some places but let's be thorough)
    content = content.replace("shopping_bag", "assignment_return")

    # 3. Database Table names
    content = content.replace("INTO purchases (", "INTO purchase_returns (")
    content = content.replace("INTO purchase_items", "INTO purchase_return_items")
    content = content.replace("UPDATE purchases SET", "UPDATE purchase_returns SET")
    content = content.replace("UPDATE purchase_items", "UPDATE purchase_return_items")
    content = content.replace("FROM purchases ", "FROM purchase_returns ")
    content = content.replace("FROM purchase_items ", "FROM purchase_return_items ")
    content = re.sub(r"DELETE FROM purchases\b", "DELETE FROM purchase_returns", content)
    content = content.replace("DELETE FROM purchase_items", "DELETE FROM purchase_return_items")
    content = content.replace("WHERE purchase_id =", "WHERE purchase_return_id =")

    # 4. Invert Stock Operations logic
    # In purchase, we do: stock_quantity + ? (receiving)
    # In Return, we do:    stock_quantity - ? (returning to supplier)
    content = content.replace("stock_quantity + ?", "TEMP_STOCK_OP")
    content = content.replace("stock_quantity - ?", "stock_quantity + ?")
    content = content.replace("TEMP_STOCK_OP", "stock_quantity - ?")

    # Expressions
    content = re.sub(r"stock_quantity\s*\+\s*([a-zA-Z0-9_{}()]+)", r"TEMP_STOCK_OP \1", content)
    content = re.sub(r"stock_quantity\s*-\s*([a-zA-Z0-9_{}()]+)", r"stock_quantity + \1", content)
    content = re.sub(r"TEMP_STOCK_OP\s*([a-zA-Z0-9_{}()]+)", r"stock_quantity - \1", content)

    # 5. Invert Accounting Debit/Credit
    # Purchase Entry: Debit Purchase [6011], Debit VAT [44210], Credit Supplier [4011]
    # Return Entry: Credit Purchase [6011], Credit VAT [44210], Debit Supplier [4011]
    
    # Save Purchase Logic:
    # {'account': '6011', 'debit': ht_amount, 'credit': 0}
    # {'account': vat_aux, 'debit': total_vat_entry, 'credit': 0}
    # {'account': supp_aux, 'debit': 0, 'credit': total_amount}

    content = content.replace("'debit': ht_amount, 'credit': 0", "TEMP_DEBIT_HT")
    content = content.replace("'debit': 0, 'credit': ht_amount", "'debit': ht_amount, 'credit': 0")
    content = content.replace("TEMP_DEBIT_HT", "'debit': 0, 'credit': ht_amount")

    content = content.replace("'debit': total_vat_entry, 'credit': 0", "TEMP_DEBIT_VAT")
    content = content.replace("'debit': 0, 'credit': total_vat_entry", "'debit': total_vat_entry, 'credit': 0")
    content = content.replace("TEMP_DEBIT_VAT", "'debit': 0, 'credit': total_vat_entry")

    content = content.replace("'debit': 0, 'credit': total_amount", "TEMP_CREDIT_TOTAL")
    content = content.replace("'debit': total_amount, 'credit': 0", "'debit': 0, 'credit': total_amount")
    content = content.replace("TEMP_CREDIT_TOTAL", "'debit': total_amount, 'credit': 0")

    # Reverse undo/delete accounting as well
    content = content.replace("'debit': 0, 'credit': ht_amount", "TEMP_CREDIT_HT_UNDO")
    content = content.replace("'debit': ht_amount, 'credit': 0", "'debit': 0, 'credit': ht_amount")
    content = content.replace("TEMP_CREDIT_HT_UNDO", "'debit': ht_amount, 'credit': 0")

    content = content.replace("'debit': refund_amount, 'credit': 0", "TEMP_DEBIT_REFUND")
    content = content.replace("'debit': 0, 'credit': refund_amount", "'debit': refund_amount, 'credit': 0")
    content = content.replace("TEMP_DEBIT_REFUND", "'debit': 0, 'credit': refund_amount")

    # Replace accounting reference
    content = content.replace('"Purchase",', '"Purchase Return",')
    content = content.replace('"Purchase Delete",', '"Purchase Return Delete",')
    content = content.replace('"Purchase Undo",', '"Purchase Return Undo",')

    with open('purchase_returns_ui.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS")

if __name__ == "__main__":
    transform()
