# Import necessary modules
from umqttsimple import MQTTClient
from machine import Pin, reset, deepsleep
from time import sleep

# ---------------------- Configuration Constants ----------------------

# Test Mode Configuration
TEST_MODE = False  # Set to True for testing (short sleep intervals)
SLEEP_DURATION = 1800 if not TEST_MODE else 5  # Sleep time in seconds

# MQTT Configuration
MQTT_SERVER = "192.168.87.2"  # Replace with your MQTT broker's IP or hostname
MQTT_CLIENT_ID = "extra_fan_controller"
TOPIC_PUB = b"javier/growdata"  # Not in use here
TOPIC_SUB = b"javier/growcontrol"

# Pin Definitions
EXTRA_FAN_PIN_NUM = 16  # GPIO 16 for fan control

# Sleep Interval Configuration
SLEEP_INTERVAL = 1  # seconds
TOTAL_SLEEP_TIME = SLEEP_DURATION

# ---------------------- Initialize Fan ----------------------

try:
    fan = Pin(FAN_PIN_NUM, Pin.OUT)
    print("Fan initialized successfully.")
except Exception as e:
    print("Fan initialization failed:", e)

# ---------------------- MQTT Callback Function ----------------------

def mqtt_callback(topic, msg):
    try:
        msg_str = msg.decode()
        print(f"Received message: '{msg_str}' on topic: '{topic.decode()}'")
    except UnicodeDecodeError:
        print("Received non-decodable message on topic:", topic)
        return

    if msg == b"send_update":
        publish_hello()
    elif msg == b"start_extra_fan":
        fan.on()
    elif msg == b"stop_extra_fan":
        fan.off()
    elif msg == b"reset":
        print("Reset command received. Restarting...")
        reset()

# ---------------------- MQTT Connection ----------------------

def publish_hello():
    try:
        hello_msg = f"Hello from {MQTT_CLIENT_ID}"
        
        #client.publish(TOPIC_PUB, b"hello")
        client.publish(TOPIC_PUB, hello_msg)
        print(f"Hello message sent to MQTT broker from {MQTT_CLIENT_ID}.")
    except Exception as e:
        print("Failed to send hello message:", e)

def connect_mqtt():
    client = MQTTClient(MQTT_CLIENT_ID, MQTT_SERVER)
    while True:
        try:
            client.connect()
            client.set_callback(mqtt_callback)
            client.subscribe(TOPIC_SUB)
            print("Connected to MQTT broker.")
            return client
        except OSError as e:
            print("Failed to connect to MQTT broker. Retrying in 10 seconds...")
            print(e)
            sleep(10)

# ---------------------- Main Execution ----------------------

client = connect_mqtt()
publish_hello()

try:
    if not TEST_MODE:
        while True:
            elapsed_sleep_time = 0
            while elapsed_sleep_time < TOTAL_SLEEP_TIME:
                client.check_msg()
                sleep(SLEEP_INTERVAL)
                elapsed_sleep_time += SLEEP_INTERVAL
    else:
        while True:
            client.check_msg()
            sleep(2)
except Exception as e:
    print("An unexpected error occurred in the main loop:", e)
    reset()

