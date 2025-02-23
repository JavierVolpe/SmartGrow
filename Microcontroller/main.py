from umqttsimple import MQTTClient
from machine import Pin, reset, ADC, PWM
# from adc_sub import ADC_substitute
from time import sleep
import utime
import esp32
import dht
import onewire, ds18x20

# Pins
adc_pin = 34  # Use GPIO 34 for ADC
ds_pin = Pin(4)  # Use GPIO 4 for DS18B20
dht_pin = Pin(5)  # Use GPIO 5 for DHT22
fan_pin = Pin(13, Pin.OUT)  # Use GPIO 13 for fan control
fan_pwm_pin = 14      # Use GPIO 14 for fan PWM control

# Config
test_mode = False # If True, then it will sleep for 5 seconds instead of 30 minutes
sleep_time = 1800 if not test_mode else 5  # Sleep time in seconds (30 minutes)

# MQTT
mqtt_server = "192.168.87.2"
topic_pub = b"javier/growdata"
topic_sub = b"javier/growcontrol"

# Soil Moisture Sensor Setup
adc = ADC(Pin(adc_pin))
adc.atten(ADC.ATTN_11DB)  # For reading up to 3.6V
adc.width(ADC.WIDTH_12BIT)  # 12-bit resolution (0-4095)


# DS18B20 Temperature Sensor Setup
ds_sensor = ds18x20.DS18X20(onewire.OneWire(ds_pin))
roms = ds_sensor.scan()  # Find DS18B20 devices

# DHT22 Sensor Setup (Temperature and Humidity)
dht_sensor = dht.DHT22(dht_pin)

# Moisture threshold values (adjustable)
DRY_SOIL = 720  # ADC value in dry soil
WET_SOIL = 276  # ADC value in wet soil

# Sleep interval and total sleep time
SLEEP_INTERVAL = 1  # seconds
TOTAL_SLEEP_TIME = 1800  # 30 minutes

# Fan PWM Setup
fan_pwm = PWM(Pin(fan_pwm_pin), freq=25000)  # 25kHz PWM frequency
fan_speed = 0  # Initial fan speed (0-1023)

def set_fan_speed(speed_percent):
    global fan_speed
    if 0 <= speed_percent <= 100:
        duty_cycle = int((speed_percent / 100) * 1023)
        fan_pwm.duty(duty_cycle)
        fan_speed = speed_percent
        print(f"Fan speed set to {speed_percent}%")
    else:
        print("Invalid fan speed percentage. Must be between 0 and 100.")

# Function to read temperature from DS18B20
def read_ds18b20():
    ds_sensor.convert_temp()
    utime.sleep_ms(750)  # MicroPython specific sleep
    for rom in roms:
        return ds_sensor.read_temp(rom)

# Function to read temperature and humidity from DHT22
def read_dht22():
    try:
        dht_sensor.measure()
        temp = dht_sensor.temperature()
        humidity = int(dht_sensor.humidity())
        return temp, humidity
    except OSError as e:
        print("Failed to read from DHT22 sensor:", e)
        return None, None

# Constants (Adjust these based on your sensor's calibration)
DRY_SOIL = 800        # ADC value corresponding to dry soil
WET_SOIL = 300        # ADC value corresponding to wet soil
NUM_SAMPLES = 50      # Number of samples to average

# Import necessary modules
import time

# Assuming 'adc' is your ADC object, initialized elsewhere
# from your_adc_library import adc  # Uncomment and modify as needed

def read_soil_moisture(return_percentage=False):
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
        #print(f"Sample {i+1}: Raw ADC value = {analog_value}")  # Debug: Print each sample
        total += analog_value
        # Optional: Add a small delay between samples to stabilize readings
        # time.sleep(0.01)  # 10ms delay

    average_analog = total / NUM_SAMPLES
    print(f"Averaged ADC value: {average_analog}")  # Debug: Print averaged value

    if return_percentage:
        # Clamp the averaged value within the expected range
        if average_analog > DRY_SOIL:
            average_analog = DRY_SOIL
        elif average_analog < WET_SOIL:
            average_analog = WET_SOIL

        # Scale the averaged ADC value to a percentage
        moisture_percent = ((DRY_SOIL - average_analog) / (DRY_SOIL - WET_SOIL)) * 100
        moisture_percent = round(moisture_percent, 2)  # Round to 2 decimal places

        print(f"Soil Moisture: {moisture_percent}%")  # Debug: Print moisture percentage
        return moisture_percent
    else:
        return average_analog  # Return the raw averaged ADC value




def mqtt_callback(topic, msg):
    print("Received message:", msg.decode(), "on topic:", topic.decode())
    # Decode the message and trigger a function
    if msg == b"send_update":
        publish_update()
    elif msg == b"start_fan":
        set_fan_speed(100)
    elif msg == b"stop_fan":
        set_fan_speed(0)
    elif msg == b"reset":
        reset()
    elif msg.decode().startswith("fan_speed_"):
        try:
            speed_percent = int(msg.decode().split("_")[2])
            set_fan_speed(speed_percent)
        except ValueError:
            print("Invalid fan speed value received.")

def publish_update(send=True):
    moisture = read_soil_moisture()
    temperature_ds = read_ds18b20()
    temperature_dht, humidity = read_dht22()
    try:   
        msg = f"{moisture:.2f}|{temperature_ds:.2f}|{temperature_dht:.2f}|{humidity:.2f}"
        if send:
            client.publish(topic_pub, msg.encode())  # Ensure message is encoded for MQTT
        print(f"Moisture: {moisture:.2f}, Soil temp: {temperature_ds:.2f}, Temp amb.: {temperature_dht}, Humidity amb.: {humidity}")
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
    sleep(5)
    reset()

if not test_mode:
    while True:
        publish_update()
        # Sleep for the specified interval
        elapsed_sleep_time = 0
        while elapsed_sleep_time < TOTAL_SLEEP_TIME:
            client.check_msg()  # Check for incoming messages
            sleep(SLEEP_INTERVAL)
            elapsed_sleep_time += SLEEP_INTERVAL
else:
    while True:
        publish_update(send=False)
        sleep(2)
        #client.check_msg()




