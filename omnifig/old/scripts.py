
import sys, os

from omnifig.util import get_printer, get_global_setting, resolve_order
from omnifig.registry import get_script
from omnifig.loading import load_profile, include_files, get_project
from omnifig.config import get_config
from omnifig.old.modes import get_run_mode, meta_arg_registry

prt = get_printer(__name__)

def entry(script_name=None):
	argv = sys.argv[1:]
	return main(*argv, script_name=script_name)

def main(*argv, script_name=None):
	initialize()
	meta, config = cmd_arg_parse(argv, script_name=script_name)
	return full_run(meta, config)

def initialize(**overrides):
	
	# region Load Init
	
	fig_init = resolve_order(get_global_setting('init_env_var'),
	                         overrides, os.environ, get_global_setting)
	
	if isinstance(fig_init, str):
		fig_init = fig_init.split(':')
	
	if fig_init is not None:
		include_files(*fig_init)
	
	# endregion
	# region Load Profile/Project
	
	profile = load_profile(**overrides)
	profile.prepare()
	
	get_project()
	
	# endregion

_error_msg = '''Error script {} is not registered.
Please specify a script (and optionally args), registered scripts:
{}'''
_error_msg = '''Error script {} is not registered.'''

def full_run(meta, config):
	
	margs = []
	for name in list(meta):
		marg = meta_arg_registry.get(name, None)
		if marg is not None:
			margs.append(marg(meta, config))
		
	mode_name = meta.pull('mode', None, silent=True)
	
	mode_cls = get_run_mode(mode_name)
	mode = mode_cls(meta, config, auto_meta_args=margs)
	
	mode.prepare(meta, config)
	
	script_name = meta.pull('script_name', None, silent=True)
	if script_name is None:
		prt.error('No script specified')
		quit()
	
	script_info = get_script(script_name)
	if script_info is None:
		print(_error_msg.format(script_name))
		return 1
	
	return mode.run(script_info, meta, config)


def run(script_name, config, **meta_args):
	
	meta = config._meta
	meta.update(meta_args)
	meta.script_name = script_name
	
	return full_run(meta, config)

def quick_run(script_name, **args):
	
	config = get_config()
	
	for k,v in args.items():
		config.push(k,v,silent=True)
	
	return run(script_name, config)

def cmd_arg_parse(argv=(), script_name=None):
	
	meta = get_config()
	config = get_config()
	
	waiting_key = None
	waiting_meta = 0
	waiting = None
	args_started = False
	config_parents = []
	# margs = []
	
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
			if arg.startswith('--'):
				config[waiting] = True
				args_started = True
				waiting = arg[2:]
			else:
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
					# margs.append(marg)
					if num:
						if len(text):
							raise Exception(f'Can\'t combine multiple meta-args if they require params: {code}')
						waiting_key = name
						waiting_meta = num
						if num > 1:
							meta[waiting_key] = []
					else:
						meta[name] = True
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
	
	parents = config.pull('parents', [], silent=True)
	config.parents = list(parents) + config_parents

	if script_name is not None and script_name != '_':
		meta['script_name'] = script_name
	
	# if len(margs):
	# 	meta._args = margs
	
	config = get_config(config, include_load_history=True)
	config._meta.update(meta)
	meta = config._meta
	
	return meta, config

