from connection import connection

def main():
    print("Creating users table...")
    connection.create_users_table()
    print("Users table creation attempted.")

if __name__ == "__main__":
    main()
