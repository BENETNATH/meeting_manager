"""Database models for the Meeting Manager application.

This module defines SQLAlchemy models for User, Event, and Registration
entities with proper relationships and validation.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class User(UserMixin, db.Model):
    """User model for authentication and authorization.
    
    Attributes:
        id: Primary key.
        username: Unique username.
        email: Unique email address.
        password: Hashed password.
        role: User role (super-admin, editor).
        temp_password: Temporary password for new users.
    """
    
    __tablename__ = 'user'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(db.String(150), nullable=False, unique=True)
    email: Mapped[str] = mapped_column(db.String(150), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(db.String(150), nullable=False)
    role: Mapped[str] = mapped_column(db.String(50), nullable=False, default='editor')
    temp_password: Mapped[Optional[str]] = mapped_column(db.String(150), nullable=True)
    
    # Relationships
    events = relationship('Event', backref='creator', lazy=True)
    registrations = relationship('Registration', backref='user', lazy=True)
    
    def set_password(self, password: str) -> None:
        """Hash and set the user's password.
        
        Args:
            password: Plain text password.
        """
        from flask_bcrypt import generate_password_hash
        self.password = generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password: str) -> bool:
        """Check if the provided password matches the hashed password.
        
        Args:
            password: Plain text password to check.
        
        Returns:
            True if password matches, False otherwise.
        """
        from flask_bcrypt import check_password_hash
        return check_password_hash(self.password, password)
    
    def __repr__(self) -> str:
        """String representation of the user."""
        return f'<User {self.username}>'


class CertificateTemplate(db.Model):
    """Model for customizable certificate templates.
    
    Attributes:
        id: Primary key.
        name: Template name.
        layout_data: JSON data describing the layout elements.
        background_img: Path to background image.
        created_at: Creation timestamp.
    """
    __tablename__ = 'certificate_template'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(100), nullable=False)
    layout_data: Mapped[dict] = mapped_column(db.JSON, nullable=False)
    background_img: Mapped[Optional[str]] = mapped_column(db.String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f'<CertificateTemplate {self.name}>'


class Event(db.Model):
    """Event model for managing events and their details.
    
    Attributes:
        id: Primary key.
        title: Event title.
        description: Event description.
        photo_url: URL to event photo.
        photo_filename: Filename of uploaded event photo.
        program: Event program details.
        date: Event date.
        start_time: Event start time.
        end_time: Event end time.
        organizer: Event organizer name.
        location: Event location.
        eligible_hours: Number of eligible hours.
        status: Event status (hidden, visible, archived).
        created_by: Foreign key to User who created the event.
        signature_url: URL to organizer signature.
        signature_filename: Filename of uploaded organizer signature.
        timezone: Event timezone.
    """
    
    __tablename__ = 'event'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(db.String(100), nullable=False)
    description: Mapped[str] = mapped_column(db.Text, nullable=False)
    photo_url: Mapped[Optional[str]] = mapped_column(db.String(200), nullable=True)
    photo_filename: Mapped[Optional[str]] = mapped_column(db.String(200), nullable=True)
    program: Mapped[str] = mapped_column(db.Text, nullable=False)
    date: Mapped[datetime.date] = mapped_column(db.Date, nullable=False)
    start_time: Mapped[Optional[datetime.time]] = mapped_column(db.Time, nullable=True)
    end_time: Mapped[Optional[datetime.time]] = mapped_column(db.Time, nullable=True)
    organizer: Mapped[Optional[str]] = mapped_column(db.String(100), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(db.String(200), nullable=True)
    eligible_hours: Mapped[Optional[float]] = mapped_column(db.Float, nullable=True)
    status: Mapped[str] = mapped_column(db.String(50), nullable=False, default='hidden')
    created_by: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    signature_url: Mapped[Optional[str]] = mapped_column(db.String(200), nullable=True)
    signature_filename: Mapped[Optional[str]] = mapped_column(db.String(200), nullable=True)

    timezone: Mapped[str] = mapped_column(db.String(50), nullable=False, default='UTC')
    template_id: Mapped[Optional[int]] = mapped_column(db.Integer, db.ForeignKey('certificate_template.id'), nullable=True)
    
    template = relationship('CertificateTemplate', backref='events')
    
    attachments = relationship('Attachment', backref='event', lazy=True, cascade="all, delete-orphan")
    registrations = relationship('Registration', backref='event', lazy=True)
    
    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('hidden', 'visible', 'archived')", name='valid_status'),
        CheckConstraint("eligible_hours >= 0", name='positive_eligible_hours'),
    )
    
    def validate_eligible_hours(self) -> bool:
        """Validate that eligible hours fit within event duration.
        
        Returns:
            True if validation passes, False otherwise.
        """
        if not self.start_time or not self.end_time or self.eligible_hours is None:
            return True
        
        duration = (datetime.combine(datetime.today(), self.end_time) - 
                   datetime.combine(datetime.today(), self.start_time)).total_seconds() / 3600
        return self.eligible_hours <= duration
    
    def __repr__(self) -> str:
        """String representation of the event."""
        return f'<Event {self.title}>'


class Attachment(db.Model):
    """Attachment model for event-related files.
    
    Attributes:
        id: Primary key.
        event_id: Foreign key to Event.
        filename: Stored filename on disk.
        original_filename: Original filename when uploaded.
        file_type: Type of attachment (registry, program, other).
    """
    
    __tablename__ = 'attachment'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    filename: Mapped[str] = mapped_column(db.String(200), nullable=False)
    original_filename: Mapped[str] = mapped_column(db.String(200), nullable=False)
    file_type: Mapped[str] = mapped_column(db.String(50), nullable=False, default='other')
    
    def __repr__(self) -> str:
        """String representation of the attachment."""
        return f'<Attachment {self.original_filename} for Event {self.event_id}>'


class Registration(db.Model):
    """Registration model for event attendance tracking.
    
    Attributes:
        id: Primary key.
        event_id: Foreign key to Event.
        user_id: Foreign key to User (optional, for user registrations).
        first_name: Registrant's first name.
        last_name: Registrant's last name.
        email: Registrant's email.
        unique_key: Unique registration key.
        attended: Attendance status.
    """
    
    __tablename__ = 'registration'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    first_name: Mapped[str] = mapped_column(db.String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(db.String(100), nullable=False)
    email: Mapped[str] = mapped_column(db.String(100), nullable=False)
    unique_key: Mapped[str] = mapped_column(db.String(100), unique=True, nullable=False)
    attended: Mapped[bool] = mapped_column(db.Boolean, default=False)
    
    def __repr__(self) -> str:
        """String representation of the registration."""
        return f'<Registration {self.first_name} {self.last_name} for Event {self.event_id}>'