from connection import connection

def display_all_tables():
    tables = connection.get_all_tables()
    if tables:
        print("Tables in the Retail database:")
        for table in tables:
            print(f"- {table}")
    else:
        print("No tables found or unable to retrieve tables.")

if __name__ == "__main__":
    display_all_tables()
