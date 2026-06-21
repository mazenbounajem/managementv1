from database_manager import db_manager
import sys

def main():
    try:
        t = 'sales_payment'
        fks = db_manager.execute_query(f"""
            SELECT obj.name AS fk_name, col.name AS col_name
            FROM sys.foreign_key_columns fkc
            JOIN sys.objects obj ON obj.object_id = fkc.constraint_object_id
            JOIN sys.tables tab ON tab.object_id = fkc.parent_object_id
            JOIN sys.columns col ON col.column_id = fkc.parent_column_id AND col.object_id = tab.object_id
            WHERE tab.name = '{t}' AND col.name = 'sales_id'
        """)
        for fk in fks:
            print(f"FK Name: {fk[0]}, Column: {fk[1]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
