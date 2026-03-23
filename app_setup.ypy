import sys
sys.coinit_flags = 0
try:
    from bleak.backends.winrt.util import allow_sta
    allow_sta()
except ImportError:
    pass

import asyncio
import pygame
from bleak import BleakScanner, BleakClient

DEVICE_NAME = "UNO R4"
CHAR_UUID = "19B10001-E8F2-537E-4F6C-D104768A1214"
DEADZONE = 0.15
JOYSTICK_AXIS = 0
BUTTON_INDEX = 0      # joystick pushbutton index (adjust if needed)
LED_ON_TIME = 1.0

async def connect_threaded(client):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: asyncio.run(client.connect()))

async def main():
    pygame.init()
    pygame.joystick.init()

    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    print(f"Joystick: {joystick.get_name()}")

    print("Scanning...")
    devices = await BleakScanner.discover()
    target = next((d for d in devices if d.name == DEVICE_NAME), None)

    if not target:
        print("No UNO R4!")
        pygame.quit()
        return

    client = BleakClient(target.address)
    print("Connecting...")

    try:
        success = await asyncio.wait_for(connect_threaded(client), timeout=10.0)
        print(f"Connected: {success}")
    except:
        print("Connect failed!")
        return

    print("Joystick → BLE: Left=1, Right=2, Center=0, Button=3")

    prev_state = "CENTER"
    prev_button = 0

    try:
        while client.is_connected:
            pygame.event.pump()

            # Axis handling (unchanged)
            x = joystick.get_axis(JOYSTICK_AXIS)
            state = "LEFT" if x < -DEADZONE else "RIGHT" if x > DEADZONE else "CENTER"

            if state != prev_state:
                if state == "LEFT":
                    await client.write_gatt_char(CHAR_UUID, b'\x01')
                    print("Sent 1 (left)")
                elif state == "RIGHT":
                    await client.write_gatt_char(CHAR_UUID, b'\x02')
                    print("Sent 2 (right)")
                elif state == "CENTER":
                    await client.write_gatt_char(CHAR_UUID, b'\x00')
                    print("Sent 0 (center)")
                prev_state = state

            # NEW: button handling
            button = joystick.get_button(BUTTON_INDEX)  # 0 or 1
            if button != prev_button:
                if button == 1:
                    # button pressed → both LEDs on
                    await client.write_gatt_char(CHAR_UUID, b'\x03')
                    print("Sent 3 (button pressed → both on)")
                else:
                    # button released → optional: both off
                    await client.write_gatt_char(CHAR_UUID, b'\x00')
                    print("Sent 0 (button released → both off)")
                prev_button = button

            await asyncio.sleep(0.05)

    except KeyboardInterrupt:
        print("\nQuitting...")
    finally:
        if client.is_connected:
            await client.disconnect()
        pygame.quit()

if __name__ == "__main__":
    asyncio.run(main())
