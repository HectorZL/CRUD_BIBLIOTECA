from app import create_app
import logging

# Configurar el registro
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = create_app()

if __name__ == '__main__':
    try:
        logger.info("Iniciando la aplicación...")
        app.run(debug=True, port=5000, threaded=True)
    except Exception as e:
        logger.error(f"Error al iniciar la aplicación: {e}", exc_info=True)
        raise
