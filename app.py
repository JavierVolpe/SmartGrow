from flask import Flask
from flask_login import LoginManager
import secrets
import logging
from logging.handlers import RotatingFileHandler
import os


# Initialize Flask app
app = Flask(__name__)
#app.secret_key = secrets.token_hex(16)  # Or use your existing secret key
app.secret_key = "AAAAAAAAAAAAAAAA"

if not os.path.exists('logs'):
    os.mkdir('logs')

# Configure the Rotating File Handler
handler = RotatingFileHandler('logs/log_app.log', maxBytes=100000, backupCount=10)
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
handler.setFormatter(formatter)
handler.setLevel(logging.INFO)


# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)
app.logger.info('Application startup')

# Import routes (make sure this import comes after initializing app and login_manager)
from routes import *

# from waitress import serve
 
# if __name__ == "__main__":
#     serve(app, host="0.0.0.0", port=5000, debug=True)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
