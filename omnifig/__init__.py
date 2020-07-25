
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


# import sys, os
#
# import __main__
# print(__main__)
#
# print(os.path.abspath(sys.modules['__main__'].__file__))