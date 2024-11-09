from flask_login import UserMixin
import sqlite3
from config import Config

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

# Load user from database
def load_user(user_id):
    try:
        conn = sqlite3.connect(Config.USERS_DB_URI)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
    except Exception as e:
        print(f"Error loading user: {e}")
        return None

    if user:
        return User(id=user[0], username=user[1], password=user[2])
    return None

# Function to ensure the watering table exists
def create_watering_table():
    try:
        conn = sqlite3.connect(Config.WATERING_DB_URI)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS watering_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                amount_ml INTEGER
            )
        """
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error creating watering table: {e}")
        return False
