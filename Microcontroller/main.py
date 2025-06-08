from umqttsimple import MQTTClient
from machine import Pin, reset, ADC, PWM
import time
import esp32
import dht
import onewire
import ds18x20
import urequests  # For OTA updates

# ------------------------------
# Custom Logging Setup
# ------------------------------
orig_print = print
log_buffer = []

def my_print(*args, **kwargs):
    message = " ".join(str(arg) for arg in args)
    log_buffer.append(message)
    if len(log_buffer) > 50:
        log_buffer.pop(0)
    orig_print(*args, **kwargs)

# Override the global print function so all prints get logged
print = my_print

# ------------------------------
# Configuration & Constants
# ------------------------------
ADC_PIN = 34             # Use GPIO 34 for ADC
DS_PIN = 4               # Use GPIO 4 for DS18B20
DHT_PIN = 5              # Use GPIO 5 for DHT22
FAN_PWM_PIN = 14         # Use GPIO 14 for fan PWM control
EXTRA_FAN_PIN_NUM = 16   # Use GPIO 16 for extra fan control
PUMP_PIN_NUM   = 32      # Use GPIO 32 for pump control

MQTT_SERVER = "vm.dk"
MQTT_USERNAME = "growtent"
MQTT_PASSWORD = ""
TOPIC_PUB = b"grow/data"
TOPIC_SUB = b"grow/control"
TOPIC_STATUS = b"grow/status"
DRY_SOIL = 720  # ADC value in dry soil
WET_SOIL = 276  # ADC value in wet soil
NUM_SAMPLES = 50
RETURN_PERCENTAGE = True

# OTA update default URL (change to your update server URL)
OTA_DEFAULT_URL = "http://192.168.87.2/ota/main.py"

# Mode configuration
TEST_MODE = False
if TEST_MODE:
    SLEEP_INTERVAL = 2       # seconds
    TOTAL_SLEEP_TIME = 2     # seconds
    SEND_UPDATE = False      # Disable MQTT update in test mode
else:
    SLEEP_INTERVAL = 1       # seconds
    TOTAL_SLEEP_TIME = 1800  # 30 minutes in seconds
    SEND_UPDATE = True

# ------------------------------
# Sensor and Actuator Setup
# ------------------------------

# Soil Moisture Sensor (ADC)
adc = ADC(Pin(ADC_PIN))
adc.atten(ADC.ATTN_11DB)  # For reading up to ~3.6V
adc.width(ADC.WIDTH_12BIT)  # 12-bit resolution

# DS18B20 Temperature Sensor Setup
ds_sensor = ds18x20.DS18X20(onewire.OneWire(Pin(DS_PIN)))
roms = ds_sensor.scan()  # Discover DS18B20 devices

# DHT22 Sensor Setup
dht_sensor = dht.DHT22(Pin(DHT_PIN))

# Fan PWM Setup
fan_pwm = PWM(Pin(FAN_PWM_PIN), freq=25000)  # 25kHz PWM frequency
fan_speed = 100  # Initial fan speed (0-100%)

# Extra Fan Setup
try:
    extra_fan = Pin(EXTRA_FAN_PIN_NUM, Pin.OUT)
    print("Extra fan initialized successfully.")
except Exception as e:
    print("Extra fan initialization failed:", e)
    
# Pump Setup
try:
    pump = Pin(PUMP_PIN_NUM, Pin.OUT)
    print("Pump initialized successfully.")
except Exception as e:
    print("Pump initialization failed:", e)

# ------------------------------
# Sensor & Actuator Functions
# ------------------------------

def set_fan_speed(speed_percent):
    """Set the main fan speed as a percentage."""
    global fan_speed
    if 0 <= speed_percent <= 100:
        duty_cycle = int((speed_percent / 100) * 1023)
        fan_pwm.duty(duty_cycle)
        fan_speed = speed_percent
        print(f"Fan speed set to {speed_percent}%")
    else:
        print("Invalid fan speed percentage. Must be between 0 and 100.")

def read_ds18b20():
    """Read temperature from DS18B20 sensor by averaging multiple readings."""
    readings = []
    for _ in range(5):  # Take 5 readings
        ds_sensor.convert_temp()
        time.sleep_ms(750)
        for rom in roms:
            temp = ds_sensor.read_temp(rom)
            if temp is not None:
                readings.append(temp)
        time.sleep(0.1)  # Small delay between readings
    if readings:
        average_temp = sum(readings) / len(readings)
        print(f"DS18B20 Average Temperature: {average_temp:.2f}°C")
        return average_temp
    else:
        print("Failed to read from DS18B20 sensor.")
        return None

def read_dht22():
    """Read temperature and humidity from DHT22 sensor by averaging multiple readings."""
    temp_readings = []
    humidity_readings = []
    for _ in range(5):  # Take 5 readings
        try:
            dht_sensor.measure()
            temp_readings.append(dht_sensor.temperature())
            humidity_readings.append(dht_sensor.humidity())
        except OSError as e:
            print("Failed to read from DHT22 sensor:", e)
        time.sleep(0.2)  # Small delay between readings
    if temp_readings and humidity_readings:
        avg_temp = sum(temp_readings) / len(temp_readings)
        avg_humidity = sum(humidity_readings) / len(humidity_readings)
        print(f"DHT22 Average Temperature: {avg_temp:.2f}°C, Average Humidity: {avg_humidity:.2f}%")
        return avg_temp, avg_humidity
    else:
        print("Failed to read from DHT22 sensor.")
        return None, None

def read_soil_moisture(return_percentage=True):
    """
    Reads soil moisture by averaging multiple ADC samples.
    
    Args:
        return_percentage (bool): If True, returns moisture as a percentage.
                                   If False, returns the raw averaged ADC value.
    
    Returns:
        float: Moisture percentage or raw ADC value.
    """
    total = 0
    for _ in range(NUM_SAMPLES):
        total += adc.read()
        time.sleep(0.01)  # 10ms delay between samples
    average_adc = total / NUM_SAMPLES
    print(f"Averaged ADC value: {average_adc:.2f}")
    
    if return_percentage:
        # Scale the ADC value to a moisture percentage
        moisture_percent = ((DRY_SOIL - average_adc) / (DRY_SOIL - WET_SOIL)) * 100
        moisture_percent = max(0, min(100, moisture_percent))
        moisture_percent = round(moisture_percent, 2)
        print(f"Soil Moisture: {moisture_percent}%")
        return moisture_percent
    else:
        return average_adc

# Store the previous value globally
previous_moisture = None

def filter_adc_value(current_value, threshold=100):
    global previous_moisture
    if previous_moisture is None:
        previous_moisture = current_value
        return current_value

    # If jump is too large, discard and return previous
    if abs(current_value - previous_moisture) > threshold:
        return previous_moisture
    else:
        previous_moisture = current_value
        return current_value



# ------------------------------
# OTA Update Function
# ------------------------------

def perform_ota_update(url):
    """Perform OTA update by downloading new code from the given URL and writing it to main.py."""
    try:
        print("Starting OTA update from", url)
        response = urequests.get(url)
        if response.status_code == 200:
            new_code = response.text

            # Check if the new code compiles without syntax errors
            try:
                compile(new_code, "main.py", "exec")
            except Exception as e:
                print("New code failed to compile:", e)
                client.publish(TOPIC_PUB, "OTA update failed. Syntax error in new code.".encode())
                response.close()
                return

            with open("main.py", "w") as f:
                f.write(new_code)
            print("OTA update successful. Rebooting now...")
            client.publish(TOPIC_PUB, "OTA update successful. Rebooting...".encode())
            time.sleep(2)
            reset()
        else:
            print("Failed to download update. HTTP Status:", response.status_code)
            client.publish(TOPIC_PUB, "OTA update failed. HTTP error.".encode())
        response.close()
    except Exception as e:
        print("OTA update failed with error:", e)
        client.publish(TOPIC_PUB, "OTA update failed. Exception occurred.".encode())

# ------------------------------
# MQTT Functions
# ------------------------------

def mqtt_callback(topic, msg):
    """Handle incoming MQTT messages."""
    decoded_msg = msg.decode()
    topic_str = topic.decode()
    print(f"Received message: {decoded_msg} on topic: {topic_str}")

    try:
        if decoded_msg == "send_update":
            publish_update()
            feedback = "Update sent."
        elif decoded_msg == "start_fan":
            set_fan_speed(100)
            feedback = "Fan started at speed 100."
        elif decoded_msg == "stop_fan":
            set_fan_speed(0)
            feedback = "Fan stopped."
        elif decoded_msg == "start_bottom_fan":
            extra_fan.on()
            feedback = "Bottom fan started."
        elif decoded_msg == "stop_bottom_fan":
            extra_fan.off()
            feedback = "Bottom fan stopped."
        elif decoded_msg == "start_pump":
            pump.on()
            print("Starting pump")
            feedback = "Pump started."
        elif decoded_msg == "stop_pump":
            pump.off()
            print("Stopping pump")
            feedback = "Pump stopped."
        elif decoded_msg == "reset":
            feedback = "Resetting"
            client.publish(TOPIC_STATUS, feedback.encode())
            print(feedback)
            time.sleep(1)
            reset()
            return
        elif decoded_msg.startswith("fan_speed_"):
            try:
                speed_val = int(decoded_msg.split("_")[2])
                set_fan_speed(speed_val)
                feedback = f"Fan speed set to {speed_val}."
            except (IndexError, ValueError):
                print("Invalid fan speed command received.")
                return
        elif decoded_msg.startswith("ota_update"):
            # Expecting command format: "ota_update" or "ota_update|<url>"
            parts = decoded_msg.split("|")
            update_url = parts[1] if len(parts) > 1 else OTA_DEFAULT_URL
            perform_ota_update(update_url)
            return
        elif decoded_msg == "get_log":
            log_text = "\n".join(log_buffer)
            client.publish(TOPIC_STATUS, log_text.encode())
            print("Sent last 50 log lines.")
            return
        else:
            print("Unknown command received.")
            return
    except Exception as e:
        feedback = f"Error executing command: {e}"

    client.publish(TOPIC_STATUS, feedback.encode())
    print(feedback)

def publish_update(send=True):
    """Publish sensor data to the MQTT server."""
    # Read sensors (moisture as percentage now)
    moisture = filter_adc_value(read_soil_moisture(return_percentage=RETURN_PERCENTAGE))
    temperature_ds = read_ds18b20()
    temperature_dht, humidity = read_dht22()
    
    if temperature_dht > 30:
        extra_fan.on()
        print("It was too warm, so the fan is on now")
        
    # If any sensor reading failed, skip the update
    if None in (moisture, temperature_ds, temperature_dht, humidity):
        print("Sensor read error. Skipping MQTT update.")
        return
    
    msg = f"{moisture:.2f}|{temperature_ds:.2f}|{temperature_dht:.2f}|{humidity:.2f}"
    
    if send:
        try:
            client.publish(TOPIC_PUB, msg.encode())
            print(f"Publishing update: {msg}")
        except Exception as e:
            print("Error publishing MQTT message:", e)
            reset()
    else:
        print(f"NOT Publishing update: {msg}")

def sleep_and_check_messages(total_sleep_time, sleep_interval):
    """Sleep in intervals while checking for incoming MQTT messages."""
    elapsed = 0
    while elapsed < total_sleep_time:
        client.check_msg()
        time.sleep(sleep_interval)
        elapsed += sleep_interval

# ------------------------------
# Main Loop
# ------------------------------

from machine import WDT

# Initialize the watchdog timer with a 60-second timeout
wdt = WDT(timeout=1800000)  # 600 seconds

def main():
    global client
    while True:
        try:
            client = MQTTClient(
                client_id="0001",
                server=MQTT_SERVER,
                user=MQTT_USERNAME,
                password=MQTT_PASSWORD
            )
            client.set_callback(mqtt_callback)


            client.connect()
            client.subscribe(TOPIC_SUB)
            print("Connected to MQTT broker and subscribed to topic.")
            break  # Exit loop once connected successfully
        except OSError as e:
            print("Error connecting to MQTT broker:", e)
            time.sleep(5)  # Wait before retrying
    while True:
        # Feed the watchdog timer in each cycle to avoid reset if the loop is healthy.
        wdt.feed()
        try:
            publish_update(send=SEND_UPDATE)
            sleep_and_check_messages(TOTAL_SLEEP_TIME, SLEEP_INTERVAL)
        except Exception as e:
            print("Exception in main loop:", e)
            # Optionally, add reconnection logic here
            try:
                client.disconnect()
            except:
                pass
            time.sleep(2)
            reset()  # Reset device if an unexpected exception occurs

if __name__ == "__main__":
    main()

