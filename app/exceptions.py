"""Custom exceptions for the Meeting Manager application."""

class MeetingManagerError(Exception):
    """Base exception for the application."""
    def __init__(self, message="An error occurred", category="danger"):
        super().__init__(message)
        self.message = message
        self.category = category

class EventError(MeetingManagerError):
    """Base exception for event-related errors."""
    pass

class EventCreationError(EventError):
    """Raised when an event cannot be created."""
    pass

class EventUpdateError(EventError):
    """Raised when an event cannot be updated."""
    pass

class RegistrationError(MeetingManagerError):
    """Base exception for registration-related errors."""
    pass

class ValidationError(MeetingManagerError):
    """Raised when data validation fails."""
    pass
