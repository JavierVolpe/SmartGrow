import os

class Config:
    # Secret key for session management
    SECRET_KEY = os.environ.get('SECRET_KEY', 'AAAAAsecretAAAAA')

    # Database configurations
    DATA_DB_URI = 'db/data.db'
    USERS_DB_URI = 'db/users.db'
    WATERING_DB_URI = 'db/watering.db'

    # MQTT configurations
    MQTT_BROKER_IP = '<broker ip>'
    MQTT_BROKER_PORT = 1883
    MQTT_PUB_TOPIC = '<name>/growcontrol'
    MQTT_SUB_TOPIC = '<name>/growdata'

    # Device configurations
    WIZLIGHT_IP = '<WiZLight IP>'
    REMOTE_PC_IP = '<PC IP>'
    REMOTE_PC_MAC = '24:4b:fe:<PC MAC>'
    REMOTE_PC_USER = 'jvolp'

    # Image directory
    IMAGE_DIR = 'static'

    # Other configurations
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    NUMBER_OF_ROWS = 24 # Number of rows to display in tables

    # Shelly configurations
    SHELLY_DEVICE_ID = 'shellyplusplugs-<device id>'  # Replace with your device ID
    SHELLY_RPC_TOPIC = f'{SHELLY_DEVICE_ID}/rpc'
    SHELLY_RESPONSE_TOPIC = 'user_script/rpc'  # Topic where responses are published

    # Notification Settings
    CALLMEBOT_PHONE_NUMBER = '<your phone>'  # Replace with your phone number
    CALLMEBOT_APIKEY = '<your API key>'  # Replace with your CallMeBot API key
    CALLMEBOT_URL_TEMPLATE = 'https://api.callmebot.com/whatsapp.php?phone={phone_number}&text={message}&apikey={apikey}'

    # Divice configurations
    PLANTATION_DATE = '2025-01-17'
