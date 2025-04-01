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
   Rename '.env-example' as `.env` file in the root directory of the project and edit the environment variables:

5. **Run the Application ONCE to initialize database**:
   ```bash
   python app.py
   ```
    
8. **Reach your webapp and start to worl**: 
   ```bash
   http://localhost:PORT
   ```  
Default credentials and PORT are defined in .env



## Related ressources

This project was mostly developped with Mistral.ai and Gemini

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
