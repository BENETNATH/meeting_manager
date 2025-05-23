import csv
import io
import os
import re
import uuid
import logging
import pytz # Added for timezone handling
from ics import Calendar, Event
from io import BytesIO
from datetime import datetime, timedelta, timezone # Added timedelta
from logging.handlers import RotatingFileHandler
from PIL import Image
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, Response, url_for, flash, abort, session, send_from_directory, send_file
from flask_babel import Babel, _
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, Spacer, SimpleDocTemplate, PageBreak
from waitress import serve
from werkzeug.utils import secure_filename
from ics import Calendar, Event as ICSEvent # Added for ICS generation

def validate_eligible_hours(start_time, end_time, eligible_hours):
    """
    Validates that the eligible hours count fits within the duration between start and end time.
    """
    if not start_time or not end_time or not eligible_hours:
        return True  # Skip validation if any of the values are missing

    duration = (datetime.combine(datetime.today(), end_time) - datetime.combine(datetime.today(), start_time)).total_seconds() / 3600
    return eligible_hours <= duration


# Initialisation de l'application Flask
app = Flask(__name__)

# Chargement des variables d'environnement
load_dotenv()
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = os.getenv('MAIL_PORT')
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS')
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
app.config['BABEL_DEFAULT_LOCALE'] = os.getenv('BABEL_DEFAULT_LOCALE')
app.config['BABEL_DEFAULT_TIMEZONE'] = os.getenv('BABEL_DEFAULT_TIMEZONE')
port = os.getenv('FLASK_PORT')
admin_password = os.getenv('ADMIN_PASSWORD')
admin_email = os.getenv('ADMIN_EMAIL')

# Initialisation des extensions
babel = Babel(app)
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
bcrypt = Bcrypt(app)
mail = Mail(app)

# Configuration des logs
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=3)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

### CLASS DEFINITIONS ####

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='editor')
    temp_password = db.Column(db.String(150), nullable=True)

    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    photo_url = db.Column(db.String(200), nullable=True)
    program = db.Column(db.Text, nullable=False)
    date = db.Column(db.Date, nullable=False) # Changed to Date
    start_time = db.Column(db.Time, nullable=True) # Added start_time
    end_time = db.Column(db.Time, nullable=True) # Added end_time
    organizer = db.Column(db.String(100), nullable=True)
    location = db.Column(db.String(200), nullable=True)
    eligible_hours = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(50), nullable=False, default='hidden')
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    signature_url = db.Column(db.String(200), nullable=True)
    timezone = db.Column(db.String(50), nullable=False, default='UTC') # Added timezone field

class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    unique_key = db.Column(db.String(100), unique=True, nullable=False)
    attended = db.Column(db.Boolean, default=False)

#### ROUTES AND FUNCTIONS DEFINITIONS ####

def strip_html(value):
    clean_text = re.sub('<.*?>', '', value)
    return clean_text

app.jinja_env.filters['strip_html'] = strip_html

def get_locale():
    lang = request.args.get('lang')
    if lang in ['fr', 'en']:
        session['lang'] = lang
        return lang
    if 'lang' in session:
        return session['lang']
    return request.accept_languages.best_match(['fr', 'en'])

babel = Babel(app, locale_selector=get_locale)

def generate_csv(data):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([_('First Name'), _('Last Name'), _('Email'), _('Unique Key'), _('Presence')])
    for row in data:
        writer.writerow([s if isinstance(s, str) else str(s) for s in row])
    return output.getvalue()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash(_('Wrong credentials'), 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/')
def index():
    events = Event.query.all()
    for event in events:
        event.registrations = Registration.query.filter_by(event_id=event.id).all()
        event.total_registered = len(event.registrations)
        event.total_attended = sum(1 for reg in event.registrations if reg.attended)
    return render_template('index.html', events=events)

@app.route('/extract_attendance/<int:event_id>')
@login_required
def extract_attendance(event_id):
    event = Event.query.get_or_404(event_id)
    if current_user.role == 'super-admin' or (current_user.role == 'editor' and event.created_by == current_user.id):
        registrations = Registration.query.filter_by(event_id=event_id).all()
        output = [[reg.first_name, reg.last_name, reg.email, reg.unique_key, reg.attended] for reg in registrations]
        csv_data = generate_csv(output)
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={event.title}_attendance.csv",
                "Content-Type": "text/csv; charset=utf-8"
            }
        )
    else:
        abort(403)

@app.route('/update_status/<int:event_id>', methods=['POST'])
@login_required
def update_status(event_id):
    event = Event.query.get_or_404(event_id)
    if current_user.role == 'super-admin' or (current_user.role == 'editor' and event.created_by == current_user.id):
        new_status = request.form.get('status')
        if new_status in ['hidden', 'visible', 'archived']:
            event.status = new_status
            db.session.commit()
            flash(_('Status updated successfully!'), 'success')
        else:
            flash(_('Invalid status'), 'error')
        return redirect(url_for('index'))
    else:
        abort(403)

@app.route('/delete_event/<int:event_id>', methods=['POST'])
@login_required
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)
    if current_user.role == 'super-admin' or (current_user.role == 'editor' and event.created_by == current_user.id):
        registrations = Registration.query.filter_by(event_id=event_id).all()
        for registration in registrations:
            db.session.delete(registration)
        if event.signature_url:
            signature_path = os.path.join('uploads', event.signature_url)
            if os.path.exists(signature_path):
                os.remove(signature_path)
        db.session.delete(event)
        db.session.commit()
        flash(_('Event and registrations successfully deleted!'), 'success')
        return redirect(url_for('index'))
    else:
        abort(403)

@app.route('/event/<int:event_id>')
def event(event_id):
    event = Event.query.get_or_404(event_id)
    return render_template('event.html', event=event)

# Add pytz timezones to the context for templates
@app.context_processor
def inject_timezones():
    return dict(timezones=pytz.common_timezones)

@app.route('/admin/create_event', methods=['GET', 'POST'])
@login_required
def create_event():
    if current_user.role not in ['super-admin', 'editor']:
        abort(403)
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        photo_url = request.form['photo_url']
        program = request.form['program']
        date_str = request.form['date']
        date = datetime.strptime(date_str, '%Y-%m-%d').date() # Get date object
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        start_time = datetime.strptime(start_time_str, '%H:%M').time() if start_time_str else None # Parse time
        end_time = datetime.strptime(end_time_str, '%H:%M').time() if end_time_str else None # Parse time
        organizer = request.form.get('organizer', '')
        timezone = request.form.get('timezone', 'UTC') # Get timezone from form

        # --- Validate Timezone ---
        if timezone not in pytz.common_timezones:
            flash(_('Invalid timezone selected. Please choose from the list.'), 'danger')
            # Re-render the form with submitted data (excluding invalid timezone)
            # We need to pass the form data back to the template
            form_data = request.form.to_dict()
            return render_template('create_event.html', form_data=form_data)
        # --- End Validate Timezone ---

        status = request.form['status']
        eligible_hours = request.form.get('eligible_hours', 0)
        if eligible_hours == '':
            eligible_hours = 0
        signature = request.files.get('signature')
        signature_url = None
        if signature:
            file_extension = os.path.splitext(signature.filename)[1]
            filename = f"{uuid.uuid4()}_signature{file_extension}"
            signature_path = os.path.join('uploads', filename)
            os.makedirs(os.path.dirname(signature_path), exist_ok=True)
            signature.save(signature_path)
            with Image.open(signature_path) as img:
                if img.width > 800 or img.height > 600:
                    flash(_('Signature must be smaller than 800*600'), 'danger')
                    return redirect(url_for('create_event'))
                img.thumbnail((250, 250))
                img.save(signature_path)
            signature_url = filename
        new_event = Event(
            title=title,
            description=description,
            photo_url=photo_url,
            program=program,
            date=date,
            start_time=start_time, # Add start_time
            end_time=end_time, # Add end_time
            organizer=organizer,
            location=request.form.get('location', ''),
            eligible_hours=eligible_hours,
            created_by=current_user.id,
            status=status,
            signature_url=signature_url,
            timezone=timezone # Save timezone
        )

        if not validate_eligible_hours(start_time, end_time, float(eligible_hours)):
            flash(_('Eligible hours must be within the event duration.'), 'danger')
            return render_template('create_event.html', form_data=request.form)

        db.session.add(new_event)
        db.session.commit()
        flash(_('Event successfully created'), 'success')
        return redirect(url_for('index'))
    # Pass empty dict if GET request
    return render_template('create_event.html', form_data=request.form if request.method == 'POST' else {})

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory('uploads', filename)

# --- Function to send event update emails ---
def send_update_email(registration, event):
    with app.app_context():
        subject = _('Event Update Notification: %(title)s', title=event.title)
        body = _('Hello %(name)s,\n\nPlease note that the event "%(event_title)s" has been updated.\nNew Date: %(date)s\nNew Start Time: %(start_time)s\nNew End Time: %(end_time)s\n\nPlease find the updated calendar details attached.\n\nThank you!',
                 name=registration.first_name,
                 event_title=event.title,
                 date=event.date.strftime('%Y-%m-%d'),
                 start_time=event.start_time.strftime('%H:%M') if event.start_time else _('N/A'),
                 end_time=event.end_time.strftime('%H:%M') if event.end_time else _('N/A'))
        msg = Message(subject=subject, recipients=[registration.email], body=body)

        # Generate and attach updated ICS file
        try:
            ics_content = generate_ics(event)
            event_title_safe = "".join(c if c.isalnum() else "_" for c in event.title)
            filename = f"{event.date.strftime('%Y-%m-%d')}_{event_title_safe}_updated.ics"
            msg.attach(filename, "text/calendar", ics_content)
        except Exception as e:
            logger.error(f"Error generating or attaching updated ICS for event {event.id} for user {registration.email}: {e}")
            # Optionally notify admin or handle the error

        try:
            mail.send(msg)
        except Exception as e:
            logger.error(f"Failed to send update email to {registration.email} for event {event.id}: {e}")


@app.route('/admin/edit_event/<int:event_id>', methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    event = Event.query.get_or_404(event_id)
    if current_user.role == 'super-admin' or (current_user.role == 'editor' and event.created_by == current_user.id):
        if request.method == 'POST':
            # Store original time details to check for changes
            original_date = event.date
            original_start_time = event.start_time
            original_end_time = event.end_time

            # Update event details from form
            event.title = request.form['title']
            event.description = request.form['description']
            event.photo_url = request.form['photo_url']
            event.program = request.form['program']
            new_date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
            start_time_str = request.form.get('start_time')
            end_time_str = request.form.get('end_time')
            new_start_time = datetime.strptime(start_time_str, '%H:%M').time() if start_time_str else None
            new_end_time = datetime.strptime(end_time_str, '%H:%M').time() if end_time_str else None
            event.organizer = request.form.get('organizer', '')
            event.location = request.form.get('location', '')
            new_timezone = request.form.get('timezone', event.timezone) # Get submitted timezone

            # --- Validate Timezone ---
            if new_timezone not in pytz.common_timezones:
                 flash(_('Invalid timezone selected. Please choose from the list.'), 'danger')
                 # Re-render edit form, keeping original event data + submitted form data
                 # Note: We don't update the event object with invalid data
                 return render_template('edit_event.html', event=event, form_data=request.form)
            # --- End Validate Timezone ---

            event.timezone = new_timezone # Update timezone only if valid
            event.eligible_hours = request.form.get('eligible_hours', 0)
            event.status = request.form['status']
            if event.eligible_hours == '':
                event.eligible_hours = 0

            if not validate_eligible_hours(new_start_time, new_end_time, float(event.eligible_hours)):
                flash(_('Eligible hours must be within the event duration.'), 'danger')
                return render_template('edit_event.html', event=event, form_data=request.form)

            # Check if time has changed
            time_changed = (new_date != original_date or
                            new_start_time != original_start_time or
                            new_end_time != original_end_time)

            # Update event times
            event.date = new_date
            event.start_time = new_start_time
            event.end_time = new_end_time

            # Handle signature upload
            signature = request.files.get('signature')
            if signature:
                file_extension = os.path.splitext(signature.filename)[1]
                filename = f"{uuid.uuid4()}_signature{file_extension}"
                signature_path = os.path.join('uploads', filename)
                os.makedirs(os.path.dirname(signature_path), exist_ok=True)
                signature.save(signature_path)
                with Image.open(signature_path) as img:
                    if img.width > 800 or img.height > 600:
                        flash(_('Signature must be smaller than 800*600'), 'danger')
                        return redirect(url_for('edit_event', event_id=event_id))
                    img.thumbnail((250, 250))
                    img.save(signature_path)
                if event.signature_url:
                    old_signature_path = os.path.join('uploads', event.signature_url)
                    if os.path.exists(old_signature_path):
                        os.remove(old_signature_path)
                event.signature_url = filename

            # Commit changes before sending emails
            db.session.commit()
            flash(_('Event successfully updated'), 'success')

            # Check if notification should be sent
            notify_users = request.form.get('notify_time_change') == 'true'
            if time_changed and notify_users:
                registrations = Registration.query.filter_by(event_id=event.id).all()
                if registrations:
                    flash(_('Sending update notifications to %(count)d registered users...', count=len(registrations)), 'info')
                    for reg in registrations:
                        send_update_email(reg, event) # Pass the updated event object
                else:
                     flash(_('Time changed and notification requested, but no users are registered.'), 'info')


            return redirect(url_for('index'))
        # Pass empty dict for form_data on GET request
        return render_template('edit_event.html', event=event, form_data={})
    else:
        abort(403)

@app.route('/admin/mark_attendance/<int:event_id>', methods=['GET', 'POST'])
@login_required
def mark_attendance(event_id):
    event = Event.query.get_or_404(event_id)
    if current_user.role == 'super-admin' or (current_user.role == 'editor' and event.created_by == current_user.id):
        registrations = Registration.query.filter_by(event_id=event_id).all()
        if request.method == 'POST':
            action = request.form.get('action')
            if action == 'check_all':
                for registration in registrations:
                    registration.attended = True
            elif action == 'update_attendance':
                for registration in registrations:
                    attended_key = f'attended_{registration.id}'
                    registration.attended = attended_key in request.form
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
                    last_name = request.form.get(f'last_name_new_{index}')
                    first_name = request.form.get(f'first_name_new_{index}')
                    email = request.form.get(f'email_new_{index}')
                    attended = request.form.get(f'attended_new_{index}') == 'on'
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
            flash(_('Modifications saved!'), 'success')
            return redirect(url_for('mark_attendance', event_id=event_id))
        return render_template('attendance.html', event=event, registrations=registrations)
    else:
        abort(403)

@app.route('/admin/delete_registration/<int:registration_id>', methods=['POST'])
@login_required
def delete_registration(registration_id):
    registration = Registration.query.get_or_404(registration_id)
    event = Event.query.get(registration.event_id)
    if current_user.role == 'super-admin' or (current_user.role == 'editor' and event.created_by == current_user.id):
        db.session.delete(registration)
        db.session.commit()
        flash(_('You have been unregistered.'), 'success')
    else:
        abort(403)
    return redirect(url_for('mark_attendance', event_id=event.id))

@app.route('/admin/create_editor', methods=['POST'])
@login_required
def create_editor():
    if current_user.role != 'super-admin':
        abort(403)
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        temp_password = generate_temp_password()
        new_user = User(username=username, email=email, role='editor', temp_password=temp_password)
        new_user.set_password(temp_password)
        db.session.add(new_user)
        db.session.commit()
        logger.info(f'User {username} successfully created')
        flash(f'Password: {temp_password}', 'success')
    return redirect(url_for('manage_users'))

def generate_temp_password():
    import random
    import string
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

@app.route('/admin/manage_users', methods=['GET', 'POST'])
@login_required
def manage_users():
    if current_user.role != 'super-admin':
        abort(403)
    users = User.query.all()
    if request.method == 'POST':
        user_id = request.form['user_id']
        new_role = request.form['role']
        user = User.query.get(user_id)
        if request.form.get('password'):
            user.password = bcrypt.generate_password_hash(request.form.get('password')).decode('utf-8')
        if user:
            user.role = new_role
            db.session.commit()
            logger.info(f"Role of {user.username} updated to {new_role}", "success")
            flash(f"Role of {user.username} updated to {new_role}", "success")
        return redirect(url_for('manage_users'))
    return render_template('manage_users.html', users=users)

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'super-admin':
        abort(403)
    user = User.query.get_or_404(user_id)
    if user.role == 'super-admin':
        other_super_admins = User.query.filter_by(role='super-admin').filter(User.id != user_id).count()
        if other_super_admins == 0:
            flash(_('Cannot delete the only super-admin user.'), 'danger')
            return redirect(url_for('manage_users'))
    events = Event.query.filter_by(created_by=user_id).all()
    for event in events:
        event.created_by = current_user.id
    logger.info(f'User {user.username} will be deleted')
    db.session.delete(user)
    db.session.commit()
    flash(_('User successfully deleted'), 'success')
    return redirect(url_for('manage_users'))

@app.route('/update_user/<int:user_id>', methods=['POST'])
@login_required
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    if current_user.role == 'super-admin' or current_user.id == user_id:
        user.role = request.form.get('role')
        if request.form.get('password'):
            user.set_password(request.form.get('password'))
        db.session.commit()
        flash(_('User successfully updated.'), 'success')
    else:
        abort(403)
    return redirect(url_for('manage_users'))

@app.route('/reset_password/<int:user_id>', methods=['POST'])
@login_required
def reset_password(user_id):
    if current_user.role != 'super-admin':
        abort(403)
    user = User.query.get_or_404(user_id)
    new_password = generate_temp_password()
    user.set_password(new_password)
    db.session.commit()
    send_reset_password_email(user.email, new_password)
    flash(_('Password has been reset and sent to the user\'s email.'), 'success')
    return redirect(url_for('manage_users'))

def send_reset_password_email(email, new_password):
    with app.app_context():
        subject = _('Password Reset')
        body = _('Hello,\n\nYour password has been reset. Your new password is: %(password)s\n\nPlease login and change your password as soon as possible.\n\nThank you!', password=new_password)
        msg = Message(subject=subject, recipients=[email], body=body)
        mail.send(msg)

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        new_password = request.form['new_password']
        current_user.set_password(new_password)
        current_user.temp_password = None
        db.session.commit()
        flash(_('Password updated.'), 'success')
        return redirect(url_for('index'))
    return render_template('change_password.html')

@app.route('/register_page/<int:event_id>', methods=['GET', 'POST'])
def register_page(event_id):
    event = Event.query.get_or_404(event_id)
    if request.method == 'POST':
        return register(event_id)
    return render_template('register.html', event=event)

def send_registration_email(email, first_name, event, unique_key): # Changed parameters to pass the whole event object
    with app.app_context():
        subject = _('Registration Confirmation')
        body = _('Hello %(name)s,\n\nYou have successfully registered for the event: %(event)s that will take place on %(date)s.\nYour unique key is: %(key)s\n\nThank you!', name=first_name, event=event.title, date=event.date.strftime('%Y-%m-%d'), key=unique_key)
        msg = Message(subject=subject, recipients=[email], body=body)

        # Generate and attach ICS file
        try:
            ics_content = generate_ics(event)
            event_title_safe = "".join(c if c.isalnum() else "_" for c in event.title)
            filename = f"{event.date.strftime('%Y-%m-%d')}_{event_title_safe}.ics"
            msg.attach(filename, "text/calendar", ics_content)
        except Exception as e:
            logger.error(f"Error generating or attaching ICS for event {event.id}: {e}")
            # Optionally notify admin or handle the error

        mail.send(msg)

@app.route('/register/<int:event_id>', methods=['POST'])
def register(event_id):
    event = Event.query.get_or_404(event_id)
    if event.status != 'visible':
        flash(_('Registration is not available'), 'error')
        return redirect(url_for('event', event_id=event_id))
    email = request.form.get('email')
    existing_registration = Registration.query.filter_by(event_id=event_id, email=email).first()
    if existing_registration:
        flash(_('Email already registered'), 'error')
        return redirect(url_for('register_page', event_id=event_id))
    unique_key = str(uuid.uuid4())
    new_registration = Registration(
        event_id=event_id,
        email=email,
        first_name=request.form.get('first_name'),
        last_name=request.form.get('last_name'),
        unique_key=unique_key
    )
    db.session.add(new_registration)
    db.session.commit()
    try:
        # Pass the event object instead of individual fields
        send_registration_email(email, request.form.get('first_name'), event, unique_key)
        flash(_('Registration successful. Your unique key is ') + unique_key, 'success')
    except Exception as e:
        logger.error(f"Failed to send registration email for {email} for event {event.id}: {e}")
        flash(_('Email notifications are not configured or failed to send. Please note down your unique key: ') + unique_key, 'warning')
    return redirect(url_for('event', event_id=event_id))

@app.route('/unregister_page/<int:event_id>', methods=['GET', 'POST'])
def unregister_page(event_id):
    event = Event.query.get_or_404(event_id)
    if request.method == 'POST':
        return unregister(event_id)
    return render_template('unregister.html', event=event)

@app.route('/unregister/<int:event_id>', methods=['POST'])
def unregister(event_id):
    email = request.form.get('email')
    unique_key = request.form.get('unique_key')
    registration = Registration.query.filter_by(event_id=event_id, email=email, unique_key=unique_key).first()
    if registration:
        db.session.delete(registration)
        db.session.commit()
        flash(_('Successful unregistration'), 'success')
    else:
        flash(_('No registration for this email and unique key on this event'), 'error')
    return redirect(url_for('event', event_id=event_id))

def generate_certificate_pdf(registration, event):
    packet = BytesIO()
    doc = SimpleDocTemplate(packet, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    story.append(Paragraph(_("Certificate of Attendance"), styles['Title']))
    story.append(Spacer(1, 24))
    story.append(Paragraph(_("This certifies that:"), styles['BodyText']))
    story.append(Paragraph(f"{_('Name:')} {registration.first_name} {registration.last_name}", styles['BodyText']))
    story.append(Paragraph(_("Has attended the event:") + f" {event.title}", styles['BodyText']))
    story.append(Paragraph(_("Held on:") + f" {event.date.strftime('%Y-%m-%d')}", styles['BodyText']))
    story.append(Paragraph(_("Organized by:") + f" {event.organizer}", styles['BodyText']))
    story.append(Spacer(1, 12))
    story.append(Paragraph(_("Event Description:"), styles['BodyText']))
    story.append(Paragraph(strip_html(event.description), styles['BodyText']))
    story.append(Spacer(1, 12))
    story.append(Paragraph(_("Event Program:"), styles['BodyText']))
    story.append(Paragraph(strip_html(event.program), styles['BodyText']))
    story.append(Spacer(1, 12))
    story.append(Paragraph(_("Eligible Hours:") + f" {event.eligible_hours}", styles['BodyText']))
    story.append(Spacer(1, 24))
    generation_date = datetime.now().strftime('%Y-%m-%d')
    story.append(Spacer(1, 24))
    story.append(Paragraph(_("Date:") + f" {generation_date}", styles['BodyText']))
    if event.signature_url:
        signature_path = f"uploads/{event.signature_url}"
        story.append(Spacer(1, 24))
        story.append(Paragraph(_("Signature:"), styles['BodyText']))
        story.append(Spacer(1, 12))
        story.append(Paragraph(f'<img src="{signature_path}" width="200" height="50" valign="top"/>', styles['BodyText']))
    doc.build(story)
    packet.seek(0)
    return packet

@app.route('/certificate', methods=['GET', 'POST'])
def request_certificate():
    if request.method == 'POST':
        email = request.form['email']
        unique_key = request.form['unique_key']
        registration = Registration.query.filter_by(email=email, unique_key=unique_key).first()
        if registration and registration.attended:
            event = Event.query.filter_by(id=registration.event_id).first()
            pdf = generate_certificate_pdf(registration, event)
            event_title_safe = "".join(c if c.isalnum() else "_" for c in event.title)
            event_date_safe = event.date.strftime('%Y-%m-%d')
            filename = f"{event_date_safe}_certificate_{event_title_safe}.pdf"
            return send_file(pdf, mimetype='application/pdf', as_attachment=True, download_name=filename)
        else:
            flash(_('Sorry, Your presence was not confirmed by the organizer.'), 'danger')
    return render_template('request_certificate.html')

# --- ICS Generation Function ---
def generate_ics(event):
    """Generates an ICS Calendar object for a given event."""
    c = Calendar()
    e = ICSEvent()
    e.name = event.title
    e.description = strip_html(event.description) + "\n\n" + _("Program:") + "\n" + strip_html(event.program)
    e.location = event.location or event.organizer # Use location if available, otherwise organizer

    # Combine date and time, handle potential None values
    if event.date and event.start_time:
        # Use the event's specific timezone
        try:
            tz = pytz.timezone(event.timezone)
        except pytz.UnknownTimeZoneError:
            logger.warning(f"Unknown timezone '{event.timezone}' for event {event.id}. Falling back to UTC.")
            tz = pytz.utc # Fallback to UTC if timezone is invalid

        start_dt_naive = datetime.combine(event.date, event.start_time)
        e.begin = tz.localize(start_dt_naive)

        if event.end_time:
            end_dt_naive = datetime.combine(event.date, event.end_time)
            # Handle overnight events if necessary
            if end_dt_naive <= start_dt_naive:
                end_dt_naive += timedelta(days=1)
            e.end = tz.localize(end_dt_naive)
        else:
            # Default duration if no end time (e.g., 1 hour) - start time is already localized
            e.duration = timedelta(hours=1)
    else:
        # Handle all-day event if no time specified
        e.begin = event.date
        e.make_all_day()

    e.uid = f"{event.id}-{event.date.strftime('%Y%m%d')}@meeting-manager.com" # Unique ID for the event
    e.created = datetime.now(timezone.utc) # Use UTC time for creation timestamp
    c.events.add(e)
    return c.serialize() # Return ICS content as string

# --- Route for ICS Download ---
@app.route('/event/<int:event_id>/download_ics')
def download_ics(event_id):
    event = Event.query.get_or_404(event_id)
    ics_content = generate_ics(event)
    event_title_safe = "".join(c if c.isalnum() else "_" for c in event.title)
    filename = f"{event.date.strftime('%Y-%m-%d')}_{event_title_safe}.ics"
    return Response(
        ics_content,
        mimetype="text/calendar",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

if __name__ == '__main__':
    with app.app_context():
        db_path = 'instance/database.db'
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin_user = User(username='admin', email=admin_email, role='super-admin')
            admin_user.set_password(admin_password)
            db.session.add(admin_user)
            db.session.commit()
    logger.info('Server is starting on port 8000...')
    serve(app, host="0.0.0.0", port=port)
