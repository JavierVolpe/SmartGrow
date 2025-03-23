from machine import Pin, PWM
from time import sleep
from umqttsimple import MQTTClient
import time
import dht
import urequests
from machine import reset

# ------------------------------
# Configuration
# ------------------------------
MQTT_SERVER = "192.168.87.2"
TOPIC_PUB = b"dry/data"
TOPIC_SUB = b"dry/control"
TOPIC_STATUS = b"dry/status"
OTA_DEFAULT_URL = "http://grow.javiervolpe.dk/static/dry.py"

FAN_PWM_PIN = 25  # GPIO25 for fan PWM
DHT_PIN = 5       # GPIO5 for DHT11

# ------------------------------
# Setup
# ------------------------------

# Fan PWM setup
fan_pwm = PWM(Pin(FAN_PWM_PIN), freq=25000)
fan_pwm.duty(60)

def set_fan_speed(percent):
    """Set fan speed as a percentage (0-100%)"""
    duty = int((percent / 100) * 1023)
    fan_pwm.duty(duty)
    print(f"Fan speed set to {percent}%")

# DHT11 sensor setup
dht_sensor = dht.DHT11(Pin(DHT_PIN))

def read_DHT11():
    """Read temperature and humidity from DHT11"""
    try:
        dht_sensor.measure()
        temp = dht_sensor.temperature()
        humidity = dht_sensor.humidity()
        print(f"DHT11: {temp:.2f}°C, {humidity:.2f}%")
        return temp, humidity
    except OSError as e:
        print("DHT11 read error:", e)
        return None, None

# OTA update
def perform_ota_update(url):
    try:
        print("Starting OTA update from", url)
        response = urequests.get(url)
        if response.status_code == 200:
            new_code = response.text
            try:
                compile(new_code, "main.py", "exec")
            except Exception as e:
                print("OTA failed: syntax error:", e)
                client.publish(TOPIC_PUB, "OTA failed: syntax error.".encode())
                response.close()
                return
            with open("main.py", "w") as f:
                f.write(new_code)
            print("OTA successful. Rebooting...")
            client.publish(TOPIC_PUB, "OTA successful. Rebooting...".encode())
            time.sleep(2)
            reset()
        else:
            print("HTTP error:", response.status_code)
            client.publish(TOPIC_PUB, "OTA failed: HTTP error.".encode())
        response.close()
    except Exception as e:
        print("OTA exception:", e)
        client.publish(TOPIC_PUB, "OTA failed: exception occurred.".encode())

# MQTT handling
def mqtt_callback(topic, msg):
    decoded_msg = msg.decode()
    topic_str = topic.decode()
    print(f"MQTT message on {topic_str}: {decoded_msg}")
    
    if decoded_msg == "send_update":
        publish_update()
    elif decoded_msg == "stop_fan":
        set_fan_speed(0)
    elif decoded_msg == "start_fan":
        set_fan_speed(100)
    elif decoded_msg.startswith("fan_speed_"):
        try:
            speed_val = int(decoded_msg.split("_")[2])
            set_fan_speed(speed_val)
        except:
            print("Invalid speed command")
    elif decoded_msg.startswith("ota_update"):
        parts = decoded_msg.split("|")
        url = parts[1] if len(parts) > 1 else OTA_DEFAULT_URL
        perform_ota_update(url)

def publish_update():
    temp, humidity = read_DHT11()
    temp = round(temp,1)
    humidity = round (humidity, 1)
    if temp is None or humidity is None:
        print("Sensor error, skipping MQTT publish")
        return
    msg = f"{temp:.1f}|{humidity:.1f}"
    try:
        client.publish(TOPIC_PUB, msg.encode())
        print("Published:", msg)
    except Exception as e:
        print("MQTT publish error:", e)
        reset()

# MQTT Connection
def mqtt_connect():
    global client
    while True:
        try:
            client = MQTTClient("fan_node", MQTT_SERVER)
            client.set_callback(mqtt_callback)
            client.connect()
            client.subscribe(TOPIC_SUB)
            print("Connected to MQTT broker")
            return
        except Exception as e:
            print("MQTT connection failed:", e)
            time.sleep(5)

# Main Loop
def main():
    mqtt_connect()
    while True:
        try:
            publish_update()
            for _ in range(60):  # 60 seconds sleep, check messages each second
                client.check_msg()
                time.sleep(1)
        except Exception as e:
            print("Main loop error:", e)
            try:
                client.disconnect()
            except:
                pass
            time.sleep(2)
            reset()

if __name__ == "__main__":
    main()

