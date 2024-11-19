#!/usr/bin/env python3

import sys
import time
import json
import requests
import paho.mqtt.client as mqtt
from config import Config

# Notification Settings
NOTIFICATION_URL_TEMPLATE = Config.CALLMEBOT_URL_TEMPLATE
PHONE_NUMBER = Config.CALLMEBOT_PHONE_NUMBER
APIKEY = Config.CALLMEBOT_APIKEY

def send_notification(message):
    url = NOTIFICATION_URL_TEMPLATE.format(phone_number=PHONE_NUMBER, message=message, apikey=APIKEY)
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print("Notification sent successfully.")
        else:
            print(f"Failed to send notification. Status Code: {response.status_code}")
    except Exception as e:
        print(f"Error sending notification: {e}")

def send_mqtt_command(client, action):
    # Send the command
    if action == 'on':
        # Turn plug ON
        method = "Switch.Set"
        params = {"id": 0, "on": True}
    elif action == 'off':
        # Turn plug OFF
        method = "Switch.Set"
        params = {"id": 0, "on": False}
    else:
        print("Invalid action. Use 'on' or 'off'.")
        sys.exit(1)

    request = {
        "id": int(time.time() * 1000),
        "src": "user_script",
        "method": method,
        "params": params
    }

    client.publish(Config.SHELLY_RPC_TOPIC, json.dumps(request))
    print(f"Published command to turn {'ON' if action == 'on' else 'OFF'} the plug.")

def get_plug_status(client, request_id, timeout=5):
    response = None

    def on_message(client, userdata, msg):
        nonlocal response
        try:
            payload = json.loads(msg.payload.decode())
            if payload.get('id') == request_id and 'result' in payload:
                response = payload['result']
        except Exception as e:
            print(f"Error processing message: {e}")

    # Assign temporary callback
    client.on_message = on_message

    # Subscribe to response topic
    client.subscribe(Config.SHELLY_RESPONSE_TOPIC)

    # Publish the status request
    request = {
        "id": request_id,
        "src": "user_script",
        "method": "Switch.GetStatus",
        "params": {"id": 0}
    }
    client.publish(Config.SHELLY_RPC_TOPIC, json.dumps(request))
    print("Published status request.")

    # Wait for the response
    start_time = time.time()
    while time.time() - start_time < timeout:
        client.loop(timeout=1)
        if response:
            break

    # Unsubscribe and reset callback
    client.unsubscribe(Config.SHELLY_RESPONSE_TOPIC)
    client.on_message = None

    if not response:
        print("No response received for status request.")
    else:
        print(f"Current Plug Status: {'ON' if response.get('output') else 'OFF'}")
        print(f"Power: {response.get('apower', 0)} W, Voltage: {response.get('voltage', 0)} V, Current: {response.get('current', 0)} A")

    return response

def main(action):
    # Setup MQTT client
    client = mqtt.Client()

    # Set username and password if required
    # if Config.MQTT_USERNAME:
    #     client.username_pw_set(Config.MQTT_USERNAME, Config.MQTT_PASSWORD)

    client.connect(Config.MQTT_BROKER, Config.MQTT_PORT, 60)
    client.loop_start()

    # Send the command
    send_mqtt_command(client, action)

    # Wait a moment to allow the command to process
    time.sleep(2)

    # Define expected state
    expected_state = True if action == 'on' else False

    # Retry parameters
    retries = 3
    delay_between_retries = 2  # seconds
    success = False

    for attempt in range(1, retries + 1):
        print(f"Attempt {attempt} to verify plug state.")
        request_id = int(time.time() * 1000)
        status = get_plug_status(client, request_id)
        if status and status.get('output') == expected_state:
            print(f"Plug successfully turned {'ON' if expected_state else 'OFF'}.")
            success = True
            break
        else:
            print(f"Plug state is not {'ON' if expected_state else 'OFF'}. Retrying in {delay_between_retries} seconds...")
            time.sleep(delay_between_retries)

    if not success:
        message = f"Failed to turn {'ON' if expected_state else 'OFF'} the plug after {retries} attempts."
        print(message)
        send_notification(message)

    client.loop_stop()
    client.disconnect()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: mqtt_plug_control.py <on|off>")
        sys.exit(1)
    action = sys.argv[1]
    main(action)
