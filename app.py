from flask import Flask
from flask_socketio import SocketIO
from config import Config
from db import create_tables
from routes.home import home_bp
from routes.auth import auth_bp
from routes.customer import customer_bp
from routes.restaurant import restaurant_bp
from websockets import setup_socket_events

app = Flask(__name__)
app.config.from_object(Config)

socketio = SocketIO(app)

setup_socket_events(socketio)

# creating all tables
create_tables()


# registering all of the blueprints
app.register_blueprint(home_bp)

app.register_blueprint(auth_bp)

app.register_blueprint(customer_bp)

app.register_blueprint(restaurant_bp, url_prefix='/restaurant')

# Prevent caching of sensitive pages (like the login page) after logout
@app.after_request
def add_cache_control(response):
    # Set cache control to prevent caching of the page
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, proxy-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

if __name__ == '__main__':
    socketio.run(app, debug=True)  # Use socketio.run instead of app.run
