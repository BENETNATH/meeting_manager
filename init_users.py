#!/usr/bin/env python3
"""
Meeting Manager - User Initialization Script

This script creates default users for the Meeting Manager application.
It's designed to be run once during initial setup or when deploying the application.

Features:
- Creates database tables if they don't exist
- Creates default super-admin and editor users if they don't already exist
- Validates database configuration and connectivity
- Provides comprehensive error handling and user feedback
- Generates secure temporary passwords for new users

Usage:
    python init_users.py

Default credentials created:
    Super-admin: username='admin', email='admin@example.com'
    Editor:      username='editor', email='editor@example.com'

Both users will have randomly generated temporary passwords displayed in the console.
Users must change their passwords on first login.

Prerequisites:
- Python 3.8+
- All required dependencies installed (see requirements.txt)
- Environment variables configured (see .env.sample)
- Database accessible and properly configured

Security Notes:
- Temporary passwords are generated using cryptographically secure random generation
- Passwords are displayed only once during creation
- Users are required to change their passwords on first login
- The script validates all required environment variables before proceeding
"""

import os
import sys
import logging
from datetime import datetime
from typing import Tuple, Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import User
from app.services.auth_service import AuthService
from config import get_config


class UserInitializationError(Exception):
    """Custom exception for user initialization errors."""
    pass


def setup_logging():
    """Configure logging for the initialization script."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('init_users.log')
        ]
    )


def validate_environment() -> Tuple[bool, str]:
    """
    Validate that all required environment variables are set.
    
    Returns:
        Tuple of (is_valid: bool, error_message: str).
    """
    required_vars = [
        'SECRET_KEY',
        'SQLALCHEMY_DATABASE_URI',
        'MAIL_SERVER',
        'MAIL_USERNAME',
        'MAIL_PASSWORD',
        'MAIL_DEFAULT_SENDER'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        return False, f"Missing required environment variables: {', '.join(missing_vars)}"
    
    return True, "Environment validation passed"


def validate_database_connection(app) -> Tuple[bool, str]:
    """
    Validate database connection and configuration.
    
    Args:
        app: Flask application instance.
    
    Returns:
        Tuple of (is_valid: bool, message: str).
    """
    try:
        with app.app_context():
            # Test database connection using SQLAlchemy 2.0 syntax
            with db.engine.connect() as connection:
                connection.execute(db.text('SELECT 1')).fetchone()
            return True, "Database connection successful"
    except Exception as e:
        return False, f"Database connection failed: {e}"


def create_database_tables(app) -> Tuple[bool, str]:
    """
    Create database tables if they don't exist.
    
    Args:
        app: Flask application instance.
    
    Returns:
        Tuple of (success: bool, message: str).
    """
    try:
        with app.app_context():
            # Create all tables
            db.create_all()
            logging.info("Database tables created successfully")
            return True, "Database tables created successfully"
    except Exception as e:
        logging.error(f"Failed to create database tables: {e}")
        return False, f"Failed to create database tables: {e}"


def check_existing_users(app) -> Tuple[bool, int]:
    """
    Check if users already exist in the database.
    
    Args:
        app: Flask application instance.
    
    Returns:
        Tuple of (users_exist: bool, user_count: int).
    """
    try:
        with app.app_context():
            user_count = db.session.query(db.func.count(User.id)).scalar()
            return user_count > 0, user_count
    except Exception as e:
        logging.error(f"Failed to check existing users: {e}")
        return False, 0


def create_default_users(app) -> Tuple[bool, list]:
    """
    Create default super-admin and editor users.
    
    Args:
        app: Flask application instance.
    
    Returns:
        Tuple of (success: bool, created_users: list).
    """
    created_users = []
    
    # Define default users to create
    default_users = [
        {
            'username': 'admin',
            'email': 'admin@example.com',
            'role': 'super-admin',
            'description': 'Super Administrator'
        },
        {
            'username': 'editor',
            'email': 'editor@example.com',
            'role': 'editor',
            'description': 'Editor'
        }
    ]
    
    for user_config in default_users:
        try:
            success, result = AuthService.create_user_service(
                username=user_config['username'],
                email=user_config['email'],
                role=user_config['role']
            )
            
            if success:
                created_users.append({
                    'username': user_config['username'],
                    'email': user_config['email'],
                    'role': user_config['role'],
                    'password': result,
                    'description': user_config['description']
                })
                logging.info(f"Successfully created user: {user_config['username']}")
            else:
                logging.error(f"Failed to create user {user_config['username']}: {result}")
                
        except Exception as e:
            logging.error(f"Exception creating user {user_config['username']}: {e}")
    
    return len(created_users) > 0, created_users


def display_user_credentials(created_users: list) -> None:
    """
    Display created user credentials in a formatted table.
    
    Args:
        created_users: List of created user dictionaries.
    """
    if not created_users:
        return
    
    print("\n" + "=" * 80)
    print("CREATED USER CREDENTIALS")
    print("=" * 80)
    print(f"{'Username':<15} {'Role':<15} {'Email':<30} {'Temporary Password'}")
    print("-" * 80)
    
    for user in created_users:
        print(f"{user['username']:<15} {user['role']:<15} {user['email']:<30} {user['password']}")
    
    print("=" * 80)


def display_security_reminders() -> None:
    """Display important security reminders."""
    print("\n" + "🔒 SECURITY REMINDERS " + "🔒".center(50, " "))
    print("=" * 80)
    print("1. Temporary passwords are displayed ONLY ONCE")
    print("2. Users MUST change their passwords on first login")
    print("3. Store these credentials securely")
    print("4. Consider using stronger passwords in production")
    print("5. Update email settings in .env for password reset functionality")
    print("=" * 80)


def display_next_steps() -> None:
    """Display next steps for the user."""
    print("\n" + "📋 NEXT STEPS " + "📋".center(50, " "))
    print("=" * 80)
    print("1. Start the application: python run.py")
    print("2. Access the login page in your browser")
    print("3. Log in with the created credentials")
    print("4. Change passwords immediately after first login")
    print("5. Configure email settings in .env for full functionality")
    print("6. Review and customize user roles as needed")
    print("=" * 80)


def main():
    """Main function to initialize default users for the application."""
    print("Meeting Manager - User Initialization")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Setup logging
    setup_logging()
    
    try:
        # Step 1: Validate environment configuration
        print("\n1. Validating environment configuration...")
        is_valid, message = validate_environment()
        if not is_valid:
            print(f"   ✗ {message}")
            print("\nPlease ensure all required environment variables are set.")
            print("See .env.sample for required variables and example values.")
            sys.exit(1)
        print(f"   ✓ {message}")
        
        # Step 2: Create Flask app
        print("\n2. Creating Flask application...")
        try:
            app = create_app()
            print("   ✓ Flask application created successfully")
        except Exception as e:
            print(f"   ✗ Failed to create Flask application: {e}")
            sys.exit(1)
        
        # Step 3: Validate database connection
        print("\n3. Validating database connection...")
        is_valid, message = validate_database_connection(app)
        if not is_valid:
            print(f"   ✗ {message}")
            print("\nPlease check your database configuration in .env file.")
            sys.exit(1)
        print(f"   ✓ {message}")
        
        # Step 4: Create database tables
        print("\n4. Creating database tables...")
        success, message = create_database_tables(app)
        if not success:
            print(f"   ✗ {message}")
            sys.exit(1)
        print(f"   ✓ {message}")
        
        # Step 5: Check for existing users
        print("\n5. Checking for existing users...")
        users_exist, user_count = check_existing_users(app)
        if users_exist:
            print(f"   ✓ Found {user_count} existing user(s)")
            print("   → Skipping user creation (users already exist)")
            print("\n" + "=" * 80)
            print("User initialization completed!")
            print("Users already exist in the database. No new users were created.")
            display_next_steps()
            return
        else:
            print("   ✓ No existing users found")
            print("   → Proceeding with default user creation")
        
        # Step 6: Create default users
        print("\n6. Creating default users...")
        with app.app_context():
            success, created_users = create_default_users(app)
        
        if success:
            print(f"   ✓ Successfully created {len(created_users)} user(s)")
            
            # Display credentials
            display_user_credentials(created_users)
            
            # Display security reminders
            display_security_reminders()
            
            print("\n" + "=" * 80)
            print("User initialization completed successfully!")
            
            # Display next steps
            display_next_steps()
            
        else:
            print("   ✗ Failed to create any users")
            print("\nPlease check the application logs for more details.")
            sys.exit(1)
            
    except UserInitializationError as e:
        print(f"\n✗ User initialization error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nUser initialization cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error during initialization: {e}")
        print("\nPlease check the application logs for more details.")
        sys.exit(1)


if __name__ == '__main__':
    main()
