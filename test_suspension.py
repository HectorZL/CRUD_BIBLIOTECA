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

def test_ban_check(user_id=7):
    """Check if user is banned"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check if user is banned
        cursor.execute("""
            SELECT is_banned FROM users WHERE id = %s
        """, (user_id,))
        
        result = cursor.fetchone()
        if not result:
            logger.error(f"❌ Usuario con ID {user_id} no encontrado")
            return
            
        is_banned = result['is_banned']
        logger.info(f"\n📋 Estado del usuario {user_id}:")
        logger.info(f"  - Está baneado: {'Sí' if is_banned else 'No'}")
        
        # Simulate loan creation
        logger.info("\n🔍 Probando creación de préstamo...")
        
        if is_banned:
            logger.warning("❌ Usuario baneado - No se puede crear préstamo")
        else:
            logger.info("✅ Usuario puede crear préstamos")
        
        return is_banned
        
    except Exception as e:
        logger.error(f"❌ Error durante la prueba: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    import sys
    user_id = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    test_ban_check(user_id)
