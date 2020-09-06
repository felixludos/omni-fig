
import sys, os

from .external import include_files
from .rules import meta_rule_fns, view_meta_rules
from .config import get_config, process_raw_argv
from .loading import get_profile

from omnibelt import get_printer, resolve_order

prt = get_printer(__name__)

PRINCEPS_NAME = 'FIG_PRINCEPS_PATH'
_disable_princeps = False


def entry(script_name=None):
	'''
	Recommended entry point when running a script from the terminal.
	This is also the entry point for the ``fig`` command.
	
	This collects the command line arguments in ``sys.argv`` and overrides the
	given script with ``script_name`` if it is provided
	
	:param script_name: script to be run (may be set with arguments) (overrides other arguments if provided)
	:return: the output of the script that is to be run
	'''
	argv = sys.argv[1:]
	return main(*argv, script_name=script_name)

def main(*argv, script_name=None):
	'''
	Runs the desired script using the provided ``argv`` which are treated as command line arguments
	
	Before running the script, this function initializes ``omni-fig`` using :func:`initialize()`,
	and then cleans up after running using :func:`cleanup()`.
	
	:param argv: raw arguments as if passed in through the terminal
	:param script_name: name of registered script to be run (may be set with arguments) (overrides other arguments if provided)
	:return: output of script that is run
	'''
	initialize()
	config = process_argv(argv, script_name=script_name)
	
	out = run(config=config)
	
	cleanup()
	
	return out



def process_argv(argv=(), script_name=None):
	'''
	Parses the command line arguments to identify the meta arguments, script name
	(optionally overridden using ``script_name``), and config args
	
	From that, this builds the config and meta config object.
	
	:param argv: list of all command line arguments to parse in order
	:param script_name: optional script name to override any script specified in ``argv``
	:return: config object (containing meta config under ``_meta``)
	'''
	
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
			remaining = argv[i+1:]
			break
			
		else:
			script_name = arg
	
	if script_name is not None:
		meta['script_name'] = script_name
	
	# call get_config
	config = get_config(*remaining)
	config.sub('_meta').update(meta)
	
	return config


def initialize(*projects, **overrides):
	'''
	Initializes omni-fig by running the "princeps" file (if one exists),
	loading the profile, and any active projects. Additionally loads the
	project in the current working directory (by default).
	
	Generally, this function should be run before running any scripts, as it should register all
	necessary scripts, components, and configs when loading a project. It is automatically called
	when running the :func:`main()` function (ie. running through the terminal). However, when
	starting scripts from other environments (such as in a jupyter notebook), this should be called
	manually after importing ``omnifig``.
	
	:param projects: additional projects that should be initialized
	:param overrides: settings to be checked before defaulting to ``os.environ`` or global settings
	:return: None
	'''
	
	# princeps script
	princeps_path = resolve_order(PRINCEPS_NAME, overrides, os.environ)
	if not _disable_princeps and princeps_path is not None:
		try:
			include_files(princeps_path)
		except Exception as e:
			prt.critical(f'Failed to run princeps: {princeps_path}')
			raise e
	
	# load profile
	profile = get_profile(**overrides)
	
	# load project/s
	profile.initialize()
	
	for proj in projects:
		profile.load_project(proj)
	

def cleanup(**overrides):
	'''
	Cleans up the projects and profile, which by default just updates the project/profile info
	yaml file if new information was added to the project/profile.
	
	Generally, this should be run after running any desired scripts.
	
	:param overrides: settings to check before defaulting to global settings or ``os.environ``
	:return: None
	'''
	get_profile(**overrides).cleanup()



def run(script_name=None, config=None, **meta_args):
	'''
	This actually runs the script given the ``config`` object.
	
	Before starting the script, all meta rules are executed in order of priority (low to high)
	as they may change the config or script behavior, then the run mode is created, which is
	then called to execute the script specified in the config object (or manually overridden
	using ``script_name``)
	
	:param script_name: registered script name to run (overrides what is specified in ``config``)
	:param config: config object (usually created with :func:`get_config()` (see :ref:`config:Config System`)
	:param meta_args: Any additional meta arguments to include before running
	:return: script output
	'''
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


def quick_run(script_name, *parents, **args):
	'''
	Convenience function to run a simple script without a given config object,
	instead the config is entirely created using the provided ``parents`` and ``args``.
	
	:param script_name: name of registered script that is to be run
	:param parents: any names of registered configs to load
	:param args: any additional arguments to be provided manually
	:return: script output
	'''
	config = get_config(*parents, **args)
	return run(script_name, config)





