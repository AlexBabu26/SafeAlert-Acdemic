"""
Application entry point for SafeAlert
"""
# Eventlet monkey patching must be done BEFORE any other imports
import eventlet
eventlet.monkey_patch()

from app import create_app
from app.config import Config
from app.extensions import socketio

app = create_app(Config)

if __name__ == '__main__':
    # Use socketio.run() for WebSocket support
    socketio.run(app, host='127.0.0.1', port=8000, debug=True)
