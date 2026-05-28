from connection import connection
data = []
connection.contogetrows("SELECT name FROM sysobjects WHERE xtype='U' ORDER BY name", data)
for r in data:
    print(r[0])
