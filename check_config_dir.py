
import pyodbc

conn = pyodbc.connect('Driver={SQL Server Native Client 11.0};Server=DESKTOP-Q7U1STD\\SQLEXPRESS02;Database=POSDB;Trusted_Connection=yes')
cursor = conn.cursor()

cursor.execute("SELECT setting_value FROM configuration WHERE setting_key = 'backup_directory'")
row = cursor.fetchone()
if row:
    print(f"current backup dest: {row[0]}")
else:
    print("No backup directory found.")

cursor.close()
conn.close()
