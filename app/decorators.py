from functools import wraps
from flask import abort
from flask_login import current_user
from app.models import Event

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
        if current_user.role != 'super-admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def event_owner_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(401)
            
        # The event ID could be in kwargs as 'event_id' or 'id' depending on the route
        event_id = kwargs.get('event_id') or kwargs.get('id')
        if not event_id:
            # Mandatory Fix 2: Harden event_owner_required to fail closed
            abort(400, description="Event identifier missing from request.")
            
        event = Event.query.get_or_404(event_id)
        is_admin = current_user.role == 'super-admin'
        is_owner = current_user.role == 'editor' and event.created_by == current_user.id
        
        if not (is_admin or is_owner):
            abort(403)
            
        return f(*args, **kwargs)
    return decorated_function

def event_access_required(f):
    @wraps(f)
    def decorated_function(event_id, *args, **kwargs):
        from flask import session, render_template
        event = Event.query.get_or_404(event_id)
        
        # Admin/Owner bypass
        is_admin_or_owner = current_user.is_authenticated and (
            current_user.role == 'super-admin' or 
            (current_user.role == 'editor' and event.created_by == current_user.id)
        )
        
        if is_admin_or_owner:
            return f(event_id, *args, **kwargs)
            
        # Password protection check
        if event.status == 'password-protected':
            if not session.get(f'event_auth_{event_id}'):
                return render_template('event_password.html', event=event)
        
        # Hidden/Archived events are only for owner/admin
        if event.status in ['hidden', 'archived']:
            abort(403)
            
        return f(event_id, *args, **kwargs)
    return decorated_function
