from app.db import get_db_connection

def check_users():
    conn = None
    cur = None
    try:
        print("\n=== Verificando conexión a la base de datos ===")
        conn = get_db_connection()
        print("Conexión exitosa a la base de datos")
        
        cur = conn.cursor(dictionary=True)
        
        # Verificar tablas existentes
        print("\n=== Tablas en la base de datos ===")
        cur.execute("SHOW TABLES")
        tables = [table[f'Tables_in_{conn.database}'] for table in cur.fetchall()]
        print("\n".join(tables))
        
        if 'users' not in tables:
            print("\n¡Error! La tabla 'users' no existe en la base de datos")
            return
        
        # Verificar estructura de la tabla users
        print("\n=== Estructura de la tabla 'users' ===")
        cur.execute("DESCRIBE users")
        for column in cur.fetchall():
            print(f"{column['Field']}: {column['Type']} ({'NULL' if column['Null'] == 'YES' else 'NOT NULL'})")
        
        # Verificar usuarios existentes
        print("\n=== Usuarios en la base de datos ===")
        cur.execute("SELECT id, username, email, is_admin, is_banned, password_hash FROM users")
        users = cur.fetchall()
        
        if not users:
            print("No hay usuarios en la base de datos")
        else:
            for i, user in enumerate(users, 1):
                print(f"\nUsuario #{i}:")
                print(f"ID: {user['id']}")
                print(f"Username: {user['username']}")
                print(f"Email: {user['email']}")
                print(f"Es admin: {'Sí' if user['is_admin'] else 'No'}")
                print(f"Está baneado: {'Sí' if user['is_banned'] else 'No'}")
                print(f"Hash de contraseña: {user['password_hash']}")
        
    except Exception as e:
        print(f"\n¡Error!: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if cur:
            cur.close()
        if conn and conn.is_connected():
            conn.close()

if __name__ == "__main__":
    check_users()
