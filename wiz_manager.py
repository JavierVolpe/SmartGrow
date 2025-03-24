# wiz_manager.py
import asyncio
import threading
from pywizlight import wizlight, PilotBuilder
from config import Config

# Define your lamps by name and IP address
WIZ_LIGHTS = {
    "Living Room": Config.WIZLIGHT_LIVINGROOM,
    "Bedroom": Config.WIZLIGHT_BEDROOM
}

# Create a persistent event loop in a background thread
loop = asyncio.new_event_loop()

def start_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

threading.Thread(target=start_loop, args=(loop,), daemon=True).start()

def update_light(lamp_name, brightness, r, g, b):
    ip = WIZ_LIGHTS.get(lamp_name)
    if not ip:
        raise ValueError("Invalid lamp name")
    
    async def update():
        light = wizlight(ip)
        await light.turn_on(PilotBuilder(brightness=brightness, rgb=(r, g, b)))
        await light.async_close()
    
    future = asyncio.run_coroutine_threadsafe(update(), loop)
    return future.result()

def turn_off_light(lamp_name):
    ip = WIZ_LIGHTS.get(lamp_name)
    if not ip:
        raise ValueError("Invalid lamp name")
    
    async def off():
        light = wizlight(ip)
        await light.turn_off()
        await light.async_close()
    
    future = asyncio.run_coroutine_threadsafe(off(), loop)
    return future.result()

def get_light_status(lamp_name):
    ip = WIZ_LIGHTS.get(lamp_name)
    if not ip:
        raise ValueError("Invalid lamp name")
    
    async def get_status():
        light = wizlight(ip)
        # Retrieve the current state. Adjust the call as needed per your pywizlight version.
        state = await light.update_state()
        await light.async_close()
        return state
    
    future = asyncio.run_coroutine_threadsafe(get_status(), loop)
    return future.result()
