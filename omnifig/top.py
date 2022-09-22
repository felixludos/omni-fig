from typing import Union, Iterator, Sequence, Any
from pathlib import Path

from omnibelt import get_printer, JSONABLE

from .abstract import AbstractProject, AbstractConfig
from .organization import get_profile

prt = get_printer(__name__)

# region Projects

def get_current_project() -> AbstractProject:
	'''Get the current project, assuming a profile is loaded, otherwise returns None'''
	return get_profile().get_current_project()


def get_project(ident: Union[str, Path]  = None) -> AbstractProject:
	'''Checks the profile to return (and possibly load) a project given the name or path ``ident``'''
	return get_profile().get_project(ident)


def switch_project(ident: Union[str, Path] = None) -> AbstractProject:
	'''Switches the current project to the one of thegiven the project name or path ``ident``'''
	return get_profile().switch_project(ident)


def iterate_projects() -> Iterator[AbstractProject]:
	'''Iterate over all loaded projects'''
	return get_profile().iterate_projects()

# endregion

# region Running

def entry(script_name: str = None) -> None:
	'''
	Recommended entry point when running a script from the terminal.
	This is also the entry point for the ``fig`` command.

	This collects the command line arguments in ``sys.argv`` and overrides the
	given script with ``script_name`` if it is provided

	:param script_name: script to be run (may be set with arguments) (overrides other arguments if provided)
	:return: None
	'''
	get_profile().entry(script_name=script_name)


def main(argv: Sequence[str], *, script_name: str = None) -> Any:
	'''
	Runs the desired script using the provided ``argv`` which are treated as command line arguments

	Before running the script, this function initializes ``omni-fig`` using :func:`initialize()`,
	and then cleans up after running using :func:`cleanup()`.

	:param argv: raw arguments as if passed in through the terminal
	:param script_name: name of registered script to be run (may be set with arguments) (overrides other arguments if provided)
	:return: output of script that is run
	'''
	return get_profile().main(argv, script_name=script_name)


def run(script_name: str, config: AbstractConfig, **meta: JSONABLE) -> Any:
	'''
	Runs the specified script registered with ``script_name`` using the current project.
	
	:param script_name: must be registered in the current project or defaults to the profile
	:param config: config object passed to the script
	:param meta: any meta rules that modify the way the script is run
	:return: output of the script, raises MissingScriptError if the script is not found
	'''
	return get_profile().run(config, script_name=script_name, **meta)


def quick_run(script_name: str, *parents: str, **args: JSONABLE) -> Any:
	'''
	Convenience function to run a simple script without a given config object,
	instead the config is entirely created using the provided ``parents`` and ``args``.

	:param script_name: name of registered script that is to be run
	:param parents: any names of registered configs to load
	:param args: any additional arguments to be provided manually
	:return: script output
	'''
	return get_profile().quick_run(script_name, *parents, **args)


def initialize(*projects: str, **overrides: Any) -> None:
	'''
	Initializes omni-fig by running the "princeps" file (if one exists),
	loading the profile, and any active projects. Additionally, loads the
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

	# # princeps script
	# princeps_path = resolve_order(global_settings['princeps_path'], overrides, os.environ)
	# if not global_settings['disable_princeps'] and princeps_path is not None:
	# 	try:
	# 		include_files(princeps_path)
	# 	except Exception as e:
	# 		prt.critical(f'Failed to run princeps: {princeps_path}')
	# 		raise e
	#
	# # load profile
	# profile = get_profile(**overrides)
	#
	# # load project/s
	# profile.initialize()
	#
	# for proj in projects:
	# 	profile.load_project(proj)

	return get_profile().initialize(*projects, **overrides)


def cleanup(*args: Any, **kwargs: Any) -> None:
	'''
	Cleans up the projects and profile, which by default just updates the project/profile info
	yaml file if new information was added to the project/profile.

	Generally, this should be run after running any desired scripts.

	:param args: optional arguments
	:param kwargs: optional keyword arguments
	:return: None
	'''
	return get_profile().cleanup(*args, **kwargs)

# endregion

# region Create

def create_config(*parents: str, **parameters: JSONABLE) -> AbstractConfig:
	'''
	Process the provided info using the current project into a config object.
	:param parents: usually a list of parent configs to be merged
	:param parameters: any manual parameters to include in the config object
	:return: config object
	'''
	return get_current_project().create_config(*parents, **parameters)


# def create_component(config):
# 	'''
# 	Create a component using the current project
# 	:param config: Must contain a "_type" parameter with the name of a registered component
# 	:return: the created component
# 	'''
# 	return get_current_project().create_component(config)


# def quick_create(_type, *parents, **parameters):
# 	'''
# 	Creates a component without an explicit config object. Effectively combines `get_config()` and `create_component()`
# 	:param _type:
# 	:param parents:
# 	:param parameters:
# 	:return:
# 	'''
# 	proj = get_current_project()
#
# 	config = proj.create_config(*parents, **parameters)
# 	config.push('_type', _type, silent=True)
#
# 	return proj.create_component(config)
	
# endregion


# # region Registration
#
# def register_script(name, fn, description=None, use_config=False):
# 	'''Manually register a new script to the current project'''
# 	monkey_patch(fn)
# 	return get_current_project().register_script(name, fn, description=description, use_config=use_config)
#
# def register_component(name, fn, description=None):
# 	'''Manually register a new component to the current project'''
# 	return get_current_project().register_component(name, fn, description=description)
#
# def register_modifier(name, fn, description=None, expects_config=False):
# 	'''Manually register a new modifier to the current project'''
# 	return get_current_project().register_modifier(name, fn, description=description, expects_config=expects_config)
#
# def register_config(name, path):
# 	'''Manually register a new config file to the current project'''
# 	return get_current_project().register_config(name, path)
#
# def register_config_dir(path, recursive=True, prefix=None, joiner='/'):
# 	'''Manually register a new config directory to the current project'''
# 	return get_current_project().register_config_dir(path, recursive=recursive, prefix=prefix, joiner=joiner)
#
# # endregion

# # region Artifacts
#
# def has_script(name):
# 	return get_current_project().has_script(name)
# def find_script(name):
# 	return get_current_project().find_script(name)
# def view_scripts():
# 	return get_current_project().view_scripts()
#
# def has_component(name):
# 	return get_current_project().has_component(name)
# def find_component(name):
# 	return get_current_project().find_component(name)
# def view_components():
# 	return get_current_project().view_components()
#
# def has_modifier(name):
# 	return get_current_project().has_modifier(name)
# def find_modifier(name):
# 	return get_current_project().find_modifier(name)
# def view_modifiers():
# 	return get_current_project().view_modifiers()
#
# def has_config(name):
# 	return get_current_project().has_config(name)
# def find_config(name):
# 	return get_current_project().find_config(name)
# def view_configs():
# 	return get_current_project().view_configs()
#
# # endregion

