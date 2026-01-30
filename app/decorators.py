from functools import wraps
from flask import flash, redirect, url_for, abort
from flask_login import current_user
from app.models import Event

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'super-admin':
            flash('Admin privileges required.', 'danger')
            return redirect(url_for('events.index'))
        return f(*args, **kwargs)
    return decorated_function

def event_owner_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # The event ID could be in kwargs as 'event_id' or 'id' depending on the route
        event_id = kwargs.get('event_id') or kwargs.get('id')
        if event_id:
            event = Event.query.get_or_404(event_id)
            is_admin = current_user.role == 'super-admin'
            is_owner = current_user.role == 'editor' and event.created_by == current_user.id
            
            if not (is_admin or is_owner):
                flash('Access denied. You do not own this event or don\'t have permission.', 'danger')
                return redirect(url_for('events.index'))
        return f(*args, **kwargs)
    return decorated_function
