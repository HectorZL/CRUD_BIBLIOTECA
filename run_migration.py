import os
from app.db import get_db_connection

def run_migration():
    try:
        # Get database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("""
            SELECT COUNT(*) as column_count 
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'users' 
            AND COLUMN_NAME = 'is_banned'
        """)
        
        result = cursor.fetchone()
        column_count = result[0] if result else 0
        
        if column_count == 0:
            print("Applying migration: Adding ban-related columns to users table...")
            # Read the migration SQL file
            with open('migrations/add_user_ban_columns.sql', 'r') as f:
                sql_statements = f.read().split(';')
            
            # Execute each SQL statement separately
            for statement in sql_statements:
                if statement.strip():
                    cursor.execute(statement)
            
            conn.commit()
            print("Migration applied successfully!")
        else:
            print("Migration already applied or not needed.")
            
    except Exception as e:
        print(f"Error applying migration: {e}")
        if conn:
            conn.rollback()
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals() and conn.is_connected():
            conn.close()

if __name__ == "__main__":
    run_migration()
