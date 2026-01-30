import os
import uuid
import logging
from typing import Optional, List, Tuple
from werkzeug.utils import secure_filename
from flask import current_app, abort
from flask_login import current_user
import bleach
from bleach.css_sanitizer import CSSSanitizer

# HTML sanitization constants
ALLOWED_TAGS = ['p', 'b', 'i', 'u', 'h1', 'h2', 'h3', 'ul', 'ol', 'li', 'strong', 'em', 'br', 'span', 'div']
ALLOWED_ATTRIBUTES = {'span': ['style'], 'div': ['style'], '*': ['class']}
CSS_SANITIZER = CSSSanitizer()

class SecurityService:
    """Centralized security service for hardening the application."""

    @staticmethod
    def sanitize_html(content: str) -> str:
        """Sanitize HTML content to prevent XSS."""
        if not content:
            return ""
        return bleach.clean(
            content,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            css_sanitizer=CSS_SANITIZER,
            strip=True
        )

    @staticmethod
    def validate_file_upload(file, allowed_extensions: List[str], max_size_mb: float = 16.0) -> Tuple[bool, str]:
        """
        Validate file extension, size, and MIME type using magic bytes.
        Returns (is_valid, error_message).
        """
        if not file or not file.filename:
            return False, "No file provided"

        # Check extension
        filename = file.filename
        ext = os.path.splitext(filename)[1].lower()
        if ext not in allowed_extensions:
            return False, f"Unsupported file extension: {ext}. Allowed: {', '.join(allowed_extensions)}"

        # Check size
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        
        if size > max_size_mb * 1024 * 1024:
            return False, f"File too large. Maximum size allowed is {max_size_mb}MB"

        # Mandatory Fix 6: Magic-byte MIME sniffing
        try:
            header = file.read(1024)
            file.seek(0)
            
            # Simple magic byte checks
            is_pdf = header.startswith(b'%PDF-')
            is_png = header.startswith(b'\x89PNG\r\n\x1a\n')
            is_jpeg = header.startswith(b'\xff\xd8\xff')
            
            if ext == '.pdf' and not is_pdf:
                return False, "Invalid PDF file (mismatched MIME type)"
            if ext in ['.jpg', '.jpeg'] and not is_jpeg:
                return False, "Invalid JPEG file (mismatched MIME type)"
            if ext == '.png' and not is_png:
                return False, "Invalid PNG file (mismatched MIME type)"
            
            # Additional check for images using Pillow
            if ext in ['.jpg', '.jpeg', '.png']:
                from PIL import Image
                try:
                    img = Image.open(file)
                    img.verify()
                    file.seek(0)
                except Exception:
                    return False, "Corrupted or invalid image file"
                    
        except Exception as e:
            logging.error(f"Error during MIME sniffing: {e}")
            return False, "Error validating file type"

        return True, ""

    @staticmethod
    def save_secure_file(file, folder: str, prefix: str = "") -> str:
        """
        Save a file with a randomized name to prevent overwrites and path traversal.
        Returns the new filename.
        """
        ext = os.path.splitext(file.filename)[1].lower()
        new_filename = f"{uuid.uuid4()}{f'_{prefix}' if prefix else ''}{ext}"
        
        # Ensure the folder is secure (non-executable should be handled at OS/Server level, 
        # but we ensure the path is clean)
        target_path = os.path.join(folder, new_filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        
        file.save(target_path)
        return new_filename

    @staticmethod
    def has_event_access(event) -> bool:
        """Centralized helper to check if user has access to event files/details."""
        # Admin / Owner always has access
        is_owner = current_user.is_authenticated and (
            current_user.role == 'super-admin' or 
            (current_user.role == 'editor' and event.created_by == current_user.id)
        )
        if is_owner:
            return True
            
        # Public access for visible events
        if event.status == 'visible':
            return True
            
        # Session access for password-protected events
        if event.status == 'password-protected':
            from flask import session
            if session.get(f'event_auth_{event.id}'):
                return True
                
        # Hidden and Archived are restricted to owner/admin
        return False

def require_role(role: str):
    """Decorator for role-based access control with 403 error."""
    if not current_user.is_authenticated:
        abort(401)
    if current_user.role != role and current_user.role != 'super-admin':
        abort(403)

def check_object_ownership(owner_id: int):
    """Helper to check if current user owns an object or is admin."""
    if not current_user.is_authenticated:
        abort(401)
    if current_user.role != 'super-admin' and current_user.id != owner_id:
        abort(403)
