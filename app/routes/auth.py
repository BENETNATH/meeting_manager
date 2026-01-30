"""Authentication routes for the Meeting Manager application.

This module defines Flask routes for user authentication, registration,
and password management using blueprints.
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.services.auth_service import AuthService
from app.decorators import admin_required
from app.exceptions import MeetingManagerError, ValidationError
from app.extensions import limiter

# Create blueprint
auth_bp = Blueprint('auth', __name__, template_folder='templates')


@auth_bp.route('/healthz')
def healthz():
    """Health check endpoint."""
    return {'status': 'healthy'}, 200


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute; 20 per hour")
def login():
    """Handle user login.
    
    GET: Display login form.
    POST: Process login form submission.
    """
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        try:
            # Try login with username first
            try:
                AuthService.login_user_service(username, password)
            except ValidationError:
                # If login fails and the input looks like an email, try using it as email
                if '@' in username:
                    from app.models import User
                    user = User.query.filter_by(email=username).first()
                    if user:
                        AuthService.login_user_service(user.username, password)
                    else:
                        raise ValidationError('Wrong credentials')
                else:
                    raise ValidationError('Wrong credentials')
            
            flash('Login successful!', 'success')
            return redirect(url_for('events.index'))
        except ValidationError as e:
            flash(e.message, e.category)
    
    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Handle user logout."""
    AuthService.logout_user_service()
    flash('You have been logged out.', 'info')
    return redirect(url_for('events.index'))


@auth_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Handle password change for authenticated users.
    
    GET: Display password change form.
    POST: Process password change form submission.
    """
    if request.method == 'POST':
        new_password = request.form['new_password']
        
        try:
            AuthService.change_password_service(current_user.id, new_password)
            flash('Password updated successfully.', 'success')
            return redirect(url_for('events.index'))
        except MeetingManagerError as e:
            flash(e.message, e.category)
    
    return render_template('change_password.html')


@auth_bp.route('/admin/manage_users', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_users():
    """Manage users (super-admin only).
    
    GET: Display user management page.
    POST: Process user updates.
    """
    
    from app.models import User
    users = User.query.all()
    
    if request.method == 'POST':
        user_id = request.form['user_id']
        new_role = request.form['role']
        password = request.form.get('password')
        
        try:
            AuthService.update_user_service(user_id, role=new_role, password=password)
            flash('User updated successfully.', 'success')
        except MeetingManagerError as e:
            flash(e.message, e.category)
        
        return redirect(url_for('auth.manage_users'))
    
    return render_template('manage_users.html', users=users)


@auth_bp.route('/admin/create_editor', methods=['POST'])
@login_required
@admin_required
@limiter.limit("10 per hour")
def create_editor():
    """Create a new editor user (super-admin only)."""
    
    username = request.form['username']
    email = request.form['email']
    
    try:
        temp_password = AuthService.create_user_service(username, email, role='editor')
        flash(f'Editor created successfully. Temporary password: {temp_password}', 'success')
    except (ValidationError, MeetingManagerError) as e:
        flash(e.message, e.category)
    
    return redirect(url_for('auth.manage_users'))


@auth_bp.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user (super-admin only)."""
    
    try:
        AuthService.delete_user_service(user_id)
        flash('User successfully deleted', 'success')
    except (ValidationError, MeetingManagerError) as e:
        flash(e.message, e.category)
    
    return redirect(url_for('auth.manage_users'))


@auth_bp.route('/reset_password/<int:user_id>', methods=['POST'])
@login_required
@admin_required
@limiter.limit("5 per hour")
def reset_password(user_id):
    """Reset user password (super-admin only)."""
    
    try:
        AuthService.reset_password_service(user_id)
        flash('Password has been reset and sent to the user\'s email.', 'success')
    except MeetingManagerError as e:
        flash(e.message, e.category)
    
    return redirect(url_for('auth.manage_users'))