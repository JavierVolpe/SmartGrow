import os

class Config:
    # Secret key for session management
    SECRET_KEY = os.environ.get('SECRET_KEY', '<your key>')

    # Database configurations
    DATA_DB_URI = 'db/data.db'
    USERS_DB_URI = 'db/users.db'
    WATERING_DB_URI = 'db/watering.db'

    # MQTT configurations
    MQTT_BROKER_IP = '192.168.87.2'
    MQTT_BROKER_PORT = 1883
    MQTT_PUB_TOPIC = 'grow/control'
    MQTT_SUB_TOPIC = 'grow/data'

    # Device configurations
    WIZLIGHT_BEDROOM = '192.168.87.102'
    WIZLIGHT_LIVINGROOM = '192.168.87.175'
    REMOTE_PC_IP = '192.168.87.3'
    REMOTE_PC_MAC = ''
    REMOTE_PC_USER = ''

    # Image directory
    IMAGE_DIR = 'static'

    # Other configurations
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    NUMBER_OF_ROWS = 24 # Number of rows to display in tables

    # Shelly configurations
    SHELLY_DEVICE_ID = 'shellyplusplugs-'  # Replace with your device ID
    SHELLY_RPC_TOPIC = f'{SHELLY_DEVICE_ID}/rpc'
    SHELLY_RESPONSE_TOPIC = 'user_script/rpc'  # Topic where responses are published

    # Notification Settings
    CALLMEBOT_PHONE_NUMBER = ''  # Replace with your phone number
    CALLMEBOT_APIKEY = ''  # Replace with your CallMeBot API key
    CALLMEBOT_URL_TEMPLATE = 'https://api.callmebot.com/whatsapp.php?phone={phone_number}&text={message}&apikey={apikey}'

    # Divice configurations
    PLANTATION_DATE = '2025-01-17'

    # Camera configurations

    PI_IP = '192.168.87.2'  
    PI_CAPTURE_URL = f"http://{PI_IP}:5000/capture"
    # URL base for static images served from the Pi
    PI_STATIC_URL = f"http://{PI_IP}:5000/static"
    # Local static directory where images will be saved on the Linux VM
    LOCAL_STATIC_DIR = "/home/azureuser/SmartGrow/static"  
    PI_VIDEO_FEED_URL = f"http://{PI_IP}:5000/video_feed"
