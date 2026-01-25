# SafeAlert - Emergency Reporting and Response Platform

SafeAlert is a comprehensive, web-based emergency reporting and response platform that enables citizens to report incidents, department users to coordinate responses, and responders to manage field operations in real-time.

## Features

### For Citizens
- **User Registration**: Register as a citizen or responder (responders require admin approval)
- **Incident Reporting**: Submit emergency reports with categories, location, and media attachments
- **Anonymous Reporting**: Option to report incidents anonymously with tracking code
- **Incident Tracking**: View and track incident status in real-time
- **Communication**: Chat with department users and responders assigned to your incident
- **Safety Alerts**: Receive location-based safety alerts and notifications
- **PWA Support**: Install as a Progressive Web App for mobile access

### For Responders
- **Responder Dashboard**: View assigned incidents and update status
- **Assignment Management**: Accept, update status (En Route, On Scene, Resolved)
- **Location Tracking**: Share real-time location with dispatch
- **Incident Details**: Full incident information with navigation
- **Real-time Chat**: Communicate with citizens and department users
- **Status Updates**: Update availability and duty status

### For Department Users (Task Allocators)
- **Command Center**: Real-time dashboard with all incidents
- **Incident Assignment**: Assign incidents to departments and responders based on proximity and availability
- **Resource Management**: View and manage department resources (vehicles, equipment)
- **Map View**: Real-time map showing incidents, responders, and resources
- **Analytics**: Department-specific analytics and statistics
- **Safety Alerts**: Create and broadcast location-based safety alerts
- **Escalation**: Manually escalate incidents when needed

### For Administrators
- **User Management**: Activate/deactivate users, manage roles (Citizen, Responder, Department User, Admin)
- **System Analytics**: View all system-wide analytics and trends
- **Incident Oversight**: View all incidents across the platform
- **Department Management**: Create and manage departments
- **Resource Management**: Manage department resources
- **Category Management**: Configure incident categories and department mappings
- **System Configuration**: Full system access and configuration

## User Roles

### 1. Citizen (Default)
- **Registration**: Public registration, active immediately
- **Capabilities**: Report incidents, track status, communicate with responders
- **Access**: Own incidents only

### 2. Responder
- **Registration**: Public registration, requires admin approval (`is_active=False` initially)
- **Requirements**: Must select a department during registration
- **Capabilities**: View assigned incidents, update status, share location, communicate
- **Access**: Assigned incidents only

### 3. Department User (Task Allocator)
- **Creation**: Created via CLI command, requires department assignment
- **Requirements**: Must be assigned to a department (`department_id` required)
- **Capabilities**: Assign incidents, manage resources, view department analytics, create alerts
- **Access**: All incidents (can assign to their department)
- **Restrictions**: Cannot manage users (admin-only)

### 4. Admin
- **Creation**: Created via CLI command
- **Capabilities**: Full system access including user management, system analytics, all incidents
- **Access**: Everything
- **Restrictions**: Cannot assign responders (department users only)

## Technology Stack

- **Backend**: Flask 3.0.0 + Flask-RESTX
- **Authentication**: JWT (Flask-JWT-Extended)
- **Database**: SQLite3 (SQLAlchemy ORM) with Alembic migrations
- **Real-time**: Flask-SocketIO for WebSocket communication
- **Frontend**: HTML + CSS + JavaScript + Bootstrap 5
- **Charts**: Chart.js
- **PWA**: Service Worker + Web App Manifest

## Project Structure

```
SafeAlert/
├── app/                    # Flask application
│   ├── api/                # API endpoints
│   │   ├── auth.py         # Authentication (register, login)
│   │   ├── incidents.py   # User incident management
│   │   ├── admin_incidents.py  # Admin incident management
│   │   ├── admin_users.py  # Admin user management
│   │   ├── admin_categories.py # Admin category management
│   │   ├── department.py   # Department user endpoints
│   │   ├── responder.py    # Responder endpoints
│   │   ├── analytics.py    # Analytics (admin + department)
│   │   ├── notifications.py # User notifications
│   │   ├── alerts.py       # Safety alerts
│   │   ├── messages.py     # Incident messaging
│   │   └── categories.py   # Incident categories
│   ├── models/             # SQLAlchemy models
│   │   ├── user.py         # User model (multi-role)
│   │   ├── incident.py     # Incident, Category, StatusHistory
│   │   ├── department.py   # Department, Resource
│   │   ├── assignment.py   # IncidentAssignment
│   │   ├── notification.py # Notification
│   │   ├── escalation.py  # EscalationRule, EscalationLog
│   │   ├── alert.py        # SafetyAlert
│   │   └── category_mapping.py # CategoryDepartmentMapping
│   ├── schemas/            # Marshmallow schemas
│   ├── services/           # Business logic
│   │   ├── allocation.py  # Smart incident allocation
│   │   ├── escalation.py  # Automated escalation
│   │   ├── notification.py # Notification delivery
│   │   ├── analytics.py    # System analytics
│   │   └── department_analytics.py # Department analytics
│   ├── utils/              # Utilities
│   │   ├── permissions.py # Role-based access control
│   │   ├── geo.py         # Geographic calculations
│   │   └── filters.py     # Query filters
│   ├── socketio_events.py  # Real-time event handlers
│   └── routes.py           # Frontend routes
├── templates/              # HTML templates
│   ├── public/            # Public pages (login, register)
│   ├── user/              # Citizen pages
│   ├── responder/         # Responder dashboard
│   ├── department/        # Department user dashboard
│   └── adminpanel/        # Admin dashboard
├── static/                 # CSS, JavaScript, images
│   ├── manifest.json      # PWA manifest
│   └── service-worker.js  # PWA service worker
├── media/                  # Uploaded files
├── migrations/             # Alembic database migrations
└── run.py                  # Application entry point
```

## Installation

### Prerequisites

- Python 3.8+
- pip
- Virtual environment (recommended)

### Setup Steps

1. **Clone the repository** (or navigate to the project directory)

2. **Create and activate virtual environment**:
   ```bash
   python -m venv .venv
   # Windows PowerShell
   .venv\Scripts\activate
   # Linux/Mac
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize the database**:
   ```bash
   flask db upgrade
   ```
   Or create tables directly:
   ```bash
   python -c "from app import create_app; from app.extensions import db; app = create_app(); app.app_context().push(); db.create_all()"
   ```

5. **Create an admin user**:
   ```bash
   flask create-admin
   # Or Django-style:
   flask createsuperuser
   ```
   Follow prompts to enter username, email, and password.

6. **Create departments** (required for department users and responders):
   ```bash
   flask create-department
   # Or seed sample departments:
   flask seed-departments
   ```

7. **Create department users** (task allocators):
   ```bash
   flask create-department-user --username dept_user1 --email dept@example.com --password <pass> --department-id 1
   ```

8. **Create responders** (or they can register themselves):
   ```bash
   flask create-responder --username responder1 --email responder@example.com --password <pass> --department-code FD-01 --badge FD-123
   ```

9. **Create sample categories** (optional):
   ```bash
   flask create-categories
   ```

10. **Run the application**:
    ```bash
    # Using Flask CLI (basic server, no SocketIO)
    flask run
    
    # Or using run.py (supports SocketIO for real-time features)
    python run.py
    ```

11. **Access the application**:
    - Frontend: http://127.0.0.1:5000
    - API Base: http://127.0.0.1:5000/api

## Usage

### User Registration

1. Navigate to `/register`
2. Select role: **Citizen** or **Responder**
3. Fill in details:
   - **Citizens**: Username, email, password (active immediately)
   - **Responders**: Username, email, password, department selection, badge number (pending approval)
4. Submit registration
5. **Citizens**: Login immediately
6. **Responders**: Wait for admin approval, then login

### Submitting an Incident Report

1. Log in as a citizen
2. Click "New Report"
3. Select category, fill description, location (GPS or text)
4. Optionally attach media files
5. Choose severity level
6. Optionally report anonymously
7. Submit the report
8. Track status in "My Reports" or use tracking code

### Department User (Task Allocator) Workflow

1. Log in as a department user
2. Access Command Center dashboard
3. View all incidents on real-time map
4. Assign incidents to your department or other departments
5. Monitor responder locations and status
6. Create safety alerts for public
7. View department-specific analytics
8. Escalate incidents when needed

### Responder Workflow

1. Log in as a responder (must be approved by admin)
2. View assigned incidents in dashboard
3. Accept assignments
4. Update status: En Route → On Scene → Resolved
5. Share real-time location (optional)
6. Communicate with citizens and department users
7. Update availability status

### Admin Functions

1. Log in with admin account
2. **User Management** (`/admin/users`):
   - View all users (Citizens, Responders, Department Users, Admins)
   - Activate/deactivate users
   - Change user roles
   - Filter by role, status, department
3. **Incident Management** (`/admin/dashboard`):
   - View all incidents
   - Update incident status
   - View analytics
4. **System Configuration**:
   - Manage departments and resources
   - Configure categories
   - System-wide analytics

## API Endpoints

### Authentication
- `POST /api/auth/register/` - User registration (citizen or responder)
- `POST /api/auth/token/` - Obtain JWT tokens (login)
- `POST /api/auth/token/refresh/` - Refresh access token
- `GET /api/auth/me/` - Get current user profile
- `GET /api/auth/departments/` - List departments (for registration)

### Categories
- `GET /api/categories/` - List active categories

### Incidents (Citizens)
- `POST /api/incidents/` - Create incident report
- `GET /api/incidents/` - List user's incidents
- `GET /api/incidents/{id}/` - Get incident details
- `GET /api/incidents/{id}/messages/` - Get messages for incident
- `POST /api/incidents/{id}/messages/` - Send message

### Incidents (Admin)
- `GET /api/admin/incidents/` - List all incidents (with filters)
- `GET /api/admin/incidents/{id}/` - Get incident details
- `PATCH /api/admin/incidents/{id}/status/` - Update incident status

### Department User Endpoints
- `GET /api/department/incidents/` - List all incidents
- `GET /api/department/incidents/{id}/` - Get incident details
- `POST /api/department/incidents/{id}/assign/` - Assign incident to departments
- `POST /api/department/incidents/{id}/escalate/` - Escalate incident
- `GET /api/department/incidents/{id}/nearby-departments/` - Get nearby departments
- `GET /api/department/map/` - Get map data (incidents, responders, resources)
- `GET /api/department/stats/` - Get dashboard statistics
- `GET /api/department/analytics/summary/` - Department analytics summary
- `GET /api/department/analytics/timeseries/?days=30` - Department time series
- `GET /api/department/departments/` - List all departments
- `GET /api/department/resources/` - List all resources
- `POST /api/alerts/` - Create safety alert

### Responder Endpoints
- `GET /api/responder/dashboard/` - Responder dashboard data
- `GET /api/responder/assignments/` - List assignments
- `GET /api/responder/assignments/{id}/` - Get assignment details
- `POST /api/responder/assignments/{id}/accept/` - Accept assignment
- `POST /api/responder/assignments/{id}/status/` - Update assignment status
- `PUT /api/responder/location/` - Update responder location

### User Management (Admin)
- `GET /api/admin/users/` - List all users (with filters)
- `GET /api/admin/users/stats/` - User statistics
- `GET /api/admin/users/{id}/` - Get user details
- `PATCH /api/admin/users/{id}/` - Update user (roles, status, department)
- `POST /api/admin/users/{id}/activate/` - Activate user
- `POST /api/admin/users/{id}/deactivate/` - Deactivate user
- `DELETE /api/admin/users/{id}/` - Delete user
- `GET /api/admin/users/pending/` - List pending users

### Notifications
- `GET /api/notifications/` - Get user notifications
- `GET /api/notifications/{id}/` - Get notification details
- `PUT /api/notifications/{id}/read/` - Mark as read
- `GET /api/notifications/unread_count/` - Get unread count

### Safety Alerts
- `GET /api/alerts/` - List active alerts
- `GET /api/alerts/{id}/` - Get alert details
- `POST /api/alerts/` - Create alert (department user/admin)
- `PUT /api/alerts/{id}/resolve/` - Resolve alert

### Analytics
- **Admin**: `GET /api/admin/analytics/summary/` - System-wide summary
- **Admin**: `GET /api/admin/analytics/timeseries/?days=30` - System-wide time series
- **Department**: `GET /api/department/analytics/summary/` - Department-specific summary
- **Department**: `GET /api/department/analytics/timeseries/?days=30` - Department time series

## Database Models

### Core Models
- **User**: Multi-role user model (`is_staff`, `is_department`, `is_responder`, `is_active`)
- **Category**: Incident categories with department mappings
- **IncidentReport**: Main incident records with status, severity, location
- **IncidentAttachment**: File attachments for incidents
- **StatusHistory**: Audit trail of status changes
- **IncidentMessage**: Messages between users, responders, and department users

### Department & Resource Models
- **Department**: Emergency service departments (Fire, Police, Medical, etc.)
- **Resource**: Vehicles, equipment, personnel tracking
- **CategoryDepartmentMapping**: Routes incidents to appropriate departments

### Assignment & Response Models
- **IncidentAssignment**: Links incidents to departments/responders with status tracking
- **Notification**: In-app notifications for users
- **EscalationRule**: Automated escalation rules
- **EscalationLog**: Escalation action history
- **SafetyAlert**: Public safety broadcasts with geo-targeting

## Flask CLI Commands

### User Management
- `flask create-admin` - Create an admin user
- `flask createsuperuser` - Create an admin user (Django-style)
- `flask create-department-user` - Create a department user (requires department-id)
- `flask create-responder` - Create a responder user (requires department-code)
- `flask delete-user --username <username>` - Delete a user account
- `flask delete-user --username <username> --force` - Delete without confirmation
- `flask list-users --role <role>` - List users by role (admin, department, responder, citizen, all)

### Department Management
- `flask create-department` - Create a new department
- `flask seed-departments` - Seed sample departments
- `flask list-departments` - List all departments

### Data Management
- `flask create-categories` - Create sample incident categories with department mappings
- `flask run-escalation-check` - Run escalation check for stale incidents

### Database
- `flask db init` - Initialize migrations (first time)
- `flask db migrate -m "message"` - Create a new migration
- `flask db upgrade` - Apply pending migrations
- `flask db downgrade` - Rollback last migration
- `flask shell` - Open Python shell with app context

## Real-Time Features

### WebSocket Events (SocketIO)
- **Location Updates**: Responders share real-time location
- **Incident Updates**: Real-time incident status changes
- **Assignment Updates**: New assignments broadcast to responders
- **Chat**: Real-time messaging in incident rooms
- **Notifications**: Push notifications for new assignments, updates

### Event Handlers
- `connect` - Client connection
- `disconnect` - Client disconnection
- `join_room` - Join incident/department room
- `send_message` - Send chat message
- `update_location` - Update responder location

## Security Features

- **JWT Authentication**: Secure token-based authentication
- **Role-Based Access Control**: Citizens, Responders, Department Users, Admins
- **Account Activation**: Responders require admin approval before login
- **User Management**: Admins can activate/deactivate accounts
- **Permission Decorators**: `@admin_required`, `@department_required`, `@responder_required`
- **Department Isolation**: Department users see department-filtered analytics
- **SQL Injection Protection**: SQLAlchemy ORM with parameterized queries
- **CORS Configuration**: Configured for frontend-backend communication
- **Password Hashing**: Werkzeug secure password hashing

## Progressive Web App (PWA)

- **Web App Manifest**: Install as mobile app
- **Service Worker**: Offline caching support
- **Mobile Optimized**: Responsive design for mobile devices
- **Push Notifications**: Ready for push notification integration

## Key Improvements (SafeAlert 2.0)

### Role-Based System
- ✅ Multi-role user system (Citizen, Responder, Department User, Admin)
- ✅ Department-based organization
- ✅ Role-specific dashboards and permissions

### Incident Management
- ✅ Smart allocation algorithm (distance, workload, specialization)
- ✅ Assignment tracking with status updates
- ✅ Real-time incident updates
- ✅ Escalation system with automated rules

### Real-Time Features
- ✅ WebSocket communication (Flask-SocketIO)
- ✅ Live location tracking for responders
- ✅ Real-time chat in incidents
- ✅ Live map with incidents and responders

### Analytics & Reporting
- ✅ System-wide analytics (admin)
- ✅ Department-specific analytics (department users)
- ✅ Time series data and trends
- ✅ Assignment statistics and response times

### User Management
- ✅ Account activation/deactivation
- ✅ Role management
- ✅ Pending user approval workflow
- ✅ User statistics and filtering

### Safety Features
- ✅ Location-based safety alerts
- ✅ Anonymous reporting with tracking
- ✅ Notification system
- ✅ Escalation workflows

## Development Notes

- **Database**: SQLite3 for development (switch to PostgreSQL/MySQL for production)
- **Real-time Server**: Use `python run.py` for SocketIO support (not `flask run`)
- **Migrations**: Use Alembic for database migrations (`flask db` commands)
- **Environment**: Always activate virtual environment: `.venv\Scripts\activate` (Windows)
- **JWT Tokens**: Stored in localStorage (consider httpOnly cookies for production)
- **File Uploads**: Stored in `media/incidents/YYYY/MM/DD/` directory structure
- **Frontend**: Bootstrap 5 + Chart.js (loaded via CDN)
- **Port**: Default port 5000 (configurable via `PORT` environment variable)

## Workflow Example

1. **Citizen reports fire incident** → Status: PENDING
2. **Admin verifies incident** → Status: VERIFIED
3. **System auto-allocates** OR **Department user manually assigns** → Status: DISPATCHED
4. **Responder accepts assignment** → Assignment Status: ACCEPTED
5. **Responder updates to En Route** → Assignment Status: EN_ROUTE
6. **Responder arrives** → Assignment Status: ON_SCENE
7. **Responder resolves** → Assignment Status: COMPLETED, Incident Status: RESOLVED
8. **Admin closes** → Incident Status: CLOSED

## License

This project is for academic/educational purposes.

## Support

For issues or questions, please refer to the project documentation or contact the development team.
