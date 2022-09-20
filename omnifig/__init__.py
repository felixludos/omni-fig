from .organization import get_profile, Profile, ProfileBase, ProjectBase, GeneralProject, register_meta_rule, Meta_Rule
from .registration import autofill_with_config, register_script, register_component, register_modifier, \
	register_creator, register_autoscript, Script, Component, Modifier, Creator, AutoScript
from .top import get_current_project, get_project, switch_project, iterate_projects, \
	entry, main, run, quick_run, initialize, cleanup, create_config

# from .config import ConfigIter
from .config import ConfigNode, ConfigManager

# Component('iter')(ConfigIter)
# del ConfigIter

from . import common
# from .common import Configurable
from omnifig.old.errors import MissingParameterError
from .old import novo
# from .farming import Farmer, Worker

import os
__info__ = {'__file__':os.path.join(os.path.abspath(os.path.dirname(__file__)), '_info.py')}
with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), '_info.py'), 'r') as f:
	exec(f.read(), __info__)
del os
del __info__['__file__']
__author__ = __info__['author']
__version__ = __info__['version']
