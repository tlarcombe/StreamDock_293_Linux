"""
Action System for Stream Dock Launcher
Defines different types of actions that can be bound to keys
"""
import subprocess
import os
import shlex
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class Action(ABC):
    """Base class for all actions"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize action from config dictionary

        Args:
            config: Action configuration from JSON
        """
        self.name = config.get('name', 'Unnamed Action')
        self.description = config.get('description', '')
        self.modifiers = config.get('modifiers', {})  # Future: ctrl, shift, alt

    @abstractmethod
    def execute(self) -> bool:
        """
        Execute the action

        Returns:
            bool: True if successful, False otherwise
        """
        pass

    def can_execute_with_modifiers(self, ctrl: bool = False, shift: bool = False, alt: bool = False) -> bool:
        """
        Check if action can execute with given modifiers (future feature)

        Args:
            ctrl: CTRL key pressed
            shift: SHIFT key pressed
            alt: ALT key pressed

        Returns:
            bool: True if modifiers match
        """
        # For now, only execute if no modifiers required
        if not self.modifiers:
            return not (ctrl or shift or alt)

        # Future: Check if modifiers match required modifiers
        return (self.modifiers.get('ctrl', False) == ctrl and
                self.modifiers.get('shift', False) == shift and
                self.modifiers.get('alt', False) == alt)

    def __repr__(self):
        return f"{self.__class__.__name__}(name='{self.name}')"


class LaunchAppAction(Action):
    """Launch a desktop application"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.command = config.get('command', '')
        self.args = config.get('args', [])
        self.detach = config.get('detach', True)  # Run in background

        if not self.command:
            raise ValueError("LaunchAppAction requires 'command' in config")

    def execute(self) -> bool:
        """Launch the application"""
        try:
            cmd = [self.command] + self.args

            logger.info(f"Launching app: {' '.join(cmd)}")

            if self.detach:
                # Launch in background, don't wait
                subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
            else:
                # Wait for completion
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.error(f"App failed: {result.stderr}")
                    return False

            logger.info(f"✅ Launched: {self.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to launch {self.name}: {e}")
            return False


class RunScriptAction(Action):
    """Run a bash script"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.script_path = config.get('script', '')
        self.args = config.get('args', [])
        self.working_dir = config.get('working_dir')
        self.detach = config.get('detach', False)

        if not self.script_path:
            raise ValueError("RunScriptAction requires 'script' in config")

        # Expand ~ and environment variables
        self.script_path = os.path.expanduser(os.path.expandvars(self.script_path))

        if not os.path.exists(self.script_path):
            logger.warning(f"Script not found: {self.script_path}")

    def execute(self) -> bool:
        """Run the script"""
        try:
            if not os.path.exists(self.script_path):
                logger.error(f"Script not found: {self.script_path}")
                return False

            # Make sure script is executable
            if not os.access(self.script_path, os.X_OK):
                os.chmod(self.script_path, 0o755)

            cmd = [self.script_path] + self.args

            logger.info(f"Running script: {' '.join(cmd)}")

            kwargs = {
                'cwd': self.working_dir if self.working_dir else None
            }

            if self.detach:
                subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                    **kwargs
                )
            else:
                result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
                if result.returncode != 0:
                    logger.error(f"Script failed: {result.stderr}")
                    return False
                logger.info(f"Script output: {result.stdout}")

            logger.info(f"✅ Executed: {self.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to run script {self.name}: {e}")
            return False


class RunCommandAction(Action):
    """Run an arbitrary shell command"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.command = config.get('command', '')
        self.shell = config.get('shell', True)
        self.detach = config.get('detach', False)
        self.working_dir = config.get('working_dir')

        if not self.command:
            raise ValueError("RunCommandAction requires 'command' in config")

    def execute(self) -> bool:
        """Execute the command"""
        try:
            logger.info(f"Running command: {self.command}")

            kwargs = {
                'cwd': self.working_dir if self.working_dir else None,
                'shell': self.shell
            }

            if self.detach:
                subprocess.Popen(
                    self.command,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                    **kwargs
                )
            else:
                result = subprocess.run(
                    self.command,
                    capture_output=True,
                    text=True,
                    **kwargs
                )
                if result.returncode != 0:
                    logger.error(f"Command failed: {result.stderr}")
                    return False
                logger.info(f"Command output: {result.stdout}")

            logger.info(f"✅ Executed: {self.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to run command {self.name}: {e}")
            return False


class ToggleDisplayAction(Action):
    """Toggle the Stream Dock display on/off"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.callback = None # Set by launcher after creation

    def execute(self) -> bool:
        """Execute the toggle via callback"""
        if self.callback:
            logger.info("Triggering display toggle callback")
            return self.callback()
        else:
            logger.warning("ToggleDisplayAction executed but no callback set")
            return False


class NoAction(Action):
    """Placeholder action that does nothing"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.name = config.get('name', 'Unassigned')

    def execute(self) -> bool:
        """Do nothing"""
        logger.debug(f"No action assigned")
        return True


# Action factory
ACTION_TYPES = {
    'launch_app': LaunchAppAction,
    'run_script': RunScriptAction,
    'run_command': RunCommandAction,
    'toggle_display': ToggleDisplayAction,
    'none': NoAction,
}


def create_action(config: Dict[str, Any]) -> Action:
    """
    Factory function to create actions from config

    Args:
        config: Action configuration dictionary with 'type' key

    Returns:
        Action instance

    Raises:
        ValueError: If action type is unknown
    """
    action_type = config.get('type', 'none')

    if action_type not in ACTION_TYPES:
        raise ValueError(f"Unknown action type: {action_type}")

    action_class = ACTION_TYPES[action_type]
    return action_class(config)
