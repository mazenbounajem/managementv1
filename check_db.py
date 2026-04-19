from database_manager import db_manager
import sys

def main():
    try:
        t = 'sales_payment'
        count = db_manager.execute_scalar(f"SELECT COUNT(*) FROM {t}")
        print(f"Count for {t}: {count}")
        cols = db_manager.execute_query(f"SELECT COLUMN_NAME, IS_NULLABLE, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{t}'")
        for c in cols:
            print(f"  {c[0]} (Nullable: {c[1]}, Type: {c[2]})")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
