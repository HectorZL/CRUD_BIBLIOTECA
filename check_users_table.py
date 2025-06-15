import os
from app.db import get_db_connection

def check_users_table():
    try:
        # Get database connection
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get table structure
        cursor.execute("DESCRIBE users")
        columns = cursor.fetchall()
        
        print("Users table structure:")
        print("-" * 80)
        for col in columns:
            print(f"{col['Field']}: {col['Type']} {'' if col['Null'] == 'YES' else 'NOT NULL'} {col.get('Default', '')} {col.get('Extra', '')}")
        
        # Check for ban-related columns
        ban_columns = ['is_banned', 'ban_reason', 'ban_expires_at', 'banned_at', 'banned_by']
        missing_columns = [col for col in ban_columns if not any(c['Field'] == col for c in columns)]
        
        if missing_columns:
            print("\nMissing ban-related columns:", ", ".join(missing_columns))
        else:
            print("\nAll ban-related columns are present!")
            
    except Exception as e:
        print(f"Error checking users table: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals() and conn.is_connected():
            conn.close()

if __name__ == "__main__":
    check_users_table()
