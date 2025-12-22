#!/bin/bash
#
# Stream Dock Launcher Installer
# Installs Stream Dock Launcher as a systemd service for the current user
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Determine script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "============================================================"
echo "Stream Dock Launcher Installer"
echo "============================================================"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Error: Do not run this installer as root${NC}"
    echo "This installer sets up a user systemd service"
    exit 1
fi

# Check for required dependencies
echo "Checking dependencies..."

MISSING_DEPS=()

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    MISSING_DEPS+=("python3")
fi

# Check for pip/pacman
if command -v pacman &> /dev/null; then
    PKG_MANAGER="pacman"
elif command -v apt &> /dev/null; then
    PKG_MANAGER="apt"
else
    echo -e "${RED}Error: Unsupported package manager${NC}"
    echo "This installer supports pacman (Arch/Manjaro) and apt (Debian/Ubuntu)"
    exit 1
fi

# Check for python-hidapi
if ! python3 -c "import hid" 2>/dev/null; then
    if [ "$PKG_MANAGER" = "pacman" ]; then
        MISSING_DEPS+=("python-hidapi")
    else
        MISSING_DEPS+=("python3-hid")
    fi
fi

# Check for python-pillow
if ! python3 -c "from PIL import Image" 2>/dev/null; then
    if [ "$PKG_MANAGER" = "pacman" ]; then
        MISSING_DEPS+=("python-pillow")
    else
        MISSING_DEPS+=("python3-pil")
    fi
fi

# Install missing dependencies
if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    echo -e "${YELLOW}Missing dependencies: ${MISSING_DEPS[*]}${NC}"
    echo "Installing dependencies..."

    if [ "$PKG_MANAGER" = "pacman" ]; then
        sudo pacman -S --needed --noconfirm "${MISSING_DEPS[@]}"
    else
        sudo apt update
        sudo apt install -y "${MISSING_DEPS[@]}"
    fi

    echo -e "${GREEN}✓ Dependencies installed${NC}"
else
    echo -e "${GREEN}✓ All dependencies satisfied${NC}"
fi

# Check USB permissions (udev rules)
echo ""
echo "Checking USB permissions..."

UDEV_RULES="/etc/udev/rules.d/99-streamdock.rules"
GROUP_NAME="plugdev"

# Ensure the group exists
if ! getent group "$GROUP_NAME" > /dev/null; then
    echo "Creating group '$GROUP_NAME'..."
    sudo groupadd "$GROUP_NAME"
fi

if [ ! -f "$UDEV_RULES" ]; then
    echo "Creating udev rules for Stream Dock..."

    sudo tee "$UDEV_RULES" > /dev/null << EOF
# udev rules for Stream Dock USB devices
# Stream Dock 293 (VID: 5500, PID: 1001)
SUBSYSTEM=="usb", ATTRS{idVendor}=="5500", ATTRS{idProduct}=="1001", MODE="0666", GROUP="$GROUP_NAME"
KERNEL=="hidraw*", ATTRS{idVendor}=="5500", MODE="0666", GROUP="$GROUP_NAME"
EOF

    sudo udevadm control --reload-rules
    sudo udevadm trigger

    echo -e "${GREEN}✓ USB permissions configured${NC}"
else
    # Check if the existing rules use the correct group
    if ! grep -q "GROUP=\"$GROUP_NAME\"" "$UDEV_RULES"; then
        echo -e "${YELLOW}Updating udev rules to use group '$GROUP_NAME'...${NC}"
        sudo sed -i "s/GROUP=\"[^\"]*\"/GROUP=\"$GROUP_NAME\"/g" "$UDEV_RULES"
        sudo udevadm control --reload-rules
        sudo udevadm trigger
    fi
    echo -e "${GREEN}✓ USB permissions already configured${NC}"
fi

# Add user to group if not already
if ! groups | grep -q "\b$GROUP_NAME\b"; then
    echo "Adding user to $GROUP_NAME group..."
    sudo usermod -a -G "$GROUP_NAME" "$USER"
    echo -e "${YELLOW}⚠ You need to log out and back in for group changes to take effect${NC}"
fi

# Install systemd service
echo ""
echo "Installing systemd service..."

SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_USER_DIR"

# Copy service file and replace %i with actual username
sed "s/%i/$USER/g" "$SCRIPT_DIR/systemd/streamdock-launcher.service" > "$SYSTEMD_USER_DIR/streamdock-launcher.service"

# Reload systemd daemon
systemctl --user daemon-reload

echo -e "${GREEN}✓ Systemd service installed${NC}"

# Ask if user wants to enable and start the service now
echo ""
read -p "Enable and start the service now? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    systemctl --user enable streamdock-launcher.service
    systemctl --user start streamdock-launcher.service

    echo -e "${GREEN}✓ Service enabled and started${NC}"
    echo ""
    echo "Service status:"
    systemctl --user status streamdock-launcher.service --no-pager
else
    echo ""
    echo "Service installed but not enabled."
    echo "To enable and start later, run:"
    echo "  systemctl --user enable --now streamdock-launcher.service"
fi

echo ""
echo "============================================================"
echo -e "${GREEN}Installation Complete!${NC}"
echo "============================================================"
echo ""
echo "Configuration file: $SCRIPT_DIR/config/config.json"
echo ""
echo "Useful commands:"
echo "  Start:   systemctl --user start streamdock-launcher"
echo "  Stop:    systemctl --user stop streamdock-launcher"
echo "  Status:  systemctl --user status streamdock-launcher"
echo "  Logs:    journalctl --user -u streamdock-launcher -f"
echo "  Restart: systemctl --user restart streamdock-launcher"
echo ""
