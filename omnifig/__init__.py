
from .registry import AutoScript, Script, Component, AutoComponent, Modifier, AutoModifier, Modification, \
	create_component, register_component, register_modifier, \
	view_component_registry, view_modifier_registry, view_script_registry
from .config import get_config, parse_config, MissingConfigError
from .preload import register_config, register_config_dir
from .scripts import entry, main, full_run, initialize, run, quick_run
from .loading import get_project, get_profile
from .containers import Registry, Entry_Registry
from .modes import Run_Mode, Meta_Argument
from .debug import Debug_Mode

import os
from omnibelt import load_yaml
__info__ = load_yaml(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.fig.yaml'))
__author__ = __info__['author']
__version__ = __info__['version']
