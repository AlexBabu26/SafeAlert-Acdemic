"""
Flask application factory for SafeAlert
"""
from flask import Flask
from pathlib import Path
from app.config import Config
from app.extensions import db, jwt, cors, socketio, migrate

# Get the base directory (project root)
BASE_DIR = Path(__file__).resolve().parent.parent


def create_app(config_class=Config):
    """Create and configure Flask application"""
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / 'templates'),
        static_folder=str(BASE_DIR / 'static')
    )
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    cors.init_app(app, origins=app.config['CORS_ORIGINS'], supports_credentials=app.config['CORS_SUPPORTS_CREDENTIALS'])
    socketio.init_app(app)
    migrate.init_app(app, db)
    
    # Configure JWT to handle integer identities
    # Flask-JWT-Extended expects string identities, so we convert
    @jwt.user_identity_loader
    def user_identity_lookup(identity):
        """Convert user ID to string for JWT"""
        return str(identity) if identity is not None else None
    
    # Register blueprints - API
    from app.api import auth, categories, incidents, admin_incidents, messages, analytics
    from app.api import responder, dispatcher, notifications, alerts, admin_users
    from app import routes as frontend
    
    app.register_blueprint(auth.bp, url_prefix='/api/auth')
    app.register_blueprint(categories.bp, url_prefix='/api/categories')
    app.register_blueprint(incidents.bp, url_prefix='/api/incidents')
    app.register_blueprint(admin_incidents.bp, url_prefix='/api/admin')
    app.register_blueprint(messages.bp)  # Messages routes are already prefixed in the blueprint
    app.register_blueprint(analytics.bp, url_prefix='/api/admin/analytics')
    app.register_blueprint(admin_users.bp, url_prefix='/api/admin/users')
    app.register_blueprint(responder.bp, url_prefix='/api/responder')
    app.register_blueprint(dispatcher.bp, url_prefix='/api/dispatcher')
    app.register_blueprint(notifications.bp, url_prefix='/api/notifications')
    app.register_blueprint(alerts.bp, url_prefix='/api/alerts')
    app.register_blueprint(frontend.bp)
    
    # Register CLI commands
    from app import cli
    cli.register_commands(app)
    
    # Import SocketIO event handlers
    from app import socketio_events  # noqa: F401
    
    return app
