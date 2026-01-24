"""
Flask CLI commands for SafeAlert
"""
import click
from app.extensions import db
from app.models import User, Category, Department, CategoryDepartmentMapping, DepartmentType


def register_commands(app):
    """Register CLI commands with Flask app"""
    
    @app.cli.command('create-admin')
    @click.option('--username', prompt=True, help='Admin username')
    @click.option('--email', prompt=True, help='Admin email')
    @click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Admin password')
    def create_admin(username, email, password):
        """Create an admin user"""
        if User.query.filter_by(username=username).first():
            click.echo(f'Error: User "{username}" already exists.')
            return
        
        if email and User.query.filter_by(email=email).first():
            click.echo(f'Error: User with email "{email}" already exists.')
            return
        
        user = User(
            username=username,
            email=email,
            is_staff=True
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        click.echo(f'Successfully created admin user: {username}')
    
    @app.cli.command('create-department-user')
    @click.option('--username', prompt=True, help='Department user username')
    @click.option('--email', prompt=True, help='Department user email')
    @click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Password')
    @click.option('--department-id', prompt=True, type=int, help='Department ID this user belongs to')
    def create_department_user(username, email, password, department_id):
        """Create a department user (task allocator)"""
        if User.query.filter_by(username=username).first():
            click.echo(f'Error: User "{username}" already exists.')
            return
        
        if email and User.query.filter_by(email=email).first():
            click.echo(f'Error: User with email "{email}" already exists.')
            return
        
        # Validate department
        department = Department.query.get(department_id)
        if not department:
            click.echo(f'Error: Department with ID {department_id} not found.')
            click.echo('Available departments:')
            for dept in Department.query.all():
                click.echo(f'  - {dept.id}: {dept.name} ({dept.code})')
            return
        
        user = User(
            username=username,
            email=email,
            is_department=True,
            department_id=department_id
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        click.echo(f'Successfully created department user: {username}')
        click.echo(f'Assigned to department: {department.name} ({department.code})')
    
    @app.cli.command('create-responder')
    @click.option('--username', prompt=True, help='Responder username')
    @click.option('--email', prompt=True, help='Responder email')
    @click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Password')
    @click.option('--department-code', prompt=True, help='Department code to assign')
    @click.option('--badge', prompt=False, default=None, help='Badge number')
    def create_responder(username, email, password, department_code, badge):
        """Create a responder user"""
        if User.query.filter_by(username=username).first():
            click.echo(f'Error: User "{username}" already exists.')
            return
        
        if email and User.query.filter_by(email=email).first():
            click.echo(f'Error: User with email "{email}" already exists.')
            return
        
        department = Department.query.filter_by(code=department_code).first()
        if not department:
            click.echo(f'Error: Department with code "{department_code}" not found.')
            click.echo('Available departments:')
            for dept in Department.query.all():
                click.echo(f'  - {dept.code}: {dept.name}')
            return
        
        user = User(
            username=username,
            email=email,
            is_responder=True,
            department_id=department.id,
            badge_number=badge,
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        click.echo(f'Successfully created responder user: {username}')
        click.echo(f'Assigned to department: {department.name}')
    
    @app.cli.command('create-department')
    @click.option('--name', prompt=True, help='Department name')
    @click.option('--code', prompt=True, help='Department code (unique)')
    @click.option('--type', 'dept_type', prompt=True, 
                  type=click.Choice(['FIRE', 'POLICE', 'MEDICAL', 'RESCUE', 'HAZMAT', 'TRAFFIC']),
                  help='Department type')
    @click.option('--latitude', prompt=True, type=float, help='Headquarters latitude')
    @click.option('--longitude', prompt=True, type=float, help='Headquarters longitude')
    @click.option('--address', prompt=False, default='', help='Address')
    @click.option('--radius', default=15.0, help='Coverage radius in km')
    def create_department(name, code, dept_type, latitude, longitude, address, radius):
        """Create a new department"""
        if Department.query.filter_by(code=code).first():
            click.echo(f'Error: Department with code "{code}" already exists.')
            return
        
        department = Department(
            name=name,
            code=code,
            type=dept_type,
            headquarters_lat=latitude,
            headquarters_lng=longitude,
            address=address,
            coverage_radius_km=radius,
        )
        
        db.session.add(department)
        db.session.commit()
        
        click.echo(f'Successfully created department: {name} ({code})')
        click.echo(f'Type: {dept_type}')
        click.echo(f'Location: {latitude}, {longitude}')
    
    @app.cli.command('seed-departments')
    def seed_departments():
        """Seed sample departments for testing"""
        departments_data = [
            {
                'name': 'Central Fire Station',
                'code': 'FD-01',
                'type': 'FIRE',
                'headquarters_lat': 40.7128,
                'headquarters_lng': -74.0060,
                'address': '100 Main Street',
                'coverage_radius_km': 15.0,
            },
            {
                'name': 'Downtown Police Station',
                'code': 'PD-01',
                'type': 'POLICE',
                'headquarters_lat': 40.7180,
                'headquarters_lng': -74.0000,
                'address': '200 Police Plaza',
                'coverage_radius_km': 20.0,
            },
            {
                'name': 'City Hospital EMS',
                'code': 'EMS-01',
                'type': 'MEDICAL',
                'headquarters_lat': 40.7100,
                'headquarters_lng': -74.0100,
                'address': '300 Hospital Drive',
                'coverage_radius_km': 25.0,
            },
            {
                'name': 'North Fire Station',
                'code': 'FD-02',
                'type': 'FIRE',
                'headquarters_lat': 40.7500,
                'headquarters_lng': -73.9800,
                'address': '400 North Avenue',
                'coverage_radius_km': 15.0,
            },
            {
                'name': 'East Police Precinct',
                'code': 'PD-02',
                'type': 'POLICE',
                'headquarters_lat': 40.7200,
                'headquarters_lng': -73.9500,
                'address': '500 East Boulevard',
                'coverage_radius_km': 20.0,
            },
        ]
        
        created_count = 0
        for dept_data in departments_data:
            if Department.query.filter_by(code=dept_data['code']).first():
                click.echo(f'Department already exists: {dept_data["code"]}')
                continue
            
            department = Department(**dept_data)
            db.session.add(department)
            created_count += 1
            click.echo(f'Created department: {dept_data["name"]} ({dept_data["code"]})')
        
        db.session.commit()
        click.echo(f'\nSuccessfully created {created_count} new department(s).')
    
    @app.cli.command('delete-user')
    @click.option('--username', prompt=True, help='Username to delete')
    @click.option('--force', is_flag=True, help='Skip confirmation prompt')
    def delete_user(username, force):
        """Delete a user account"""
        user = User.query.filter_by(username=username).first()
        
        if not user:
            click.echo(f'Error: User "{username}" not found.')
            return
        
        if not force:
            click.confirm(f'Are you sure you want to delete user "{username}"?', abort=True)
        
        db.session.delete(user)
        db.session.commit()
        
        click.echo(f'Successfully deleted user: {username}')
    
    # Alias for Django compatibility
    @app.cli.command('createsuperuser')
    @click.option('--username', prompt=True, help='Admin username')
    @click.option('--email', prompt=True, help='Admin email')
    @click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='Admin password')
    def createsuperuser(username, email, password):
        """Create a superuser (admin) - Django-style command"""
        if User.query.filter_by(username=username).first():
            click.echo(f'Error: User "{username}" already exists.')
            return
        
        if email and User.query.filter_by(email=email).first():
            click.echo(f'Error: User with email "{email}" already exists.')
            return
        
        user = User(
            username=username,
            email=email,
            is_staff=True
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        click.echo(f'Successfully created admin user: {username}')
    
    @app.cli.command('create-categories')
    def create_categories():
        """Create sample incident categories with department mappings"""
        categories_data = [
            {
                'name': 'Fire Emergency', 
                'description': 'Fire incidents and fire-related emergencies',
                'icon': '🔥',
                'color': '#FF5722',
                'default_severity': 'CRITICAL',
                'department_mappings': [('FIRE', 1), ('MEDICAL', 2)],
            },
            {
                'name': 'Medical Emergency', 
                'description': 'Health-related emergencies requiring immediate medical attention',
                'icon': '🏥',
                'color': '#E91E63',
                'default_severity': 'CRITICAL',
                'department_mappings': [('MEDICAL', 1)],
            },
            {
                'name': 'Crime/Security', 
                'description': 'Security threats, breaches, or criminal activity',
                'icon': '🚨',
                'color': '#3F51B5',
                'default_severity': 'HIGH',
                'department_mappings': [('POLICE', 1)],
            },
            {
                'name': 'Traffic Accident', 
                'description': 'Vehicle accidents and traffic incidents',
                'icon': '🚗',
                'color': '#FF9800',
                'default_severity': 'HIGH',
                'department_mappings': [('POLICE', 1), ('MEDICAL', 2), ('FIRE', 3)],
            },
            {
                'name': 'Natural Disaster', 
                'description': 'Natural disasters like floods, earthquakes, storms',
                'icon': '🌪️',
                'color': '#795548',
                'default_severity': 'CRITICAL',
                'department_mappings': [('FIRE', 1), ('RESCUE', 1), ('MEDICAL', 2), ('POLICE', 2)],
            },
            {
                'name': 'Hazardous Material', 
                'description': 'Chemical spills, gas leaks, and hazmat situations',
                'icon': '☢️',
                'color': '#FFEB3B',
                'default_severity': 'CRITICAL',
                'department_mappings': [('HAZMAT', 1), ('FIRE', 2), ('MEDICAL', 3)],
            },
            {
                'name': 'Infrastructure', 
                'description': 'Infrastructure issues, utilities, or facility problems',
                'icon': '🏗️',
                'color': '#607D8B',
                'default_severity': 'MEDIUM',
                'department_mappings': [],
            },
            {
                'name': 'Other', 
                'description': 'Other types of incidents not covered above',
                'icon': '📋',
                'color': '#9E9E9E',
                'default_severity': 'MEDIUM',
                'department_mappings': [],
            },
        ]
        
        created_count = 0
        for cat_data in categories_data:
            mappings = cat_data.pop('department_mappings', [])
            
            category = Category.query.filter_by(name=cat_data['name']).first()
            if category:
                click.echo(f'Category already exists: {category.name}')
            else:
                category = Category(**cat_data)
                db.session.add(category)
                db.session.flush()  # Get the ID
                
                # Create department mappings
                for dept_type, priority in mappings:
                    mapping = CategoryDepartmentMapping(
                        category_id=category.id,
                        department_type=dept_type,
                        priority=priority,
                    )
                    db.session.add(mapping)
                
                created_count += 1
                click.echo(f'Created category: {category.name}')
        
        db.session.commit()
        click.echo(f'\nSuccessfully created {created_count} new category(ies).')
    
    @app.cli.command('run-escalation-check')
    def run_escalation_check():
        """Run escalation check for stale incidents (for cron)"""
        from app.services.escalation import EscalationService
        
        service = EscalationService()
        logs = service.check_all_escalations()
        
        click.echo(f'Escalation check complete. {len(logs)} escalation(s) triggered.')
        for log in logs:
            click.echo(f'  - Incident #{log.incident_id}: {log.trigger_type} -> {log.action_type}')
    
    @app.cli.command('list-departments')
    def list_departments():
        """List all departments"""
        departments = Department.query.order_by(Department.type, Department.name).all()
        
        if not departments:
            click.echo('No departments found.')
            return
        
        click.echo('\nDepartments:')
        click.echo('-' * 60)
        for dept in departments:
            status = '✓' if dept.is_active else '✗'
            click.echo(f'{status} [{dept.code}] {dept.name} ({dept.type})')
            click.echo(f'    Location: {dept.headquarters_lat}, {dept.headquarters_lng}')
            click.echo(f'    Capacity: {dept.current_active_incidents}/{dept.max_concurrent_incidents}')
    
    @app.cli.command('list-users')
    @click.option('--role', type=click.Choice(['admin', 'department', 'responder', 'citizen', 'all']), default='all')
    def list_users(role):
        """List users by role"""
        query = User.query
        
        if role == 'admin':
            query = query.filter(User.is_staff == True)
        elif role == 'department':
            query = query.filter(User.is_department == True)
        elif role == 'responder':
            query = query.filter(User.is_responder == True)
        elif role == 'citizen':
            query = query.filter(
                User.is_staff == False,
                User.is_department == False,
                User.is_responder == False
            )
        
        users = query.order_by(User.username).all()
        
        if not users:
            click.echo(f'No {role} users found.')
            return
        
        click.echo(f'\nUsers ({role}):')
        click.echo('-' * 60)
        for user in users:
            roles = user.role_display
            dept = f' [{user.department.code}]' if user.department else ''
            status = '✓' if user.is_active else '(pending)'
            click.echo(f'{status} {user.username} ({roles}){dept}')
