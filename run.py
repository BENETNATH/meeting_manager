"""Development entry point for the Meeting Manager application.

This module creates the Flask application instance and handles
initialization tasks like database setup and admin user creation.
It loads configuration from environment variables defined in .env file.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from app import create_app
from app.models import User, db



# Get configuration name from environment or default to development
config_name = os.environ.get('FLASK_ENV', 'development')
app = create_app(config_name)


def create_default_users_if_needed():
    """Create default admin and editor users if no users exist in the database."""
    with app.app_context():
        # Check if any users exist
        user_count = User.query.count()
        
        if user_count == 0:
            app.logger.info('No users found in database. Creating default users...')
            
            try:
                # Create super-admin
                admin = User(username='admin', email='admin@example.com', role='super-admin')
                admin.set_password('admin123')  # Default password for easy setup
                db.session.add(admin)
                
                # Create editor
                editor = User(username='editor', email='editor@example.com', role='editor')
                editor.set_password('editor123')  # Default password for easy setup
                db.session.add(editor)
                
                db.session.commit()
                
                app.logger.info('Default users created successfully:')
                app.logger.info('- Super-admin: username=admin, password=admin123')
                app.logger.info('- Editor: username=editor, password=editor123')
                app.logger.info('IMPORTANT: Change these default passwords after first login!')
                
            except Exception as e:
                db.session.rollback()
                app.logger.error(f'Failed to create default users: {e}')
        else:
            app.logger.info(f'Found {user_count} existing user(s). Skipping default user creation.')


if __name__ == '__main__':
    # Create default users if needed (only in development)
    if config_name == 'development':
        create_default_users_if_needed()
    
    # Load PORT and HOST from environment variables with fallback defaults
    port = int(os.environ.get('PORT', 8000))
    host = os.environ.get('HOST', '127.0.0.1')
    
    # Run the application
    app.logger.info(f'Development server starting on {host}:{port}...')
    app.run(host=host, port=port, debug=True)
