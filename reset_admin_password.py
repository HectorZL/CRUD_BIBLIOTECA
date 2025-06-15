from app.db import get_db_connection
from werkzeug.security import generate_password_hash

def reset_admin_password():
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        
        # Set the new admin password
        new_password = "admin123"  # Change this to your desired password
        hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256')
        
        # Check if admin user exists
        cur.execute("SELECT id FROM users WHERE username = 'admin'")
        admin = cur.fetchone()
        
        if admin:
            # Update existing admin password
            cur.execute("UPDATE users SET password_hash = %s WHERE username = 'admin'", (hashed_password,))
            print("Admin password updated successfully!")
        else:
            # Create admin user if it doesn't exist
            cur.execute("""
                INSERT INTO users (username, password_hash, email, full_name, is_admin)
                VALUES (%s, %s, %s, %s, %s)
            """, ('admin', hashed_password, 'admin@example.com', 'Administrator', True))
            print("Admin user created successfully!")
        
        conn.commit()
        print(f"Admin username: admin\nPassword: {new_password}")
        
    except Exception as e:
        print(f"Error: {e}")
        if conn:
            conn.rollback()
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    reset_admin_password()
