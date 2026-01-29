# Meeting Manager

Meeting Manager is a web application designed to manage events and generate certificates of attendance. It allows users to register for events, track attendance, and send email notifications.

## Features

- **Event Management**: Create, edit, and delete events. Track event details such as title, description, date, and organizer.
- **Registration**: Users can register for events and receive a unique key for attendance tracking.
- **Attendance Tracking**: Mark attendees as present and generate certificates of attendance.
- **Email Notifications**: Send registration confirmation emails to users.
- **User Roles**: Different user roles (super-admin, editor) with varying levels of access.
- **CSV Export**: Export attendance lists as CSV files.

## Setup Instructions

### Prerequisites

- Python 3.x
- Virtual Environment (optional but recommended)

### Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/BENETNATH/meeting_manager.git
   cd meeting_manager
   ```

2. **Create a Virtual Environment** (optional):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up Environment Variables**:
   Copy `.env.sample` to `.env` file in the root directory of the project and edit the environment variables:
   ```bash
   cp .env.sample .env
   ```

5. **Initialize Database and Create Default Users**:
   ```bash
   python run.py
   ```
   This will automatically create default admin and editor users if none exist.
    
6. **Reach your webapp and start to work**: 
   ```bash
   http://localhost:PORT
   ```  
   Default credentials and PORT are defined in `.env`

## User Management

### Default Users
When you first run the application, two default users are automatically created:

- **Super-admin**: username=`admin`, password=`admin123`
- **Editor**: username=`editor`, password=`editor123`

**IMPORTANT**: Change these default passwords after first login for security.

### Creating Additional Users

#### Method 1: Using the Management Interface
1. Log in as super-admin
2. Go to "Admin" → "Manage Users"
3. Click "Create Editor" to add new editor users
4. Users will receive a temporary password via email

#### Method 2: Using Command Line Scripts

**Create Default Users** (if none exist):
```bash
python init_users.py
```

**Create Specific Users**:
```bash
# Create a super-admin
python create_default_users.py create-superadmin --username myadmin --email admin@mycompany.com

# Create an editor
python create_default_users.py create-editor --username myeditor --email editor@mycompany.com

# Reset password for existing user
python create_default_users.py reset-password --username editor --password newpassword123

# List all users
python create_default_users.py list-users

# Show help
python create_default_users.py help
```

### User Roles

- **Super-admin**: Full access to all features including user management
- **Editor**: Can create and manage events, but cannot manage users

### Security Notes

1. **Change Default Passwords**: Always change the default passwords after setup
2. **Temporary Passwords**: New users receive temporary passwords that must be changed on first login
3. **Password Reset**: Super-admins can reset passwords for any user
4. **Email Configuration**: Configure email settings in `.env` for password reset functionality

## Deployment Options

### Development (Linux/Windows)
```bash
python run.py
```

### Production Windows
```bash
python serve.py
```

### Production Docker
```bash
# Build and run with Docker Compose
docker-compose up -d

# Or build manually
docker build -t meeting-manager .
docker run -p 8000:8000 --env-file .env meeting-manager
```

### Environment Configuration
All configuration is managed through the `.env` file:
- `PORT=8000` - Application port
- `HOST=0.0.0.0` - Network interface
- `FLASK_ENV=production` - Environment mode
- Database, email, and security settings

The application follows 12-Factor App principles with environment-based configuration.



## Related ressources

This project was mostly developped with Mistral.ai and Gemini

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
