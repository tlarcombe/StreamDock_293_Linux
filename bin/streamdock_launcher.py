#!/usr/bin/env python3
"""
Stream Dock Launcher - Direct HID Version
Bypasses the buggy C library and reads HID directly
"""
import sys
import os
import hid
import time
import logging

# Determine installation directory
INSTALL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB_DIR = os.path.join(INSTALL_DIR, 'lib', 'launcher')
CONFIG_DIR = os.path.join(INSTALL_DIR, 'config')
DEFAULT_CONFIG = os.path.join(CONFIG_DIR, 'config.json')

# Add launcher library to path
sys.path.insert(0, LIB_DIR)

from config_loader import LauncherConfig
from icon_manager import IconManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Stream Dock 293 USB IDs
VENDOR_ID = 0x5500
PRODUCT_ID = 0x1001

# HID Protocol Constants
PREFIX = b"CRT\x00\x00"
CMD_BAT = b"BAT"
CMD_STP = b"STP\x00\x00"
CMD_LIG = b"LIG\x00\x00"
CMD_CLE = b"CLE\x00\x00\x00"

# Report size
REPORT_SIZE = 512


class StreamDockLauncherDirect:
    """Direct HID-based launcher (no SDK)"""

    def __init__(self, config_path: str = None):
        self.config_path = config_path or DEFAULT_CONFIG
        self.config = None
        self.device = None
        self.icon_manager = None
        self.running = False
        self.display_on = True
        
        # Key mapping (Physical code -> Logical ID)
        self.key_map = {
            0x0b: 1, 0x0c: 2, 0x0d: 3, 0x0e: 4, 0x0f: 5,    # Top row
            0x06: 6, 0x07: 7, 0x08: 8, 0x09: 9, 0x0a: 10,   # Middle row
            0x01: 11, 0x02: 12, 0x03: 13, 0x04: 14, 0x05: 15 # Bottom row
        }

    def _send_report(self, payload: bytes):
        """Send a 512-byte report with leading 0x00 byte for Report ID 0"""
        if not self.device:
            return
        
        # Ensure payload is exactly REPORT_SIZE (512)
        if len(payload) > REPORT_SIZE:
            payload = payload[:REPORT_SIZE]
        elif len(payload) < REPORT_SIZE:
            payload = payload.ljust(REPORT_SIZE, b"\x00")
            
        # Send with leading 0x00 (Report ID 0)
        # Total size sent to hidapi.write() is 513 bytes
        self.device.write(b"\x00" + payload)

    def initialize(self):
        """Initialize all components"""
        logger.info("=" * 70)
        logger.info("Stream Dock Launcher Starting (Direct HID Mode)...")
        logger.info("=" * 70)

        # Load configuration
        logger.info(f"Loading configuration from: {self.config_path}")
        self.config = LauncherConfig(self.config_path)

        # Initialize icon manager (specifically for Stream Dock 293)
        logger.info("Initializing icon manager...")
        self.icon_manager = IconManager(button_size=(100, 100), rotation=180)

        # Open HID device directly
        logger.info(f"Opening HID device (VID: 0x{VENDOR_ID:04x}, PID: 0x{PRODUCT_ID:04x})...")
        self.device = hid.device()
        try:
            self.device.open(VENDOR_ID, PRODUCT_ID)
            self.device.set_nonblocking(1)  # Restore non-blocking reads
            logger.info("✅ Device opened successfully (Direct HID)")

            # Get device info
            manufacturer = self.device.get_manufacturer_string()
            product = self.device.get_product_string()
            logger.info(f"  Manufacturer: {manufacturer}")
            logger.info(f"  Product: {product}")

            # Apply initial configuration
            self.set_brightness(self.config.brightness)
            self.update_all_keys()

        except Exception as e:
            logger.error(f"Failed to open HID device: {e}")
            return False

        logger.info("=" * 70)
        logger.info("✅ Stream Dock Launcher Ready! (Direct HID Mode)")
        logger.info("=" * 70)
        logger.info(f"Configured keys: {sorted(self.config.bindings.keys())}")
        logger.info("Press any key to execute its action")
        
        # Setup special actions
        for binding in self.config.bindings.values():
            from actions import ToggleDisplayAction
            if isinstance(binding.action, ToggleDisplayAction):
                binding.action.callback = self.toggle_display
                logger.info(f"  Configured display toggle on key {binding.key_number}")

        logger.info("Press Ctrl+C to exit")
        logger.info("=" * 70)

        return True

    def run(self):
        """Main run loop with direct HID reading"""
        self.running = True

        logger.info("Starting HID polling loop...")

        try:
            while self.running:
                try:
                    # Read from HID device (non-blocking)
                    # Use REPORT_SIZE (512) as per endpoint wMaxPacketSize
                    data = self.device.read(REPORT_SIZE)

                    if data:
                        logger.debug(f"HID Data ({len(data)} bytes): {bytes(data).hex()}")

                        if len(data) >= 11:
                            # data[9] = key (physical code)
                            # data[10] = state (1=pressed, 2=released)
                            if data[9] != 0xFF and data[9] != 0:
                                raw_key = data[9]
                                state = data[10]

                                # Map physical key to logical key
                                key = self.key_map.get(raw_key, raw_key)

                                # Normalize state
                                if state == 0x01:
                                    logger.info(f"Key {key} pressed (raw: 0x{raw_key:02x})")
                                    self._handle_key_press(key)
                                elif state == 0x02:
                                    logger.info(f"Key {key} released (raw: 0x{raw_key:02x})")

                except OSError as e:
                    # Log but keep running unless it's a fatal error
                    logger.debug(f"HID read error: {e}")
                    time.sleep(1) # Wait longer on error
                except Exception as e:
                    logger.error(f"Unexpected error in HID loop: {e}", exc_info=True)

                # Small delay to avoid busy waiting
                time.sleep(0.01)

        except KeyboardInterrupt:
            logger.info("\nReceived interrupt signal")
        finally:
            self.shutdown()

    def _handle_key_press(self, key: int):
        """Handle a key press event"""
        try:
            # Get binding
            binding = self.config.get_binding(key)

            if not binding:
                logger.info(f"Key {key} has no binding")
                return

            # Execute action
            logger.info(f"Executing: {binding.name}")
            success = binding.action.execute()
            if success:
                logger.info(f"✅ Action completed: {binding.name}")
            else:
                logger.warning(f"⚠️ Action failed: {binding.name}")
        except Exception as e:
            logger.error(f"❌ Error handling key press: {e}", exc_info=True)

    def set_brightness(self, value: int):
        """Set device brightness (0-100)"""
        if not self.device:
            return

        logger.info(f"Setting brightness to {value}%")
        try:
            # Command: PREFIX + CMD_LIG + brightness_byte
            payload = PREFIX + CMD_LIG + bytes([value])
            self._send_report(payload)
        except Exception as e:
            logger.error(f"Failed to set brightness: {e}")

    def toggle_display(self) -> bool:
        """Toggle the display on/off"""
        self.display_on = not self.display_on
        state_str = "ON" if self.display_on else "OFF"
        logger.info(f"Toggling display: {state_str}")

        if not self.display_on:
            # Turn OFF: Send black images to all keys
            logger.info("Turning display OFF (sending black icons)")
            # Path to a black icon if it exists, or let icon_manager handle null
            for key_id in range(1, 16):
                processed_path = self.icon_manager.prepare_icon(None, "")
                self.set_key_image(key_id, processed_path)
        else:
            # Turn ON: Restore original icons
            logger.info("Turning display ON (restoring icons)")
            self.update_all_keys()
            
        return True

    def set_key_image(self, key: int, image_path: str):
        """Send an image to a specific key"""
        if not self.device:
            return

        try:
            if not os.path.exists(image_path):
                logger.error(f"Image not found: {image_path}")
                return

            with open(image_path, "rb") as f:
                img_data = f.read()

            size = len(img_data)
            logger.debug(f"Sending image to key {key} ({size} bytes)")

            # 1. Send Header (Prefix + BAT + size[4] + key[1])
            # size is big-endian 4 bytes
            header = PREFIX + CMD_BAT + size.to_bytes(4, "big") + bytes([key])
            self._send_report(header)

            # 2. Send Data Chunks (raw data, 512 bytes each, NO PREFIX)
            for i in range(0, size, REPORT_SIZE):
                chunk = img_data[i : i + REPORT_SIZE]
                self._send_report(chunk)

            # 3. Send Refresh/Stop Command
            refresh = PREFIX + CMD_STP
            self._send_report(refresh)

        except Exception as e:
            logger.error(f"Failed to set image for key {key}: {e}")

    def update_all_keys(self):
        """Apply icons to all configured keys"""
        logger.info("Applying icons to all keys...")
        for key_id in range(1, 16):
            binding = self.config.get_binding(key_id)
            icon_path = None
            label = ""

            if binding:
                label = binding.name
                if binding.icon_spec:
                    if binding.icon_spec.startswith("auto:"):
                        icon_path = self.icon_manager.find_system_icon(binding.icon_spec[5:])
                    else:
                        icon_path = binding.icon_spec

            # Prepare icon (will create default if path is None)
            processed_path = self.icon_manager.prepare_icon(icon_path, label)
            self.set_key_image(key_id, processed_path)

        logger.info("✅ All icons applied")

    def shutdown(self):
        """Clean shutdown"""
        logger.info("Shutting down...")

        if self.device:
            try:
                self.device.close()
                logger.info("Device closed")
            except Exception as e:
                logger.error(f"Error closing device: {e}")

        if self.icon_manager:
            self.icon_manager.cleanup()

        logger.info("✅ Shutdown complete")


def main():
    """Entry point"""
    import signal

    launcher = StreamDockLauncherDirect()

    # Setup signal handlers
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}")
        launcher.running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Initialize
    if not launcher.initialize():
        logger.error("Failed to initialize launcher")
        return 1

    # Run
    launcher.run()

    return 0


if __name__ == '__main__':
    sys.exit(main())
