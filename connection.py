import pyodbc

class connection():
            

            def contogetrows(sql= '',data=[]):
            
                    try:
                        cnxn = pyodbc.connect("Driver={SQL Server Native Client 11.0};"
                                        "Server=DESKTOP-Q7U1STD;"
                                        "Database=Retail;"
                                        "Trusted_Connection=yes;")


                        cursor = cnxn.cursor()
                        cursor.execute(sql)
                    except:
                        print("cant open connection") 
                    else:         

                        for row in cursor:
                            data.append(row)
                        cursor.commit()
                         
            
            def contogetheaders(sqlh='',datah=[]):
                   try:
                        cnxn = pyodbc.connect("Driver={SQL Server Native Client 11.0};"
                                        "Server=DESKTOP-Q7U1STD;"
                                        "Database=Retail;"
                                        "Trusted_Connection=yes;")


                        cursor = cnxn.cursor()
                        cursor.execute(sqlh)
                   except Exception as ex:
                        print(f"cant open connection:{str(ex)}") 
                   else:
                        
                        #datah = [i[0] for i in cursor.description]
                        for i in cursor.description:
                              datah.append(i[0])
                         
            def insertingtodatabase(sqli='',values=()):
                   try:
                        cnxn = pyodbc.connect("Driver={SQL Server Native Client 11.0};"
                                        "Server=DESKTOP-Q7U1STD;"
                                        "Database=Retail;"
                                        "Trusted_Connection=yes;")


                        cursor = cnxn.cursor()
                        cursor.execute(sqli,values)
                   except Exception as ex:
                        print(f"cant open connection:{str(ex)}") 
                   else:
                        
                        #datah = [i[0] for i in cursor.description]
                        cursor.commit()      
            def deleterow(sqli='',name=''):
                   try:
                        cnxn = pyodbc.connect("Driver={SQL Server Native Client 11.0};"
                                        "Server=DESKTOP-Q7U1STD;"
                                        "Database=Retail;"
                                        "Trusted_Connection=yes;")


                        cursor = cnxn.cursor()
                        cursor.execute(sqli,name)
                   except Exception as ex:
                        print(f"cant open connection:{str(ex)}") 
                   else:
                        
                        #datah = [i[0] for i in cursor.description]
                        if cursor.commit()==True:
                              print("deleted")
                        
                        
      
                         
# testting= connection.contogetrows
# variable=[]
# query=testting('SELECT * FROM dbo.customer',variable) 
# print (variable)
# testting2=connection.contogetheaders
# variable2=[]
# query2=testting2('SELECT * FROM dbo.customer')
# print(query2)
             