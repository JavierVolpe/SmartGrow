import os

class Config:
    # Secret key for session management
    SECRET_KEY = os.environ.get('SECRET_KEY', 'AAAAAAAAAAAAAAAA')

    # Database configurations
    DATA_DB_URI = 'db/data.db'
    USERS_DB_URI = 'db/users.db'
    WATERING_DB_URI = 'db/watering.db'

    # MQTT configurations
    MQTT_BROKER_IP = 'localhost'
    MQTT_BROKER_PORT = 1883
    MQTT_PUB_TOPIC = 'javier/growcontrol'
    MQTT_SUB_TOPIC = 'javier/growdata'

    # Device configurations
    WIZLIGHT_IP = '192.168.87.102'
    REMOTE_PC_IP = '192.168.87.3'
    REMOTE_PC_MAC = '24:4b:fe:93:78:f8'
    REMOTE_PC_USER = 'jvolp'

    # Image directory
    IMAGE_DIR = 'static'

    # Other configurations
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    NUMBER_OF_ROWS = 24 # Number of rows to display in tables
