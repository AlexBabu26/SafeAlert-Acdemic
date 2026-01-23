# SafeAlert - Emergency Reporting Platform

SafeAlert is a secure, web-based emergency reporting platform that enables registered users to submit structured incident alerts, track their progress, and receive responses from administrators.

## Features

### For Users
- User registration and login with JWT authentication
- Submit emergency reports with predefined categories
- View and track incident status (Pending, Verified, Resolved)
- Receive admin responses/updates on incidents
- Search and filter reports by status and category

### For Administrators
- View all incident reports in an admin dashboard
- Filter and monitor reports by category, status, and date
- Update incident status (Pending → Verified → Resolved)
- Communicate with reporting users (send messages)
- Analyze trends with summary statistics and time series charts

## Technology Stack

- **Backend**: Flask 3.0.0 + Flask-RESTX
- **Authentication**: JWT (Flask-JWT-Extended)
- **Database**: SQLite3 (SQLAlchemy ORM)
- **Frontend**: HTML + CSS + JavaScript + Bootstrap 5
- **Charts**: Chart.js

## Project Structure

```
SafeAlert/
├── app/                # Flask application
│   ├── api/            # API endpoints (auth, incidents, messages, analytics)
│   ├── models/         # SQLAlchemy models (User, Incident, Category, etc.)
│   ├── schemas/        # Marshmallow schemas for validation
│   ├── services/       # Business logic (analytics)
│   ├── utils/          # Utilities (permissions, filters)
│   └── routes.py       # Frontend routes
├── templates/          # HTML templates
├── static/             # CSS, JavaScript, images
├── media/              # Uploaded files
├── migrations/         # Alembic database migrations
└── run.py              # Application entry point
```

## Installation

### Prerequisites

- Python 3.8+
- pip

### Setup Steps

1. **Clone the repository** (or navigate to the project directory)

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize the database** (if needed):
   ```bash
   flask db upgrade
   ```
   Or create tables directly using Python:
   ```bash
   python -c "from app import create_app; from app.extensions import db; app = create_app(); app.app_context().push(); db.create_all()"
   ```

5. **Create a superuser** (admin account):
   ```bash
   flask createsuperuser
   ```
   Or use the alternative command:
   ```bash
   flask create-admin
   ```
   Follow the prompts to enter username, email, and password. The user will be created with `is_staff=True` for admin access.

6. **Delete a user** (if needed):
   ```bash
   flask delete-user --username <username>
   ```
   Or with confirmation prompt:
   ```bash
   flask delete-user --username <username> --force
   ```

7. **Create sample categories** (optional):
   ```bash
   flask create-categories
   ```
   This will create default incident categories if they don't already exist.

8. **Run the Flask development server**:
   ```bash
   # Set Flask app (Windows PowerShell)
   set FLASK_APP=app.py
   flask run
   
   # Or on Linux/Mac
   export FLASK_APP=app.py
   flask run
   
   # Or use the run.py script directly
   python run.py
   ```

9. **Access the application**:
   - Frontend: http://127.0.0.1:5000
   - API Base: http://127.0.0.1:5000/api

## Usage

### User Registration and Login

1. Navigate to the landing page
2. Click "Register" to create an account
3. Fill in your details and submit
4. Log in with your credentials

### Submitting an Incident Report

1. Log in as a user
2. Click "New Report"
3. Select a category, fill in the description and optional fields
4. Submit the report
5. View your reports in "My Reports"

### Admin Functions

1. Log in with an admin account (user with `is_staff=True`)
2. Access the Admin Dashboard to view all incidents
3. Click on an incident to view details
4. Update status and send messages to users
5. View Analytics for trend analysis

## API Endpoints

### Authentication
- `POST /api/auth/register/` - User registration
- `POST /api/auth/token/` - Obtain JWT tokens
- `POST /api/auth/token/refresh/` - Refresh access token
- `GET /api/auth/me/` - Get current user profile

### Categories
- `GET /api/categories/` - List active categories

### Incidents (User)
- `POST /api/incidents/` - Create incident
- `GET /api/incidents/` - List user's incidents
- `GET /api/incidents/{id}/` - Get incident details

### Incidents (Admin)
- `GET /api/admin/incidents/` - List all incidents
- `PATCH /api/admin/incidents/{id}/status/` - Update incident status

### Messages
- `GET /api/incidents/{id}/messages/` - Get messages for an incident
- `POST /api/incidents/{id}/messages/` - Send a message (admin)

### Analytics (Admin)
- `GET /api/admin/analytics/summary/` - Get summary statistics
- `GET /api/admin/analytics/timeseries/?days=30` - Get time series data

## Database Models

- **User**: Custom User model (admin identified by `is_staff=True`)
- **Category**: Incident categories
- **IncidentReport**: Main incident records
- **IncidentAttachment**: File attachments (optional)
- **StatusHistory**: Audit trail of status changes
- **IncidentMessage**: Messages between admin and users

## Flask CLI Commands

### User Management
- `flask createsuperuser` - Create an admin user (Django-style command)
- `flask create-admin` - Create an admin user
- `flask delete-user --username <username>` - Delete a user account
- `flask delete-user --username <username> --force` - Delete without confirmation

### Data Management
- `flask create-categories` - Create sample incident categories

### Database
- `flask db upgrade` - Apply database migrations
- `flask db migrate -m "message"` - Create a new migration
- `flask shell` - Open a Python shell with app context

## Security Features

- JWT-based authentication (Flask-JWT-Extended)
- Role-based access control (user/admin)
- Users can only view their own incidents
- Admin-only endpoints protected
- SQL injection protection via SQLAlchemy ORM
- CORS configured for frontend-backend communication
- Password hashing with Werkzeug

## Development Notes

- The application uses SQLite3 for simplicity (can be switched to PostgreSQL/MySQL for production)
- JWT tokens are stored in localStorage (consider httpOnly cookies for production)
- File uploads are fully implemented and stored in `media/incidents/YYYY/MM/DD/` directory structure
- The frontend uses Bootstrap 5 and Chart.js (loaded via CDN)
- Flask development server runs on port 5000 by default
- Use `FLASK_APP=app.py` environment variable or `run.py` to start the server
- Database migrations can be managed with Alembic (`flask db` commands)

## License

This project is for academic/educational purposes.

## Support

For issues or questions, please refer to the project documentation or contact the development team.

