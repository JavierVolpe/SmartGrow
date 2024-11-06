from umqttsimple import MQTTClient
from machine import Pin, reset, deepsleep, ADC
# from adc_sub import ADC_substitute
from time import sleep
import utime
import esp32
import ntptime
import dht
import onewire, ds18x20

# Pins
adc_pin = 34  # Use GPIO 34 for ADC
ds_pin = Pin(4)  # Use GPIO 4 for DS18B20
dht_pin = Pin(5)  # Use GPIO 5 for DHT22
# pump_pin = Pin(12, Pin.OUT)  # Use GPIO 12 for pump control

# Config
deepsleep_activated = False
deepsleep_tid = 21600000

# MQTT
mqtt_server = "192.168.87.2"
topic_pub = b"javier/growdata"

# Soil Moisture Sensor Setup
adc = ADC(Pin(adc_pin))
adc.atten(ADC.ATTN_11DB)  # For reading up to 3.3V
adc.width(ADC.WIDTH_10BIT)  # 10-bit resolution (0-1023)

# DS18B20 Temperature Sensor Setup
ds_sensor = ds18x20.DS18X20(onewire.OneWire(ds_pin))
roms = ds_sensor.scan()  # Find DS18B20 devices

# DHT22 Sensor Setup (Temperature and Humidity)
dht_sensor = dht.DHT22(dht_pin)

# Pump Setup
# pump_pin.value(0)  # Ensure the pump is off initially

# Moisture threshold values (adjustable)
MOISTURE_MIN = 720  # ADC value in dry air
MOISTURE_MAX = 276  # ADC value in fully wet condition

# def update_time(retries=5):
#     try:
#         ntptime.settime()
#     except Exception as e:
#         if retries > 0:
#             update_time(retries - 1)
#         else:
#             print("Failed to update time after multiple retries:", e)

# MQTT client setup
client = MQTTClient("0001", mqtt_server)

try:
    client.connect() 
except OSError as e:
    print("Problem connecting to MQTT broker. Restarting in 10 seconds...")
    print(e)
    sleep(5)
    reset()

# def get_battery_percentage(): 
#     adc_at_0_percent = 1509
#     adc_at_100_percent = 2165
#     min_battery_voltage = 3.0
#     max_battery_voltage = 4.2
#     adc_value = adc.read()
# 
#     voltage_range_per_unit_adc = (max_battery_voltage - min_battery_voltage) / (
#         adc_at_100_percent - adc_at_0_percent)
# 
#     voltage = (adc_value - adc_at_0_percent) * voltage_range_per_unit_adc + min_battery_voltage
# 
#     battery_percentage = ((voltage - min_battery_voltage) / (max_battery_voltage - min_battery_voltage)) * 100
#     battery_percentage = round(battery_percentage)
#     if battery_percentage < 0:
#         battery_percentage = 0
#     elif battery_percentage > 100:
#         battery_percentage = 100
#     return battery_percentage

def send_update(moisture, temperature_ds, temperature_dht, humidity):
    # Format the values to two decimal places
    msg = f"{moisture:.2f}|{temperature_ds:.2f}|{temperature_dht:.2f}|{humidity:.2f}"
    client.publish(topic_pub, msg.encode())  # Ensure message is encoded for MQTT


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


while True:
    # current_time calculation and adjustment
#     current_time = utime.time()
#     current_time = utime.localtime(current_time + gmt_adjust) 
#     date_time_str = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}.000".format(
#         current_time[0],    # Year (YYYY)
#         current_time[1],    # Month (MM)
#         current_time[2],    # Day (DD)
#         current_time[3],    # Hour (HH)
#         current_time[4],    # Minute (MM)
#         current_time[5]     # Second (SS)
#     )
# 
#     sleep(1)

    # Read soil moisture
    moisture = read_soil_moisture()
    print("Soil moisture: {:.2f}%".format(moisture))

    # Read temperature from DS18B20
    if roms:
        temperature_ds = read_ds18b20()
        print("Temperature (DS18B20): {:.2f}°C".format(temperature_ds))
    else:
        temperature_ds = 0

    # Read temperature and humidity from DHT22
    temperature_dht, humidity = read_dht22()

    print(f"Moisture: {moisture:.2f}, Soil temp: {temperature_ds:.2f}, Temp amb.: {temperature_dht}, Humidity amb.: {humidity}")

    try:
        # Send update to MQTT broker
        send_update(moisture, temperature_ds, temperature_dht, int(humidity))
        print("Sent OK\n Sleeping 30 min.\n")
        sleep(1800)
    except OSError as e:
        print("Failed to send data to MQTT broker. Resetting in 10 sec...")
        sleep(10)
        reset()
    except Exception as e:
        print("An error occurred:", e)
        sleep(10)
        reset()
    except KeyboardInterrupt:
        print("Keyboard interrupt")
        break

