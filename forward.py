# Initialize clients for local and remote brokers
import paho.mqtt.client as mqtt

# Local MQTT broker configuration (no authentication)
LOCAL_MQTT_HOST = "localhost"
LOCAL_MQTT_PORT = 1883  # Default MQTT port
LOCAL_MQTT_TOPIC = "javier/growdata"

# Remote MQTT broker configuration (with authentication)
REMOTE_MQTT_HOST = "miplantita.uksouth.cloudapp.azure.com"  # Replace with your remote MQTT broker address
REMOTE_MQTT_PORT = 1883                       # Replace with your remote MQTT broker port if different
REMOTE_MQTT_TOPIC = "javier/growdata"         # You can change this if needed
REMOTE_MQTT_USERNAME = "growtent"        # Replace with your username
REMOTE_MQTT_PASSWORD = "G987rowtent."        # Replace with your password

# Create clients for local and remote brokers
local_client = mqtt.Client()
remote_client = mqtt.Client()

# Set username and password for remote broker
remote_client.username_pw_set(REMOTE_MQTT_USERNAME, REMOTE_MQTT_PASSWORD)

def on_connect_local(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to local MQTT broker.")
        client.subscribe(LOCAL_MQTT_TOPIC)
        print(f"Subscribed to topic '{LOCAL_MQTT_TOPIC}'")
    else:
        print(f"Failed to connect to local MQTT broker, return code {rc}")

def on_message(client, userdata, msg):
    # When a message is received on the local broker, forward it to the remote broker
    payload = msg.payload
    topic = msg.topic

    # Publish to the remote broker
    result = remote_client.publish(REMOTE_MQTT_TOPIC, payload)
    status = result[0]

    if status == mqtt.MQTT_ERR_SUCCESS:
        print(f"Message forwarded to remote MQTT broker on topic '{REMOTE_MQTT_TOPIC}': {payload.decode()}")
    else:
        print(f"Failed to forward message to remote MQTT broker, error code {status}")

def on_connect_remote(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to remote MQTT broker.")
    else:
        print(f"Failed to connect to remote MQTT broker, return code {rc}")

# Assign callback functions
local_client.on_connect = on_connect_local
local_client.on_message = on_message
remote_client.on_connect = on_connect_remote

def main():
    # Connect to the remote broker
    print("Connecting to remote MQTT broker...")
    try:
        remote_client.connect(REMOTE_MQTT_HOST, REMOTE_MQTT_PORT, 60)
    except Exception as e:
        print(f"Could not connect to remote MQTT broker: {e}")
        return

    # Start the remote client loop in a separate thread
    remote_client.loop_start()

    # Connect to the local broker
    print("Connecting to local MQTT broker...")
    try:
        local_client.connect(LOCAL_MQTT_HOST, LOCAL_MQTT_PORT, 60)
    except Exception as e:
        print(f"Could not connect to local MQTT broker: {e}")
        remote_client.loop_stop()
        return

    # Start the local client loop (blocking call)
    local_client.loop_forever()

if __name__ == "__main__":
    main()
