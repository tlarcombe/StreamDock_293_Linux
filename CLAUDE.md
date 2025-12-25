# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

StreamDock Launcher is a Python-based application launcher for the Stream Dock 293 hardware device. It uses direct HID communication to bypass the buggy SDK C library, providing reliable key press detection and icon display functionality.

## Key Commands

### Running the Application

```bash
# Manual test run (from project root)
python3 bin/streamdock_launcher.py

# Service management
systemctl --user start streamdock-launcher
systemctl --user stop streamdock-launcher
systemctl --user restart streamdock-launcher  # After config changes
systemctl --user status streamdock-launcher

# View logs
journalctl --user -u streamdock-launcher -f
```

### Installation/Uninstallation

```bash
./install.sh      # Sets up dependencies, udev rules, systemd service
./uninstall.sh    # Removes service and udev rules
```

## Architecture

### Core Components

1. **bin/streamdock_launcher.py** - Main entry point
   - `StreamDockLauncherDirect` class: Core launcher using direct HID
   - Manages device connection, event loop, and action execution
   - Key physical-to-logical mapping (15 buttons in 3x5 grid)
   - Display toggle feature (sleep mode with zero brightness)

2. **lib/launcher/config_loader.py** - Configuration management
   - `LauncherConfig`: Loads/saves JSON configuration
   - `KeyBinding`: Represents individual key bindings (1-15)
   - Validates config and creates action instances

3. **lib/launcher/actions.py** - Action system
   - `Action` base class with execute() method
   - `LaunchAppAction`: Launch desktop applications
   - `RunScriptAction`: Execute shell scripts
   - `RunCommandAction`: Run arbitrary commands
   - `ToggleDisplayAction`: Sleep mode (brightness 0 + black icons)
   - `NoAction`: Placeholder for unassigned keys
   - Factory pattern via `create_action()`

4. **lib/launcher/icon_manager.py** - Icon processing
   - `IconManager`: Handles icon loading, resizing, caching
   - Processes icons to 96x96 canvas with 72x72 icon size
   - Applies 180° rotation for Stream Dock 293 orientation
   - Converts to JPEG format for HID transmission
   - Auto-finds system icons from `/usr/share/icons`

### HID Protocol Constants

Located in `bin/streamdock_launcher.py`:
- `VENDOR_ID = 0x5500`, `PRODUCT_ID = 0x1001`
- Prefix: `b"CRT\x00\x00"`
- Commands: `CMD_BAT` (set button), `CMD_WPA` (wallpaper), `CMD_LIG` (brightness), `CMD_CLE` (clear), `CMD_STP` (stop/refresh)
- Report size: 512 bytes

### Data Flow

1. Config loaded from `config/config.json`
2. HID device opened via `python-hidapi`
3. Icons processed and uploaded to device (one by one with delays)
4. Main loop polls HID for key press events (512-byte reports)
5. Physical key codes mapped to logical keys (1-15)
6. Key bindings execute corresponding actions

### Key Mapping

Physical codes (from HID) → Logical keys (1-15):
```
Top row:    0x0b→1, 0x0c→2, 0x0d→3, 0x0e→4, 0x0f→5
Middle row: 0x06→6, 0x07→7, 0x08→8, 0x09→9, 0x0a→10
Bottom row: 0x01→11, 0x02→12, 0x03→13, 0x04→14, 0x05→15
```

### Configuration Structure

`config/config.json` defines:
- Device settings (brightness, background)
- Key bindings (1-15) with name, description, icon, action
- Icon specs: `"auto:app-name"` (auto-detect), `"/path/to/icon.png"` (direct), or `null` (text only)
- Action types: `launch_app`, `run_script`, `run_command`, `toggle_display`, `none`

## Critical Implementation Details

### Display Toggle (Sleep Mode)
When toggling off (`set_brightness(0)`):
- Sweeps ALL 256 indices with brightness 0 for absolute blackout
- Sends black icons to all keys
- Neutralizes background slots (indices 17, 0, 16, 18)

When toggling on:
- Restores original brightness and icons
- Re-applies background and all key images

### Icon Programming Sequence
1. Send `CMD_CLE` to clear persistent state
2. Deep clean: wipe all 256 indices with `DEL` and zero brightness
3. Global reset with `CRTINT` command
4. Neutralize wallpaper with black frames on multiple indices
5. Apply key icons one by one with 0.1s delays

### Image Transmission Protocol
1. Send header: `PREFIX + CMD + size(4 bytes big-endian) + index(1 byte)`
2. Send data in 512-byte chunks (raw data, no prefix)
3. Send stop/refresh: `PREFIX + CMD_STP`

## Important Notes

- Always use 0.1s+ delays when sending multiple HID commands
- Icons must be 96x96 JPEG with 180° rotation
- Background is 480x272 (full screen resolution)
- Wallpaper index 17 is the primary background slot
- Device reconnection logic handles USB disconnects
- Temp icons stored in `/tmp/streamdock_icons/`

## Testing & Debugging

- Manual test: `python3 bin/streamdock_launcher.py` (Ctrl+C to exit)
- Check device: `lsusb | grep 5500`
- Check permissions: `ls -l /dev/hidraw*` and `groups` (need `plugdev`)
- Service logs show key presses and HID events
- Debug logging shows raw HID data and command sequences
