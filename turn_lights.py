# Source: https://github.com/sbidy/pywizlight


import asyncio
from pywizlight import wizlight, PilotBuilder

async def control_wiz_light(ip_address, action):
    """
    Control a WiZ smart bulb.

    Args:
        ip_address (str): IP address of the WiZ bulb.
        action (str): Either 'ON' (to turn light warm white) or 'OFF' (to turn off the light).
    """
    try:
        # Create a Wiz light object
        light = wizlight(ip_address)

        if action.upper() == 'ON':
            # Turn the light on with warm white color
            await light.turn_on(PilotBuilder(warm_white=255))
            print("Light turned ON with warm white color!")
        elif action.upper() == 'OFF':
            # Turn the light off
            await light.turn_off()
            print("Light turned OFF successfully!")
        else:
            print("Invalid action. Please use 'ON' or 'OFF'.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Always close the connection
        # await light.turn_off()
        ...

# Example usage:
# asyncio.run(control_wiz_light("192.168.87.102", "ON"))


async def get_light_status(ip_address):
    """
    Get and display the status of a WiZ smart bulb.

    Args:
        ip_address (str): IP address of the WiZ bulb.
    """
    try:
        # Create a Wiz light object
        light = wizlight(ip_address)

        # Get the current state of the bulb
        state = await light.updateState()

        # Extract relevant information
        brightness = state.get_brightness()
        color_temp = state.get_colortemp()
        rgb_values = state.get_rgb()
        power_state = state.get_state()
        if power_state == True:
            power_state = "<font color=green>ON</font>"
        elif power_state == False:
            power_state = "<font color=red>OFF</font>"
        
        display_data = (f"Light Status for Bulb at {ip_address}: \n Power state: {power_state} Brightness: {brightness} (0-255), Color Temperature: {color_temp} K, RGB Values: R={rgb_values[0]}, G={rgb_values[1]}, B={rgb_values[2]}")
        return display_data
    except Exception as e:
        print(f"Error fetching light status: {e}")
        return e