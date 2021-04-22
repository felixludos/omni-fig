
import sys, os, io
import inspect
import yaml
import time

from omnibelt import primitives, get_printer, \
	get_global_settings, set_global_setting, get_global_setting, get_now, resolve_order, \
	spawn_path_options
from omnibelt.logging import global_settings as belt_global_settings

from .errors import PythonizeError, ConfigurizeFailed

LIB_PATH = os.path.dirname(__file__)

global_settings = belt_global_settings.copy()
global_settings.update({
	
	# naming settings
	'default_entry_name': 'default',
	'profile_env_var': 'FIG_PROFILE',
	'profile_src_env_var': 'FIG_PROFILE_SRC',
	'init_env_var': 'FIG_INIT',
	
	'disable_princeps': False,
	'princeps_path': 'FIG_PRINCEPS',
	
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
	
	'arg_parse_language': 'yaml',
	
})

prt = get_printer(__name__)



def configurize(data):
	'''
	Transform data container to use config objects (ConfigDict/ConfigList)

	:param data: dict/list data
	:return: deep copy of data using ConfigDict/ConfigList
	'''
	if isinstance(data, global_settings['config_type']):
		return data
	for typ, convert in global_settings.get('config_converters', {}).items():
		allow_subtypes = True
		if isinstance(convert, tuple):
			allow_subtypes, convert = convert
		try:
			if (allow_subtypes and isinstance(data, typ)) or type(data) == typ:
				return convert(data, configurize)
		except ConfigurizeFailed:
			pass
	return data


def pythonize(data):  # TODO: allow adding yamlify rules for custom objects
	'''
	Transform data container into regular dicts/lists to export to yaml file

	:param data: Config object
	:return: deep copy of data using dict/list
	'''
	# if data is None:
	# 	return '_None'
	if data is None or isinstance(data, primitives):
		return data
	if isinstance(data, dict):
		return {k: pythonize(v) for k, v in data.items() if not str(k).startswith('__')}
	if isinstance(data, (list, tuple, set)):
		return [pythonize(x) for x in data]
	
	raise PythonizeError(data)

# parse args

def parse_arg(arg, mode=None):
	
	if mode is None:
		mode = global_settings['arg_parse_language']
	
	if mode == 'python':
		raise NotImplementedError
	
	try:
		if isinstance(mode, str):
			if mode == 'yaml':
				return yaml.safe_load(io.StringIO(arg))
			elif mode == 'python':
				return eval(arg, {}, {})
			else:
				pass
		else:
			return mode(arg)
	except:
		pass
	return arg


# autofill

def autofill_args(fn, config, aliases=None, run=True): # TODO: move to omnibelt (?)

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




