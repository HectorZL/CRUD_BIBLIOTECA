import os
import ssl
import logging
import mysql.connector
from mysql.connector import Error, errorcode
from flask import current_app
from functools import wraps
import time

# Configurar logging
logger = logging.getLogger(__name__)

# Variable global para la conexión
db_connection = None

def get_db_connection():
    """Obtener una conexión a la base de datos"""
    global db_connection
    
    if db_connection is None or not db_connection.is_connected():
        try:
            ssl_config = {}
            ssl_ca = os.getenv('MYSQL_SSL_CA', './ssl/ca.pem')
            
            if os.getenv('MYSQL_SSL_MODE') == 'REQUIRED' and os.path.exists(ssl_ca):
                ssl_config = {
                    'ssl_ca': ssl_ca,
                    'ssl_verify_cert': True
                }
            
            db_connection = mysql.connector.connect(
                host=os.getenv('MYSQL_HOST', 'mybdcontacsmc-competenciautm123.h.aivencloud.com'),
                port=int(os.getenv('MYSQL_PORT', 17550)),
                user=os.getenv('MYSQL_USER', 'avnadmin'),
                password=os.getenv('MYSQL_PASSWORD', 'AVNS_qeAbBvUD5MS0PCRZdyH'),
                database=os.getenv('MYSQL_DB', 'defaultdb'),
                auth_plugin='mysql_native_password',  # Mantener compatibilidad
                **ssl_config
            )
            logger.info("Conexión a la base de datos establecida exitosamente")
            
        except Error as e:
            logger.error(f"Error al conectar a la base de datos: {e}")
            raise
    
    return db_connection
    
def init_app(app):
    """Inicializar la aplicación con la base de datos"""
    try:
        # Probar la conexión
        conn = get_db_connection()
        if conn.is_connected():
            logger.info("Conexión a la base de datos exitosa")
            
            # Verificar la existencias de las tablas
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SHOW TABLES")
            tables = [table['Tables_in_' + os.getenv('MYSQL_DB', 'defaultdb')] for table in cursor.fetchall()]
            
            if not tables:
                logger.info("No se encontraron tablas, creando estructura inicial...")
                create_tables()
            else:
                logger.info(f"Tablas existentes: {', '.join(tables)}")
                
            cursor.close()
            
    except Error as e:
        logger.error(f"Error al inicializar la base de datos: {e}")
        raise

    
    
    
def create_tables():
    """Crear tablas de la base de datos si no existen"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        logger.info("Creando tablas...")
        
        # Create users table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            email VARCHAR(255) UNIQUE,
            full_name VARCHAR(255),
            is_admin BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        
        # Create genres table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS genres (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE
        )""")
        
        # Create books table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            author VARCHAR(255) NOT NULL,
            isbn VARCHAR(20) UNIQUE,
            publication_year INT,
            publisher VARCHAR(255),
            genre_id INT,
            total_copies INT NOT NULL DEFAULT 1,
            available_copies INT NOT NULL DEFAULT 1,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (genre_id) REFERENCES genres(id) ON DELETE SET NULL
        )""")
        
        # Create loans table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS loans (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            book_id INT NOT NULL,
            loan_date DATE NOT NULL,
            due_date DATE NOT NULL,
            return_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        )""")
        
        # Create reservations table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS reservations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            book_id INT NOT NULL,
            reservation_date DATE NOT NULL,
            status ENUM('pending', 'ready_for_pickup', 'cancelled', 'fulfilled') DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        )""")
        
        # Create book_movements table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS book_movements (
            id INT AUTO_INCREMENT PRIMARY KEY,
            book_id INT NOT NULL,
            user_id INT NOT NULL,
            movement_type ENUM('alta', 'prestamo', 'devolucion', 'ajuste') NOT NULL,
            quantity INT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            description VARCHAR(255),
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )""")
        # Create book_movements table
        cur.execute("""
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
        """)
        
        # Insert default admin user if not exists
        cur.execute("SELECT * FROM users WHERE username = 'admin'")
        admin = cur.fetchone()
        
        if not admin:
            # Default admin password: admin123 (you should change this in production)
            from werkzeug.security import generate_password_hash
            hashed_password = generate_password_hash('admin123', method='sha256')
            
            cur.execute("""
                INSERT INTO users (username, password_hash, email, full_name, is_admin)
                VALUES (%s, %s, %s, %s, %s)
            """, ('admin', hashed_password, 'admin@example.com', 'Administrador', True))
        
        conn.commit()
        print("Tablas creadas exitosamente")
        
    except Exception as e:
        print(f"Error al crear tablas: {e}")
        conn.rollback()
    finally:
        if 'cur' in locals():
            cur.close()

def get_cursor():
    """Obtener un cursor de la base de datos"""
    try:
        conn = get_db_connection()
        return conn.cursor(dictionary=True)
    except Error as e:
        logger.error(f"Error al obtener cursor: {e}")
        raise

def init_ssl_config(app):
    """Initialize SSL configuration for MySQL"""
    # SSL Configuration for Aiven
    if app.config.get('MYSQL_SSL_MODE') == 'REQUIRED':
        ssl_config = {
            'ssl': {
                'ca': app.config.get('MYSQL_SSL_CA'),
                'check_hostname': False
            }
        }
        app.config['MYSQL_SSL'] = ssl_config
    return mysql

def test_connection():
    from app import create_app
    app = create_app()
    with app.app_context():
        try:
            conn = mysql.connection
            if conn is None:
                conn = mysql.connect()
            cur = conn.cursor()
            cur.execute('SELECT 1')
            print("¡Conexión exitosa a la base de datos!")
            return True
        except Exception as e:
            print(f"Error al conectar a la base de datos: {e}")
            return False
