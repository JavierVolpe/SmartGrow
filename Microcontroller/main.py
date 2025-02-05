from umqttsimple import MQTTClient
from machine import Pin, reset, ADC, PWM
import time
import esp32
import dht
import onewire
import ds18x20

# Pins
adc_pin = 34  # Use GPIO 34 for ADC
ds_pin = Pin(4)  # Use GPIO 4 for DS18B20
dht_pin = Pin(5)  # Use GPIO 5 for DHT22
# fan_pin = Pin(13, Pin.OUT)  # Use GPIO 13 for fan control
fan_pwm_pin = 14      # Use GPIO 14 for fan PWM control
# bottom_fan_pin = Pin(15, Pin.OUT)  # Use GPIO 15 for bottom fan control
bottom_fan_pwm_pin = 16  # Use GPIO 16 for bottom fan PWM control
EXTRA_FAN_PIN_NUM = 16  # GPIO 16 for fan control

# Config
test_mode = True  # If True, it will sleep for 5 seconds instead of 30 minutes

# MQTT
mqtt_server = "192.168.87.2"
topic_pub = b"javier/growdata"
topic_sub = b"javier/growcontrol"

# Moisture threshold values (adjustable)
DRY_SOIL = 800  # ADC value in dry soil
WET_SOIL = 300  # ADC value in wet soil

# Number of samples to average
NUM_SAMPLES = 50

# Sleep interval and total sleep time
if test_mode:
    SLEEP_INTERVAL = 2       # In test mode, sleep for 2 seconds
    TOTAL_SLEEP_TIME = 2     # Total sleep time is 2 seconds
    send_update = False      # Do not send updates over MQTT in test mode
else:
    SLEEP_INTERVAL = 1       # Sleep interval for checking messages
    TOTAL_SLEEP_TIME = 1800  # 30 minutes total sleep time
    send_update = True       # Send updates over MQTT

# Soil Moisture Sensor Setup
adc = ADC(Pin(adc_pin))
adc.atten(ADC.ATTN_11DB)  # For reading up to 3.6V
adc.width(ADC.WIDTH_12BIT)  # 12-bit resolution (0-4095)

# DS18B20 Temperature Sensor Setup
ds_sensor = ds18x20.DS18X20(onewire.OneWire(ds_pin))
roms = ds_sensor.scan()  # Find DS18B20 devices

# DHT22 Sensor Setup (Temperature and Humidity)
dht_sensor = dht.DHT22(dht_pin)

# Fan PWM Setup
fan_pwm = PWM(Pin(fan_pwm_pin), freq=25000)  # 25kHz PWM frequency
fan_speed = 100  # Initial fan speed (0-100%)

# Bottom Fan PWM Setup
# bottom_fan_pwm = PWM(Pin(bottom_fan_pwm_pin), freq=25000)  # 25kHz PWM frequency
# bottom_fan_speed = 0  # Initial bottom fan speed (0-100%)

try:
    fan = Pin(EXTRA_FAN_PIN_NUM, Pin.OUT)
    
    print("Fan initialized successfully.")
except Exception as e:
    print("Fan initialization failed:", e)

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

# def set_bottom_fan_speed(speed_percent):
#     """Set the bottom fan speed as a percentage."""
#     global bottom_fan_speed
#     if 0 <= speed_percent <= 100:
#         duty_cycle = int((speed_percent / 100) * 1023)
#         bottom_fan_pwm.duty(duty_cycle)
#         bottom_fan_speed = speed_percent
#         print(f"Bottom fan speed set to {speed_percent}%")
#     else:
#         print("Invalid bottom fan speed percentage. Must be between 0 and 100.")

def control_extra_fan(start=True):
    if start == True:
        fan.on()
    elif start == False:
        fan.off()

def read_ds18b20():
    """Read temperature from DS18B20 sensor, averaging multiple readings."""
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
    """Read temperature and humidity from DHT22 sensor, averaging multiple readings."""
    temp_readings = []
    humidity_readings = []
    for _ in range(5):  # Take 5 readings
        try:
            dht_sensor.measure()
            temp = dht_sensor.temperature()
            humidity = dht_sensor.humidity()
            temp_readings.append(temp)
            humidity_readings.append(humidity)
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
        float: Moisture percentage or raw ADC value based on the argument.
    """
    total = 0
    for i in range(NUM_SAMPLES):
        analog_value = adc.read()  # Read the raw ADC value
        total += analog_value
        # Optional: Add a small delay between samples to stabilize readings
        time.sleep(0.01)  # 10ms delay

    average_analog = total / NUM_SAMPLES
    print(f"Averaged ADC value: {average_analog}")  # Debug: Print averaged value

    # Clamp the averaged value within the expected range
    # if average_analog > DRY_SOIL:
    #     average_analog = DRY_SOIL
    # elif average_analog < WET_SOIL:
    #     average_analog = WET_SOIL

    if return_percentage:
        # Scale the averaged ADC value to a percentage
        moisture_percent = ((DRY_SOIL - average_analog) / (DRY_SOIL - WET_SOIL)) * 100
        moisture_percent = max(0, min(100, moisture_percent))  # Ensure percentage is between 0 and 100
        moisture_percent = round(moisture_percent, 2)  # Round to 2 decimal places

        print(f"Soil Moisture: {moisture_percent}%")  # Debug: Print moisture percentage
        return moisture_percent
    else:
        return average_analog  # Return the raw averaged ADC value

def mqtt_callback(topic, msg):
    """Handle incoming MQTT messages."""
    print("Received message:", msg.decode(), "on topic:", topic.decode())
    # Decode the message and trigger a function
    msg_decoded = msg.decode()
    if msg_decoded == "send_update":
        publish_update()
    elif msg_decoded == "start_fan":
        set_fan_speed(100)
    elif msg_decoded == "stop_fan":
        set_fan_speed(0)
    elif msg_decoded == "start_bottom_fan":
        control_extra_fan(start=True)
    elif msg_decoded == "stop_bottom_fan":
        control_extra_fan(start=False)
    elif msg_decoded == "reset":
        reset()
    elif msg_decoded.startswith("fan_speed_"):
        try:
            speed_percent = int(msg_decoded.split("_")[2])
            set_fan_speed(speed_percent)
        except ValueError:
            print("Invalid fan speed value received.")
#     elif msg_decoded.startswith("bottom_fan_speed_"):
#         try:
#             speed_percent = int(msg_decoded.split("_")[3])
#             set_bottom_fan_speed(speed_percent)
#         except ValueError:
#             print("Invalid bottom fan speed value received.")

def publish_update(send=True):
    """Publish sensor data to MQTT server."""
    moisture = read_soil_moisture(return_percentage=False)
    temperature_ds = read_ds18b20()
    #temperature_ds = 1
    temperature_dht, humidity = read_dht22()
    try:
        msg = f"{moisture:.2f}|{temperature_ds:.2f}|{temperature_dht:.2f}|{humidity:.2f}"
        if send:
            client.publish(topic_pub, msg.encode())  # Ensure message is encoded for MQTT
        print(f"Moisture: {moisture:.2f}%, Soil Temp: {temperature_ds:.2f}°C, Ambient Temp: {temperature_dht:.2f}°C, Humidity: {humidity:.2f}%")
    except Exception as e:
        print("An error occurred:", e)
        reset()

# MQTT client setup
client = MQTTClient("0001", mqtt_server)

try:
    client.connect()
    client.set_callback(mqtt_callback)
    client.subscribe(topic_sub)
except OSError as e:
    print("Problem connecting to MQTT broker. Restarting in 10 seconds...")
    print(e)
    time.sleep(5)
    reset()

# Helper function to sleep and check messages
def sleep_and_check_messages(total_sleep_time, sleep_interval):
    elapsed_sleep_time = 0
    while elapsed_sleep_time < total_sleep_time:
        client.check_msg()  # Check for incoming messages
        time.sleep(sleep_interval)
        elapsed_sleep_time += sleep_interval

# Main loop
while True:
    publish_update(send=send_update)
    sleep_and_check_messages(TOTAL_SLEEP_TIME, SLEEP_INTERVAL)



