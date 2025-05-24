import os
import mysql.connector

def init_database():
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
        
        # Leer el archivo SQL
        with open('sql/db.sql', 'r') as sql_file:
            # Leer todo el contenido y dividir por punto y coma para obtener cada sentencia SQL
            sql_script = sql_file.read()
            # Dividir las sentencias SQL y eliminar líneas vacías
            statements = [stmt.strip() for stmt in sql_script.split(';') if stmt.strip()]
        
        # Ejecutar cada sentencia SQL por separado
        for statement in statements:
            try:
                if statement.upper().startswith('SELECT'):
                    cursor.execute(statement)
                    result = cursor.fetchall()
                    print(f"Ejecutada: {statement[:50]}...")
                    print("Resultado:", result)
                else:
                    cursor.execute(statement)
                    print(f"Ejecutada: {statement[:50]}...")
            except Exception as e:
                print(f"Error al ejecutar: {statement[:50]}...")
                print(f"Error: {e}")
        
        connection.commit()
        print("¡Todas las tablas se han creado exitosamente!")
        
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
            print("Conexión cerrada.")

if __name__ == "__main__":
    init_database()
