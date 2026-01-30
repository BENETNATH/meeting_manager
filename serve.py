"""Production entry point for Windows using Waitress WSGI server.

This module serves the Flask application in production on Windows systems.
It loads configuration from environment variables defined in .env file.
"""

import os
import logging
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()


# Configure SQLAlchemy logging BEFORE importing the app
# This ensures the loggers are configured before SQLAlchemy creates them
sqlalchemy_logger = logging.getLogger('sqlalchemy.engine')
sqlalchemy_logger.setLevel(logging.WARNING)
sqlalchemy_logger.propagate = False  # Prevent propagation to root logger
sqlalchemy_logger.handlers.clear()   # Remove any existing handlers

sqlalchemy_base_logger = logging.getLogger('sqlalchemy')
sqlalchemy_base_logger.setLevel(logging.WARNING)
sqlalchemy_base_logger.propagate = False  # Prevent propagation to root logger
sqlalchemy_base_logger.handlers.clear()   # Remove any existing handlers

from app import create_app



# Get configuration name from environment or default to production
config_name = os.environ.get('FLASK_ENV', 'production')
app = create_app(config_name)


def main():
    """Start the production server using Waitress."""
    # Load PORT and HOST from environment variables with fallback defaults
    port = int(os.environ.get('PORT', 8000))
    host = os.environ.get('HOST', '0.0.0.0')
    
    # Configure logging for production
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Configure SQLAlchemy logging to reduce verbosity
    # Set SQLAlchemy engine logger to WARNING level to suppress SQL query logs
    sqlalchemy_logger = logging.getLogger('sqlalchemy.engine')
    sqlalchemy_logger.setLevel(logging.WARNING)
    
    # Also configure the generic sqlalchemy logger
    sqlalchemy_base_logger = logging.getLogger('sqlalchemy')
    sqlalchemy_base_logger.setLevel(logging.WARNING)
    
    # Also configure the Flask app's SQLAlchemy logging
    # This ensures the logging configuration is applied when the app is created
    app.config['SQLALCHEMY_ENGINE_LOG_LEVEL'] = 'WARNING'
    
    logger = logging.getLogger(__name__)
    logger.info(f'Production server starting on {host}:{port}...')
    logger.info(f'Using configuration: {config_name}')
    logger.info(f'Environment: {os.environ.get("FLASK_ENV", "development")}')
    
    try:
        from waitress import serve
        serve(app, host=host, port=port)
    except ImportError:
        logger.error('Waitress is not installed. Please install it with: pip install waitress')
        raise
    except Exception as e:
        logger.error(f'Failed to start server: {e}')
        raise


if __name__ == '__main__':
    main()