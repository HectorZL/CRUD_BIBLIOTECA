from app.db import get_db_connection

def create_book_movements_table():
    sql = """
    CREATE TABLE IF NOT EXISTS book_movements (
        id INT AUTO_INCREMENT PRIMARY KEY,
        book_id INT NOT NULL,
        user_id INT NOT NULL,
        movement_type VARCHAR(20) NOT NULL,
        quantity INT NOT NULL,
        description VARCHAR(255),
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (book_id) REFERENCES books(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql)
        conn.commit()
        print("Tabla book_movements creada correctamente.")
    except Exception as e:
        print("Error al crear la tabla:", e)
    finally:
        cur.close()

if __name__ == "__main__":
    create_book_movements_table()
