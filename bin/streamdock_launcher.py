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
CMD_WPA = b"WPA"

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
        
        try:
            # Ensure payload is exactly REPORT_SIZE (512)
            if len(payload) > REPORT_SIZE:
                payload = payload[:REPORT_SIZE]
            elif len(payload) < REPORT_SIZE:
                payload = payload.ljust(REPORT_SIZE, b"\x00")
                
            # Send with leading 0x00 (Report ID 0)
            # Total size sent to hidapi.write() is 513 bytes
            self.device.write(b"\x00" + payload)
        except OSError as e:
            logger.warning(f"HID write error: {e}")
            # Try to re-open device on next attempt if it's a fatal-looking error
            if "device" in str(e).lower() or "broken pipe" in str(e).lower():
                self.device = None
        except Exception as e:
            logger.error(f"Unexpected error in _send_report: {e}")

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
        self.icon_manager = IconManager(button_size=(96, 96), rotation=180, icon_size=(72, 72))

        # Open HID device directly
        logger.info(f"Opening HID device (VID: 0x{VENDOR_ID:04x}, PID: 0x{PRODUCT_ID:04x})...")
        self.device = hid.device()
        try:
            self.device.open(VENDOR_ID, PRODUCT_ID)
            # self.device.set_nonblocking(1)  # Switching to explicit timeout in read()
            logger.info("✅ Device opened successfully (Direct HID)")

            # Get device info
            manufacturer = self.device.get_manufacturer_string()
            product = self.device.get_product_string()
            logger.info(f"  Manufacturer: {manufacturer}")
            logger.info(f"  Product: {product}")

            # Apply initial configuration
            self.set_brightness(self.config.brightness)
            
            # 1. Clear screen
            logger.info("Sending screen clear command (CMD_CLE)...")
            self.clear_screen()

            # 2. Deep Clean - Wipe all indices (0-255) with DEL and LIG(0)
            logger.info("Performing deep clean (Wiping all 256 indices)...")
            self.deep_clean()
            
            # Final attempt at a Global Reset/Initialize command
            logger.info("Sending Global Reset (CRTINT)...")
            self._send_report(PREFIX + b"INT" + (0).to_bytes(4, 'big') + b"\x00")
            time.sleep(0.5)

            # Additional targeted background clear with a physical black image
            logger.info("Neutralizing wallpaper with black frame...")
            black_bg = self.icon_manager.prepare_background("black")
            for idx in [17, 0, 16, 18]:
                self.set_key_image(idx, black_bg, cmd=CMD_WPA)
                time.sleep(0.1)

            # 3. Apply key icons ONE BY ONE with delays
            self.update_all_keys(include_background=False)

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
            last_heartbeat = time.time()
            while self.running:
                # Re-initialize device if it was lost
                if not self.device:
                    logger.info("Attempting to reconnect HID device...")
                    try:
                        self.device = hid.device()
                        self.device.open(VENDOR_ID, PRODUCT_ID)
                        # self.device.set_nonblocking(1)
                        logger.info("✅ Reconnected successfully")
                        self.set_brightness(self.config.brightness)
                        self.update_all_keys(include_background=True)
                    except Exception as e:
                        logger.debug(f"Reconnection attempt failed: {e}")
                        time.sleep(2)
                        continue

                # Periodic heartbeat log (every 10 seconds - kept at debug level)
                if time.time() - last_heartbeat > 10:
                    logger.debug("HID Polling heartbeat...")
                    last_heartbeat = time.time()

                try:
                    # Read from HID device with small timeout
                    # Use REPORT_SIZE (512) as per endpoint wMaxPacketSize
                    data = self.device.read(REPORT_SIZE, timeout_ms=50)

                    if data:
                        logger.debug(f"HID Data Received ({len(data)} bytes): {bytes(data).hex()}")

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

                except (OSError, ValueError) as e:
                    # Log as warning if it looks like a disconnection
                    # ValueError is thrown by some versions of hidapi when device is closed
                    logger.warning(f"HID read error ({type(e).__name__}): {e}")
                    self.device = None # Trigger reconnection
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
            # If value is 0, we perform a sweep of all possible indices to ensure absolute blackout
            if value == 0:
                logger.info("  Zero brightness requested (Absolute Blackout)")
                # 1. Send Global 0
                self._send_report(PREFIX + CMD_LIG + bytes([0]))
                
                # 2. Sweep all per-index candidates
                for idx in range(256):
                    # Format: PREFIX + CMD_LIG + size(0) + index
                    payload = PREFIX + CMD_LIG + (0).to_bytes(4, 'big') + bytes([idx])
                    self._send_report(payload)
            else:
                # Normal global brightness command
                payload = PREFIX + CMD_LIG + bytes([value])
                self._send_report(payload)
        except Exception as e:
            logger.error(f"Failed to set brightness: {e}")

    def clear_screen(self):
        """Send CMD_CLE to reset the persistent background/screen state"""
        if not self.device:
            return

        logger.info("Sending screen clear command (CMD_CLE)...")
        try:
            # Command: PREFIX + CMD_CLE
            payload = PREFIX + CMD_CLE
            self._send_report(payload)
            # Give the device a moment to process the clear
            time.sleep(0.1)
        except Exception as e:
            logger.error(f"Failed to clear screen: {e}")

    def toggle_display(self) -> bool:
        """Toggle the display on/off"""
        self.display_on = not self.display_on
        state_str = "ON" if self.display_on else "OFF"
        logger.info(f"Toggling display: {state_str}")

        if not self.display_on:
            # Turn OFF: Sweep all indices to 0 brightness and send black icons
            logger.info("Turning display OFF (absolute blackout)")
            self.set_brightness(0)
            
            # Set background to black (just in case)
            black_bg = self.icon_manager.prepare_background("black")
            for idx in [17, 0, 16, 18]:
                self.set_key_image(idx, black_bg, cmd=CMD_WPA)
            
            # Send black icons to all keys to be thorough
            for key_id in range(1, 16):
                processed_path = self.icon_manager.prepare_icon(None, "")
                self.set_key_image(key_id, processed_path)
        else:
            # Turn ON: Restore original icons and brightness
            logger.info("Turning display ON (restoring icons and brightness)")
            
            # Restore brightness
            self.set_brightness(self.config.brightness)
            
            # Restore background
            bg_path = self.icon_manager.prepare_background(self.config.background or "black")
            self.set_key_image(17, bg_path, cmd=CMD_WPA)
                
            self.update_all_keys(include_background=False)
            
        return True

    def set_key_image(self, key: int, image_path: str, cmd: bytes = CMD_BAT):
        """Send an image to a specific key or wallpaper"""
        if not self.device:
            return

        try:
            if not os.path.exists(image_path):
                logger.error(f"Image not found: {image_path}")
                return

            with open(image_path, "rb") as f:
                img_data = f.read()

            size = len(img_data)
            logger.debug(f"Sending image to {cmd.decode()} index {key} ({size} bytes)")

            # 1. Send Header (Prefix + CMD + size[4] + key[1])
            # size is big-endian 4 bytes
            header = PREFIX + cmd + size.to_bytes(4, "big") + bytes([key])
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

    def deep_clean(self):
        """Exhaustively wipe all possible indices on the device"""
        logger.info("  Sending CMD_DEL to all indices (0-255)...")
        for idx in range(256):
            payload = PREFIX + b"DEL" + (0).to_bytes(4, 'big') + bytes([idx])
            self._send_report(payload)
            if idx % 64 == 0: time.sleep(0.1)
            
        logger.info("  Sending zero brightness (CMD_LIG) to all indices (0-255)...")
        for idx in range(256):
            # Try setting brightness to 0 for each index
            payload = PREFIX + CMD_LIG + (0).to_bytes(4, 'big') + bytes([idx])
            self._send_report(payload)
            if idx % 64 == 0: time.sleep(0.1)

        time.sleep(0.5)

    def update_all_keys(self, include_background: bool = False):
        """Apply icons to all configured keys ONE BY ONE"""
        logger.info("Applying icons to all keys one by one...")
        for key_id in range(1, 16):
            logger.info(f"  Programming button {key_id}...")
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
            
            # Reduced delay for faster responsiveness as requested
            time.sleep(0.1)

        if include_background:
            # Neutralize background slots if requested
            bg_path = self.icon_manager.prepare_background(self.config.background or "black")
            for idx in [17, 0, 16, 18, 19, 32, 64, 128, 255]:
                self.set_key_image(idx, bg_path, cmd=CMD_WPA)
                time.sleep(0.2)

        logger.info("✅ All icons applied one by one")

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
