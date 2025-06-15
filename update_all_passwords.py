from app.db import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash

def update_all_passwords():
    conn = None
    cur = None
    try:
        print("\n=== Actualizando contraseñas a pbkdf2:sha256 ===")
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        
        # Obtener todos los usuarios
        cur.execute("SELECT id, username, password_hash FROM users")
        users = cur.fetchall()
        
        if not users:
            print("No hay usuarios en la base de datos")
            return
        
        updated_count = 0
        
        for user in users:
            user_id = user['id']
            username = user['username']
            old_hash = user['password_hash']
            
            # Si el hash ya usa pbkdf2, lo saltamos
            if old_hash.startswith('pbkdf2:sha256:'):
                print(f"Usuario {username} (ID: {user_id}) ya usa pbkdf2:sha256")
                continue
            
            # Extraer la contraseña del hash antiguo (asumiendo que es sha256)
            # El formato es: method$salt$hash
            parts = old_hash.split('$')
            if len(parts) != 3:
                print(f"Formato de hash no reconocido para el usuario {username} (ID: {user_id})")
                continue
            
            # La contraseña es la parte después del último $
            password = parts[2]
            
            # Generar un nuevo hash con pbkdf2:sha256
            new_hash = generate_password_hash(password, method='pbkdf2:sha256')
            
            # Actualizar el hash en la base de datos
            cur.execute("UPDATE users SET password_hash = %s WHERE id = %s", 
                      (new_hash, user_id))
            
            print(f"Actualizado usuario {username} (ID: {user_id})")
            print(f"  Hash antiguo: {old_hash}")
            print(f"  Hash nuevo: {new_hash}")
            updated_count += 1
        
        conn.commit()
        print(f"\n¡Listo! Se actualizaron {updated_count} usuarios.")
        
    except Exception as e:
        print(f"\n¡Error!: {str(e)}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
    finally:
        if cur:
            cur.close()
        if conn and conn.is_connected():
            conn.close()

if __name__ == "__main__":
    print("=== Actualizador de contraseñas ===")
    print("Este script actualizará todas las contraseñas para usar el método pbkdf2:sha256")
    confirm = input("¿Desea continuar? (s/n): ")
    if confirm.lower() == 's':
        update_all_passwords()
    else:
        print("Operación cancelada")
