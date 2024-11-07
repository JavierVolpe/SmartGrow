from flask import Flask
from flask_login import LoginManager
import secrets

# Initialize Flask app
app = Flask(__name__)
#app.secret_key = secrets.token_hex(16)  # Or use your existing secret key
app.secret_key = "AAAAAAAAAAAAAAAA"



# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Import routes (make sure this import comes after initializing app and login_manager)
from routes import *

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
