import os
from app.db import get_db_connection, get_cursor

def check_columns():
    """Check if the suspension columns exist in the users table"""
    try:
        conn = get_db_connection()
        cur = get_cursor()
        
        # Check if suspension_type column exists
        cur.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'users' 
            AND COLUMN_NAME = 'suspension_type'
        """)
        
        if cur.fetchone():
            print("✅ La columna 'suspension_type' existe en la tabla 'users'")
        else:
            print("❌ La columna 'suspension_type' NO existe en la tabla 'users'")
            print("\nEjecuta el siguiente comando SQL para agregar las columnas faltantes:")
            print("""
            ALTER TABLE users
            ADD COLUMN is_banned BOOLEAN DEFAULT FALSE COMMENT 'Indica si el usuario está baneado',
            ADD COLUMN ban_reason VARCHAR(255) DEFAULT NULL COMMENT 'Razón de la restricción',
            ADD COLUMN ban_expires_at DATETIME DEFAULT NULL COMMENT 'Fecha de expiración de la restricción',
            ADD COLUMN banned_at DATETIME DEFAULT NULL COMMENT 'Fecha en que se aplicó la restricción',
            ADD COLUMN banned_by INT DEFAULT NULL COMMENT 'ID del administrador que aplicó la restricción',
            ADD COLUMN suspension_type ENUM('none', 'temporary', 'permanent') DEFAULT 'none' COMMENT 'Tipo de suspensión',
            ADD COLUMN suspension_until DATETIME DEFAULT NULL COMMENT 'Hasta cuándo está suspendido el usuario';

            -- Agregar llave foránea para banned_by
            ALTER TABLE users
            ADD CONSTRAINT fk_banned_by
            FOREIGN KEY (banned_by) REFERENCES users(id)
            ON DELETE SET NULL;

            -- Actualizar usuarios existentes
            UPDATE users SET 
                is_banned = COALESCE(is_banned, FALSE),
                suspension_type = 'none';

            -- Crear índice para mejor rendimiento
            CREATE INDEX idx_user_ban_status ON users(is_banned, suspension_type, ban_expires_at, suspension_until);
            """)
            
    except Exception as e:
        print(f"Error al verificar las columnas: {e}")
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    check_columns()
