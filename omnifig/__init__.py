
from .loading import get_profile

from .decorators import AutoScript, Script, Component, AutoComponent, Modifier, AutoModifier, Modification

from .config import ConfigIter
Component('iter')(ConfigIter)
del ConfigIter

from .top import get_project, get_current_project, \
	entry, main, run, quick_run, initialize, cleanup, \
	get_config, create_component, quick_create, \
	register_script, register_config, register_component, \
	register_config_dir, register_modifier, resolve_order

from . import projects
from .modes import Run_Mode
from .rules import Meta_Rule
from . import debug
from . import help
from .common import Configurable

from humpack import AbortTransaction


import os
__info__ = {'__file__':os.path.join(os.path.abspath(os.path.dirname(__file__)), '_info.py')}
with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), '_info.py'), 'r') as f:
	exec(f.read(), __info__)
del os
del __info__['__file__']
__author__ = __info__['author']
__version__ = __info__['version']
