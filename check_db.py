import os
import mysql.connector
from dotenv import load_dotenv

def check_database():
    try:
        # Load environment variables
        load_dotenv()
        
        # Database configuration
        db_config = {
            'host': os.getenv('MYSQL_HOST', 'mybdcontacsmc-competenciautm123.h.aivencloud.com'),
            'port': int(os.getenv('MYSQL_PORT', 17550)),
            'user': os.getenv('MYSQL_USER', 'avnadmin'),
            'password': os.getenv('MYSQL_PASSWORD', 'AVNS_qeAbBvUD5MS0PCRZdyH'),
            'database': os.getenv('MYSQL_DB', 'defaultdb'),
            'ssl_ca': './ssl/ca.pem' if os.path.exists('./ssl/ca.pem') else None
        }
        
        print("Connecting to database...")
        conn = mysql.connector.connect(**{k: v for k, v in db_config.items() if v is not None})
        cursor = conn.cursor(dictionary=True)
        
        print("\nConnection successful!")
        
        # Check if loans table exists
        cursor.execute("SHOW TABLES LIKE 'loans'")
        loans_table = cursor.fetchone()
        
        if not loans_table:
            print("\nERROR: The 'loans' table does not exist in the database.")
            return
            
        print("\n'loans' table exists. Checking structure...")
        
        # Check loans table structure
        cursor.execute("DESCRIBE loans")
        print("\nLoans table structure:")
        print("-" * 80)
        for column in cursor.fetchall():
            print(f"{column['Field']}: {column['Type']} {'NULL' if column['Null'] == 'YES' else 'NOT NULL'}")
        
        # Check if there are any loans
        cursor.execute("SELECT COUNT(*) as count FROM loans")
        count = cursor.fetchone()['count']
        print(f"\nNumber of loans in database: {count}")
        
        # Check foreign key constraints
        cursor.execute("""
            SELECT 
                TABLE_NAME, COLUMN_NAME, CONSTRAINT_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
            FROM 
                INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE 
                REFERENCED_TABLE_NAME IS NOT NULL 
                AND TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME = 'loans'
        """)
        
        print("\nForeign key constraints for 'loans' table:")
        print("-" * 80)
        fks = cursor.fetchall()
        if fks:
            for fk in fks:
                print(f"{fk['COLUMN_NAME']} -> {fk['REFERENCED_TABLE_NAME']}({fk['REFERENCED_COLUMN_NAME']})")
        else:
            print("No foreign key constraints found for 'loans' table")
        
        # Check if there are any books and users
        cursor.execute("SELECT COUNT(*) as count FROM books")
        books_count = cursor.fetchone()['count']
        cursor.execute("SELECT COUNT(*) as count FROM users")
        users_count = cursor.fetchone()['count']
        
        print(f"\nNumber of books in database: {books_count}")
        print(f"Number of users in database: {users_count}")
        
        # Check for any recent loans
        if count > 0:
            print("\nMost recent loans:")
            print("-" * 80)
            cursor.execute("""
                SELECT l.*, b.title as book_title, u.username as user_name 
                FROM loans l
                LEFT JOIN books b ON l.book_id = b.id
                LEFT JOIN users u ON l.user_id = u.id
                ORDER BY l.loan_date DESC LIMIT 5
            """)
            for loan in cursor.fetchall():
                print(f"ID: {loan['id']}, Book: {loan.get('book_title', 'N/A')}, "
                      f"User: {loan.get('user_name', 'N/A')}, "
                      f"Loan Date: {loan['loan_date']}, "
                      f"Due Date: {loan['due_date']}, "
                      f"Returned: {'Yes' if loan['return_date'] else 'No'}")
        
    except mysql.connector.Error as err:
        print(f"\nDatabase error: {err}")
        
        # Provide more detailed error information
        if err.errno == 2003:
            print("\nCould not connect to the database server. Please check if the server is running.")
        elif err.errno == 1045:
            print("\nAccess denied. Please check your database credentials.")
        elif err.errno == 1049:
            print("\nThe specified database does not exist. Please check the database name.")
        elif err.errno == 1146:
            print("\nA required table is missing. The database schema may need to be updated.")
            
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        
    finally:
        if 'cursor' in locals() and cursor is not None:
            cursor.close()
        if 'conn' in locals() and conn.is_connected():
            conn.close()
            print("\nDatabase connection closed.")

if __name__ == "__main__":
    check_database()
