
import pyodbc

def fix_vat():
    try:
        conn = pyodbc.connect('Driver={SQL Server Native Client 11.0};Server=DESKTOP-Q7U1STD\\SQLEXPRESS02;Database=POSDB;Trusted_Connection=yes')
        cursor = conn.cursor()

        cursor.execute("INSERT INTO vat_settings (vat_percentage, effective_date, created_at) VALUES (0.0, GETDATE(), GETDATE())")
        cursor.execute("INSERT INTO vat_settings (vat_percentage, effective_date, created_at) VALUES (11.0, GETDATE(), GETDATE())")
        conn.commit()
        print("Added 0% and 11% VAT rates.")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_vat()
