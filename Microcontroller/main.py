from umqttsimple import MQTTClient
from machine import Pin, reset, ADC
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
# pump_pin = Pin(12, Pin.OUT)  # Use GPIO 12 for pump control

# Config
test_mode = False # If True, then it will sleep for 5 seconds instead of 30 minutes
sleep_time = 1800 if not test_mode else 5  # Sleep time in seconds (30 minutes)

# MQTT
mqtt_server = "192.168.87.2"
topic_pub = b"javier/growdata"
topic_sub = b"javier/growcontrol"

# Soil Moisture Sensor Setup
adc = ADC(Pin(adc_pin))
adc.atten(ADC.ATTN_11DB)  # For reading up to 3.3V
adc.width(ADC.WIDTH_10BIT)  # 10-bit resolution (0-1023)

# DS18B20 Temperature Sensor Setup
ds_sensor = ds18x20.DS18X20(onewire.OneWire(ds_pin))
roms = ds_sensor.scan()  # Find DS18B20 devices

# DHT22 Sensor Setup (Temperature and Humidity)
dht_sensor = dht.DHT22(dht_pin)

# Moisture threshold values (adjustable)
MOISTURE_MIN = 720  # ADC value in dry air
MOISTURE_MAX = 276  # ADC value in fully wet condition

SLEEP_INTERVAL = 1  # seconds
TOTAL_SLEEP_TIME = 1800  # 30 minutes



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

# Function to read soil moisture
def read_soil_moisture():
    analog_value = adc.read()  # Read the raw ADC value

    # Ensure the value is within the correct bounds
    if analog_value < MOISTURE_MIN:
        analog_value = MOISTURE_MIN
    elif analog_value > MOISTURE_MAX:
        analog_value = MOISTURE_MAX

    # Properly scale the raw ADC value to a percentage
    moisture_percent = ((MOISTURE_MAX - analog_value) / (MOISTURE_MAX - MOISTURE_MIN)) * 100

    return round(analog_value, 2)  # Round to 2 decimal places for better precision

def mqtt_callback(topic, msg):
    print("Received message:", msg, "on topic:", topic)
    # Decode the message and trigger a function
    if msg == b"send_update":
        publish_update()
    elif msg == b"restart":
        reset()
    # Add more conditions as needed

def publish_update():
    moisture = read_soil_moisture()
    temperature_ds = read_ds18b20()
    temperature_dht, humidity = read_dht22()
    try:   
        msg = f"{moisture:.2f}|{temperature_ds:.2f}|{temperature_dht:.2f}|{humidity:.2f}"
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

while True:
    publish_update()
    # Sleep for the specified interval
    elapsed_sleep_time = 0
    while elapsed_sleep_time < TOTAL_SLEEP_TIME:
        client.check_msg()  # Check for incoming messages
        sleep(SLEEP_INTERVAL)
        elapsed_sleep_time += SLEEP_INTERVAL

