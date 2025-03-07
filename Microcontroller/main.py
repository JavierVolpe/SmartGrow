from umqttsimple import MQTTClient
from machine import Pin, reset, ADC, PWM
import time
import esp32
import dht
import onewire
import ds18x20

# ------------------------------
# Configuration & Constants
# ------------------------------
ADC_PIN = 34             # Use GPIO 34 for ADC
DS_PIN = 4               # Use GPIO 4 for DS18B20
DHT_PIN = 5              # Use GPIO 5 for DHT22
FAN_PWM_PIN = 14         # Use GPIO 14 for fan PWM control
EXTRA_FAN_PIN_NUM = 16   # Use GPIO 16 for extra fan control

MQTT_SERVER = "192.168.87.2"
TOPIC_PUB = b"javier/growdata"
TOPIC_SUB = b"javier/growcontrol"

DRY_SOIL = 800  # ADC value in dry soil
WET_SOIL = 300  # ADC value in wet soil
NUM_SAMPLES = 50
RETURN_PERCENTAGE = False

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

# ------------------------------
# MQTT Functions
# ------------------------------

def mqtt_callback(topic, msg):
    """Handle incoming MQTT messages."""
    decoded_msg = msg.decode()
    print(f"Received message: {decoded_msg} on topic: {topic.decode()}")
    if decoded_msg == "send_update":
        publish_update()
    elif decoded_msg == "start_fan":
        set_fan_speed(100)
    elif decoded_msg == "stop_fan":
        set_fan_speed(0)
    elif decoded_msg == "start_bottom_fan":
        extra_fan.on()
    elif decoded_msg == "stop_bottom_fan":
        extra_fan.off()
    elif decoded_msg == "reset":
        reset()
    elif decoded_msg.startswith("fan_speed_"):
        try:
            speed_val = int(decoded_msg.split("_")[2])
            set_fan_speed(speed_val)
        except (IndexError, ValueError):
            print("Invalid fan speed command received.")

def publish_update(send=True):
    """Publish sensor data to the MQTT server."""
    # Read sensors (moisture as percentage now)
    moisture = read_soil_moisture(return_percentage=RETURN_PERCENTAGE)
    temperature_ds = read_ds18b20()
    temperature_dht, humidity = read_dht22()
    
    if temperature_dht > 30:
        extra_fan.on()
        print(f"It was too warm({current_temp[0]}), so the fan is on now")
        
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

def main():
    global client
    client = MQTTClient("0001", MQTT_SERVER)
    try:
        client.set_callback(mqtt_callback)
        client.connect()
        client.subscribe(TOPIC_SUB)
        print("Connected to MQTT broker and subscribed to topic.")
    except OSError as e:
        print("Error connecting to MQTT broker:", e)
        time.sleep(5)
        reset()
    
    while True:

        publish_update(send=SEND_UPDATE)
        sleep_and_check_messages(TOTAL_SLEEP_TIME, SLEEP_INTERVAL)
        



if __name__ == "__main__":
    main()



