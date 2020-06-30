
import sys, os
import time

from omnibelt import *
from omnibelt import primitives, autofill_args, get_printer, \
	global_settings, get_global_settings, set_global_setting, get_global_setting

LIB_PATH = os.path.dirname(__file__)

global_settings.update({
	
	# naming settings
	'default_entry_name': 'default',
	'profile_env_var': 'FIG_PROFILE',
	'profile_src_env_var': 'FIG_PROFILE_SRC',
	'init_env_var': 'FIG_INIT',
	
	# default infos
	'default_profile': None,
	
	'allow_profile_sources': True,
	'use_last_entry_as_default': True,
	'default_ptype': 'default',
	
	# 'resolution_order': [ # for scripts, configs, components, and modifiers
	# 	 'local', # check the current working dir if its in a project
	#      'active-project', # currently active project
	#      'related-projects', # any projects related to the active project
	#      'init' # scripts loaded through init (no project)
	#      ],
})


prt = get_printer(__name__)




