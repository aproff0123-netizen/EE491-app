import sys
import os
import asyncio
import tkinter as tk
from tkinter import ttk

import pygame
from bleak import BleakScanner, BleakClient

# --- PyInstaller Resource Helper ---
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- Windows / Bleak setup ---
sys.coinit_flags = 0
try:
    from bleak.backends.winrt.util import allow_sta
    allow_sta()
except ImportError:
    pass

# --- Settings ---
DEVICE_NAME = "UNO R4"
CHAR_UUID = "19B10001-E8F2-537E-4F6C-D104768A1214"
DEADZONE = 0.15
JOYSTICK_AXIS = 0
BUTTON_INDEX = 0


# --- Custom Image Button with Text Outline ---
class ImageButton(tk.Canvas):
    def __init__(self, parent, image, text, command, **kwargs):
        self.img = image
        self.command = command
        self.is_disabled = False
        
        w, h = self.img.width(), self.img.height()
        # Create canvas sized exactly to the image
        super().__init__(parent, width=w, height=h, highlightthickness=0, bg="#ffffff", **kwargs)
        
        # Place the image in the center
        self.create_image(w//2, h//2, image=self.img)
        
        font = ("Segoe UI", 12, "bold")
        
        # Draw the black outline by shifting text 1px in 8 different directions
        for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1), (-1,0), (1,0), (0,-1), (0,1)]:
            self.create_text(w//2 + dx, h//2 + dy, text=text, fill="black", font=font)
        
        # Draw the main white text in the center
        self.create_text(w//2, h//2, text=text, fill="white", font=font)
        
        # Bind the left mouse click
        self.bind("<Button-1>", self.on_click)

    def on_click(self, event):
        if not self.is_disabled and self.command:
            self.command()

    def config(self, **kwargs):
        # Allow disabling the button so it can't be spam-clicked
        if "state" in kwargs:
            self.is_disabled = (kwargs.pop("state") == "disabled")
        if kwargs:
            super().config(**kwargs)


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Joystick BLE Controller")
        self.root.geometry("800x533")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.status_var = tk.StringVar(value="Ready")

        # Load images
        self.bg_image = tk.PhotoImage(file=resource_path("fb1sm.png"))
        self.football_image = tk.PhotoImage(file=resource_path("football.png")).subsample(9, 9)

        # Put background image behind everything
        self.bg_label = tk.Label(root, image=self.bg_image)
        self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)

        # Foreground container
        self.main_frame = tk.Frame(root, bg="#ffffff")
        self.main_frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            self.main_frame,
            text="Joystick → BLE Controller",
            font=("Segoe UI", 12, "bold"),
            bg="#ffffff"
        ).pack(pady=(15, 5))

        tk.Label(
            self.main_frame,
            textvariable=self.status_var,
            bg="#ffffff"
        ).pack(pady=5)

        # Replace standard ttk.Button with our Custom ImageButton
        self.start_btn = ImageButton(
            self.main_frame,
            image=self.football_image,
            text="START",
            command=lambda: asyncio.create_task(self.start())
        )
        self.start_btn.pack(pady=5)

        self.stop_btn = ttk.Button(
            self.main_frame,
            text="Stop",
            command=self.stop,
            state="disabled"
        )
        self.stop_btn.pack(pady=5)

        self.stop_event = asyncio.Event()
        self.running = False
        self.client = None

    def set_status(self, text):
        self.status_var.set(text)

    def stop(self):
        self.stop_event.set()
        self.set_status("Disconnecting...")
        self.stop_btn.config(state="disabled")

    def on_close(self):
        self.stop()
        self.root.after(100, self.root.destroy)

    async def start(self):
        if self.running:
            return

        self.running = True
        self.stop_event.clear()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")

        pygame.init()
        pygame.joystick.init()

        if pygame.joystick.get_count() == 0:
            self.set_status("No joystick found")
            self.finish()
            return

        joystick = pygame.joystick.Joystick(0)
        joystick.init()

        self.set_status("Scanning...")
        # UPGRADED SCANNING SPEED: Connects the exact millisecond the UNO R4 is spotted
        target = await BleakScanner.find_device_by_name(DEVICE_NAME, timeout=5.0)

        if not target:
            self.set_status("UNO R4 not found")
            self.finish()
            return

        self.client = BleakClient(target.address)

        try:
            self.set_status("Connecting...")
            await self.client.connect()

            if not self.client.is_connected:
                self.set_status("Connect failed")
                self.finish()
                return

            self.set_status("Connected")

            prev_state = "CENTER"
            prev_button = 0

            while not self.stop_event.is_set() and self.client.is_connected:
                pygame.event.pump()

                x = joystick.get_axis(JOYSTICK_AXIS)
                state = "LEFT" if x < -DEADZONE else "RIGHT" if x > DEADZONE else "CENTER"

                if state != prev_state:
                    if state == "LEFT":
                        await self.client.write_gatt_char(CHAR_UUID, b"\x01")
                    elif state == "RIGHT":
                        await self.client.write_gatt_char(CHAR_UUID, b"\x02")
                    else:
                        await self.client.write_gatt_char(CHAR_UUID, b"\x00")
                    prev_state = state

                button = joystick.get_button(BUTTON_INDEX)
                if button != prev_button:
                    if button == 1:
                        await self.client.write_gatt_char(CHAR_UUID, b"\x03")
                    else:
                        await self.client.write_gatt_char(CHAR_UUID, b"\x00")
                    prev_button = button

                await asyncio.sleep(0.05)

        except Exception as e:
            if not self.stop_event.is_set():
                self.set_status("Connection lost / Error")
        finally:
            if self.client and self.client.is_connected:
                try:
                    await self.client.disconnect()
                except Exception:
                    pass
            pygame.quit()
            self.finish()

    def finish(self):
        self.running = False
        self.client = None
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        
        if self.status_var.get() in ["Disconnecting...", "Stopping..."]:
            self.set_status("Stopped")


async def gui_loop(root, interval=0.05):
    while True:
        root.update()
        await asyncio.sleep(interval)


async def main():
    root = tk.Tk()
    app = App(root)
    await gui_loop(root)


if __name__ == "__main__":
    asyncio.run(main())