import os
import logging
from flask import Flask, redirect, url_for, flash, session, render_template, jsonify, request
from flask_wtf.csrf import CSRFProtect, generate_csrf
from datetime import timedelta
from dotenv import load_dotenv
from .db import get_db_connection, get_cursor, init_app as init_db

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_app():
    try:
        # Cargar variables de entorno
        load_dotenv()
        logger.info("Variables de entorno cargadas correctamente")
        
        app = Flask(__name__)
        
        # Configuración básica
        app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'clave-secreta-predeterminada')
        app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
        app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max-limit
        
        # Configuración de MySQL desde variables de entorno
        app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST', 'mybdcontacsmc-competenciautm123.h.aivencloud.com')
        app.config['MYSQL_PORT'] = int(os.getenv('MYSQL_PORT', 17550))
        app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'avnadmin')
        app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', 'AVNS_qeAbBvUD5MS0PCRZdyH')
        app.config['MYSQL_DB'] = os.getenv('MYSQL_DB', 'defaultdb')
        app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
        
        logger.info("Configuración de la aplicación cargada")
    
        # Configurar protección CSRF
        csrf = CSRFProtect()
        csrf.init_app(app)
        app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 hora de validez para el token CSRF
        app.config['WTF_CSRF_CHECK_DEFAULT'] = False  # Desactivar la verificación global
        
        # Configuración de SSL si es necesario
        if os.getenv('MYSQL_SSL_MODE') == 'REQUIRED':
            app.config['MYSQL_SSL_MODE'] = 'REQUIRED'
            app.config['MYSQL_SSL_CA'] = os.getenv('MYSQL_SSL_CA', './ssl/ca.pem')
        
        # Inicializar la base de datos
        try:
            init_db(app)
            logger.info("Base de datos inicializada correctamente")
            
            # Configurar contexto para generar tokens CSRF
            @app.context_processor
            def inject_csrf_token():
                return dict(csrf_token=generate_csrf())
        except Exception as e:
            logger.error(f"Error al inicializar la base de datos: {e}", exc_info=True)
            raise
    
        # Registrar blueprints
        try:
            # Importar e inicializar las rutas desde el paquete routes
            from .routes import init_app as init_routes
            init_routes(app)
            
            logger.info("Blueprints registrados correctamente")
        except Exception as e:
            logger.error(f"Error al registrar blueprints: {e}", exc_info=True)
            raise
    
        # Ruta principal
        @app.route('/')
        def index():
            try:
                if 'user_id' not in session:
                    return redirect(url_for('auth.login'))
                return redirect(url_for('dashboard.index'))
            except Exception as e:
                logger.error(f"Error en la ruta principal: {e}", exc_info=True)
                return render_template('errors/500.html'), 500
    
        # Ruta de bienvenida (para pruebas)
        @app.route('/welcome')
        def welcome():
            try:
                return render_template('welcome.html')
            except Exception as e:
                logger.error(f"Error en la ruta de bienvenida: {e}", exc_info=True)
                return render_template('errors/500.html'), 500
    
        # Manejo de errores
        @app.errorhandler(404)
        def page_not_found(e):
            logger.warning(f"Página no encontrada: {request.url}")
            return render_template('errors/404.html'), 404
        
        @app.errorhandler(500)
        def internal_error(e):
            logger.error(f"Error interno del servidor: {e}", exc_info=True)
            return render_template('errors/500.html'), 500
            
        @app.errorhandler(413)
        def request_entity_too_large(error):
            return jsonify({"error": "El archivo es demasiado grande. El tamaño máximo permitido es 16MB"}), 413
            
        @app.teardown_appcontext
        def shutdown_session(exception=None):
            from .db import mysql
            if hasattr(mysql, 'connection'):
                mysql.connection.close()
                logger.info("Conexión a la base de datos cerrada")
    
        # Filtro de plantilla para formatear fechas
        @app.template_filter('format_datetime')
        def format_datetime(value, format='%d/%m/%Y %H:%M'):
            if value is None:
                return ""
            try:
                return value.strftime(format)
            except Exception as e:
                logger.error(f"Error al formatear fecha: {e}")
                return ""
        
        logger.info("Aplicación inicializada correctamente")
        return app
        
    except Exception as e:
        logger.critical(f"Error crítico al crear la aplicación: {e}", exc_info=True)
        if 'app' in locals():
            return app
        # Si no se pudo crear la app, devolver una aplicación mínima para mostrar el error
        app = Flask(__name__)
        
        @app.route('/')
        def error_route():
            return f"<h1>Error crítico en la aplicación</h1><p>{str(e)}</p>", 500
            
        return app
