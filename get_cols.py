
import pyodbc

conn = pyodbc.connect('Driver={SQL Server Native Client 11.0};Server=DESKTOP-Q7U1STD\\SQLEXPRESS02;Database=POSDB;Trusted_Connection=yes')
cursor = conn.cursor()
cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'vat_settings'")
cols = [row[0] for row in cursor.fetchall()]
print(cols)
cursor.close()
conn.close()
