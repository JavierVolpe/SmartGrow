# config.py
# WIFI Configuration
ssid = 'Jwifi5'
password = '<deleted>'

# MQTT Configuration
MQTT_SERVER = "vm.azure.dk"
MQTT_USERNAME = "growtent"
MQTT_PASSWORD = "yourpassword"
TOPIC_PUB = b"grow/data"
TOPIC_SUB = b"grow/control"
TOPIC_STATUS = b"grow/status"

# OTA
OTA_DEFAULT_URL = "http://192.168.87.2/ota/main.py"

# Pin Assignments
ADC_PIN = 34
DS_PIN = 4
DHT_PIN = 5
FAN_PWM_PIN = 14
EXTRA_FAN_PIN_NUM = 16
PUMP_PIN_NUM = 32
RELAY_PIN_NUM = 33

# Soil Moisture Calibration
DRY_SOIL = 720
WET_SOIL = 276
NUM_SAMPLES = 50
RETURN_PERCENTAGE = True

# Mode Configuration
TEST_MODE = False
SLEEP_INTERVAL = 1
TOTAL_SLEEP_TIME = 1800
SEND_UPDATE = True
