import os
__info__ = {'__file__':os.path.join(os.path.abspath(os.path.dirname(__file__)), '_info.py')}
with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), '_info.py'), 'r') as f:
	exec(f.read(), __info__)
del os
del __info__['__file__']
__author__ = __info__['author']
__version__ = __info__['version']

from .organization import get_profile, ProfileBase, ProjectBase, GeneralProject, Profile
from .registration import script, component, modifier, creator, autocomponent, autoscript
from .top import get_current_project, get_project, switch_project, iterate_projects, \
	entry, main, run_script, run, quick_run, initialize, create_config, parse_argv

from .config import ConfigNode as Node
from . import exporting as _exporting
from .behaviors import Behavior

from .configurable import Configurable, Certifiable, config_aliases

