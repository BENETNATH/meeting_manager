"""Authentication service for the Meeting Manager application.

This module provides business logic for user authentication, registration,
and password management operations.
"""

import logging
import random
import string
from typing import Optional, Tuple

from flask import flash, url_for
from flask_login import login_user, logout_user
from flask_mail import Message
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db, mail
from app.models import User


class AuthService:
    """Service class for authentication-related operations."""
    
    @staticmethod
    def login_user_service(username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Authenticate a user.
        
        Args:
            username: Username to authenticate.
            password: Plain text password.
        
        Returns:
            Tuple of (success: bool, error_message: Optional[str]).
        """
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return True, None
        return False, 'Wrong credentials'
    
    @staticmethod
    def logout_user_service() -> None:
        """Log out the current user."""
        logout_user()
    
    @staticmethod
    def create_user_service(username: str, email: str, role: str = 'editor') -> Tuple[bool, str]:
        """Create a new user with a temporary password.
        
        Args:
            username: New username.
            email: User email address.
            role: User role (default: 'editor').
        
        Returns:
            Tuple of (success: bool, password_or_error: str).
        """
        if User.query.filter_by(username=username).first():
            return False, 'Username already exists'
        
        if User.query.filter_by(email=email).first():
            return False, 'Email already registered'
        
        temp_password = AuthService._generate_temp_password()
        new_user = User(username=username, email=email, role=role, temp_password=temp_password)
        new_user.set_password(temp_password)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            logging.info(f'User {username} successfully created')
            return True, temp_password
        except Exception as e:
            db.session.rollback()
            logging.error(f'Error creating user {username}: {e}')
            return False, 'Error creating user'
    
    @staticmethod
    def update_user_service(user_id: int, role: Optional[str] = None, 
                          password: Optional[str] = None) -> Tuple[bool, str]:
        """Update user role and/or password.
        
        Args:
            user_id: ID of user to update.
            role: New role (optional).
            password: New password (optional).
        
        Returns:
            Tuple of (success: bool, message: str).
        """
        user = User.query.get_or_404(user_id)
        
        if role:
            user.role = role
        
        if password:
            user.set_password(password)
        
        try:
            db.session.commit()
            return True, f'User {user.username} successfully updated.'
        except Exception as e:
            db.session.rollback()
            logging.error(f'Error updating user {user.username}: {e}')
            return False, 'Error updating user'
    
    @staticmethod
    def delete_user_service(user_id: int) -> Tuple[bool, str]:
        """Delete a user.
        
        Args:
            user_id: ID of user to delete.
        
        Returns:
            Tuple of (success: bool, message: str).
        """
        user = User.query.get_or_404(user_id)
        
        # Prevent deletion of the last super-admin
        if user.role == 'super-admin':
            other_super_admins = User.query.filter_by(role='super-admin').filter(User.id != user_id).count()
            if other_super_admins == 0:
                return False, 'Cannot delete the only super-admin user.'
        
        try:
            # Reassign events to current user before deletion
            from flask_login import current_user
            events = user.events
            for event in events:
                event.created_by = current_user.id
            
            db.session.delete(user)
            db.session.commit()
            logging.info(f'User {user.username} successfully deleted')
            return True, 'User successfully deleted'
        except Exception as e:
            db.session.rollback()
            logging.error(f'Error deleting user {user.username}: {e}')
            return False, 'Error deleting user'
    
    @staticmethod
    def reset_password_service(user_id: int) -> Tuple[bool, str]:
        """Reset user password and send email notification.
        
        Args:
            user_id: ID of user to reset password for.
        
        Returns:
            Tuple of (success: bool, message: str).
        """
        user = User.query.get_or_404(user_id)
        new_password = AuthService._generate_temp_password()
        user.set_password(new_password)
        
        try:
            db.session.commit()
            AuthService._send_reset_password_email(user.email, new_password)
            return True, 'Password has been reset and sent to the user\'s email.'
        except Exception as e:
            db.session.rollback()
            logging.error(f'Error resetting password for user {user.username}: {e}')
            return False, 'Error resetting password'
    
    @staticmethod
    def change_password_service(user_id: int, new_password: str) -> Tuple[bool, str]:
        """Change user password.
        
        Args:
            user_id: ID of user to change password for.
            new_password: New password.
        
        Returns:
            Tuple of (success: bool, message: str).
        """
        user = User.query.get_or_404(user_id)
        user.set_password(new_password)
        user.temp_password = None
        
        try:
            db.session.commit()
            return True, 'Password updated successfully.'
        except Exception as e:
            db.session.rollback()
            logging.error(f'Error changing password for user {user.username}: {e}')
            return False, 'Error updating password'
    
    @staticmethod
    def _generate_temp_password(length: int = 8) -> str:
        """Generate a temporary password.
        
        Args:
            length: Length of the password.
        
        Returns:
            Generated password string.
        """
        characters = string.ascii_letters + string.digits
        return ''.join(random.choices(characters, k=length))
    
    @staticmethod
    def _send_reset_password_email(email: str, new_password: str) -> None:
        """Send password reset email notification.
        
        Args:
            email: Recipient email address.
            new_password: New password to include in email.
        """
        subject = 'Password Reset'
        body = f'Hello,\n\nYour password has been reset. Your new password is: {new_password}\n\nPlease login and change your password as soon as possible.\n\nThank you!'
        
        msg = Message(subject=subject, recipients=[email], body=body)
        mail.send(msg)