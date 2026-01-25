"""
Flask extensions initialization
"""
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_migrate import Migrate

# Initialize extensions
db = SQLAlchemy()
jwt = JWTManager()
cors = CORS(supports_credentials=True)
socketio = SocketIO(cors_allowed_origins="*", async_mode='eventlet')
migrate = Migrate()
