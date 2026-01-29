"""Event service for the Meeting Manager application.

This module provides business logic for event management, registration,
and certificate generation operations.
"""

import csv
import io
import logging
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from io import BytesIO

import pytz
from ics import Calendar, Event as ICSEvent
from PIL import Image
from flask import flash, send_file, url_for, current_app
from flask_mail import Message
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, Spacer, SimpleDocTemplate

from app.extensions import db, mail
from app.models import Event, Registration, User


class EventService:
    """Service class for event-related operations."""
    
    @staticmethod
    def create_event_service(data: Dict[str, Any], creator_id: int) -> Tuple[bool, str]:
        """Create a new event.
        
        Args:
            data: Event data dictionary.
            creator_id: ID of the user creating the event.
        
        Returns:
            Tuple of (success: bool, message: str).
        """
        # Validate timezone
        timezone_str = data.get('timezone', 'UTC')
        if timezone_str not in pytz.common_timezones:
            return False, 'Invalid timezone selected. Please choose from the list.'
        
        # Parse date and times
        date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        start_time = (datetime.strptime(data['start_time'], '%H:%M').time() 
                     if data.get('start_time') else None)
        end_time = (datetime.strptime(data['end_time'], '%H:%M').time() 
                   if data.get('end_time') else None)
        
        # Validate eligible hours
        eligible_hours = float(data.get('eligible_hours', 0) or 0)
        if eligible_hours > 0:
            if not EventService._validate_eligible_hours(start_time, end_time, eligible_hours):
                return False, 'Eligible hours must be within the event duration.'
        
        # Handle picture upload
        photo_filename = None
        if data.get('picture'):
            photo_filename = EventService._save_picture(data['picture'])
            if not photo_filename:
                return False, 'Invalid picture file'
        
        # Handle signature upload
        signature_filename = None
        if data.get('signature'):
            signature_filename = EventService._save_signature(data['signature'])
            if not signature_filename:
                return False, 'Invalid signature file'
        
        # Create event
        event = Event(
            title=data['title'],
            description=data['description'],
            photo_url=data.get('photo_url', ''),
            photo_filename=photo_filename,
            program=data['program'],
            date=date,
            start_time=start_time,
            end_time=end_time,
            organizer=data.get('organizer', ''),
            location=data.get('location', ''),
            eligible_hours=eligible_hours,
            created_by=creator_id,
            status=data['status'],
            signature_url=data.get('signature_url', ''),
            signature_filename=signature_filename,
            timezone=timezone_str
        )
        
        try:
            db.session.add(event)
            db.session.commit()
            logging.info(f'Event "{event.title}" successfully created by user {creator_id}')
            return True, 'Event successfully created'
        except Exception as e:
            db.session.rollback()
            logging.error(f'Error creating event: {e}')
            return False, 'Error creating event'
    
    @staticmethod
    def update_event_service(event_id: int, data: Dict[str, Any]) -> Tuple[bool, str]:
        """Update an existing event.
        
        Args:
            event_id: ID of the event to update.
            data: Event data dictionary.
        
        Returns:
            Tuple of (success: bool, message: str).
        """
        event = Event.query.get_or_404(event_id)
        
        # Store original time details for change detection
        original_date = event.date
        original_start_time = event.start_time
        original_end_time = event.end_time
        
        # Validate timezone
        timezone_str = data.get('timezone', event.timezone)
        if timezone_str not in pytz.common_timezones:
            return False, 'Invalid timezone selected. Please choose from the list.'
        
        # Parse date and times
        new_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        new_start_time = (datetime.strptime(data['start_time'], '%H:%M').time() 
                         if data.get('start_time') else None)
        new_end_time = (datetime.strptime(data['end_time'], '%H:%M').time() 
                       if data.get('end_time') else None)
        
        # Validate eligible hours
        eligible_hours = float(data.get('eligible_hours', 0) or 0)
        if eligible_hours > 0:
            if not EventService._validate_eligible_hours(new_start_time, new_end_time, eligible_hours):
                return False, 'Eligible hours must be within the event duration.'
        
        # Update event details
        event.title = data['title']
        event.description = data['description']
        event.photo_url = data.get('photo_url', '')
        event.program = data['program']
        event.date = new_date
        event.start_time = new_start_time
        event.end_time = new_end_time
        event.organizer = data.get('organizer', '')
        event.location = data.get('location', '')
        event.eligible_hours = eligible_hours
        event.status = data['status']
        event.timezone = timezone_str
        
        # Handle picture upload
        if data.get('picture'):
            photo_filename = EventService._save_picture(data['picture'])
            if photo_filename:
                # Remove old picture if exists
                if event.photo_filename:
                    old_picture_path = os.path.join(current_app.config['UPLOAD_FOLDER'], event.photo_filename)
                    if os.path.exists(old_picture_path):
                        os.remove(old_picture_path)
                event.photo_filename = photo_filename
        
        # Handle signature upload
        if data.get('signature'):
            signature_filename = EventService._save_signature(data['signature'])
            if signature_filename:
                # Remove old signature if exists
                if event.signature_filename:
                    old_signature_path = os.path.join(current_app.config['UPLOAD_FOLDER'], event.signature_filename)
                    if os.path.exists(old_signature_path):
                        os.remove(old_signature_path)
                event.signature_filename = signature_filename
        
        try:
            db.session.commit()
            
            # Check if time has changed and send notifications
            time_changed = (new_date != original_date or 
                           new_start_time != original_start_time or 
                           new_end_time != original_end_time)
            
            if time_changed and data.get('notify_time_change') == 'true':
                EventService._send_update_notifications(event)
            
            logging.info(f'Event "{event.title}" successfully updated')
            return True, 'Event successfully updated'
        except Exception as e:
            db.session.rollback()
            logging.error(f'Error updating event {event_id}: {e}')
            return False, 'Error updating event'
    
    @staticmethod
    def delete_event_service(event_id: int) -> Tuple[bool, str]:
        """Delete an event and its registrations.
        
        Args:
            event_id: ID of the event to delete.
        
        Returns:
            Tuple of (success: bool, message: str).
        """
        event = Event.query.get_or_404(event_id)
        
        try:
            # Delete registrations
            registrations = Registration.query.filter_by(event_id=event_id).all()
            for registration in registrations:
                db.session.delete(registration)
            
            # Delete picture file if exists
            if event.photo_filename:
                picture_path = os.path.join(current_app.config['UPLOAD_FOLDER'], event.photo_filename)
                if os.path.exists(picture_path):
                    os.remove(picture_path)
            
            # Delete signature file if exists
            if event.signature_filename:
                signature_path = os.path.join(current_app.config['UPLOAD_FOLDER'], event.signature_filename)
                if os.path.exists(signature_path):
                    os.remove(signature_path)
            
            # Delete event
            db.session.delete(event)
            db.session.commit()
            
            logging.info(f'Event "{event.title}" and registrations successfully deleted')
            return True, 'Event and registrations successfully deleted!'
        except Exception as e:
            db.session.rollback()
            logging.error(f'Error deleting event {event_id}: {e}')
            return False, 'Error deleting event'
    
    @staticmethod
    def update_event_status_service(event_id: int, status: str) -> Tuple[bool, str]:
        """Update event status.
        
        Args:
            event_id: ID of the event.
            status: New status (hidden, visible, archived).
        
        Returns:
            Tuple of (success: bool, message: str).
        """
        if status not in ['hidden', 'visible', 'archived']:
            return False, 'Invalid status'
        
        event = Event.query.get_or_404(event_id)
        event.status = status
        
        try:
            db.session.commit()
            return True, 'Status updated successfully!'
        except Exception as e:
            db.session.rollback()
            logging.error(f'Error updating event status {event_id}: {e}')
            return False, 'Error updating status'
    
    @staticmethod
    def register_for_event_service(event_id: int, registration_data: Dict[str, str]) -> Tuple[bool, str]:
        """Register a user for an event.
        
        Args:
            event_id: ID of the event.
            registration_data: Registration form data.
        
        Returns:
            Tuple of (success: bool, message: str).
        """
        event = Event.query.get_or_404(event_id)
        
        if event.status != 'visible':
            return False, 'Registration is not available'
        
        email = registration_data['email']
        existing_registration = Registration.query.filter_by(
            event_id=event_id, email=email
        ).first()
        
        if existing_registration:
            return False, 'Email already registered'
        
        unique_key = str(uuid.uuid4())
        registration = Registration(
            event_id=event_id,
            email=email,
            first_name=registration_data['first_name'],
            last_name=registration_data['last_name'],
            unique_key=unique_key
        )
        
        try:
            db.session.add(registration)
            db.session.commit()
            
            # Send registration email - wrapped to ignore errors if SMTP is not configured
            try:
                EventService._send_registration_email(
                    email, registration_data['first_name'], event, unique_key
                )
            except Exception as e:
                logging.error(f'Error sending registration email for event {event_id}: {e}')
            
            return True, {
                'message': 'Registration successful',
                'unique_key': unique_key,
                'email': email,
                'first_name': registration_data['first_name'],
                'last_name': registration_data['last_name']
            }
        except Exception as e:
            db.session.rollback()
            logging.error(f'Error registering for event {event_id}: {e}')
            return False, 'Error processing registration'
    
    @staticmethod
    def unregister_from_event_service(event_id: int, email: str, unique_key: str) -> Tuple[bool, str]:
        """Unregister a user from an event.
        
        Args:
            event_id: ID of the event.
            email: User email.
            unique_key: User registration key.
        
        Returns:
            Tuple of (success: bool, message: str).
        """
        registration = Registration.query.filter_by(
            event_id=event_id, email=email, unique_key=unique_key
        ).first()
        
        if not registration:
            return False, 'No registration found for this email and unique key on this event'
        
        try:
            db.session.delete(registration)
            db.session.commit()
            return True, 'Successful unregistration'
        except Exception as e:
            db.session.rollback()
            logging.error(f'Error unregistering from event {event_id}: {e}')
            return False, 'Error processing unregistration'
    
    @staticmethod
    def mark_attendance_service(event_id: int, attendance_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Mark attendance for event registrations.
        
        Args:
            event_id: ID of the event.
            attendance_data: Attendance form data.
        
        Returns:
            Tuple of (success: bool, message: str).
        """
        try:
            action = attendance_data.get('action')
            
            if action == 'check_all':
                registrations = Registration.query.filter_by(event_id=event_id).all()
                for registration in registrations:
                    registration.attended = True
            
            elif action == 'update_attendance':
                registrations = Registration.query.filter_by(event_id=event_id).all()
                for registration in registrations:
                    attended_key = f'attended_{registration.id}'
                    registration.attended = attended_key in attendance_data
            
            elif action and action.startswith('delete_'):
                try:
                    registration_id = int(action.split('_')[1])
                    registration = Registration.query.get_or_404(registration_id)
                    db.session.delete(registration)
                except (ValueError, AttributeError):
                    pass
            
            elif action == 'save_new_registrations':
                index = 0
                while True:
                    last_name = attendance_data.get(f'last_name_new_{index}')
                    first_name = attendance_data.get(f'first_name_new_{index}')
                    email = attendance_data.get(f'email_new_{index}')
                    attended = attendance_data.get(f'attended_new_{index}') == 'on'
                    
                    if not last_name and not first_name and not email:
                        break
                    
                    unique_key = str(uuid.uuid4())
                    new_registration = Registration(
                        event_id=event_id,
                        last_name=last_name,
                        first_name=first_name,
                        email=email,
                        unique_key=unique_key,
                        attended=attended
                    )
                    db.session.add(new_registration)
                    index += 1
            
            db.session.commit()
            return True, 'Modifications saved!'
        except Exception as e:
            db.session.rollback()
            logging.error(f'Error updating attendance for event {event_id}: {e}')
            return False, 'Error updating attendance'
    
    @staticmethod
    def delete_registration_service(registration_id: int) -> Tuple[bool, str]:
        """Delete a specific registration.
        
        Args:
            registration_id: ID of the registration to delete.
        
        Returns:
            Tuple of (success: bool, message: str).
        """
        registration = Registration.query.get_or_404(registration_id)
        
        try:
            db.session.delete(registration)
            db.session.commit()
            return True, 'Registration successfully deleted'
        except Exception as e:
            db.session.rollback()
            logging.error(f'Error deleting registration {registration_id}: {e}')
            return False, 'Error deleting registration'
    
    @staticmethod
    def generate_certificate_service(registration_id: int) -> Optional[BytesIO]:
        """Generate a certificate PDF for a registration.
        
        Args:
            registration_id: ID of the registration.
        
        Returns:
            BytesIO object containing PDF data, or None if not eligible.
        """
        registration = Registration.query.get_or_404(registration_id)
        
        if not registration.attended:
            return None
        
        event = Event.query.get_or_404(registration.event_id)
        
        try:
            return EventService._generate_certificate_pdf(registration, event)
        except Exception as e:
            logging.error(f'Error generating certificate for registration {registration_id}: {e}')
            return None
    
    @staticmethod
    def generate_ics_service(event_id: int) -> Optional[str]:
        """Generate ICS calendar file for an event.
        
        Args:
            event_id: ID of the event.
        
        Returns:
            ICS content as string, or None if event not found.
        """
        event = Event.query.get_or_404(event_id)
        
        try:
            return EventService._generate_ics(event)
        except Exception as e:
            logging.error(f'Error generating ICS for event {event_id}: {e}')
            return None
    
    @staticmethod
    def extract_attendance_csv_service(event_id: int) -> Optional[str]:
        """Extract attendance data as CSV.
        
        Args:
            event_id: ID of the event.
        
        Returns:
            CSV content as string, or None if event not found.
        """
        event = Event.query.get_or_404(event_id)
        
        try:
            registrations = Registration.query.filter_by(event_id=event_id).all()
            output = []
            for reg in registrations:
                output.append([
                    reg.first_name, reg.last_name, reg.email, 
                    reg.unique_key, reg.attended
                ])
            
            return EventService._generate_csv(output)
        except Exception as e:
            logging.error(f'Error extracting CSV for event {event_id}: {e}')
            return None
    
    @staticmethod
    def _validate_eligible_hours(start_time: Optional[datetime.time], 
                               end_time: Optional[datetime.time], 
                               eligible_hours: float) -> bool:
        """Validate that eligible hours fit within event duration.
        
        Args:
            start_time: Event start time.
            end_time: Event end time.
            eligible_hours: Number of eligible hours.
        
        Returns:
            True if validation passes, False otherwise.
        """
        if not start_time or not end_time or eligible_hours <= 0:
            return True
        
        duration = (datetime.combine(datetime.today(), end_time) - 
                   datetime.combine(datetime.today(), start_time)).total_seconds() / 3600
        return eligible_hours <= duration
    
    @staticmethod
    def _save_signature(signature_file) -> Optional[str]:
        """Save and validate signature file.
        
        Args:
            signature_file: Uploaded signature file.
        
        Returns:
            Filename if successful, None if failed.
        """
        if not signature_file:
            return None
        
        file_extension = os.path.splitext(signature_file.filename)[1]
        filename = f"{uuid.uuid4()}_signature{file_extension}"
        signature_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        
        os.makedirs(os.path.dirname(signature_path), exist_ok=True)
        signature_file.save(signature_path)
        
        try:
            with Image.open(signature_path) as img:
                if img.width > 800 or img.height > 600:
                    os.remove(signature_path)
                    return None
                img.thumbnail((250, 250))
                img.save(signature_path)
        except Exception:
            if os.path.exists(signature_path):
                os.remove(signature_path)
            return None
        
        return filename
    
    @staticmethod
    def _save_picture(picture_file) -> Optional[str]:
        """Save and validate picture file.
        
        Args:
            picture_file: Uploaded picture file.
        
        Returns:
            Filename if successful, None if failed.
        """
        if not picture_file:
            return None
        
        file_extension = os.path.splitext(picture_file.filename)[1]
        filename = f"{uuid.uuid4()}_picture{file_extension}"
        picture_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        
        os.makedirs(os.path.dirname(picture_path), exist_ok=True)
        picture_file.save(picture_path)
        
        try:
            with Image.open(picture_path) as img:
                # Validate image dimensions (max 1920x1080)
                if img.width > 1920 or img.height > 1080:
                    os.remove(picture_path)
                    return None
                # Create a thumbnail for display
                img.thumbnail((800, 600))
                img.save(picture_path)
        except Exception:
            if os.path.exists(picture_path):
                os.remove(picture_path)
            return None
        
        return filename
    
    @staticmethod
    def _send_registration_email(email: str, first_name: str, event: Event, unique_key: str) -> None:
        """Send registration confirmation email.
        
        Args:
            email: Recipient email.
            first_name: User's first name.
            event: Event object.
            unique_key: Registration unique key.
        """
        subject = 'Registration Confirmation'
        body = (f'Hello {first_name},\n\n'
               f'You have successfully registered for the event: {event.title} '
               f'that will take place on {event.date.strftime("%Y-%m-%d")}.\n'
               f'Your unique key is: {unique_key}\n\nThank you!')
        
        msg = Message(subject=subject, recipients=[email], body=body)
        
        # Attach ICS file
        try:
            ics_content = EventService._generate_ics(event)
            event_title_safe = "".join(c if c.isalnum() else "_" for c in event.title)
            filename = f"{event.date.strftime('%Y-%m-%d')}_{event_title_safe}.ics"
            msg.attach(filename, "text/calendar", ics_content)
        except Exception as e:
            logging.error(f"Error generating or attaching ICS for event {event.id}: {e}")
        
        try:
            mail.send(msg)
        except Exception as e:
            logging.error(f"Error sending registration email to {email}: {e}")
    
    @staticmethod
    def _send_update_notifications(event: Event) -> None:
        """Send update notifications to registered users.
        
        Args:
            event: Updated event object.
        """
        registrations = Registration.query.filter_by(event_id=event.id).all()
        
        if not registrations:
            return
        
        logging.info(f'Sending update notifications to {len(registrations)} registered users...')
        
        for registration in registrations:
            try:
                subject = f'Event Update Notification: {event.title}'
                body = (f'Hello {registration.first_name},\n\n'
                       f'Please note that the event "{event.title}" has been updated.\n'
                       f'New Date: {event.date.strftime("%Y-%m-%d")}\n'
                       f'New Start Time: {event.start_time.strftime("%H:%M") if event.start_time else "N/A"}\n'
                       f'New End Time: {event.end_time.strftime("%H:%M") if event.end_time else "N/A"}\n\n'
                       f'Please find the updated calendar details attached.\n\nThank you!')
                
                msg = Message(subject=subject, recipients=[registration.email], body=body)
                
                # Attach updated ICS file
                ics_content = EventService._generate_ics(event)
                event_title_safe = "".join(c if c.isalnum() else "_" for c in event.title)
                filename = f"{event.date.strftime('%Y-%m-%d')}_{event_title_safe}_updated.ics"
                msg.attach(filename, "text/calendar", ics_content)
                
                mail.send(msg)
            except Exception as e:
                logging.error(f'Failed to send update email to {registration.email} for event {event.id}: {e}')
    
    @staticmethod
    def _generate_certificate_pdf(registration: Registration, event: Event) -> BytesIO:
        """Generate certificate PDF.
        
        Args:
            registration: Registration object.
            event: Event object.
        
        Returns:
            BytesIO object containing PDF data.
        """
        packet = BytesIO()
        doc = SimpleDocTemplate(packet, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        story.append(Paragraph("Certificate of Attendance", styles['Title']))
        story.append(Spacer(1, 24))
        story.append(Paragraph("This certifies that:", styles['BodyText']))
        story.append(Paragraph(f"Name: {registration.first_name} {registration.last_name}", styles['BodyText']))
        story.append(Paragraph(f"Has attended the event: {event.title}", styles['BodyText']))
        story.append(Paragraph(f"Held on: {event.date.strftime('%Y-%m-%d')}", styles['BodyText']))
        story.append(Paragraph(f"Organized by: {event.organizer}", styles['BodyText']))
        story.append(Spacer(1, 12))
        story.append(Paragraph("Event Description:", styles['BodyText']))
        story.append(Paragraph(EventService._strip_html(event.description), styles['BodyText']))
        story.append(Spacer(1, 12))
        story.append(Paragraph("Event Program:", styles['BodyText']))
        story.append(Paragraph(EventService._strip_html(event.program), styles['BodyText']))
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"Eligible Hours: {event.eligible_hours}", styles['BodyText']))
        story.append(Spacer(1, 24))
        
        generation_date = datetime.now().strftime('%Y-%m-%d')
        story.append(Spacer(1, 24))
        story.append(Paragraph(f"Date: {generation_date}", styles['BodyText']))
        
        if event.signature_filename:
            signature_path = os.path.join(current_app.config['UPLOAD_FOLDER'], event.signature_filename)
            story.append(Spacer(1, 24))
            story.append(Paragraph("Signature:", styles['BodyText']))
            story.append(Spacer(1, 12))
            story.append(Paragraph(f'<img src="{signature_path}" width="200" height="50" valign="top"/>', styles['BodyText']))
        
        doc.build(story)
        packet.seek(0)
        return packet
    
    @staticmethod
    def _generate_ics(event: Event) -> str:
        """Generate ICS calendar content.
        
        Args:
            event: Event object.
        
        Returns:
            ICS content as string.
        """
        c = Calendar()
        e = ICSEvent()
        e.name = event.title
        e.description = (EventService._strip_html(event.description) + "\n\n" + 
                        "Program:\n" + EventService._strip_html(event.program))
        e.location = event.location or event.organizer
        
        # Combine date and time with timezone
        if event.date and event.start_time:
            try:
                tz = pytz.timezone(event.timezone)
            except pytz.UnknownTimeZoneError:
                logging.warning(f"Unknown timezone '{event.timezone}' for event {event.id}. Falling back to UTC.")
                tz = pytz.utc
            
            start_dt_naive = datetime.combine(event.date, event.start_time)
            e.begin = tz.localize(start_dt_naive)
            
            if event.end_time:
                end_dt_naive = datetime.combine(event.date, event.end_time)
                if end_dt_naive <= start_dt_naive:
                    end_dt_naive += timedelta(days=1)
                e.end = tz.localize(end_dt_naive)
            else:
                e.duration = timedelta(hours=1)
        else:
            e.begin = event.date
            e.make_all_day()
        
        e.uid = f"{event.id}-{event.date.strftime('%Y%m%d')}@meeting-manager.com"
        e.created = datetime.now(timezone.utc)
        c.events.add(e)
        return c.serialize()
    
    @staticmethod
    def _generate_csv(data: List[List[Any]]) -> str:
        """Generate CSV content from data.
        
        Args:
            data: List of rows, where each row is a list of values.
        
        Returns:
            CSV content as string.
        """
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['First Name', 'Last Name', 'Email', 'Unique Key', 'Presence'])
        for row in data:
            writer.writerow([str(s) if isinstance(s, (int, bool)) else s for s in row])
        return output.getvalue()
    
    @staticmethod
    def _strip_html(value: str) -> str:
        """Remove HTML tags from string.
        
        Args:
            value: String containing HTML.
        
        Returns:
            String with HTML tags removed.
        """
        return re.sub('<.*?>', '', value)