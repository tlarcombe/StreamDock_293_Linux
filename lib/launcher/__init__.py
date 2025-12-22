"""
Stream Dock Launcher Package
Customizable application launcher for Stream Dock devices
"""

__version__ = '1.0.0'
__author__ = 'Stream Dock Launcher'

from .actions import Action, LaunchAppAction, RunScriptAction, RunCommandAction, create_action
from .icon_manager import IconManager
from .config_loader import LauncherConfig, KeyBinding

__all__ = [
    'Action',
    'LaunchAppAction',
    'RunScriptAction',
    'RunCommandAction',
    'create_action',
    'IconManager',
    'LauncherConfig',
    'KeyBinding',
]
