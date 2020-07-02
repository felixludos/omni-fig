
import sys, os
import inspect
import time

from omnibelt import primitives, get_printer, \
	get_global_settings, set_global_setting, get_global_setting, get_now, resolve_order, \
	spawn_path_options
from omnibelt.logging import global_settings

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


def autofill_args(fn, config, aliases=None, run=True):

	params = inspect.signature(fn).parameters

	args = []
	kwargs = {}

	for n, p in params.items():

		order = [n]
		if aliases is not None and n in aliases: # include aliases
			order.extend('<>{}'.format(a) for a in aliases[n])
		if p.default != inspect._empty:
			order.append(p.default)
		elif p.kind == p.VAR_POSITIONAL:
			order.append(())
		elif p.kind == p.VAR_KEYWORD:
			order.append({})

		arg = config.pull(*order)

		if p.kind == p.POSITIONAL_ONLY:
			args.append(arg)
		elif p.kind == p.VAR_POSITIONAL:
			args.extend(arg)
		elif p.kind == p.VAR_KEYWORD:
			kwargs.update(arg)
		else:
			kwargs[n] = arg
	if run:
		return fn(*args, **kwargs)
	return args, kwargs




