
import pyodbc
import os
from datetime import datetime

directory = r"E:\posdbbuckup"
if not os.path.exists(directory):
    os.makedirs(directory, exist_ok=True)
    
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
filename = f"POSDB_Backup_{timestamp}.bak"
filepath = os.path.join(directory, filename)

conn_str = (
    "Driver={SQL Server Native Client 11.0};"
    "Server=DESKTOP-Q7U1STD\\SQLEXPRESS02;"
    "Database=master;" 
    "Trusted_Connection=yes;"
)

try:
    print(f"Attempting backup to {filepath}...")
    conn = pyodbc.connect(conn_str, autocommit=True)
    cursor = conn.cursor()
    
    backup_query = f"BACKUP DATABASE [POSDB] TO DISK = '{filepath}' WITH FORMAT, MEDIANAME = 'SQLServerBackups', NAME = 'Full Backup of POSDB';"
    cursor.execute(backup_query)
    while cursor.nextset():
        pass
        
    print("Backup query executed successfully.")
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Exception during backup: {e}")
