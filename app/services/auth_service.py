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
from app.exceptions import ValidationError, MeetingManagerError


class AuthService:
    """Service class for authentication-related operations."""
    
    @staticmethod
    def login_user_service(username: str, password: str) -> None:
        """Authenticate a user.
        
        Args:
            username: Username to authenticate.
            password: Plain text password.
            
        Raises:
            ValidationError: If credentials are wrong.
        """
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return
        raise ValidationError('Wrong credentials')
    
    @staticmethod
    def logout_user_service() -> None:
        """Log out the current user."""
        logout_user()
    
    @staticmethod
    def create_user_service(username: str, email: str, role: str = 'editor') -> str:
        """Create a new user with a temporary password.
        
        Args:
            username: New username.
            email: User email address.
            role: User role (default: 'editor').
        
        Returns:
            The generated temporary password.
            
        Raises:
            ValidationError: If user or email already exists.
            MeetingManagerError: If creation fails.
        """
        if User.query.filter_by(username=username).first():
            raise ValidationError('Username already exists')
        
        if User.query.filter_by(email=email).first():
            raise ValidationError('Email already registered')
        
        temp_password = AuthService._generate_temp_password()
        new_user = User(username=username, email=email, role=role, temp_password=temp_password)
        new_user.set_password(temp_password)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            logging.info(f'User {username} successfully created')
            return temp_password
        except Exception as e:
            db.session.rollback()
            logging.error(f'Error creating user {username}: {e}')
            raise MeetingManagerError('Error creating user')
    
    @staticmethod
    def update_user_service(user_id: int, role: Optional[str] = None, 
                          password: Optional[str] = None) -> None:
        """Update user role and/or password.
        
        Args:
            user_id: ID of user to update.
            role: New role (optional).
            password: New password (optional).
            
        Raises:
            MeetingManagerError: If update fails.
        """
        user = User.query.get_or_404(user_id)
        
        if role:
            user.role = role
        
        if password:
            user.set_password(password)
        
        try:
            db.session.commit()
            logging.info(f'User {user.username} successfully updated')
        except Exception as e:
            db.session.rollback()
            logging.error(f'Error updating user {user.username}: {e}')
            raise MeetingManagerError('Error updating user')

    @staticmethod
    def delete_user_service(user_id: int) -> None:
        """Delete a user.
        
        Args:
            user_id: ID of user to delete.
            
        Raises:
            ValidationError: If trying to delete the last super-admin.
            MeetingManagerError: If deletion fails.
        """
        user = User.query.get_or_404(user_id)
        
        # Prevent deletion of the last super-admin
        if user.role == 'super-admin':
            other_super_admins = User.query.filter_by(role='super-admin').filter(User.id != user_id).count()
            if other_super_admins == 0:
                raise ValidationError('Cannot delete the only super-admin user.')
        
        try:
            # Reassign events to current user before deletion
            from flask_login import current_user
            events = user.events
            for event in events:
                event.created_by = current_user.id
            
            db.session.delete(user)
            db.session.commit()
            logging.info(f'User {user.username} successfully deleted')
        except Exception as e:
            db.session.rollback()
            logging.error(f'Error deleting user {user.username}: {e}')
            raise MeetingManagerError('Error deleting user')

    @staticmethod
    def reset_password_service(user_id: int) -> None:
        """Reset user password and send email notification.
        
        Args:
            user_id: ID of user to reset password for.
            
        Raises:
            MeetingManagerError: If reset fails.
        """
        user = User.query.get_or_404(user_id)
        new_password = AuthService._generate_temp_password()
        user.set_password(new_password)
        
        try:
            db.session.commit()
            AuthService._send_reset_password_email(user.email, new_password)
        except Exception as e:
            db.session.rollback()
            logging.error(f'Error resetting password for user {user.username}: {e}')
            raise MeetingManagerError('Error resetting password')

    @staticmethod
    def change_password_service(user_id: int, new_password: str) -> None:
        """Change user password.
        
        Args:
            user_id: ID of user to change password for.
            new_password: New password.
            
        Raises:
            MeetingManagerError: If change fails.
        """
        user = User.query.get_or_404(user_id)
        user.set_password(new_password)
        user.temp_password = None
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logging.error(f'Error changing password for user {user.username}: {e}')
            raise MeetingManagerError('Error updating password')
    
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