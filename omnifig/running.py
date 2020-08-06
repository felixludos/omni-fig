
import sys, os

from .external import include_files
from .rules import meta_rule_fns, view_meta_rules
from .config import get_config, process_raw_argv
from .loading import get_profile

from omnibelt import get_printer, resolve_order

prt = get_printer(__name__)

PRINCEPS_NAME = 'FIG_PRINCEPS_PATH'

def entry(script_name=None):
	argv = sys.argv[1:]
	return main(*argv, script_name=script_name)

def main(*argv, script_name=None):
	initialize()
	config = process_argv(argv, script_name=script_name)
	
	out = run(config=config)
	
	cleanup()
	
	return out



def process_argv(argv=(), script_name=None):
	
	# check for meta args and script name
	
	meta = {}
	
	waiting_key = None
	waiting_meta = 0
	
	remaining = []
	for i, arg in enumerate(argv):
		
		if waiting_meta > 0:
			if waiting_key in meta and isinstance(meta[waiting_key], list):
				meta[waiting_key].append(process_raw_argv(arg))
			else:
				meta[waiting_key] = process_raw_argv(arg)
			waiting_meta -=1
			if waiting_meta == 0:
				waiting_key = None
	
		elif '-' == arg[0] and not arg.startswith('--'):
			text = arg[1:]
			for rule in view_meta_rules():
				name = rule.name
				code = rule.code
				if code is not None and text.startswith(code):
					text = text[len(code):]
					num = rule.num_args
					if num:
						if len(text):
							raise Exception(f'Can\'t combine multiple meta-rules if they require params: {code} in {text}')
						waiting_key = name
						waiting_meta = num
						if num > 1:
							meta[waiting_key] = []
					else:
						meta[name] = True
				if not len(text):
					break
					
		elif arg == '_' or script_name is not None:
			remaining = argv[i:]
			break
			
		else:
			script_name = arg
	
	if script_name is not None:
		meta['script_name'] = script_name
	
	# call get_config
	config = get_config(*remaining)
	config.sub('_meta').update(meta)
	
	return config


def initialize(**overrides):
	
	# princeps script
	princeps_path = resolve_order(PRINCEPS_NAME, overrides, os.environ)
	if princeps_path is not None:
		try:
			include_files(princeps_path)
		except Exception as e:
			prt.critical(f'Failed to run princeps: {princeps_path}')
			raise e
	
	# load profile
	profile = get_profile(**overrides)
	
	# load project/s
	profile.initialize()

def cleanup(**overrides):
	get_profile(**overrides).cleanup()



def run(script_name=None, config=None, **meta_args):
	if config is None:
		config = get_config()
	
	if script_name is not None:
		config.push('_meta.script_name', script_name, overwrite=True, silent=True)
	for k, v in meta_args.items():
		config.push(f'_meta.{k}', v, overwrite=True, silent=True)
	# config._meta.update(meta_args)
	
	for rule in meta_rule_fns():
		config = rule(config.sub('_meta'), config)
	
	config.push('_meta._type', 'run_mode/default', overwrite=False, silent=True)
	silent = config.pull('_meta._quiet_run_mode', True, silent=True)
	mode = config.pull('_meta', silent=silent)
	# config = mode.process(config)
	
	return mode.run(config.sub('_meta'), config)


def quick_run(script_name, **args):
	config = get_config()
	
	for k, v in args.items():
		config.push(k, v, silent=True)
	
	return run(script_name, config)





