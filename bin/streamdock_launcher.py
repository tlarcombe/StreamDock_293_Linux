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


class StreamDockLauncherDirect:
    """Direct HID-based launcher (no SDK)"""

    def __init__(self, config_path: str = None):
        self.config_path = config_path or DEFAULT_CONFIG
        self.config = None
        self.device = None
        self.icon_manager = None
        self.running = False

    def initialize(self):
        """Initialize all components"""
        logger.info("=" * 70)
        logger.info("Stream Dock Launcher Starting (Direct HID Mode)...")
        logger.info("=" * 70)

        # Load configuration
        logger.info(f"Loading configuration from: {self.config_path}")
        self.config = LauncherConfig(self.config_path)

        # Initialize icon manager (without SDK device)
        logger.info("Initializing icon manager...")
        self.icon_manager = IconManager(button_size=(100, 100), rotation=0)

        # Open HID device directly
        logger.info(f"Opening HID device (VID: 0x{VENDOR_ID:04x}, PID: 0x{PRODUCT_ID:04x})...")
        self.device = hid.device()
        try:
            self.device.open(VENDOR_ID, PRODUCT_ID)
            self.device.set_nonblocking(1)  # Non-blocking reads
            logger.info("✅ Device opened successfully (Direct HID)")

            # Get device info
            manufacturer = self.device.get_manufacturer_string()
            product = self.device.get_product_string()
            logger.info(f"  Manufacturer: {manufacturer}")
            logger.info(f"  Product: {product}")

        except Exception as e:
            logger.error(f"Failed to open HID device: {e}")
            return False

        logger.info("=" * 70)
        logger.info("✅ Stream Dock Launcher Ready! (Direct HID Mode)")
        logger.info("=" * 70)
        logger.info(f"Configured keys: {sorted(self.config.bindings.keys())}")
        logger.info("Press any key to execute its action")
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
                    data = self.device.read(64)

                    if data and len(data) >= 11:
                        # Check if it's a key event
                        # data[9] = key number (1-15 or 0xFF for status)
                        # data[10] = state (0x01 = pressed, 0x02 = released)

                        if data[9] != 0xFF and data[9] != 0:
                            key = data[9]
                            state = data[10]

                            # Normalize state
                            if state == 0x01:
                                logger.info(f"Key {key} pressed")
                                self._handle_key_press(key)
                            elif state == 0x02:
                                logger.debug(f"Key {key} released")

                except Exception as e:
                    logger.error(f"Error reading HID data: {e}")

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
