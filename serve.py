"""Production entry point for Windows using Waitress WSGI server.

This module serves the Flask application in production on Windows systems.
It loads configuration from environment variables defined in .env file.
"""

import os
import logging
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()

# --- DEFENSIVE LOGGING SUPPRESSION ---
# This must happen as early as possible to catch loggers before they are initialized by imports
# We use WARNING level and NullHandler to ensure silence even if propagate is True somewhere
for logger_name in [
    'fontTools', 'weasyprint', 'sqlalchemy', 'sqlalchemy.engine', 
    'fontTools.subset', 'fontTools.ttLib.ttFont', 'fontTools.subset.timer',
    'weasyprint.progress', 'pill', 'PIL', 'asyncio'
]:
    l = logging.getLogger(logger_name)
    l.setLevel(logging.WARNING)
    l.propagate = False
    l.handlers = [logging.NullHandler()] 

# --- END LOGGING SUPPRESSION ---

# Set locale environment variables to help GLib/WeasyPrint with encoding on Windows
# This fixes "Conversion from character set UTF-8 to iso_1 is not supported" errors
os.environ['LANG'] = 'en_US.UTF-8'
os.environ['LC_ALL'] = 'en_US.UTF-8'

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