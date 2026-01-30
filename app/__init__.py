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
    db, migrate, login_manager, bcrypt, mail, babel, csrf, limiter, talisman
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
    limiter.init_app(app)
    
    # Configure CSP for Talisman
    csp = {
        'default-src': [
            '\'self\'',
            'https://fonts.googleapis.com',
            'https://fonts.gstatic.com',
            'https://cdn.jsdelivr.net',
            'https://cdnjs.cloudflare.com',
            'data:',
        ],
        'style-src': [
            '\'self\'',
            'https://fonts.googleapis.com',
            'https://cdn.jsdelivr.net',
            'https://cdnjs.cloudflare.com',
            '\'unsafe-inline\'', # Fallback for older browsers
        ],
        'style-src-elem': [
            '\'self\'',
            'https://fonts.googleapis.com',
            'https://cdn.jsdelivr.net',
            'https://cdnjs.cloudflare.com',
            # Nonce will be injected here by Talisman
        ],
        'style-src-attr': [
            '\'self\'',
            '\'unsafe-inline\'', # To allow style="..." attributes
        ],
        'script-src': [
            '\'self\'',
            'https://cdn.jsdelivr.net',
            'https://cdnjs.cloudflare.com',
            # Nonce will be injected here
        ],
        'font-src': [
            '\'self\'',
            'https://fonts.gstatic.com',
            'https://cdnjs.cloudflare.com',
        ],
        'img-src': ['\'self\'', 'data:', 'blob:', '*', 'https:'],
    }
    
    # Always initialize Talisman to provide csp_nonce() to templates
    # but only enable strict features (CSP, HTTPS, HSTS) in production
    is_production = not app.debug and not app.testing
    
    talisman.init_app(
        app,
        content_security_policy=csp if is_production else None,
        content_security_policy_nonce_in=['script-src', 'style-src', 'style-src-elem'],
        force_https=app.config.get('FORCE_HTTPS', False) if is_production else False,
        session_cookie_secure=app.config.get('SESSION_COOKIE_SECURE', True) if is_production else False,
        session_cookie_http_only=True,
        session_cookie_samesite='Lax',
        force_file_save=True if is_production else False
    )


def register_blueprints(app: Flask) -> None:
    """Register Flask blueprints.
    
    Args:
        app: Flask application instance.
    """
    from app.routes.auth import auth_bp
    from app.routes.events import events_bp
    from app.routes.certificates import certificates_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(certificates_bp)


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
        
        # Silence excessive logging from libraries
        for logger_name in [
            'fontTools', 'weasyprint', 'sqlalchemy', 'sqlalchemy.engine', 
            'fontTools.subset', 'fontTools.ttLib.ttFont', 'fontTools.subset.timer',
            'weasyprint.progress', 'pill', 'PIL'
        ]:
            l = logging.getLogger(logger_name)
            l.setLevel(logging.WARNING)
            l.propagate = False


def register_template_filters(app: Flask) -> None:
    """Register Jinja2 template filters.
    
    Args:
        app: Flask application instance.
    """
    import re
    
    def strip_html(value: str) -> str:
        """Remove HTML tags from a string while preserving line breaks.
        
        Args:
            value: String containing HTML.
        
        Returns:
            String with HTML tags removed and line breaks preserved.
        """
        if not value:
            return ""
        from html import unescape
        # Replace block tags and <br> with newlines
        s = re.sub(r'</?(p|div|br|li|h[1-6])[^>]*>', '\n', value)
        # Remove all other tags
        s = re.sub(r'<[^>]+>', '', s)
        # Decode HTML entities
        s = unescape(s)
        # Clean up: strip whitespace from lines and reduce multiple newlines
        lines = [line.strip() for line in s.split('\n')]
        s = '\n'.join(lines)
        s = re.sub(r'\n{3,}', '\n\n', s)
        return s.strip()
    
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