import os
__info__ = {'__file__':os.path.join(os.path.abspath(os.path.dirname(__file__)), '_info.py')}
with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), '_info.py'), 'r') as f:
	exec(f.read(), __info__)
del os
del __info__['__file__']
__author__ = __info__['author']
__version__ = __info__['version']

from .organization import get_profile, Profile, ProfileBase, ProjectBase, GeneralProject
from .registration import meta_rule, Meta_Rule, script, component, modifier, creator, autocomponent, autoscript
from .top import get_current_project, get_project, switch_project, iterate_projects, \
	entry, main, run, quick_run, initialize, cleanup, create_config, parse_argv

from .config import ConfigNode as Node
from . import rules as _rules
from . import exporting as _exporting

from .configurable import Configurable, Certifiable, config_aliases

