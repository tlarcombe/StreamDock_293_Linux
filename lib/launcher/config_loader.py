"""
Configuration Loader for Stream Dock Launcher
Loads and validates configuration from JSON
"""
import json
import os
from typing import Dict, Any, Optional
import logging

try:
    from .actions import create_action, Action
except ImportError:
    from actions import create_action, Action

logger = logging.getLogger(__name__)


class KeyBinding:
    """Represents a single key binding"""

    def __init__(self, key_number: int, config: Dict[str, Any]):
        """
        Initialize key binding

        Args:
            key_number: Key number (1-15)
            config: Configuration dictionary for this key
        """
        self.key_number = key_number
        self.name = config.get('name', f'Key {key_number}')
        self.description = config.get('description', '')
        self.icon_spec = config.get('icon')  # Path, 'auto:name', or None

        # Parse action
        action_config = config.get('action', {'type': 'none'})
        action_config['name'] = self.name  # Pass name to action
        action_config['description'] = self.description

        try:
            self.action = create_action(action_config)
        except Exception as e:
            logger.error(f"Failed to create action for key {key_number}: {e}")
            self.action = create_action({'type': 'none', 'name': self.name})

    def __repr__(self):
        return f"KeyBinding(key={self.key_number}, name='{self.name}', action={self.action})"


class LauncherConfig:
    """Configuration for the entire launcher"""

    def __init__(self, config_path: str):
        """
        Load configuration from file

        Args:
            config_path: Path to config.json
        """
        self.config_path = os.path.expanduser(config_path)
        self.bindings: Dict[int, KeyBinding] = {}
        self.brightness = 80
        self.background = None

        self._load()

    def _load(self):
        """Load configuration from file"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)

            # Load device settings
            device_config = config.get('device', {})
            self.brightness = device_config.get('brightness', 80)
            self.background = device_config.get('background')

            # Load key bindings
            keys_config = config.get('keys', {})
            for key_str, key_config in keys_config.items():
                try:
                    key_number = int(key_str)
                    if 1 <= key_number <= 15:
                        self.bindings[key_number] = KeyBinding(key_number, key_config)
                    else:
                        logger.warning(f"Invalid key number: {key_number} (must be 1-15)")
                except ValueError:
                    logger.warning(f"Invalid key number format: {key_str}")

            logger.info(f"Loaded configuration from {self.config_path}")
            logger.info(f"  Bindings: {len(self.bindings)} keys configured")

        except FileNotFoundError:
            logger.error(f"Config file not found: {self.config_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            raise

    def get_binding(self, key_number: int) -> Optional[KeyBinding]:
        """
        Get binding for a key

        Args:
            key_number: Key number (1-15)

        Returns:
            KeyBinding or None if not configured
        """
        return self.bindings.get(key_number)

    def reload(self):
        """Reload configuration from file"""
        logger.info("Reloading configuration...")
        self.bindings.clear()
        self._load()

    def save(self):
        """Save current configuration to file"""
        try:
            config = {
                'device': {
                    'brightness': self.brightness,
                    'background': self.background
                },
                'keys': {}
            }

            for key_num, binding in self.bindings.items():
                config['keys'][str(key_num)] = {
                    'name': binding.name,
                    'description': binding.description,
                    'icon': binding.icon_spec,
                    'action': {
                        'type': binding.action.__class__.__name__.replace('Action', '').lower(),
                        # ... more action details would go here
                    }
                }

            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)

            logger.info(f"Saved configuration to {self.config_path}")

        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            raise
