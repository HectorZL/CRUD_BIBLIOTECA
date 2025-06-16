import os
from app.db import get_db_connection, get_cursor

def apply_migration():
    """Apply the suspension columns migration to the database"""
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = get_cursor()
        
        print("🔧 Aplicando migración para agregar columnas de suspensión...")
        
        # Add suspension columns
        cur.execute("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS is_banned BOOLEAN DEFAULT FALSE COMMENT 'Indica si el usuario está baneado',
            ADD COLUMN IF NOT EXISTS ban_reason VARCHAR(255) DEFAULT NULL COMMENT 'Razón de la restricción',
            ADD COLUMN IF NOT EXISTS ban_expires_at DATETIME DEFAULT NULL COMMENT 'Fecha de expiración de la restricción',
            ADD COLUMN IF NOT EXISTS banned_at DATETIME DEFAULT NULL COMMENT 'Fecha en que se aplicó la restricción',
            ADD COLUMN IF NOT EXISTS banned_by INT DEFAULT NULL COMMENT 'ID del administrador que aplicó la restricción',
            ADD COLUMN IF NOT EXISTS suspension_type ENUM('none', 'temporary', 'permanent') DEFAULT 'none' COMMENT 'Tipo de suspensión',
            ADD COLUMN IF NOT EXISTS suspension_until DATETIME DEFAULT NULL COMMENT 'Hasta cuándo está suspendido el usuario';
        """)
        
        # Add foreign key constraint if it doesn't exist
        cur.execute("""
            SELECT COUNT(*) as count 
            FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS 
            WHERE CONSTRAINT_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'users' 
            AND CONSTRAINT_NAME = 'fk_banned_by';
        """)
        
        if cur.fetchone()['count'] == 0:
            cur.execute("""
                ALTER TABLE users
                ADD CONSTRAINT fk_banned_by
                FOREIGN KEY (banned_by) REFERENCES users(id)
                ON DELETE SET NULL;
            """)
        
        # Update existing users
        cur.execute("""
            UPDATE users SET 
                is_banned = COALESCE(is_banned, FALSE),
                suspension_type = 'none';
        """)
        
        # Create index if it doesn't exist
        cur.execute("""
            SELECT COUNT(*) as count 
            FROM INFORMATION_SCHEMA.STATISTICS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'users' 
            AND INDEX_NAME = 'idx_user_ban_status';
        """)
        
        if cur.fetchone()['count'] == 0:
            cur.execute("""
                CREATE INDEX idx_user_ban_status 
                ON users(is_banned, suspension_type, ban_expires_at, suspension_until);
            """)
        
        conn.commit()
        print("✅ Migración aplicada exitosamente!")
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Error al aplicar la migración: {e}")
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    apply_migration()
