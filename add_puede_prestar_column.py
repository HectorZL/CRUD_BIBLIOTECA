import mysql.connector
from mysql.connector import Error
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_puede_prestar_column():
    """Agrega la columna puede_prestar a la tabla users si no existe"""
    conn = None
    cursor = None
    
    try:
        # Configuración de la conexión a la base de datos
        conn = mysql.connector.connect(
            host='mybdcontacsmc-competenciautm123.h.aivencloud.com',
            port=17550,
            user='avnadmin',
            password='AVNS_qeAbBvUD5MS0PCRZdyH',
            database='defaultdb'
        )
        
        if conn.is_connected():
            cursor = conn.cursor()
            
            # Verificar si la columna ya existe
            cursor.execute("""
                SELECT COUNT(*)
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = 'defaultdb' 
                AND TABLE_NAME = 'users' 
                AND COLUMN_NAME = 'puede_prestar'
            """)
            
            column_exists = cursor.fetchone()[0] > 0
            
            if not column_exists:
                # Agregar la columna
                cursor.execute("""
                    ALTER TABLE users 
                    ADD COLUMN puede_prestar BOOLEAN DEFAULT TRUE NOT NULL 
                    COMMENT 'Indica si el usuario puede realizar préstamos de libros';
                """)
                conn.commit()
                logger.info("✅ Columna 'puede_prestar' agregada exitosamente a la tabla 'users'")
            else:
                logger.info("ℹ️ La columna 'puede_prestar' ya existe en la tabla 'users'")
                
    except Error as e:
        logger.error(f"❌ Error al conectar o ejecutar la consulta: {e}")
        if conn and conn.is_connected():
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
            logger.info("🔌 Conexión a la base de datos cerrada")

if __name__ == "__main__":
    print("Iniciando script para agregar columna 'puede_prestar'...")
    add_puede_prestar_column()
