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


import subprocess

# You might store these in your Config, environment variables, or 
# a secure secret manager rather than hardcoding them.


def remote_shutdown_func(ip_address):
    """
    Shuts down a Windows PC remotely using Samba's 'net rpc shutdown' command.
    Prerequisites:
      - Target PC must allow Remote Shutdown.
      - Correct Windows Firewall rules open.
      - Samba client installed on the local machine (e.g. 'samba-common-bin').
      - Valid Windows user credentials with shutdown privileges.
    """
    cmd = [
        "net",
        "rpc",
        "shutdown",
        "-I", ip_address,
        "-U", f"{Config.WINDOWS_USER}%{Config.WINDOWS_PASS}",
        "-f"             # Force all running apps to close
        # You can also add "-t", "60" to set a 60-second delay if desired
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
    process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    output, error = process.communicate()
    return error or output