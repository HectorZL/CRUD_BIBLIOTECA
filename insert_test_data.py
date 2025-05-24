import os
import mysql.connector
from werkzeug.security import generate_password_hash

def insert_test_data():
    # Configuración de conexión
    config = {
        'host': os.getenv('MYSQL_HOST', 'mybdcontacsmc-competenciautm123.h.aivencloud.com'),
        'port': int(os.getenv('MYSQL_PORT', 17550)),
        'user': os.getenv('MYSQL_USER', 'avnadmin'),
        'password': os.getenv('MYSQL_PASSWORD', 'AVNS_qeAbBvUD5MS0PCRZdyH'),
        'database': os.getenv('MYSQL_DB', 'defaultdb'),
        'ssl_ca': os.getenv('MYSQL_SSL_CA', './ssl/ca.pem'),
        'ssl_verify_identity': True
    }
    
    try:
        # Conectar a la base de datos
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor()
        
        # Insertar un usuario administrador si no existe
        cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        if not cursor.fetchone():
            hashed_password = generate_password_hash('admin123')
            cursor.execute(
                """
                INSERT INTO users (username, password_hash, email, full_name, is_admin) 
                VALUES (%s, %s, %s, %s, %s)
                """,
                ('admin', hashed_password, 'admin@example.com', 'Administrador', True)
            )
            print("Usuario administrador creado exitosamente.")
        
        # Insertar algunos géneros si no existen
        cursor.execute("SELECT COUNT(*) FROM genres")
        if cursor.fetchone()[0] == 0:
            genres = [
                ('Ficción',),
                ('No Ficción',),
                ('Ciencia Ficción',),
                ('Fantasía',),
                ('Misterio',),
                ('Romance',),
                ('Aventura',),
                ('Biografía',),
                ('Historia',),
                ('Ciencia',)
            ]
            cursor.executemany("INSERT INTO genres (name) VALUES (%s)", genres)
            print(f"Insertados {len(genres)} géneros.")
        
        # Insertar algunos libros si no hay libros
        cursor.execute("SELECT COUNT(*) FROM books")
        if cursor.fetchone()[0] == 0:
            cursor.execute("SELECT id FROM genres LIMIT 1")
            genre_id = cursor.fetchone()[0]
            
            books = [
                ('El Principito', 'Antoine de Saint-Exupéry', '9780156012195', 1943, 'Reynal & Hitchcock', genre_id, 5, 5, 'Un clásico de la literatura infantil y juvenil.'),
                ('Cien años de soledad', 'Gabriel García Márquez', '9780307474728', 1967, 'Editorial Sudamericana', genre_id, 3, 3, 'Una obra maestra del realismo mágico.'),
                ('1984', 'George Orwell', '9780451524935', 1949, 'Secker & Warburg', genre_id, 4, 4, 'Una distopía clásica sobre la vigilancia y el control estatal.')
            ]
            
            cursor.executemany(
                """
                INSERT INTO books 
                (title, author, isbn, publication_year, publisher, genre_id, total_copies, available_copies, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                books
            )
            print(f"Insertados {len(books)} libros.")
        
        # Confirmar los cambios
        connection.commit()
        print("Datos de prueba insertados exitosamente.")
        
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
            print("Conexión cerrada.")

if __name__ == "__main__":
    insert_test_data()
