# smart_plug.py

import json
import time
import threading
import paho.mqtt.client as mqtt
from config import Config
from datetime import datetime, timedelta

class ShellyPlugMQTTClient:
    def __init__(self):
        self.client = mqtt.Client()
        # Set username and password if required
        # if Config.MQTT_USERNAME:
        #     self.client.username_pw_set(Config.MQTT_USERNAME, Config.MQTT_PASSWORD)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.rpc_topic = Config.SHELLY_RPC_TOPIC
        self.response_topic = Config.SHELLY_RESPONSE_TOPIC

        self.responses = {}  # Store responses keyed by request ID
        self.responses_lock = threading.Lock()

        # Connect to the MQTT broker
        self.client.connect(Config.MQTT_BROKER_IP, Config.MQTT_BROKER_PORT, 60)
        # Start the MQTT client loop in a separate thread
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker")
            # Subscribe to both RPC and response topics
            self.client.subscribe(self.rpc_topic)
            self.client.subscribe(self.response_topic)
        else:
            print(f"Failed to connect, return code {rc}")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            with self.responses_lock:
                request_id = payload.get('id')
                if request_id:
                    self.responses[request_id] = payload
        except Exception as e:
            print(f"Error processing message: {e}")

    def send_request(self, method, params=None):
        request_id = int(time.time() * 1000)  # Use timestamp as unique ID
        request = {
            "id": request_id,
            "src": "user_script",
            "method": method,
            "params": params or {}
        }
        with self.responses_lock:
            self.responses[request_id] = None
        self.client.publish(self.rpc_topic, json.dumps(request))

        # Wait for the response (timeout after 5 seconds)
        timeout = 5
        start_time = time.time()
        while True:
            with self.responses_lock:
                response = self.responses.get(request_id)
                if response is not None:
                    return response
            if (time.time() - start_time) > timeout:
                print(f"No response received for request ID {request_id}")
                return None
            time.sleep(0.1)

    def get_plug_status(self):
        response = self.send_request("Switch.GetStatus", {"id": 0})
        if response and 'result' in response:
            return response['result']
        return None

    def set_plug_state(self, state):
        response = self.send_request("Switch.Set", {"id": 0, "on": state})
        if response and 'result' in response:
            return response['result']
        return None

    def get_next_status_change(self):
        now = datetime.now()
        # Define the schedule times
        on_time = now.replace(hour=8, minute=0, second=0, microsecond=0)
        off_time = now.replace(hour=23, minute=0, second=0, microsecond=0)

        if now < on_time:
            next_change = on_time
            next_state = "ON"
        elif now < off_time:
            next_change = off_time
            next_state = "OFF"
        else:
            # It's after 11 PM, next change is tomorrow at 8 AM
            next_change = on_time + timedelta(days=1)
            next_state = "ON"

        countdown = next_change - now
        return {
            "next_change": next_change,
            "next_state": next_state,
            "countdown": countdown
        }

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

# Create an instance of the client
mqtt_client = ShellyPlugMQTTClient()
