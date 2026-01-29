#!/usr/bin/env python3
"""
Script to create default users for the Meeting Manager application.

This script provides functionality to:
1. Create default super-admin and editor users
2. Reset passwords for existing users
3. List all users in the system

Usage:
    python create_default_users.py [command] [options]

Commands:
    create-default     Create default super-admin and editor users
    create-superadmin  Create a super-admin user
    create-editor      Create an editor user
    reset-password     Reset password for a user
    list-users         List all users
    help              Show help message

Examples:
    python create_default_users.py create-default
    python create_default_users.py create-superadmin --username admin --email admin@example.com
    python create_default_users.py reset-password --username editor --password newpass123
"""

import argparse
import os
import sys
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import User
from app.services.auth_service import AuthService


def create_default_users(app: object) -> None:
    """Create default super-admin and editor users.
    
    Args:
        app: Flask application instance.
    """
    with app.app_context():
        # Check if users already exist
        super_admin = User.query.filter_by(role='super-admin').first()
        editor = User.query.filter_by(username='editor').first()
        
        if super_admin:
            print(f"Super-admin user '{super_admin.username}' already exists.")
        else:
            # Create super-admin
            success, password = AuthService.create_user_service(
                username='admin',
                email='admin@example.com',
                role='super-admin'
            )
            if success:
                print(f"✓ Created super-admin user 'admin' with temporary password: {password}")
            else:
                print(f"✗ Failed to create super-admin: {password}")
        
        if editor:
            print(f"Editor user '{editor.username}' already exists.")
        else:
            # Create editor
            success, password = AuthService.create_user_service(
                username='editor',
                email='editor@example.com',
                role='editor'
            )
            if success:
                print(f"✓ Created editor user 'editor' with temporary password: {password}")
            else:
                print(f"✗ Failed to create editor: {password}")


def create_user(username: str, email: str, role: str, app: object) -> None:
    """Create a new user.
    
    Args:
        username: Username for the new user.
        email: Email address for the new user.
        role: Role for the new user (super-admin or editor).
        app: Flask application instance.
    """
    with app.app_context():
        success, result = AuthService.create_user_service(username, email, role)
        if success:
            print(f"✓ Created {role} user '{username}' with temporary password: {result}")
        else:
            print(f"✗ Failed to create user: {result}")


def reset_password(username: str, new_password: Optional[str], app: object) -> None:
    """Reset password for an existing user.
    
    Args:
        username: Username of the user to reset password for.
        new_password: New password (if None, generates a temporary one).
        app: Flask application instance.
    """
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if not user:
            print(f"✗ User '{username}' not found.")
            return
        
        if new_password:
            success, message = AuthService.change_password_service(user.id, new_password)
            if success:
                print(f"✓ Password for user '{username}' updated successfully.")
            else:
                print(f"✗ Failed to update password: {message}")
        else:
            success, message = AuthService.reset_password_service(user.id)
            if success:
                print(f"✓ Password for user '{username}' reset successfully.")
            else:
                print(f"✗ Failed to reset password: {message}")


def list_users(app: object) -> None:
    """List all users in the system.
    
    Args:
        app: Flask application instance.
    """
    with app.app_context():
        users = User.query.all()
        if not users:
            print("No users found in the database.")
            return
        
        print(f"Found {len(users)} user(s):")
        print("-" * 60)
        for user in users:
            print(f"ID: {user.id}")
            print(f"Username: {user.username}")
            print(f"Email: {user.email}")
            print(f"Role: {user.role}")
            if user.temp_password:
                print(f"Temporary password: {user.temp_password}")
            print("-" * 60)


def main():
    """Main function to parse arguments and execute commands."""
    parser = argparse.ArgumentParser(
        description="Manage users for the Meeting Manager application.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create_default_users.py create-default
  python create_default_users.py create-superadmin --username admin --email admin@example.com
  python create_default_users.py reset-password --username editor --password newpass123
  python create_default_users.py list-users
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create default users command
    parser_default = subparsers.add_parser('create-default', help='Create default super-admin and editor users')
    
    # Create super-admin command
    parser_superadmin = subparsers.add_parser('create-superadmin', help='Create a super-admin user')
    parser_superadmin.add_argument('--username', required=True, help='Username for the super-admin')
    parser_superadmin.add_argument('--email', required=True, help='Email address for the super-admin')
    
    # Create editor command
    parser_editor = subparsers.add_parser('create-editor', help='Create an editor user')
    parser_editor.add_argument('--username', required=True, help='Username for the editor')
    parser_editor.add_argument('--email', required=True, help='Email address for the editor')
    
    # Reset password command
    parser_reset = subparsers.add_parser('reset-password', help='Reset password for a user')
    parser_reset.add_argument('--username', required=True, help='Username of the user')
    parser_reset.add_argument('--password', help='New password (optional, generates temporary if not provided)')
    
    # List users command
    parser_list = subparsers.add_parser('list-users', help='List all users')
    
    # Help command
    parser_help = subparsers.add_parser('help', help='Show this help message')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'help':
        parser.print_help()
        return
    
    # Create Flask app
    try:
        app = create_app()
    except Exception as e:
        print(f"✗ Failed to create Flask app: {e}")
        print("Make sure you have set all required environment variables.")
        print("See .env.sample for required variables.")
        return
    
    # Execute command
    if args.command == 'create-default':
        create_default_users(app)
    elif args.command == 'create-superadmin':
        create_user(args.username, args.email, 'super-admin', app)
    elif args.command == 'create-editor':
        create_user(args.username, args.email, 'editor', app)
    elif args.command == 'reset-password':
        reset_password(args.username, args.password, app)
    elif args.command == 'list-users':
        list_users(app)


if __name__ == '__main__':
    main()