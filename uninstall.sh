#!/bin/bash
#
# Stream Dock Launcher Uninstaller
# Removes Stream Dock Launcher systemd service
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "============================================================"
echo "Stream Dock Launcher Uninstaller"
echo "============================================================"
echo ""

# Check if service exists
if [ -f "$HOME/.config/systemd/user/streamdock-launcher.service" ]; then
    echo "Stopping and disabling service..."

    # Stop the service if running
    if systemctl --user is-active streamdock-launcher.service >/dev/null 2>&1; then
        systemctl --user stop streamdock-launcher.service
        echo -e "${GREEN}✓ Service stopped${NC}"
    fi

    # Disable the service if enabled
    if systemctl --user is-enabled streamdock-launcher.service >/dev/null 2>&1; then
        systemctl --user disable streamdock-launcher.service
        echo -e "${GREEN}✓ Service disabled${NC}"
    fi

    # Remove service file
    rm -f "$HOME/.config/systemd/user/streamdock-launcher.service"
    systemctl --user daemon-reload

    echo -e "${GREEN}✓ Service removed${NC}"
else
    echo "Service not found - nothing to uninstall"
fi

echo ""
echo "============================================================"
echo -e "${GREEN}Uninstallation Complete!${NC}"
echo "============================================================"
echo ""
echo "The application files remain in ~/projects/StreamDock"
echo "To completely remove, run: rm -rf ~/projects/StreamDock"
echo ""
