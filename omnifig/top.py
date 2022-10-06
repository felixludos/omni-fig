from typing import Union, Iterator, Sequence, Any, Optional
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

	Args:
		script_name: script to be run (maybe set with arguments) (overrides other arguments if provided)

	Returns:
		:code:`None`

	'''
	get_profile().entry(script_name=script_name)


def main(argv: Sequence[str], *, script_name: Optional[str] = None) -> Any:
	'''
	Runs the desired script using the provided ``argv`` which are treated as command line arguments

	Before running the script, this function initializes ``omni-fig`` using :func:`initialize()`,
	and then cleans up after running using :func:`cleanup()`.

	Args:
		argv: raw arguments as if passed in through the terminal
		script_name: name of registered script to be run (maybe set with arguments) (overrides other arguments if provided)

	Returns:
		The output of script that is run

	'''
	return get_profile().main(argv, script_name=script_name)


def run(script_name: str, config: AbstractConfig, *args: Any, **kwargs: Any) -> Any:
	'''
	Runs the specified script registered with ``script_name`` using the current project.

	Args:
		script_name: Must be registered in the current project
		config: The config object passed to the script
		*args: Manual arguments to be passed to the script
		**kwargs: Manual keyword arguments to be passed to the script

	Returns:
		The output of the script, raises MissingScriptError if the script is not found

	'''
	return get_profile().run(config, script_name=script_name, args=args, kwargs=kwargs)


def quick_run(script_name: str, *parents: str, **parameters: JSONABLE) -> Any:
	'''
	Convenience function to run a simple script without a given config object,
	instead the config is entirely created using the provided ``parents`` and ``parameters``.

	Args:
		script_name: name of registered script that is to be run
		*parents: any names of registered configs to load
		**parameters: any additional arguments to be provided manually

	Returns:
		The script output

	'''
	return get_profile().quick_run(script_name, *parents, **parameters)


def initialize(*projects: str, **meta: Any) -> None:
	'''
	Initializes omni-fig by running the "princeps" file (if one exists),
	loading the profile, and any active projects. Additionally, loads the
	project in the current working directory (by default).

	Generally, this function should be run before running any scripts, as it should register all
	necessary scripts, components, and configs when loading a project. It is automatically called
	when running the :func:`main()` function (ie. running through the terminal). However, when
	starting scripts from other environments (such as in a jupyter notebook), this should be called
	manually after importing ``omnifig``.

	Args:
		projects: additional projects that should be initialized
		meta: settings to be checked before defaulting to ``os.environ`` or global settings

	Returns:
		:code:`None`

	'''
	return get_profile().initialize(*projects, **meta)


def cleanup() -> None:
	'''
	Cleans up the projects and profile, which by default just updates the project/profile info
	yaml file if new information was added to the project/profile.

	Generally, this should be run after running any desired scripts.

	Returns:
		:code:`None`

	'''
	return get_profile().cleanup()

# endregion

# region Create

def create_config(*configs: str, **parameters: JSONABLE) -> AbstractConfig:
	'''
	Process the provided info using the current project into a config object.

	Args:
		configs: usually a list of parent configs to be merged
		parameters: any manual parameters to include in the config object

	Returns:
		Config object resulting from loading/merging `configs` and including `data`.
	'''
	return get_current_project().create_config(*configs, **parameters)

# endregion
