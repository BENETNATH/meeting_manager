"""Certificate service for the Meeting Manager application.

This module provides business logic for certificate template management
and PDF generation using WeasyPrint.
"""

import os
import uuid
import json
import logging
from typing import Dict, Any, List, Optional
from flask import current_app, url_for
from werkzeug.utils import secure_filename
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except OSError:
    # WeasyPrint requires GTK, which might not be installed on Windows
    WEASYPRINT_AVAILABLE = False
    HTML = None
    CSS = None
    logging.warning("WeasyPrint (GTK) not available. PDF generation will be disabled.")

from app.extensions import db
from app.models import CertificateTemplate, Event, Registration
from app.exceptions import MeetingManagerError

class CertificateService:
    """Service class for certificate-related operations."""
    
    @staticmethod
    def create_template(name: str) -> CertificateTemplate:
        """Create a new blank certificate template."""
        template = CertificateTemplate(
            name=name,
            layout_data={"elements": []}
        )
        db.session.add(template)
        db.session.commit()
        return template

    @staticmethod
    def get_all_templates() -> List[CertificateTemplate]:
        """Retrieve all certificate templates."""
        return CertificateTemplate.query.order_by(CertificateTemplate.created_at.desc()).all()

    @staticmethod
    def get_template(template_id: int) -> CertificateTemplate:
        """Retrieve a specific template by ID."""
        return CertificateTemplate.query.get_or_404(template_id)

    @staticmethod
    def update_layout(template_id: int, layout_data: Dict[str, Any]) -> None:
        """Update the layout data of a template."""
        template = CertificateService.get_template(template_id)
        template.layout_data = layout_data
        db.session.commit()

    @staticmethod
    def upload_asset(file) -> str:
        """Upload an image asset for certificates.
        
        Returns:
            Public URL of the uploaded image.
        """
        if not file:
            raise MeetingManagerError("No file provided")
            
        filename = secure_filename(file.filename)
        file_ext = os.path.splitext(filename)[1]
        new_filename = f"{uuid.uuid4()}{file_ext}"
        
        save_dir = os.path.join(current_app.static_folder, 'uploads', 'certificates')
        os.makedirs(save_dir, exist_ok=True)
        
        file_path = os.path.join(save_dir, new_filename)
        file.save(file_path)
        
        # Return URL path
        return url_for('static', filename=f'uploads/certificates/{new_filename}')

    @staticmethod
    def generate_certificate_pdf(event_id: int, user_registration: Registration) -> bytes:
        """Generate a PDF certificate for a specific user and event.
        
        Args:
            event_id: The event ID.
            user_registration: The registration object of the participant.
            
        Returns:
            PDF bytes.
        """
        if not WEASYPRINT_AVAILABLE:
            raise MeetingManagerError(
                "PDF generation is currently unavailable. "
                "The server requires the GTK3 runtime specific for Windows to use WeasyPrint. "
                "Please install it from: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases"
            )

        event = Event.query.get_or_404(event_id)
        
        if not event.template_id:
            # Fallback to default generation if no custom template
            from app.services.event_service import EventService
            pdf_io = EventService.generate_certificate_service(user_registration.id)
            if pdf_io:
                return pdf_io.getvalue()
            raise MeetingManagerError("Certificate generation failed (Fallback)")

        template = CertificateTemplate.query.get(event.template_id)
        if not template:
             raise MeetingManagerError("Assigned template not found")

        # Prepare context data
        context = {
            "nom": user_registration.last_name,
            "prenom": user_registration.first_name,
            "date": event.date.strftime("%d/%m/%Y"),
            "event_name": event.title,
            "organizer": event.organizer or "",
            "eligible_hours": str(event.eligible_hours or 0)
        }
        
        # Add signature URL if available
        if event.signature_filename:
            # Direct file check using UPLOAD_FOLDER
            upload_folder = current_app.config.get('UPLOAD_FOLDER')
            if upload_folder:
                # Ensure absolute path
                if not os.path.isabs(upload_folder):
                    upload_folder = os.path.abspath(upload_folder)
                
                sig_path = os.path.join(upload_folder, event.signature_filename)
                
                if os.path.exists(sig_path):
                    if os.name == 'nt':
                        context["signature"] = 'file:///' + sig_path.replace('\\', '/')
                    else:
                        context["signature"] = 'file://' + sig_path
                else:
                    context["signature"] = ""
            else:
                 context["signature"] = ""
        else:
            context["signature"] = ""

        # Generate HTML from layout
        html_content = CertificateService._render_html_from_layout(template.layout_data, context)
        
        # Generate PDF
        # Use absolute path to static folder for WeasyPrint
        base_url = os.path.abspath(current_app.static_folder)
        
        # Basic CSS for printing A4
        css = CSS(string="""
            @page { size: A4; margin: 0; }
            body { margin: 0; padding: 0; -webkit-print-color-adjust: exact; }
        """)

        return HTML(string=html_content, base_url=base_url).write_pdf(stylesheets=[css])

    @staticmethod
    def _render_html_from_layout(layout_data: Dict[str, Any], context: Dict[str, str]) -> str:
        """Construct HTML string from JSON layout and context data."""
        
        # 1. Obtenir le chemin ABSOLU du dossier static sur le disque
        # C'est crucial pour que WeasyPrint trouve les fichiers sans passer par http://
        static_root = os.path.abspath(current_app.static_folder)
        
        elements_html = ""
        elements = layout_data.get('elements', [])
        
        for el in elements:
            el_type = el.get('type')
            x = el.get('x', 0)
            y = el.get('y', 0)
            content = el.get('content', '')
            style = el.get('style', {})
            
            # Read width and height from style object (where the editor stores them)
            width = style.get('width', 'auto')
            height = style.get('height', 'auto')
            
            # Extract numeric value if it's a string like "100px"
            def parse_dim(val):
                if val is None or val == 'auto':
                    return 'auto'
                s_val = str(val).replace('px', '').strip()
                if not s_val:
                    return 'auto'
                try:
                    num = float(s_val)
                    if num >= 0:
                        return str(int(num))
                except (ValueError, TypeError):
                    pass
                return 'auto'

            width = parse_dim(width)
            height = parse_dim(height)
            
            # Position style
            common_style = f"position: absolute; left: {x}px; top: {y}px;"
            
            if width != 'auto':
                common_style += f" width: {width}px;"
            if height != 'auto':
                common_style += f" height: {height}px;"
                
            # Font styling if text
            if el_type in ['text', 'variable']:
                 font_size = style.get('fontSize') or '16px'
                 font_family = style.get('fontFamily') or 'Arial'
                 font_weight = style.get('fontWeight') or 'normal'
                 color = style.get('color') or '#000000'
                 text_align = style.get('textAlign') or 'left'
                 common_style += f" font-size: {font_size}; font-family: {font_family}; font-weight: {font_weight}; color: {color}; text-align: {text_align};"

            if el_type == 'text':
                elements_html += f'<div style="{common_style}">{content}</div>'
            
            elif el_type == 'variable':
                key = content.replace('{{', '').replace('}}', '').strip()
                val = context.get(key, content)
                
                # Special handling for signature variable
                if key == 'signature' and val:
                    img_src = val
                    
                    # Ensure it is a file:/// URI if it's an absolute path
                    if os.path.isabs(img_src):
                        if os.name == 'nt':
                            img_src = 'file:///' + img_src.replace('\\', '/')
                        else:
                            img_src = 'file://' + img_src

                    img_width = f"{width}px" if width != 'auto' else '200px'
                    img_height = f"{height}px" if height != 'auto' else 'auto'
                    elements_html += f'<img src="{img_src}" style="position: absolute; left: {x}px; top: {y}px; width: {img_width}; height: {img_height}; display: block;">'
                else:
                    elements_html += f'<div style="{common_style}">{val}</div>'
                
            elif el_type == 'image':
                 img_src = content
                 try:
                     from urllib.parse import urlparse
                     parsed = urlparse(img_src)
                     path = parsed.path
                     
                     abs_path = None
                     if path.startswith('/static/'):
                         rel_path = path.replace('/static/', '', 1).lstrip('/')
                         abs_path = os.path.abspath(os.path.join(static_root, rel_path))
                     elif path.startswith('/uploads/'):
                         rel_path = path.replace('/uploads/', '', 1).lstrip('/')
                         upload_folder = current_app.config.get('UPLOAD_FOLDER')
                         if upload_folder:
                             abs_path = os.path.abspath(os.path.join(upload_folder, rel_path))
                     
                     if abs_path and os.path.exists(abs_path):
                         if os.name == 'nt':
                             img_src = 'file:///' + abs_path.replace('\\', '/')
                         else:
                             img_src = 'file://' + abs_path
                         # logging.info(f"Resolved image {path} to {img_src}")
                 except Exception as e:
                     logging.error(f"Error resolving image path: {e}")

                 img_width = f"{width}px" if width != 'auto' else 'auto'
                 img_height = f"{height}px" if height != 'auto' else 'auto'
                 elements_html += f'<img src="{img_src}" style="position: absolute; left: {x}px; top: {y}px; width: {img_width}; height: {img_height}; display: block;">'

        # --- FIX POUR LE BACKGROUND ---
        background_style = ""
        bg_img = layout_data.get('backgroundImage')
        if bg_img:
            try:
                from urllib.parse import urlparse
                parsed_bg = urlparse(bg_img)
                bg_path = parsed_bg.path
                
                if bg_path.startswith('/static/'):
                    bg_rel_path = bg_path.replace('/static/', '', 1).lstrip('/')
                    bg_abs_path = os.path.join(static_root, bg_rel_path)
                    
                    if os.path.exists(bg_abs_path):
                        if os.name == 'nt':
                            bg_img_uri = 'file:///' + bg_abs_path.replace('\\', '/')
                        else:
                            bg_img_uri = 'file://' + bg_abs_path
                        
                        background_style = f'background-image: url("{bg_img_uri}"); background-size: cover; background-position: center;'
                    else:
                        # Fallback
                        background_style = f'background-image: url("{bg_img}"); background-size: cover; background-position: center;'
                else:
                    background_style = f'background-image: url("{bg_img}"); background-size: cover; background-position: center;'
            except Exception as e:
                 logging.error(f"Error resolving background path: {e}")
                 background_style = f'background-image: url("{bg_img}"); background-size: cover; background-position: center;'

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                @page {{ size: A4; margin: 0; }}
                body {{ margin: 0; padding: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
                .certificate-container {{
                    position: relative;
                    width: 794px;
                    height: 1123px;
                    overflow: hidden;
                    {background_style}
                }}
            </style>
        </head>
        <body>
            <div class="certificate-container">
                {elements_html}
            </div>
        </body>
        </html>
        """
        return html
