# Import necessary modules
from umqttsimple import MQTTClient
from machine import Pin, reset, PWM
from time import sleep
import dht

# ---------------------- Configuration Constants ----------------------

# Test Mode Configuration
TEST_MODE = False  # Set to True for testing (short sleep intervals)
SLEEP_DURATION = 1800 if not TEST_MODE else 5  # Sleep time in seconds

# MQTT Configuration
MQTT_SERVER = "192.168.87.2"
MQTT_CLIENT_ID = "pico_w_client"
TOPIC_PUB = b"javier/drydata"
TOPIC_SUB = b"javier/drycontrol"

# Pin Definitions
DHT_PIN = Pin(5)  # GPIO 5 for DHT11
TOP_FAN_PWM_PIN = 15  # GPIO 15 for top fan PWM control
BOTTOM_FAN_PWM_PIN = 13  # GPIO 13 for bottom fan PWM control

# PWM Configuration
PWM_FREQ = 25000  # 25kHz PWM frequency

# Sleep Interval Configuration
SLEEP_INTERVAL = 1  # seconds
TOTAL_SLEEP_TIME = SLEEP_DURATION  # Total sleep time in seconds

# ---------------------- Initialize Sensors and Actuators ----------------------

# Initialize DHT11 Sensor (Temperature and Humidity)
try:
    dht_sensor = dht.DHT11(DHT_PIN)
    SENSOR_AVAILABLE = True
    print("DHT11 sensor initialized successfully.")
except Exception as e:
    print("DHT11 sensor initialization failed:", e)
    SENSOR_AVAILABLE = False

# Initialize Fans with PWM
try:
    top_fan_pwm = PWM(Pin(TOP_FAN_PWM_PIN), freq=PWM_FREQ)
    bottom_fan_pwm = PWM(Pin(BOTTOM_FAN_PWM_PIN), freq=PWM_FREQ)
    # Initialize fan speeds to 0%
    top_fan_pwm.duty_u16(0)
    bottom_fan_pwm.duty_u16(0)
    print("Fans initialized successfully.")
except Exception as e:
    print("Fan PWM initialization failed:", e)

# ---------------------- Global Variables ----------------------

fan_speed = 0  # Initial fan speed percentage (0-100)

# ---------------------- Helper Functions ----------------------

def set_fan_speed(speed_percent, position="top"):
    """
    Sets the speed of the specified fan.

    :param speed_percent: Desired speed percentage (0-100)
    :param position: 'top' or 'bottom' to specify which fan to control
    """
    global fan_speed
    if 0 <= speed_percent <= 100:
        duty_cycle = int((speed_percent / 100) * 65535)  # Scale to 0-65535
        if position == "top":
            top_fan_pwm.duty_u16(duty_cycle)
        elif position == "bottom":
            bottom_fan_pwm.duty_u16(duty_cycle)
        fan_speed = speed_percent
        print("Fan speed set to {}% for {} fan.".format(speed_percent, position))
    else:
        print("Invalid fan speed percentage. Must be between 0 and 100.")

def read_dht11_sensor():
    """
    Reads temperature and humidity from the DHT11 sensor.

    :return: Tuple containing temperature (°C) and humidity (%)
    """
    if not SENSOR_AVAILABLE:
        print("DHT11 sensor not available.")
        return None, None
    try:
        dht_sensor.measure()
        temp = dht_sensor.temperature()
        humidity = dht_sensor.humidity()
        return temp, humidity
    except OSError as e:
        print("Failed to read from DHT11 sensor:", e)
        return None, None

def mqtt_callback(topic, msg):
    """
    Callback function that is called when a subscribed MQTT message is received.

    :param topic: Topic on which the message was received
    :param msg: The message payload
    """
    try:
        topic_str = topic.decode()
        msg_str = msg.decode()
        print("Received message: '{}' on topic: '{}'".format(msg_str, topic_str))
    except UnicodeDecodeError:
        print("Received non-decodable message on topic:", topic)
        return

    if msg == b"send_update":
        publish_update()
    elif msg == b"start_top_fan":
        set_fan_speed(100, "top")
    elif msg == b"stop_top_fan":
        set_fan_speed(0, "top")
    elif msg == b"start_bottom_fan":
        set_fan_speed(100, "bottom")
    elif msg == b"stop_bottom_fan":
        set_fan_speed(0, "bottom")
    elif msg == b"reset":
        print("Reset command received. Restarting...")
        reset()
    elif msg_str.startswith("top_fan_speed_"):
        parse_fan_speed(msg_str, "top")
    elif msg_str.startswith("bottom_fan_speed_"):
        parse_fan_speed(msg_str, "bottom")

def parse_fan_speed(message, fan_position):
    """
    Parses the fan speed percentage from the message and sets the fan speed.

    :param message: The MQTT message containing the speed command
    :param fan_position: 'top' or 'bottom' indicating which fan to control
    """
    try:
        # Expecting message format: "top_fan_speed_50" or "bottom_fan_speed_75"
        parts = message.split("_")
        speed_percent = int(parts[-1])
        set_fan_speed(speed_percent, fan_position)
    except (IndexError, ValueError):
        print("Invalid {} fan speed value received.".format(fan_position))

def publish_update(send=True):
    """
    Publishes sensor data to the MQTT broker.

    :param send: Boolean indicating whether to send the MQTT message
    """
    moisture = 0.0  # Placeholder for moisture sensor reading
    temperature_ds = 0.0  # Placeholder for DS18B20 sensor reading

    temperature_dht, humidity = read_dht11_sensor()

    # If you have moisture and DS18B20 sensors, implement their readings here
    # Example:
    # moisture = read_moisture_sensor()
    # temperature_ds = read_ds18b20_sensor()

    try:
        # Prepare sensor data with fallback for None values
        temp_dht_str = "{0:.2f}".format(temperature_dht) if temperature_dht is not None else "N/A"
        humidity_str = "{0:.2f}".format(humidity) if humidity is not None else "N/A"

        msg = "{0:.2f}|{1:.2f}|{2}|{3}".format(moisture, temperature_ds, temp_dht_str, humidity_str)
        if send:
            client.publish(TOPIC_PUB, msg.encode())  # Publish the MQTT message
        print("Moisture: {0:.2f}, Soil Temp: {1:.2f}, Ambient Temp: {2}, Humidity: {3}".format(
            moisture, temperature_ds, temp_dht_str, humidity_str))
    except Exception as e:
        print("An error occurred while publishing update:", e)
        reset()

def connect_mqtt():
    """
    Connects to the MQTT broker with reconnection attempts.

    :return: Connected MQTTClient instance
    """
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

# Initialize MQTT Client
client = connect_mqtt()

try:
    if not TEST_MODE:
        while True:
            publish_update()
            # Sleep loop with message checking
            elapsed_sleep_time = 0
            while elapsed_sleep_time < TOTAL_SLEEP_TIME:
                client.check_msg()  # Non-blocking check for incoming messages
                sleep(SLEEP_INTERVAL)
                elapsed_sleep_time += SLEEP_INTERVAL
    else:
        # Test Mode: Publish updates without sending MQTT messages
        while True:
            publish_update(send=False)
            client.check_msg()  # Optional: Uncomment to handle incoming messages in test mode
            sleep(2)
except Exception as e:
    print("An unexpected error occurred in the main loop:", e)
    reset()

