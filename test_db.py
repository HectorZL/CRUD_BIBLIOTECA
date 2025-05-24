from app import app
from app.db import test_connection

if __name__ == "__main__":
    print("Probando conexión a la base de datos...")
    with app.app_context():
        if test_connection():
            print("¡La conexión se estableció correctamente!")
        else:
            print("No se pudo establecer la conexión. Verifica la configuración en el archivo .env")
