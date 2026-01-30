"""Extensions module for the Meeting Manager application.

This module initializes and configures Flask extensions to prevent
circular imports when using the Application Factory pattern.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from flask_babel import Babel
from flask_wtf.csrf import CSRFProtect

# Initialize extensions without the app instance
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
bcrypt = Bcrypt()
mail = Mail()
babel = Babel()
csrf = CSRFProtect()

# Configure extension settings
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'