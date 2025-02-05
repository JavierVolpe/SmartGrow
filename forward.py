import paho.mqtt.client as mqtt
import logging
import warnings
import time

# Configure logging to write to a file with timestamps
logging.basicConfig(filename='log_forward.log', level=logging.INFO,
                    format='%(asctime)s %(levelname)s:%(message)s')

# Local MQTT broker configuration (no authentication)
LOCAL_MQTT_HOST = "localhost"
LOCAL_MQTT_PORT = 1883
LOCAL_MQTT_TOPIC = "javier/growdata"

# Remote MQTT broker configuration (with authentication)
#REMOTE_MQTT_HOST = "miplantita.uksouth.cloudapp.azure.com"
REMOTE_MQTT_HOST = "172.167.230.193"
REMOTE_MQTT_PORT = 1883
REMOTE_MQTT_TOPIC = "javier/growdata"
REMOTE_MQTT_USERNAME = "growtent"
REMOTE_MQTT_PASSWORD = "G987rowtent."

# Initialize clients for local and remote brokers with unique client IDs
local_client = mqtt.Client(client_id="local_client")
remote_client = mqtt.Client(client_id="remote_client")

# Set username and password for remote broker
remote_client.username_pw_set(REMOTE_MQTT_USERNAME, REMOTE_MQTT_PASSWORD)

# Define on_connect callback for the local MQTT broker
def on_connect_local(client, userdata, flags, rc):
    if rc == 0:
        logging.info("Connected to local MQTT broker.")
        client.subscribe(LOCAL_MQTT_TOPIC)
        logging.info(f"Subscribed to topic '{LOCAL_MQTT_TOPIC}'")
    else:
        logging.error(f"Failed to connect to local MQTT broker, return code {rc}")

# Define on_message callback for forwarding messages
def on_message(client, userdata, msg):
    payload = msg.payload
    topic = msg.topic
    # Publish message to the remote broker
    result = remote_client.publish(REMOTE_MQTT_TOPIC, payload)
    status = result.rc  # Using .rc as per updated API
    if status == mqtt.MQTT_ERR_SUCCESS:
        logging.info(f"Message forwarded to remote MQTT broker on topic '{REMOTE_MQTT_TOPIC}': {payload.decode()}")
    else:
        logging.error(f"Failed to forward message to remote MQTT broker, error code {status}")

# Define on_connect callback for the remote MQTT broker
def on_connect_remote(client, userdata, flags, rc):
    if rc == 0:
        logging.info("Connected to remote MQTT broker.")
    else:
        logging.error(f"Failed to connect to remote MQTT broker, return code {rc}")

# Assign callback functions using updated syntax
local_client.on_connect = on_connect_local
local_client.on_message = on_message
remote_client.on_connect = on_connect_remote

def main():
    # Connect to the remote broker
    logging.info("Connecting to remote MQTT broker...")
    try:
        remote_client.connect(REMOTE_MQTT_HOST, REMOTE_MQTT_PORT, 60)
    except Exception as e:
        logging.error(f"Could not connect to remote MQTT broker: {e}")
        return

    # Start the remote client loop in a non-blocking way
    remote_client.loop_start()

    # Connect to the local broker
    logging.info("Connecting to local MQTT broker...")
    try:
        local_client.connect(LOCAL_MQTT_HOST, LOCAL_MQTT_PORT, 60)
    except Exception as e:
        logging.error(f"Could not connect to local MQTT broker: {e}")
        remote_client.loop_stop()
        return

    # Start the local client loop in a non-blocking way
    local_client.loop_start()

    # Keep the main process alive to let MQTT loops run in the background
    try:
        while True:
            time.sleep(1)  # Keep the loop alive with a short sleep interval
    except KeyboardInterrupt:
        logging.info("Terminating script.")
    finally:
        local_client.loop_stop()
        remote_client.loop_stop()
        logging.info("MQTT clients stopped.")

if __name__ == "__main__":
    # Suppress deprecation warnings if they persist
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        main()
