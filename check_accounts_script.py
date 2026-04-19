from database_manager import db_manager
try:
    results = db_manager.execute_query("SELECT number, account_name FROM auxiliary WHERE number LIKE '7%' OR number LIKE '6%'")
    with open('accounts_check.txt', 'w') as f:
        for r in results:
            f.write(f"{r[0]}: {r[1]}\n")
except Exception as e:
    with open('accounts_check.txt', 'w') as f:
        f.write(f"Error: {e}\n")
