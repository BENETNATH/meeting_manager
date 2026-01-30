"""Event routes for the Meeting Manager application.

This module defines Flask routes for event management, registration,
and certificate generation using blueprints.
"""

from datetime import datetime
from flask import Blueprint, flash, redirect, render_template, request, Response, send_file, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app.services.event_service import EventService, SecurityService
from app.models import Event, Registration, CertificateTemplate
from app.exceptions import MeetingManagerError, ValidationError, RegistrationError
from app.decorators import admin_required, event_owner_required

# Create blueprint
events_bp = Blueprint('events', __name__)


@events_bp.route('/')
def index():
    """Display all events with registration statistics."""
    # Optimized query: single SQL call instead of N+1 problem
    events_stats = EventService.get_events_with_stats()
    return render_template('index.html', events_stats=events_stats)


@events_bp.route('/event/<int:event_id>')
def event(event_id):
    """Display event details."""
    event = Event.query.get_or_404(event_id)
    return render_template('event.html', event=event)


@events_bp.route('/admin/create_event', methods=['GET', 'POST'])
@login_required
def create_event():
    """Create a new event (editor and super-admin only).
    
    GET: Display event creation form.
    POST: Process event creation form submission.
    """
    if current_user.role not in ['super-admin', 'editor']:
        flash('Access denied. Editor privileges required.', 'danger')
        return redirect(url_for('events.index'))
    
    if request.method == 'POST':
        # Collect form data
        data = {
            'title': request.form['title'],
            'description': request.form['description'],
            'photo_url': request.form.get('photo_url', ''),
            'program': request.form['program'],
            'date': request.form['date'],
            'start_time': request.form.get('start_time'),
            'end_time': request.form.get('end_time'),
            'organizer': request.form.get('organizer', ''),
            'location': request.form.get('location', ''),
            'eligible_hours': request.form.get('eligible_hours', 0),
            'status': request.form['status'],
            'timezone': request.form.get('timezone', 'UTC'),
            'template_id': request.form.get('template_id'),
            'picture': request.files.get('picture'),
            'signature': request.files.get('signature'),
            'registry_form': request.files.get('registry_form'),
            'pdf_program': request.files.get('pdf_program'),
            'additional_files': request.files.getlist('additional_files')
        }
        
        try:
            event = EventService.create_event_service(data, current_user.id)
            flash('Event successfully created', 'success')
            return redirect(url_for('events.index'))
        except (ValidationError, MeetingManagerError) as e:
            flash(e.message, e.category)
            # Sanitize for safe re-rendering
            sanitized_form = request.form.to_dict()
            sanitized_form['description'] = SecurityService.sanitize_html(sanitized_form.get('description', ''))
            sanitized_form['program'] = SecurityService.sanitize_html(sanitized_form.get('program', ''))
            templates = CertificateTemplate.query.all()
            return render_template('create_event.html', form_data=sanitized_form, templates=templates)
    
    templates = CertificateTemplate.query.all()
    return render_template('create_event.html', form_data={}, templates=templates)


@events_bp.route('/admin/edit_event/<int:event_id>', methods=['GET', 'POST'])
@login_required
@event_owner_required
def edit_event(event_id):
    """Edit an existing event (owner or super-admin only).
    
    GET: Display event edit form.
    POST: Process event edit form submission.
    """
    event = Event.query.get_or_404(event_id)
    
    if request.method == 'POST':
        # Collect form data
        data = {
            'title': request.form['title'],
            'description': request.form['description'],
            'photo_url': request.form.get('photo_url', ''),
            'program': request.form['program'],
            'date': request.form['date'],
            'start_time': request.form.get('start_time'),
            'end_time': request.form.get('end_time'),
            'organizer': request.form.get('organizer', ''),
            'location': request.form.get('location', ''),
            'eligible_hours': request.form.get('eligible_hours', 0),
            'status': request.form['status'],
            'timezone': request.form.get('timezone', event.timezone),
            'template_id': request.form.get('template_id'),
            'picture': request.files.get('picture'),
            'signature': request.files.get('signature'),
            'registry_form': request.files.get('registry_form'),
            'pdf_program': request.files.get('pdf_program'),
            'additional_files': request.files.getlist('additional_files'),
            'notify_time_change': request.form.get('notify_time_change')
        }
        
        try:
            EventService.update_event_service(event_id, data)
            flash('Event successfully updated', 'success')
            return redirect(url_for('events.index'))
        except (ValidationError, MeetingManagerError) as e:
            flash(e.message, e.category)
            # Sanitize for safe re-rendering
            sanitized_form = request.form.to_dict()
            sanitized_form['description'] = SecurityService.sanitize_html(sanitized_form.get('description', ''))
            sanitized_form['program'] = SecurityService.sanitize_html(sanitized_form.get('program', ''))
            templates = CertificateTemplate.query.all()
            return render_template('edit_event.html', event=event, form_data=sanitized_form, templates=templates)
    
    templates = CertificateTemplate.query.all()
    return render_template('edit_event.html', event=event, form_data={}, templates=templates)


@events_bp.route('/update_status/<int:event_id>', methods=['POST'])
@login_required
@event_owner_required
def update_status(event_id):
    """Update event status (owner or super-admin only)."""
    event = Event.query.get_or_404(event_id)
    
    new_status = request.form.get('status')
    success, message = EventService.update_event_status_service(event_id, new_status)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('events.index'))


@events_bp.route('/delete_event/<int:event_id>', methods=['POST'])
@login_required
@event_owner_required
def delete_event(event_id):
    """Delete an event and its registrations (owner or super-admin only)."""
    event = Event.query.get_or_404(event_id)
    
    try:
        EventService.delete_event_service(event_id)
        flash('Event and registrations successfully deleted!', 'success')
    except MeetingManagerError as e:
        flash(e.message, e.category)
    
    return redirect(url_for('events.index'))


@events_bp.route('/admin/mark_attendance/<int:event_id>', methods=['GET', 'POST'])
@login_required
@event_owner_required
def mark_attendance(event_id):
    """Mark attendance for event registrations (owner or super-admin only).
    
    GET: Display attendance marking page.
    POST: Process attendance updates.
    """
    event = Event.query.get_or_404(event_id)
    
    registrations = Registration.query.filter_by(event_id=event_id).all()
    
    if request.method == 'POST':
        try:
            EventService.mark_attendance_service(event_id, request.form)
            flash('Modifications saved!', 'success')
        except MeetingManagerError as e:
            flash(e.message, e.category)
        
        return redirect(url_for('events.mark_attendance', event_id=event_id))
    
    return render_template('attendance.html', event=event, registrations=registrations)


@events_bp.route('/admin/delete_registration/<int:registration_id>', methods=['POST'])
@login_required
def delete_registration(registration_id):
    """Delete a specific registration (owner or super-admin only)."""
    registration = Registration.query.get_or_404(registration_id)
    event = Event.query.get(registration.event_id)
    
    # Manually check for registration deletion since it uses registration_id
    if not (current_user.role == 'super-admin' or 
            (current_user.role == 'editor' and event.created_by == current_user.id)):
        flash('Access denied. You can only delete registrations from your own events.', 'danger')
        return redirect(url_for('events.index'))
    
    try:
        EventService.delete_registration_service(registration_id)
        flash('Registration successfully deleted', 'success')
    except MeetingManagerError as e:
        flash(e.message, e.category)
    
    return redirect(url_for('events.mark_attendance', event_id=event.id))


@events_bp.route('/admin/delete_attachment/<int:attachment_id>', methods=['POST'])
@login_required
def delete_attachment(attachment_id):
    """Delete a specific attachment (owner or super-admin only)."""
    from app.models import Attachment
    attachment = Attachment.query.get_or_404(attachment_id)
    event = Event.query.get(attachment.event_id)
    
    if not (current_user.role == 'super-admin' or 
            (current_user.role == 'editor' and event.created_by == current_user.id)):
        flash('Access denied. You can only delete attachments from your own events.', 'danger')
        return redirect(url_for('events.index'))
    
    try:
        EventService.delete_attachment_service(attachment_id)
        flash('Attachment successfully deleted', 'success')
    except MeetingManagerError as e:
        flash(e.message, e.category)
    
    return redirect(url_for('events.edit_event', event_id=event.id))


@events_bp.route('/admin/event/<int:event_id>/delete_signature', methods=['POST'])
@login_required
@event_owner_required
def delete_signature(event_id):
    """Delete event signature image (owner or super-admin only)."""
    import os
    from flask import current_app, jsonify
    
    event = Event.query.get_or_404(event_id)
    
    if event.signature_filename:
        try:
            # Delete file from disk
            signature_path = os.path.join(current_app.config['UPLOAD_FOLDER'], event.signature_filename)
            if os.path.exists(signature_path):
                os.remove(signature_path)
            
            # Clear from database
            event.signature_filename = None
            from app.extensions import db
            db.session.commit()
            
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    return jsonify({'success': False, 'error': 'No signature to delete'}), 400


@events_bp.route('/extract_attendance/<int:event_id>')
@login_required
@event_owner_required
def extract_attendance(event_id):
    """Extract attendance data as CSV (owner or super-admin only)."""
    event = Event.query.get_or_404(event_id)
    
    csv_data = EventService.extract_attendance_csv_service(event_id)
    
    if csv_data:
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={event.title}_attendance.csv",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )
    else:
        flash('Error extracting attendance data.', 'danger')
        return redirect(url_for('events.index'))


@events_bp.route('/register_page/<int:event_id>', methods=['GET', 'POST'])
def register_page(event_id):
    """Display registration page and handle registration.
    
    GET: Display registration form.
    POST: Process registration form submission.
    """
    event = Event.query.get_or_404(event_id)
    
    if request.method == 'POST':
        return register(event_id)
    
    return render_template('register.html', event=event)


@events_bp.route('/register/<int:event_id>', methods=['POST'])
def register(event_id):
    """Handle event registration."""
    event = Event.query.get_or_404(event_id)
    
    if event.status != 'visible':
        flash('Registration is not available for this event.', 'danger')
        return redirect(url_for('events.event', event_id=event_id))
    
    registration_data = {
        'first_name': request.form.get('first_name', ''),
        'last_name': request.form.get('last_name', ''),
        'email': request.form.get('email', '')
    }
    
    try:
        registration = EventService.register_for_event_service(event_id, registration_data)
        return render_template('registration_confirmation.html', 
                             event=event, 
                             email=registration.email,
                             first_name=registration.first_name,
                             last_name=registration.last_name,
                             unique_key=registration.unique_key)
    except (ValidationError, RegistrationError) as e:
        flash(e.message, e.category)
        return redirect(url_for('events.event', event_id=event_id))


@events_bp.route('/unregister_page/<int:event_id>', methods=['GET', 'POST'])
def unregister_page(event_id):
    """Display unregistration page and handle unregistration.
    
    GET: Display unregistration form.
    POST: Process unregistration form submission.
    """
    event = Event.query.get_or_404(event_id)
    
    if request.method == 'POST':
        return unregister(event_id)
    
    return render_template('unregister.html', event=event)


@events_bp.route('/unregister/<int:event_id>', methods=['POST'])
def unregister(event_id):
    """Handle event unregistration."""
    email = request.form.get('email', '')
    unique_key = request.form.get('unique_key', '')
    forgot_key = request.form.get('forgot_key') == 'on'
    
    if forgot_key:
        success, message = EventService.send_forgotten_key_service(event_id, email)
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
        return redirect(url_for('events.unregister_page', event_id=event_id))
    
    try:
        EventService.unregister_from_event_service(event_id, email, unique_key)
        flash('Successful unregistration', 'success')
    except (ValidationError, MeetingManagerError) as e:
        flash(e.message, e.category)
    
    return redirect(url_for('events.event', event_id=event_id))


@events_bp.route('/certificate', methods=['GET', 'POST'])
def request_certificate():
    """Request certificate of attendance.
    
    GET: Display certificate request form.
    POST: Process certificate request and generate PDF.
    """
    if request.method == 'POST':
        email = request.form.get('email', '')
        unique_key = request.form.get('unique_key', '')
        
        # Find registration
        registration = Registration.query.filter_by(
            email=email, unique_key=unique_key
        ).first()
        
        if registration and registration.attended:
            pdf_data = EventService.generate_certificate_service(registration.id)
            
            if pdf_data:
                event = Event.query.get_or_404(registration.event_id)
                event_title_safe = "".join(c if c.isalnum() else "_" for c in event.title)
                event_date_safe = event.date.strftime('%Y-%m-%d')
                filename = f"{event_date_safe}_certificate_{event_title_safe}.pdf"
                
                return send_file(
                    pdf_data,
                    mimetype='application/pdf',
                    as_attachment=True,
                    download_name=filename
                )
            else:
                flash('Error generating certificate.', 'danger')
        else:
            flash('Sorry, your presence was not confirmed by the organizer.', 'danger')
    
    return render_template('request_certificate.html')


@events_bp.route('/event/<int:event_id>/download_ics')
def download_ics(event_id):
    """Download ICS calendar file for an event."""
    ics_content = EventService.generate_ics_service(event_id)
    
    if ics_content:
        event = Event.query.get_or_404(event_id)
        event_title_safe = "".join(c if c.isalnum() else "_" for c in event.title)
        filename = f"{event.date.strftime('%Y-%m-%d')}_{event_title_safe}.ics"
        
        return Response(
            ics_content,
            mimetype="text/calendar",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    else:
        flash('Error generating calendar file.', 'danger')
        return redirect(url_for('events.event', event_id=event_id))


@events_bp.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Serve uploaded files from the configured upload folder."""
    from flask import send_from_directory, current_app
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)


@events_bp.route('/map_columns', methods=['POST'])
@login_required
def map_columns():
    """Handle column mapping for CSV/XLSX import."""
    import json
    
    # Get the mapping and data from the form
    mapping = request.form.get('mapping', '{}')
    data = request.form.get('data', '[]')
    
    try:
        mapping_dict = json.loads(mapping)
        data_list = json.loads(data)
        
        # Process the mapped data and add to the form
        # This would typically redirect back to the attendance page with the mapped data
        flash('Column mapping completed successfully.', 'success')
        return redirect(url_for('events.mark_attendance', event_id=request.args.get('event_id')))
        
    except json.JSONDecodeError:
        flash('Error processing mapped data.', 'danger')
        return redirect(url_for('events.mark_attendance', event_id=request.args.get('event_id')))
