
from .registry import AutoScript, Script, Component, AutoComponent, Modifier, AutoModifier, Modification, \
	create_component, register_component, register_modifier, \
	view_component_registry, view_modifier_registry, view_script_registry
from .config import get_config, MissingConfigError
from .preload import register_config, register_config_dir
from .scripts import entry, main, full_run, initialize, run, quick_run
from .loading import get_project, get_profile
from .containers import Registry, Entry_Registry
from .modes import Run_Mode, Meta_Argument
from .debug import Debug_Mode

import os
__info__ = {'__file__':os.path.join(os.path.abspath(os.path.dirname(__file__)), '_info.py')}
with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), '_info.py'), 'r') as f:
	exec(f.read(), __info__)
del os
del __info__['__file__']
__author__ = __info__['author']
__version__ = __info__['version']
