import re

def transform_repo():
    with open('purchase_returns_repository.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Rename class
    content = content.replace("class PurchaseRepository:", "class PurchaseReturnRepository:")
    
    # Tables
    content = content.replace("INTO purchases (", "INTO purchase_returns (")
    content = content.replace("INTO purchase_items", "INTO purchase_return_items")
    content = content.replace("UPDATE purchases SET", "UPDATE purchase_returns SET")
    content = content.replace("UPDATE purchase_items", "UPDATE purchase_return_items")
    content = content.replace("FROM purchases ", "FROM purchase_returns ")
    content = content.replace("FROM purchase_items ", "FROM purchase_return_items ")
    content = re.sub(r"DELETE FROM purchases\b", "DELETE FROM purchase_returns", content)
    content = content.replace("DELETE FROM purchase_items", "DELETE FROM purchase_return_items")
    
    # ID retrieval
    content = content.replace("SELECT MAX(id) FROM purchases", "SELECT MAX(id) FROM purchase_returns")

    # Invert Stock
    # Receipt: stock_quantity = stock_quantity + ?
    # Return: stock_quantity = stock_quantity - ?
    content = content.replace("stock_quantity = stock_quantity + ?", "TEMP_STOCK_PLUS")
    content = content.replace("stock_quantity = stock_quantity - ?", "stock_quantity = stock_quantity + ?")
    content = content.replace("TEMP_STOCK_PLUS", "stock_quantity = stock_quantity - ?")
    
    # Revert Receipt logic (Undo/Delete):
    # Receipts undo: stock_quantity = stock_quantity - ? (decrement)
    # Return undo:    stock_quantity = stock_quantity + ? (increment)
    # The regex swap above already handles the standard strings.

    with open('purchase_returns_repository.py', 'w', encoding='utf-8') as f:
        f.write(content)

def transform_service():
    with open('purchase_returns_service.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Class and dependencies
    content = content.replace("class PurchaseService:", "class PurchaseReturnService:")
    content = content.replace("from purchase_repository import PurchaseRepository", "from purchase_returns_repository import PurchaseReturnRepository")
    content = content.replace("self.repository = PurchaseRepository()", "self.repository = PurchaseReturnRepository()")

    # Labels
    content = content.replace('"Purchase"', '"Purchase Return"')
    content = content.replace('"Purchase Delete"', '"Purchase Return Delete"')
    content = content.replace('"Purchase Undo"', '"Purchase Return Undo"')
    content = content.replace("'Purchase'", "'Purchase Return'")
    content = content.replace("'Purchase Receipt'", "'Purchase Return Receipt'")

    # Invert Accounting Logic in save_purchase / _create_new_purchase
    # Standard:
    # {'account': '6011', 'debit': ht_amount, 'credit': 0}
    # {'account': vat_aux, 'debit': total_vat_entry, 'credit': 0}
    # {'account': supp_aux, 'debit': 0, 'credit': total_amount}

    # Swap for return:
    content = content.replace("'debit': ht_amount, 'credit': 0", "TEMP_DEBIT_HT")
    content = content.replace("'debit': 0, 'credit': ht_amount", "'debit': ht_amount, 'credit': 0")
    content = content.replace("TEMP_DEBIT_HT", "'debit': 0, 'credit': ht_amount")

    content = content.replace("'debit': total_vat_entry, 'credit': 0", "TEMP_DEBIT_VAT")
    content = content.replace("'debit': 0, 'credit': total_vat_entry", "'debit': total_vat_entry, 'credit': 0")
    content = content.replace("TEMP_DEBIT_VAT", "'debit': 0, 'credit': total_vat_entry")

    content = content.replace("'debit': 0, 'credit': total_amount", "TEMP_CREDIT_TOTAL")
    content = content.replace("'debit': total_amount, 'credit': 0", "'debit': 0, 'credit': total_amount")
    content = content.replace("TEMP_CREDIT_TOTAL", "'debit': total_amount, 'credit': 0")

    # Invert cash drawer update
    # Standard: Receipt is 'Out' (money out for purchase)
    # Return: Receipt is 'In' (money back from supplier)
    content = content.replace("'In'", "TEMP_IN")
    content = content.replace("'Out'", "'In'")
    content = content.replace("TEMP_IN", "'Out'")

    # Invert supplier balance update
    # Standard: update_supplier_balance (add to balance)
    # Return: should subtract from balance
    # I need to check the repo methods for this.

    with open('purchase_returns_service.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == "__main__":
    transform_repo()
    transform_service()
    print("SUCCESS")
