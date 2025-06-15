def init_app(app):
    """Initialize the routes with the Flask app"""
    # Importar y registrar blueprints en orden de dependencia
    from .main import bp as main_bp
    app.register_blueprint(main_bp)
    
    from .auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from .dashboard import bp as dashboard_bp
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    
    from .books import bp as books_bp
    app.register_blueprint(books_bp, url_prefix='/books')
    
    from .loans import bp as loans_bp
    app.register_blueprint(loans_bp, url_prefix='/loans')
    
    from .reports import bp as reports_bp
    app.register_blueprint(reports_bp, url_prefix='/reports')
    
    from .users import bp as users_bp
    app.register_blueprint(users_bp, url_prefix='/users')
