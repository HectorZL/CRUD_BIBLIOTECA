import os
import mysql.connector
from mysql.connector import Error
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_connection():
    """Create a direct database connection"""
    try:
        conn = mysql.connector.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            user=os.getenv('MYSQL_USER', 'avnadmin'),
            password=os.getenv('MYSQL_PASSWORD', 'AVNS_qeAbBvUD5MS0PCRZdyH'),
            database=os.getenv('MYSQL_DB', 'defaultdb'),
            use_unicode=True,
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci'
        )
        logger.info("Conexión a la base de datos establecida exitosamente")
        return conn
    except Error as e:
        logger.error(f"Error al conectar a la base de datos: {e}")
        raise

def check_column_exists(conn, table, column):
    """Check if a column exists in a table"""
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = %s 
            AND COLUMN_NAME = %s
        """, (table, column))
        return cursor.fetchone() is not None
    finally:
        cursor.close()

def apply_migration():
    """Apply the suspension columns migration to the database"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        logger.info("🔧 Iniciando migración para agregar columnas de suspensión...")
        
        # Add suspension columns one by one with error handling
        columns_to_add = [
            ("is_banned", "BOOLEAN DEFAULT FALSE COMMENT 'Indica si el usuario está baneado'"),
            ("ban_reason", "VARCHAR(255) DEFAULT NULL COMMENT 'Razón de la restricción'"),
            ("ban_expires_at", "DATETIME DEFAULT NULL COMMENT 'Fecha de expiración de la restricción'"),
            ("banned_at", "DATETIME DEFAULT NULL COMMENT 'Fecha en que se aplicó la restricción'"),
            ("banned_by", "INT DEFAULT NULL COMMENT 'ID del administrador que aplicó la restricción'"),
            ("suspension_type", "ENUM('none', 'temporary', 'permanent') DEFAULT 'none' COMMENT 'Tipo de suspensión'"),
            ("suspension_until", "DATETIME DEFAULT NULL COMMENT 'Hasta cuándo está suspendido el usuario'")
        ]
        
        for column, definition in columns_to_add:
            if not check_column_exists(conn, 'users', column):
                logger.info(f"Agregando columna: {column}")
                cursor.execute(f"ALTER TABLE users ADD COLUMN {column} {definition}")
        
        # Add foreign key constraint if it doesn't exist
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS 
            WHERE CONSTRAINT_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'users' 
            AND CONSTRAINT_NAME = 'fk_banned_by';
        """)
        
        if cursor.fetchone()[0] == 0:
            logger.info("Agregando llave foránea fk_banned_by")
            cursor.execute("""
                ALTER TABLE users
                ADD CONSTRAINT fk_banned_by
                FOREIGN KEY (banned_by) REFERENCES users(id)
                ON DELETE SET NULL;
            """)
        
        # Update existing users
        logger.info("Actualizando usuarios existentes...")
        cursor.execute("""
            UPDATE users SET 
                is_banned = COALESCE(is_banned, FALSE),
                suspension_type = 'none';
        """)
        
        # Create index if it doesn't exist
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM INFORMATION_SCHEMA.STATISTICS 
            WHERE TABLE_SCHEMA = DATABASE() 
            AND TABLE_NAME = 'users' 
            AND INDEX_NAME = 'idx_user_ban_status';
        """)
        
        if cursor.fetchone()[0] == 0:
            logger.info("Creando índice idx_user_ban_status")
            cursor.execute("""
                CREATE INDEX idx_user_ban_status 
                ON users(is_banned, suspension_type, ban_expires_at, suspension_until);
            """)
        
        conn.commit()
        logger.info("✅ Migración aplicada exitosamente!")
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"❌ Error al aplicar la migración: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    apply_migration()
