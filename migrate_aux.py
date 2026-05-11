import sys
import os

sys.path.append(r"e:\managementv1")
from connection import connection

def run_migration():
    bases = ['6011', '6019', '7011', '7090']
    for base in bases:
        print(f"Migrating base: {base}")
        
        # update accounting_transaction_lines: set base and wipe auxiliary_id since we delete them
        try:
            connection.insertingtodatabase(
                "UPDATE accounting_transaction_lines SET account_number = ?, auxiliary_id = NULL WHERE account_number LIKE ?",
                (base, f"{base}.%")
            )
            print(f"OK: accounting_transaction_lines for {base}")
        except Exception as e:
            print(f"Error accounting_transaction_lines {base}: {repr(e)}")
        
        # update purchase_invoice_account_links
        if base in ('6011', '6019'):
            try:
                connection.insertingtodatabase(
                    "UPDATE purchase_invoice_account_links SET expense_aux_number = ? WHERE expense_aux_number LIKE ?",
                    (base, f"{base}.%")
                )
                print(f"OK: purchase links expense for {base}")
            except Exception as e:
                print(f"Error purchase links expense {base}: {repr(e)}")
            try:
                connection.insertingtodatabase(
                    "UPDATE purchase_invoice_account_links SET discount_aux_number = ? WHERE discount_aux_number LIKE ?",
                    (base, f"{base}.%")
                )
                print(f"OK: purchase links discount for {base}")
            except Exception as e:
                print(f"Error purchase links discount {base}: {repr(e)}")
                
        # update sales_invoice_account_links
        if base in ('7011', '7090'):
            try:
                connection.insertingtodatabase(
                    "UPDATE sales_invoice_account_links SET revenue_aux_number = ? WHERE revenue_aux_number LIKE ?",
                    (base, f"{base}.%")
                )
                print(f"OK: sales links revenue for {base}")
            except Exception as e:
                print(f"Error sales links revenue {base}: {repr(e)}")
            try:
                connection.insertingtodatabase(
                    "UPDATE sales_invoice_account_links SET discount_aux_number = ? WHERE discount_aux_number LIKE ?",
                    (base, f"{base}.%")
                )
                print(f"OK: sales links discount for {base}")
            except Exception as e:
                print(f"Error sales links discount {base}: {repr(e)}")
                
        # delete from auxiliary
        try:
            connection.insertingtodatabase(
                "DELETE FROM auxiliary WHERE number LIKE ?",
                (f"{base}.%",)
            )
            print(f"OK: auxiliary deleted for {base}")
        except Exception as e:
            print(f"Error auxiliary {base}: {repr(e)}")
            
        # delete from ledgerextend
        try:
            connection.insertingtodatabase(
                "DELETE FROM ledgerextend WHERE ledger_root = ?",
                (base,)
            )
            print(f"OK: ledgerextend deleted for {base}")
        except Exception as e:
            print(f"Error ledgerextend {base}: {repr(e)}")
            
    print("Migration complete!")

if __name__ == "__main__":
    run_migration()
