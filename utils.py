from flask import flash, redirect, url_for
import paho.mqtt.client as mqtt
import subprocess
from smart_home import is_valid_mac, is_valid_ip, execute_command, remote_shutdown_func
from config import Config

def publish_mqtt_message(message, success_msg, error_msg):
    try:
        mqtt_client = mqtt.Client()
        mqtt_client.connect(Config.MQTT_BROKER_IP, Config.MQTT_BROKER_PORT, 60)
        mqtt_client.publish("javier/growcontrol", message)
        mqtt_client.disconnect()
        flash(success_msg, "success")
    except Exception as e:
        flash(f"{error_msg}: {e}", "danger")
    return redirect(url_for("temperature"))



def execute_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout if result.returncode == 0 else result.stderr
    except Exception as e:
        return str(e)
