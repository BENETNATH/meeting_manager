"""Application package for the Meeting Manager application.

This module contains the Application Factory function and initializes
all Flask extensions and blueprints.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional

from flask import Flask, request
from flask_babel import Babel

from app.extensions import (
    db, migrate, login_manager, bcrypt, mail, babel, csrf
)
from app.models import User
from config import get_config


def create_app(config_name: Optional[str] = None) -> Flask:
    """Application Factory function.
    
    Creates and configures the Flask application instance.
    
    Args:
        config_name: Configuration name (development, production, testing).
                     If None, uses FLASK_ENV environment variable.
    
    Returns:
        Configured Flask application instance.
    
    Raises:
        ValueError: If configuration validation fails.
    """
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static',
                static_url_path='/static')
    
    # Uploads are handled by the events blueprint
    pass
    
    # Load configuration
    config_class = get_config(config_name)
    app.config.from_object(config_class)
    
    # Validate required configuration
    config_class.validate_required_config()
    
    # Initialize extensions
    init_extensions(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Configure logging
    configure_logging(app)
    
    # Register template filters
    register_template_filters(app)
    
    # Register context processors
    register_context_processors(app)
    
    return app


def init_extensions(app: Flask) -> None:
    """Initialize Flask extensions with the application instance.
    
    Args:
        app: Flask application instance.
    """
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)
    babel.init_app(app)
    csrf.init_app(app)


def register_blueprints(app: Flask) -> None:
    """Register Flask blueprints.
    
    Args:
        app: Flask application instance.
    """
    from app.routes.auth import auth_bp
    from app.routes.events import events_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(events_bp)


def configure_logging(app: Flask) -> None:
    """Configure application logging.
    
    Args:
        app: Flask application instance.
    """
    if not app.testing:
        if app.config['LOG_TO_STDOUT']:
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(logging.INFO)
            app.logger.addHandler(stream_handler)
        else:
            if not os.path.exists('logs'):
                os.mkdir('logs')
            file_handler = RotatingFileHandler(
                'logs/app.log',
                maxBytes=10240000,
                backupCount=10
            )
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s '
                '[in %(pathname)s:%(lineno)d]'
            ))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('Meeting Manager startup')
        
        # Configure SQLAlchemy logging to reduce verbosity in production
        # Set SQLAlchemy engine logger to WARNING level to suppress SQL query logs
        sqlalchemy_logger = logging.getLogger('sqlalchemy.engine')
        sqlalchemy_logger.setLevel(logging.WARNING)
        
        # Also configure the generic sqlalchemy logger
        sqlalchemy_base_logger = logging.getLogger('sqlalchemy')
        sqlalchemy_base_logger.setLevel(logging.WARNING)


def register_template_filters(app: Flask) -> None:
    """Register Jinja2 template filters.
    
    Args:
        app: Flask application instance.
    """
    import re
    
    def strip_html(value: str) -> str:
        """Remove HTML tags from a string.
        
        Args:
            value: String containing HTML.
        
        Returns:
            String with HTML tags removed.
        """
        return re.sub('<.*?>', '', value)
    
    app.jinja_env.filters['strip_html'] = strip_html


def register_context_processors(app: Flask) -> None:
    """Register template context processors.
    
    Args:
        app: Flask application instance.
    """
    import pytz
    
    @app.context_processor
    def inject_timezones():
        """Inject timezone list into template context.
        
        Returns:
            Dictionary with timezone list.
        """
        return dict(timezones=pytz.common_timezones)


@login_manager.user_loader
def load_user(user_id: str):
    """Load user by ID for Flask-Login.
    
    Args:
        user_id: User ID as string.
    
    Returns:
        User object or None.
    """
    return User.query.get(int(user_id))