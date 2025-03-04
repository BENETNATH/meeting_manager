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
   Rename '.env-example' as `.env` file in the root directory of the project and edit the following environment variables:
   ```plaintext
   MAIL_SERVER=smtp.example.com
   MAIL_PORT=587
   MAIL_USE_TLS=True
   MAIL_USERNAME=your-email@example.com
   MAIL_PASSWORD=your-email-password
   MAIL_DEFAULT_SENDER=your-email@example.com
   SECRET_KEY=your-secret-key
   SQLALCHEMY_DATABASE_URI=sqlite:///database.db
   ```

5. **Run the Application**:
   ```bash
   flask run
   ```

## Deployment

### Using a Platform as a Service (PaaS)

1. **Heroku**:
   - Create a new Heroku app.
   - Connect your GitHub repository to Heroku.
   - Set the config vars in Heroku to match your `.env` file.
   - Deploy the app using the Heroku GitHub integration.

2. **Vercel** or **Netlify**:
   - These platforms are more suited for frontend applications but can be configured to deploy full-stack applications with serverless functions.

### Using Docker

1. **Create a Dockerfile**:
   ```dockerfile
   FROM python:3.9-slim

   WORKDIR /app

   COPY requirements.txt requirements.txt
   RUN pip install -r requirements.txt

   COPY . .

   CMD ["flask", "run", "--host=0.0.0.0"]
   ```

2. **Build and Run the Docker Container**:
   ```bash
   docker build -t meeting-manager .
   docker run -p 5000:5000 meeting-manager
   ```

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
