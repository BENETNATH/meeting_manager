"""Authentication routes for the Meeting Manager application.

This module defines Flask routes for user authentication, registration,
and password management using blueprints.
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.services.auth_service import AuthService

# Create blueprint
auth_bp = Blueprint('auth', __name__, template_folder='templates')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login.
    
    GET: Display login form.
    POST: Process login form submission.
    """
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Try login with username first, then try with email if that fails
        success, error_message = AuthService.login_user_service(username, password)
        
        # If login fails and the input looks like an email, try using it as email
        if not success and '@' in username:
            from app.models import User
            user = User.query.filter_by(email=username).first()
            if user:
                success, error_message = AuthService.login_user_service(user.username, password)
        
        if success:
            flash('Login successful!', 'success')
            return redirect(url_for('events.index'))
        else:
            flash(error_message, 'danger')
    
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
        
        success, message = AuthService.change_password_service(current_user.id, new_password)
        
        if success:
            flash(message, 'success')
            return redirect(url_for('events.index'))
        else:
            flash(message, 'danger')
    
    return render_template('change_password.html')


@auth_bp.route('/admin/manage_users', methods=['GET', 'POST'])
@login_required
def manage_users():
    """Manage users (super-admin only).
    
    GET: Display user management page.
    POST: Process user updates.
    """
    if current_user.role != 'super-admin':
        flash('Access denied. Super-admin privileges required.', 'danger')
        return redirect(url_for('events.index'))
    
    from app.models import User
    users = User.query.all()
    
    if request.method == 'POST':
        user_id = request.form['user_id']
        new_role = request.form['role']
        password = request.form.get('password')
        
        success, message = AuthService.update_user_service(user_id, role=new_role, password=password)
        
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
        
        return redirect(url_for('auth.manage_users'))
    
    return render_template('manage_users.html', users=users)


@auth_bp.route('/admin/create_editor', methods=['POST'])
@login_required
def create_editor():
    """Create a new editor user (super-admin only)."""
    if current_user.role != 'super-admin':
        flash('Access denied. Super-admin privileges required.', 'danger')
        return redirect(url_for('events.index'))
    
    username = request.form['username']
    email = request.form['email']
    
    success, result = AuthService.create_user_service(username, email, role='editor')
    
    if success:
        flash(f'Editor created successfully. Temporary password: {result}', 'success')
    else:
        flash(result, 'danger')
    
    return redirect(url_for('auth.manage_users'))


@auth_bp.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    """Delete a user (super-admin only)."""
    if current_user.role != 'super-admin':
        flash('Access denied. Super-admin privileges required.', 'danger')
        return redirect(url_for('events.index'))
    
    success, message = AuthService.delete_user_service(user_id)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('auth.manage_users'))


@auth_bp.route('/reset_password/<int:user_id>', methods=['POST'])
@login_required
def reset_password(user_id):
    """Reset user password (super-admin only)."""
    if current_user.role != 'super-admin':
        flash('Access denied. Super-admin privileges required.', 'danger')
        return redirect(url_for('events.index'))
    
    success, message = AuthService.reset_password_service(user_id)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('auth.manage_users'))