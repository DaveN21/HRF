import os
import logging
from flask import Flask
from flask_login import LoginManager
from database import db

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_app():
    logger.info("Creating Flask application...")
    app = Flask(__name__)

    # Configuration
    logger.info("Configuring application...")
    app.secret_key = os.environ.get("SESSION_SECRET")
    if not app.secret_key:
        logger.error("SESSION_SECRET not set!")
        raise RuntimeError("SESSION_SECRET environment variable is required!")

    # Database configuration
    logger.info("Configuring database...")
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL not set!")
        raise RuntimeError("DATABASE_URL environment variable is required!")

    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 5,
        "max_overflow": 10,
        "connect_args": {
            "sslmode": "require",
            "connect_timeout": 10
        }
    }

    # Initialize extensions
    logger.info("Initializing database...")
    db.init_app(app)

    # Initialize login manager
    logger.info("Initializing login manager...")
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Import models
    logger.info("Importing models...")
    from models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Create database tables
    logger.info("Creating database tables...")
    with app.app_context():
        try:
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {str(e)}")
            raise

    # Register blueprints
    logger.info("Registering blueprints...")
    try:
        from routes.main import main_bp
        from routes.auth import auth_bp
        from routes.trial import trial_bp
        app.register_blueprint(main_bp)
        app.register_blueprint(auth_bp, url_prefix='/auth')
        app.register_blueprint(trial_bp, url_prefix='/trial')
        logger.info("Blueprints registered successfully")
    except Exception as e:
        logger.error(f"Error registering blueprints: {str(e)}")
        raise

    logger.info("Application created successfully")
    return app

# Create the application instance
app = create_app()