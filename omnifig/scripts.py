
import sys, os
import inspect
import logging


from .util import get_printer, get_global_setting, resolve_order, autofill_args, set_global_setting
from .registry import get_script
from .loading import load_profile, include_files, get_project
from .config import parse_config, get_config
from .modes import get_run_mode, meta_arg_registry

prt = get_printer(__name__)

def entry():
	argv = sys.argv[1:]
	# print(argv)
	return main(*argv)

def main(*argv):
	initialize()
	meta, config = cmd_arg_parse(argv)
	return run(meta, config)

def initialize(**overrides):
	
	# region Load Init
	
	fig_init = resolve_order(get_global_setting('init_env_var'),
	                         overrides, os.environ, get_global_setting)
	
	if isinstance(fig_init, str):
		fig_init = fig_init.split(':')
	
	if fig_init is not None:
		include_files(*fig_init)
	
	# endregion
	# region Load Profile
	
	profile = load_profile(**overrides)

	# endregion
	# region Local Projects
	
	project = get_project()
	
	# endregion

_error_msg = '''Error script {} is not registered.
Please specify a script (and optionally args), registered scripts:
{}'''
_error_msg = '''Error script {} is not registered.'''

def run(meta, config):
	mode_name = meta.pull('mode', None)
	script_name = meta.pull('script_name')
	
	mode_cls = get_run_mode(mode_name)
	mode = mode_cls(meta)
	
	mode.prepare(meta, config)
	
	script_info = get_script(script_name)
	
	if script_info is None:
		print(_error_msg.format(script_name, ))
		return 1
	
	return mode.run(script_info.fn, meta, config)



def cmd_arg_parse(argv=()):
	
	meta = get_config()
	config = get_config()
	
	script_name = None
	waiting_key = None
	waiting_meta = 0
	waiting = None
	args_started = False
	config_parents = []
	
	for arg in argv:
		if waiting_meta > 0:
			if waiting_key in meta and isinstance(meta[waiting_key], list):
				meta[waiting_key].append(arg)
			else:
				meta[waiting_key] = arg
			waiting_meta -=1
			if waiting_meta == 0:
				waiting_key = None
				
			continue
		
		elif waiting is not None:
			config[waiting] = arg
			waiting = None
			continue
		
		elif '-' == arg[0] and not arg.startswith('--'):
			text = arg[1:]
			for marg in meta_arg_registry.values():
				name = marg.get_name()
				code = marg.get_code()
				if text.startswith(code):
					text = text[len(code):]
					num = marg.get_num_params()
					if num:
						if len(text):
							raise Exception(f'Can\'t combine multiple meta-args if they require params: {code}')
						waiting_key = name
						waiting_meta = num
						if num > 1:
							meta[waiting_key] = []
				if not len(text):
					break
				
			continue
		
		elif script_name is None:
			script_name = arg
			continue
			
		elif arg.startswith('--'):
			args_started = True
			waiting = arg[2:]
			continue
		
		elif not args_started and script_name is not None:
			config_parents.append(arg)
		
		else:
			prt.error(f'Failed to parse arg: {arg}')
	
	
	meta['script_name'] = script_name
	return meta, config



# def main_script(script_name, *argv):
# 	return _main_script((script_name, *argv))
#
# def _main_script(argv=None):
# 	if argv is None:
# 		argv = sys.argv[1:]
#
# 	scripts = view_script_registry()
# 	script_names = ', '.join(scripts.keys())
#
# 	if len(argv) == 0 or (len(argv) == 1 and argv[0] in _help_cmds):
# 		print(_help_msg.format(script_names))
# 		return 0
# 	elif argv[0] not in scripts:
# 		print(_error_msg.format(argv[0], script_names))
# 		return 1
#
# 	name, *argv = argv
# 	fn, use_config = scripts[name]
#
# 	if len(argv) == 1 and argv[0] in _help_cmds:
# 		print(f'Help message for script: {name}')
#
# 		doc = fn.__doc__
#
# 		if doc is None and not use_config:
# 			doc = str(inspect.signature(fn))
# 			doc = f'Arguments {doc}'
#
# 		print(doc)
# 		return 0
#
# 	A = parse_config(argv=argv)
#
# 	if use_config:
# 		out = fn(A)
# 	else:
# 		out = autofill_args(fn, A)
#
# 	if out is None:
# 		return 0
# 	return out


