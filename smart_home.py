import subprocess
from config import Config
import socket

def is_valid_ip(ip):
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    for part in parts:
        try:
            num = int(part)
            if num < 0 or num > 255:
                return False
        except ValueError:
            return False
    return True

def is_valid_mac(mac):
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
    try:
        # Attempt SSH connection with a timeout of 10 seconds
        ssh_command = ["ssh", "-o", "ConnectTimeout=10", f"{Config.REMOTE_PC_USER}@{ip_address}", "shutdown", "/s", "/t", "60"]
        subprocess.run(ssh_command, check=True)
        return True
    except subprocess.CalledProcessError as e:
        # Handle SSH command execution errors
        print(f"Error occurred: {e}")
        return False
    except socket.timeout:
        # Handle timeout (host didn't respond)
        print("Connection timed out. Host didn't respond.")
        return False
    except Exception as ex:
        # Handle other exceptions (e.g., connection refused)
        print(f"An error occurred: {ex}")
        return False


def execute_command(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    output, error = process.communicate()
    return error or output