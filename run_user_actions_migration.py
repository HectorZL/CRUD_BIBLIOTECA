import os
import mysql.connector
from mysql.connector import Error

def apply_migration():
    """Apply the user_actions table migration."""
    try:
        # Database connection parameters - using your remote server details
        db_config = {
            'host': 'mybdcontacsmc-competenciautm123.h.aivencloud.com',
            'port': 17550,
            'user': 'avnadmin',
            'password': 'AVNS_qeAbBvUD5MS0PCRZdyH',
            'database': 'defaultdb',
            'ssl_disabled': True  # Adjust based on your SSL requirements
        }
        
        # Connect to the database
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        print("Connected to database successfully")
        
        # Check if user_actions table exists
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.TABLES 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'user_actions'
        """)
        
        table_exists = cursor.fetchone()[0] > 0
        
        if not table_exists:
            print("Creating user_actions table...")
            # Create user_actions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_actions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    action_type VARCHAR(50) NOT NULL,
                    description TEXT,
                    ip_address VARCHAR(45),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """)
            
            conn.commit()
            print("Migration applied successfully!")
        else:
            print("user_actions table already exists. No migration needed.")
            
    except Error as e:
        print(f"Error applying migration: {e}")
        if 'conn' in locals() and conn.is_connected():
            conn.rollback()
    finally:
        if 'cursor' in locals() and cursor is not None:
            cursor.close()
        if 'conn' in locals() and conn.is_connected():
            conn.close()
            print("Database connection closed")

if __name__ == "__main__":
    apply_migration()
