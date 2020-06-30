
from .registry import AutoScript, Script, Component, AutoComponent, Modifier, AutoModifier, Modification, \
	create_component, register_component, register_modifier, \
	view_component_registry, view_modifier_registry, view_script_registry
from .config import get_config, parse_config
from .scripts import entry, main, run

from .modes import Run_Mode, Meta_Argument



# import sys, os
#
# import __main__
# print(__main__)
#
# print(os.path.abspath(sys.modules['__main__'].__file__))