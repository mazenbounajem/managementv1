
import pyodbc
import pandas as pd
import time

CONNECTION_CONFIG = {
    "driver": "SQL Server Native Client 11.0",
    "server": "DESKTOP-Q7U1STD\\SQLEXPRESS02",
    "database": "POSDB",
    "trusted_connection": "yes"
}

def get_connection_string():
    return (
        f"Driver={{{CONNECTION_CONFIG['driver']}}};"
        f"Server={CONNECTION_CONFIG['server']};"
        f"Database={CONNECTION_CONFIG['database']};"
        f"Trusted_Connection={CONNECTION_CONFIG['trusted_connection']};"
    )

def performance_test():
    conn_str = get_connection_string()
    try:
        conn = pyodbc.connect(conn_str)
        
        print("--- Performance Test with ~1000 rows per table ---")
        
        # Test 1: Complex Join Query
        start_time = time.time()
        query1 = """
            SELECT TOP 10 p.product_name, SUM(si.quantity) as total_sold, SUM(si.total_price) as revenue
            FROM sale_items si
            JOIN products p ON si.product_id = p.id
            GROUP BY p.product_name
            ORDER BY revenue DESC
        """
        df1 = pd.read_sql(query1, conn)
        end_time = time.time()
        print(f"Query 1 (Sales Analysis) took: {end_time - start_time:.4f} seconds")
        print(df1)
        
        # Test 2: Multi-table join
        start_time = time.time()
        query2 = """
            SELECT TOP 10 c.customer_name, s.invoice_number, s.total_amount, sp.amount_paid
            FROM sales s
            JOIN customers c ON s.customer_id = c.id
            LEFT JOIN sales_payment sp ON s.id = sp.sales_id
            ORDER BY s.sale_date DESC
        """
        df2 = pd.read_sql(query2, conn)
        end_time = time.time()
        print(f"\nQuery 2 (Sales & Customer Join) took: {end_time - start_time:.4f} seconds")
        print(df2)
        
        # Test 3: Aggregation over 1000 rows
        start_time = time.time()
        query3 = "SELECT SUM(total_amount) as grand_total FROM sales"
        df3 = pd.read_sql(query3, conn)
        end_time = time.time()
        print(f"\nQuery 3 (Aggregation) took: {end_time - start_time:.4f} seconds")
        print(f"Grand Total Sales: {df3.iloc[0]['grand_total']}")
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    performance_test()
