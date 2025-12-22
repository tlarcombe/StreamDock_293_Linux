# Yinker 293 Stream Dock Launcher

A customizable application launcher for Stream Dock devices on Linux.

## Features

- ✅ **Direct HID Communication** - No proprietary software required
- ✅ **Customizable Key Bindings** - Assign applications, scripts, or commands to any key
- ✅ **Auto Icon Detection** - Automatically finds system icons for applications
- ✅ **Display Toggle (Sleep Mode)** - Turn off backlight (0%) and icons for total darkness
- ✅ **Systemd Service** - Runs automatically on startup
- ✅ **Zero-Glow Sleep** - Explicit brightness control eliminates backlight bleed
- ✅ **Crash-Free** - Bypasses buggy SDK C library with direct HID access

## Supported Devices

- Stream Dock 293 (VID: 0x5500, PID: 0x1001)

## Requirements

- Linux (Arch/Manjaro or Debian/Ubuntu)
- Python 3
- python-hidapi
- python-pillow

## Installation

Run the installer script:

```bash
cd ~/projects/StreamDock
./install.sh
```

The installer will:
1. Check and install required dependencies
2. Configure USB permissions (udev rules)
3. Install systemd user service
4. Optionally enable and start the service

**Note:** You may need to log out and back in after installation for group permissions to take effect.

## Configuration

Edit the configuration file at `~/projects/StreamDock/config/config.json`:

```json
{
  "device": {
    "brightness": 80,
    "background": null
  },
  "keys": {
    "1": {
      "name": "LibreOffice Writer",
      "description": "Open LibreOffice Writer",
      "icon": "auto:libreoffice-writer",
      "action": {
        "type": "launch_app",
        "command": "libreoffice",
        "args": ["--writer"],
        "detach": true
      }
    }
  }
}
```

### Action Types

#### 1. Launch Application

```json
{
  "type": "launch_app",
  "command": "firefox",
  "args": [],
  "detach": true
}
```

#### 2. Run Script

```json
{
  "type": "run_script",
  "script": "~/scripts/my-script.sh",
  "args": [],
  "detach": false
}
```

#### 3. Run Command

```json
{
  "type": "run_command",
  "command": "pactl set-sink-volume @DEFAULT_SINK@ +5%",
  "detach": false
}
```
#### 4. Display Toggle
Special action to turn the unit dark:
```json
{
  "type": "toggle_display"
}
```
*Note: In sleep mode, buttons remain active. A second press on the toggle key restores icons and brightness.*

### Icon Specifications

- **Auto-detect**: `"auto:firefox"` - Automatically finds system icon
- **Direct path**: `"/path/to/icon.png"` - Use a specific icon file
- **No icon**: `null` - Display key label only

## Usage

### Service Management

```bash
# Start the service
systemctl --user start streamdock-launcher

# Stop the service
systemctl --user stop streamdock-launcher

# Check status
systemctl --user status streamdock-launcher

# View logs
journalctl --user -u streamdock-launcher -f

# Restart after config changes
systemctl --user restart streamdock-launcher
```

### Manual Launch (for testing)

```bash
cd ~/projects/StreamDock
python3 bin/streamdock_launcher.py
```

Press Ctrl+C to exit.

## Troubleshooting

### Device Not Found

1. Check if device is connected:
   ```bash
   lsusb | grep 5500
   ```

2. Check USB permissions:
   ```bash
   ls -l /dev/hidraw*
   ```

3. Ensure you're in the `plugdev` group:
   ```bash
   groups
   ```

### Service Won't Start

Check the service logs:
```bash
journalctl --user -u streamdock-launcher -n 50
```

### Icons Displaying
Icons are now supported using direct HID commands. The launcher automatically processes images to the required format (100x100 JPEG, 180° rotation) and sends them to the device on startup.

### Button Presses Not Detected

1. Make sure no other application is accessing the device
2. Try unplugging and replugging the Stream Dock
3. Check that udev rules are installed: `/etc/udev/rules.d/99-streamdock.rules`

## Uninstallation

Run the uninstaller script:

```bash
cd ~/projects/StreamDock
./uninstall.sh
```

To completely remove all files:

```bash
rm -rf ~/projects/StreamDock
```

## Architecture

The launcher uses direct HID communication instead of the SDK's C library to avoid crashes:

- **Direct HID**: Uses Python `hid` library for USB communication
- **Event Loop**: Polls for key press events without callbacks
- **No SDK**: Bypasses the buggy `libtransport.so` completely

## Known Limitations

- **Icon Setting Support**: Correctly sets key icons using direct HID protocol
- **Stream Dock 293 Only**: Only tested with Stream Dock 293
- **Linux Only**: Windows and macOS not supported

## Future Enhancements

- [x] Implement direct HID commands for setting key icons
- [x] Implement Sleep Mode (backlight 0% + black icons)
- [x] Support for custom minimalist icons
- [ ] Support for other Stream Dock models
- [ ] GUI configuration tool
- [ ] Multi-page support

## License

This project uses the [Stream Dock Plugin SDK](https://github.com/MiraboxSpace/StreamDock-Plugin-SDK) for reference.

## Credits

- Stream Dock SDK by Mirabox Space
- Developed using Claude Code

## Support

For issues or questions, please check:
- Configuration file: `~/projects/StreamDock/config/config.json`
- Service logs: `journalctl --user -u streamdock-launcher`
- USB device: `lsusb | grep 5500`
