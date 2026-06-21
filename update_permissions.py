from connection import connection
import sys

def main():
    print("Updating role permissions for Returns modules...")
    try:
        # Get all roles from DB
        from database_manager import db_manager
        roles = db_manager.execute_query("SELECT id FROM roles")
        
        pages_to_add = ['sales-returns', 'purchase-returns']
        
        for role in roles:
            role_id = role[0]
            for page in pages_to_add:
                # Check if permission exists
                exists = db_manager.execute_scalar(
                    "SELECT COUNT(*) FROM role_permissions WHERE role_id = ? AND page_name = ?",
                    (role_id, page)
                )
                
                if not exists:
                    db_manager.execute_update(
                        "INSERT INTO role_permissions (role_id, page_name, can_access) VALUES (?, ?, 1)",
                        (role_id, page)
                    )
                    print(f"  [+] Added '{page}' for role ID {role_id}")
                else:
                    db_manager.execute_update(
                        "UPDATE role_permissions SET can_access = 1 WHERE role_id = ? AND page_name = ?",
                        (role_id, page)
                    )
                    print(f"  [*] Enabled '{page}' for role ID {role_id}")
                    
        print("Permissions updated successfully.")
    except Exception as e:
        print(f"Error updating permissions: {e}")

if __name__ == "__main__":
    main()
