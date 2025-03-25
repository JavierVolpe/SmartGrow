from machine import Pin, PWM, reset
from umqttsimple import MQTTClient
import time
import dht
import urequests

# ------------------------------
# Configuration
# ------------------------------
MQTT_SERVER = "192.168.87.2"
TOPIC_PUB = b"dry/data"
TOPIC_SUB = b"dry/control"
TOPIC_STATUS = b"dry/status"
OTA_DEFAULT_URL = "http://grow.javiervolpe.dk/static/dry.py"

FAN_PWM_PIN = 25     # GPIO25 for PWM
RELAY_PIN = 26       # GPIO26 for relay control
DHT_PIN = 5          # GPIO5 for DHT11

# ------------------------------
# Setup
# ------------------------------
relay = Pin(RELAY_PIN, Pin.OUT)
relay.off()  # Start with relay OFF (active LOW logic)

fan_pwm = None  # We'll create it when needed

def set_fan_speed(percent):
    global fan_pwm
    if percent <= 0:
        if fan_pwm:
            fan_pwm.deinit()
            fan_pwm = None
        relay.off()  # Relay OFF (active LOW)
        print("Fan OFF (relay and PWM)")
    else:
        if fan_pwm is None:
            fan_pwm = PWM(Pin(FAN_PWM_PIN), freq=25000)
        duty = int((percent / 100) * 1023)
        fan_pwm.duty(duty)
        relay.on()  # Relay ON (active LOW)
        print(f"Fan set to {percent}%")

# ------------------------------
# DHT11 Sensor
# ------------------------------
dht_sensor = dht.DHT11(Pin(DHT_PIN))

def read_DHT11():
    try:
        dht_sensor.measure()
        temp = dht_sensor.temperature()
        hum = dht_sensor.humidity()
        print(f"DHT11: {temp:.1f}°C, {hum:.1f}%")
        return temp, hum
    except OSError as e:
        print("DHT11 read error:", e)
        return None, None

# ------------------------------
# OTA Update
# ------------------------------
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
                client.publish(TOPIC_STATUS, b"OTA failed: syntax error")
                response.close()
                return
            with open("main.py", "w") as f:
                f.write(new_code)
            client.publish(TOPIC_STATUS, b"OTA successful. Rebooting...")
            print("OTA done, rebooting...")
            time.sleep(2)
            reset()
        else:
            print("HTTP error:", response.status_code)
            client.publish(TOPIC_STATUS, b"OTA failed: HTTP error")
        response.close()
    except Exception as e:
        print("OTA exception:", e)
        client.publish(TOPIC_STATUS, b"OTA failed: exception")

# ------------------------------
# MQTT Handling
# ------------------------------
def mqtt_callback(topic, msg):
    decoded = msg.decode()
    print("MQTT message:", decoded)

    feedback = None

    if decoded == "start_fan":
        set_fan_speed(100)
        feedback = "Fan started at 100%."
    elif decoded == "stop_fan":
        set_fan_speed(0)
        feedback = "Fan stopped."
    elif decoded.startswith("fan_speed_"):
        try:
            speed = int(decoded.split("_")[2])
            set_fan_speed(speed)
            feedback = f"Fan speed set to {speed}%."
        except:
            feedback = "Invalid fan speed command."
    elif decoded == "send_update":
        publish_update()
        feedback = "Update sent."
    elif decoded.startswith("ota_update"):
        parts = decoded.split("|")
        url = parts[1] if len(parts) > 1 else OTA_DEFAULT_URL
        perform_ota_update(url)
        return

    if feedback:
        try:
            client.publish(TOPIC_STATUS, feedback.encode())
        except:
            print("Failed to send feedback.")

def publish_update():
    temp, hum = read_DHT11()
    if temp is None or hum is None:
        print("Skipping publish due to sensor error.")
        return
    msg = f"{round(temp,1)}|{round(hum,1)}"
    try:
        client.publish(TOPIC_PUB, msg.encode())
        print("Published:", msg)
    except:
        print("MQTT error — rebooting.")
        reset()

# ------------------------------
# MQTT Connection & Main Loop
# ------------------------------
def mqtt_connect():
    global client
    while True:
        try:
            client = MQTTClient("dry_fan_node", MQTT_SERVER)
            client.set_callback(mqtt_callback)
            client.connect()
            client.subscribe(TOPIC_SUB)
            print("MQTT connected and subscribed.")
            return
        except Exception as e:
            print("MQTT connection failed:", e)
            time.sleep(5)

def main():
    mqtt_connect()
    while True:
        try:
            publish_update()
            for _ in range(60):  # check messages every second
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


