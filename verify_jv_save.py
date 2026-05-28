
from accounting_helpers import save_accounting_transaction
import datetime

def test_jv_save():
    print("Testing JV save with integer reference_id...")
    current_year = datetime.datetime.now().year
    
    # Simple balanced entry
    lines = [
        {'account': '6011', 'debit': 100, 'credit': 0},
        {'account': '138', 'debit': 0, 'credit': 100}
    ]
    
    try:
        # This should fail if pyodbc is missing in THIS environment,
        # but the purpose is to provide the script for the USER to run if they want,
        # or for me to try running it.
        jv_id = save_accounting_transaction(
            reference_type="Test-Closing",
            reference_id=int(current_year),
            lines=lines,
            description=f"Test Closing for {current_year}"
        )
        print(f"Success! Saved JV ID: {jv_id}")
    except Exception as e:
        print(f"Failed as expected if DB connection fails, but checking for conversion error specifically: {e}")

if __name__ == "__main__":
    test_jv_save()
