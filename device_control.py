import json
import time
import threading
import subprocess
import socket
import sys
import requests
from datetime import datetime, timedelta
import paho.mqtt.client as mqtt
from config import Config

# -------------------------
# Utility Functions
# -------------------------

def is_valid_ip(ip):
    """Validate an IPv4 address using socket.inet_aton."""
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False

def is_valid_mac(mac):
    """Validate a MAC address (format: xx:xx:xx:xx:xx:xx)."""
    parts = mac.split(':')
    if len(parts) != 6:
        return False
    for part in parts:
        try:
            num = int(part, 16)
            if num < 0 or num > 255:
                return False
        except ValueError:
            return False
    return True

def remote_shutdown_func(ip_address):
    """
    Shuts down a Windows PC remotely using Samba's 'net rpc shutdown' command.
    Prerequisites:
      - Remote shutdown must be allowed on the target.
      - Proper firewall and Samba client configuration.
    """
    cmd = [
        "net",
        "rpc",
        "shutdown",
        "-I", ip_address,
        "-U", f"{Config.WINDOWS_USER}%{Config.WINDOWS_PASS}",
        "-f"
    ]
    try:
        subprocess.run(cmd, check=True)
        print(f"Shutdown command sent successfully to {ip_address}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to shut down {ip_address}. Error: {e}")
        return False
    except Exception as ex:
        print(f"An error occurred attempting to shut down {ip_address}: {ex}")
        return False

def execute_command(command):
    """Execute a shell command and return its output or error."""
    process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    output, error = process.communicate()
    return error or output

def send_notification(message):
    """
    Send a notification via the CallMeBot API (or similar).
    Expects configuration settings in Config.
    """
    url = Config.CALLMEBOT_URL_TEMPLATE.format(
        phone_number=Config.CALLMEBOT_PHONE_NUMBER,
        message=message,
        apikey=Config.CALLMEBOT_APIKEY
    )
    try:
        response = requests.get(url)
        if response.status_code == 200:
            print("Notification sent successfully.")
        else:
            print(f"Failed to send notification. Status Code: {response.status_code}")
    except Exception as e:
        print(f"Error sending notification: {e}")

# -------------------------
# MQTT Smart Plug Control
# -------------------------

class ShellyPlugMQTTClient:
    """
    A client for controlling a Shelly smart plug via MQTT.
    Provides methods to send commands and query status.
    """
    def __init__(self):
        self.client = mqtt.Client()
        # Uncomment and set credentials if required:
        # self.client.username_pw_set(Config.MQTT_USERNAME, Config.MQTT_PASSWORD)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.rpc_topic = Config.SHELLY_RPC_TOPIC
        self.response_topic = Config.SHELLY_RESPONSE_TOPIC

        self.responses = {}  # Responses keyed by request ID.
        self.responses_lock = threading.Lock()

        # Connect to the MQTT broker and start loop in a separate thread.
        self.client.connect(Config.MQTT_BROKER_IP, Config.MQTT_BROKER_PORT, 60)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker")
            # Subscribe to RPC and response topics.
            self.client.subscribe(self.rpc_topic)
            self.client.subscribe(self.response_topic)
        else:
            print(f"Failed to connect, return code {rc}")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            request_id = payload.get('id')
            if request_id:
                with self.responses_lock:
                    self.responses[request_id] = payload
        except Exception as e:
            print(f"Error processing message: {e}")

    def send_request(self, method, params=None):
        """
        Sends an MQTT request and waits (busy-looping) up to 5 seconds for a response.
        (This loop can be improved using threading.Event.)
        """
        request_id = int(time.time() * 1000)
        request = {
            "id": request_id,
            "src": "user_script",
            "method": method,
            "params": params or {}
        }
        with self.responses_lock:
            self.responses[request_id] = None
        self.client.publish(self.rpc_topic, json.dumps(request))

        timeout = 5
        start_time = time.time()
        while True:
            with self.responses_lock:
                response = self.responses.get(request_id)
                if response is not None:
                    return response
            if time.time() - start_time > timeout:
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
        on_time = now.replace(hour=7, minute=30, second=0, microsecond=0)
        off_time = now.replace(hour=23, minute=30, second=0, microsecond=0)
        if now < on_time:
            next_change = on_time
            next_state = "ON"
        elif now < off_time:
            next_change = off_time
            next_state = "OFF"
        else:
            next_change = on_time + timedelta(days=1)
            next_state = "ON"
        countdown = next_change - now
        return {"next_change": next_change, "next_state": next_state, "countdown": countdown}

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

# Global instance for programmatic use.
mqtt_client = ShellyPlugMQTTClient()

# -------------------------
# Command-Line Interface Functions
# -------------------------

def send_mqtt_command(client, action):
    """Send an MQTT command to turn the plug on or off."""
    if action == 'on':
        method = "Switch.Set"
        params = {"id": 0, "on": True}
    elif action == 'off':
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

def get_plug_status_cli(client, request_id, timeout=5):
    """Get plug status via MQTT using a temporary callback."""
    response = None

    def on_message(client, userdata, msg):
        nonlocal response
        try:
            payload = json.loads(msg.payload.decode())
            if payload.get('id') == request_id and 'result' in payload:
                response = payload['result']
        except Exception as e:
            print(f"Error processing message: {e}")

    client.on_message = on_message
    client.subscribe(Config.SHELLY_RESPONSE_TOPIC)
    request = {
        "id": request_id,
        "src": "user_script",
        "method": "Switch.GetStatus",
        "params": {"id": 0}
    }
    client.publish(Config.SHELLY_RPC_TOPIC, json.dumps(request))
    print("Published status request.")
    start_time = time.time()
    while time.time() - start_time < timeout:
        client.loop(timeout=1)
        if response:
            break
    client.unsubscribe(Config.SHELLY_RESPONSE_TOPIC)
    client.on_message = None

    if not response:
        print("No response received for status request.")
    else:
        status_str = "ON" if response.get('output') else "OFF"
        print(f"Current Plug Status: {status_str}")
        print(f"Power: {response.get('apower', 0)} W, Voltage: {response.get('voltage', 0)} V, Current: {response.get('current', 0)} A")
    return response

def main_cli(action):
    """
    Command-line interface to send a plug command (on/off),
    verify its state with retries, and send a notification if unsuccessful.
    """
    client = mqtt.Client()
    # Uncomment if credentials are required:
    # client.username_pw_set(Config.MQTT_USERNAME, Config.MQTT_PASSWORD)
    client.connect(Config.MQTT_BROKER_IP, Config.MQTT_BROKER_PORT, 60)
    client.loop_start()

    send_mqtt_command(client, action)
    time.sleep(2)  # Allow time for the command to be processed.
    expected_state = True if action == 'on' else False
    retries = 3
    delay_between_retries = 2
    success = False

    for attempt in range(1, retries + 1):
        print(f"Attempt {attempt} to verify plug state.")
        request_id = int(time.time() * 1000)
        status = get_plug_status_cli(client, request_id)
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

# -------------------------
# WiZ Light Control (pywizlight)
# -------------------------

import asyncio
from pywizlight import wizlight, PilotBuilder

# -------------------------
# WiZ Light Control (pywizlight)
# -------------------------

async def get_light_status(ip_address):
    """Return the light's status in a structured format for JSON/API/UI display."""
    try:
        light = wizlight(ip_address)
        state = await light.updateState()
        return {
            "power": state.get_state(),
            "brightness": state.get_brightness(),
            "rgb": state.get_rgb()
        }
    except Exception as e:
        print(f"Error getting light status: {e}")
        return {"error": str(e)}

async def set_light_state(ip_address, brightness=255, r=255, g=255, b=255):
    """Set brightness and RGB color."""
    try:
        light = wizlight(ip_address)
        await light.turn_on(PilotBuilder(brightness=brightness, rgb=(r, g, b)))
        return True
    except Exception as e:
        print(f"Error setting light state: {e}")
        return False

async def turn_off_light(ip_address):
    """Turn off the light."""
    try:
        light = wizlight(ip_address)
        await light.turn_off()
        return True
    except Exception as e:
        print(f"Error turning off light: {e}")
        return False

# Wrapper function to handle async calls
def get_light_status_sync(ip_address):
    """Call the async function to get light status."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(get_light_status(ip_address))
    loop.close()
    return result

def set_light_state_sync(ip_address, brightness, r, g, b):
    """Call the async function to set light state."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(set_light_state(ip_address, brightness, r, g, b))
    loop.close()
    return result

def turn_off_light_sync(ip_address):
    """Call the async function to turn off light."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(turn_off_light(ip_address))
    loop.close()
    return result



# -------------------------
# Main Script Entry Point
# -------------------------

if __name__ == "__main__":
    if len(sys.argv) == 2:
        action = sys.argv[1].lower()
        if action in ['on', 'off']:
            main_cli(action)
        else:
            print("Usage: python device_control.py <on|off>")
    else:
        print("Usage: python device_control.py <on|off>")
