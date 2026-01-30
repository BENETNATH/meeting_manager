"""Certificate routes for the Meeting Manager application."""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, Response
from flask_login import login_required, current_user

from app.models import Event, Registration, CertificateTemplate
from app.services.certificate_service import CertificateService
from app.decorators import admin_required, event_access_required
from app.exceptions import MeetingManagerError
from app.extensions import db

certificates_bp = Blueprint('certificates', __name__)

@certificates_bp.route('/admin/templates')
@login_required
@admin_required
def list_templates():
    """List all certificate templates."""
    templates = CertificateService.get_all_templates()
    return render_template('list_templates.html', templates=templates)

@certificates_bp.route('/admin/create_template', methods=['POST'])
@login_required
@admin_required
def create_template():
    """Create a new certificate template."""
    name = request.form.get('name', 'New Template')
    CertificateService.create_template(name)
    flash('Template created successfully', 'success')
    return redirect(url_for('certificates.list_templates'))

@certificates_bp.route('/admin/template/<int:template_id>/edit')
@login_required
@admin_required
def edit_template(template_id):
    """Edit a certificate template."""
    template = CertificateService.get_template(template_id)
    return render_template('edit_template.html', template=template)

@certificates_bp.route('/admin/template/<int:template_id>/duplicate', methods=['POST'])
@login_required
@admin_required
def duplicate_template(template_id):
    """Duplicate a certificate template."""
    original = CertificateService.get_template(template_id)
    new_template = CertificateTemplate(
        name=f"{original.name} (Copy)",
        layout_data=original.layout_data,
        background_img=original.background_img
    )
    db.session.add(new_template)
    db.session.commit()
    flash('Template duplicated successfully', 'success')
    return redirect(url_for('certificates.list_templates'))

@certificates_bp.route('/admin/template/<int:template_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_template(template_id):
    """Delete a certificate template."""
    template = CertificateService.get_template(template_id)
    db.session.delete(template)
    db.session.commit()
    flash('Template deleted successfully', 'success')
    return redirect(url_for('certificates.list_templates'))

@certificates_bp.route('/api/upload-asset', methods=['POST'])
@login_required
@admin_required
def upload_asset():
    """Upload an asset for the certificate editor."""
    if 'image' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    try:
        url = CertificateService.upload_asset(file)
        return jsonify({'url': url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@certificates_bp.route('/api/save_template/<int:template_id>', methods=['POST'])
@login_required
@admin_required
def save_template_layout(template_id):
    """Save the layout of a certificate template."""
    try:
        layout_data = request.json
        CertificateService.update_layout(template_id, layout_data)
        return jsonify({'message': 'Layout saved successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@certificates_bp.route('/event/<int:event_id>/download-certificate')
@event_access_required
def download_certificate(event_id):
    """Download the customized PDF certificate."""
    # Find registration
    # Check if user matches email in registration or is the user linked
    # For simplicity, assuming user is logged in
    
    registration = Registration.query.filter_by(
        event_id=event_id, 
        email=current_user.email # Assuming current_user has email matching registration
    ).first()
    
    # If not found by email, maybe fallback or check logic if user registered with a different email?
    # In this app, users might not strictly be linked to registrations by user_id yet everywhere.
    # We'll assume email match for now (or improve logical lookup)
    if not registration:
         # Try looking up by user_id if column populated
         registration = Registration.query.filter_by(event_id=event_id, user_id=current_user.id).first()

    if not registration or not registration.attended:
         flash('Certificate not available or attendance not confirmed.', 'warning')
         return redirect(url_for('events.event', event_id=event_id))

    try:
        pdf_bytes = CertificateService.generate_certificate_pdf(event_id, registration)
        
        return Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={
                "Content-Disposition": f"attachment; filename=certificate_{event_id}.pdf"
            }
        )
    except Exception as e:
        flash(f'Error generating certificate: {str(e)}', 'danger')
        return redirect(url_for('events.event', event_id=event_id))
