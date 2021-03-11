
from .loading import get_profile

from .decorators import AutoScript, Script, Component, AutoComponent, Modifier, AutoModifier, Modification

from .config import ConfigIter, EmptyElement
Component('iter')(ConfigIter)
del ConfigIter

from .top import get_project, get_current_project, \
	entry, main, run, quick_run, initialize, cleanup, \
	get_config, create_component, quick_create, \
	register_script, register_config, register_component, \
	register_config_dir, register_modifier, resolve_order, \
	find_script, find_component, find_modifier, find_config, \
	has_script, has_component, has_config, has_modifier, \
	view_configs, view_components, view_scripts, view_modifiers

from .rules import Meta_Rule
from .modes import Run_Mode
from . import common
from .common import Configurable
# from .farming import Farmer, Worker

from humpack import AbortTransaction

import os
__info__ = {'__file__':os.path.join(os.path.abspath(os.path.dirname(__file__)), '_info.py')}
with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), '_info.py'), 'r') as f:
	exec(f.read(), __info__)
del os
del __info__['__file__']
__author__ = __info__['author']
__version__ = __info__['version']
