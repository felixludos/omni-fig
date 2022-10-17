from typing import Dict, Tuple, Optional, Any, Sequence, Callable, Iterator, NamedTuple
import sys
from collections import OrderedDict
from omnibelt import get_printer, Function_Registry

from ..abstract import AbstractConfig, AbstractProfile
from .workspaces import ProjectBase

prt = get_printer(__name__)



class _MetaRule_Registry(Function_Registry, components=['code', 'priority', 'num_args', 'description']):
	'''The registry for meta rules (used by profiles).'''
	pass


class ProfileBase(AbstractProfile):  # profile that should be extended
	'''
	Generally, a run environment uses a single profile to keep track of loading projects,
	and invoking the top level methods (such as :func:`entry()`, :func:`main()`, :func:`run()`,
	:func:`quick_run`, etc.).

	It is recommended to subclass this class to create a custom profile classes with expected functionality
	(unlike :class:`AbstractProfile`).

	'''

	meta_rule_registry = _MetaRule_Registry()
	'''Global registry for meta rules (used by the profile).'''

	_default_profile_cls = None
	_profile = None
	
	def __init_subclass__(cls, default_profile: Optional[bool] = False, **kwargs):
		super().__init_subclass__(**kwargs)
		cls._profile = None
		if default_profile is not None:
			ProfileBase._default_profile_cls = cls
	
	# region Class Methods
	Project: ProjectBase = ProjectBase
	'''Default project class that is used when creating a new project'''
	
	@classmethod
	def get_project_type(cls, ident: str) -> NamedTuple:
		'''
		Gets the project type entry for the given identifier (from a registry).

		Args:
			ident: Name of the registered project type.

		Returns:
			Project type entry.

		'''
		return cls.Project.get_project_type(ident)
	
	@classmethod
	def replace_profile(cls, profile: 'ProfileBase' = None) -> 'ProfileBase':
		'''
		Replaces the current profile instance with the given profile. This is used to set the global profile.

		Args:
			profile: New profile instance.

		Returns:
			Old profile instance (which is now replaced).

		'''
		if profile is None:
			profile = cls()
		ProfileBase._profile = profile
		old = cls._profile
		cls._profile = profile
		return old
	
	@classmethod
	def get_profile(cls) -> 'ProfileBase':
		'''
		Gets the current profile instance of the runtime environment.

		Returns:
			Profile instance.

		'''
		if cls._profile is None:
			cls._profile = cls._default_profile_cls()
			cls._profile.activate()
		return cls._profile
	
	@classmethod
	def register_meta_rule(cls, name: str, func: Callable[[AbstractConfig, Dict[str, Any]], Optional[AbstractConfig]],
	                       *, code: str, description: Optional[str] = None, priority: Optional[int] = 0,
	                       num_args: Optional[int] = 0) -> NamedTuple:
		'''
		Registers a new meta rule in the profile.

		Meta rules are functions that are applied in order of their priority to the config object
		before running a script to modify the behavior.

		Args:
			name: Name of the meta rule.
			func: Callable meta rule function (input should be config object and dict of meta params,
			output is None or a new config object).
			code: Code to invoke the meta rule function (parsed into the config from :code:`sys.argv`).
			priority: Order in which the meta rule is applied (higher priority is applied first).
			num_args: When invoking the meta rule from the command line, the number of arguments
			required for this meta rule

		Returns:
			Registration entry for the meta rule.

		'''
		cls.meta_rule_registry.new(name, func, code=code, priority=priority, num_args=num_args,
		                           description=description)
	
	@classmethod
	def get_meta_rule(cls, name: str) -> NamedTuple:
		'''
		Gets the meta rule entry for the given identifier (from the registry).

		Args:
			name: Name of the registered meta rule.

		Returns:
			Meta rule entry.

		'''
		return cls.meta_rule_registry.find(name)
	
	@classmethod
	def iterate_meta_rules(cls) -> Iterator[NamedTuple]:
		'''
		Iterates over all registered meta rules.

		Returns:
			Iterator over all meta rule entries.

		'''
		entries = list(cls.meta_rule_registry.values())
		for entry in sorted(entries, key=lambda e: (e.priority, e.name), reverse=True):
			yield entry
	
	# endregion
	
	def __init__(self, data: Dict[str, Any] = None) -> None:
		super().__init__(data)
		self._loaded_projects = OrderedDict()
		self._current_project_key = None
	
	# region Top Level Methods
	def entry(self, script_name: Optional[str] = None) -> None:
		'''
		Primary entry point for the profile. This method is called when using the :command:`fig` command.

		Args:
			script_name: Manually specified script name to run (if not provided, will be parsed from :code:`sys.argv`).

		Returns:
			:code:`None`

		'''
		argv = sys.argv[1:]
		self.main(argv, script_name=script_name)
	
	def initialize(self, *projects: str, **kwargs: Any) -> None:
		'''
		Initializes the specified projects (including activating them, which generally registers
		all associated configs and imports files and packages)

		Args:
			*projects: Identifiers of projects to initialize (activates the current project only, if none is provided).

		Returns:
			:code:`None`

		'''
		self.activate(**kwargs)
		if len(projects):
			for project in projects:
				self.get_project(project).activate()
		else:
			self.get_current_project().activate()
	
	def main(self, argv: Sequence[str], *, script_name: str = None) -> None:
		'''
		Runs the script with the given arguments using :func:`main()` of the current project.

		Args:
			argv: List of top-level arguments (expected to be :code:`sys.argv[1:]`).
			script_name: specified name of the script
			(defaults to what is specified in argv when it is parsed into a config object).

		Returns:
			The output of the script.

		'''
		return self.get_current_project().main(argv, script_name=script_name)
	
	def run(self, config, *, script_name=None, args: Optional[Tuple] = None,
	        kwargs: Optional[Dict[str, Any]] = None, **meta: Any):
		'''
		Runs the script with the given arguments using :func:`run()` of the current project.

		Args:
			config: Config object to run the script with.
			script_name: Name of the script to run (usually must be registered beforehand to find the function).
			args: Manual arguments to pass to the script.
			kwargs: Manual keyword arguments to pass to the script.
			**meta: Meta arguments to modify the run mode (generally not recommended).

		Returns:
			The output of the script.

		'''
		return self.get_current_project().run(config, script_name=script_name, args=args, kwargs=kwargs)
	
	def quick_run(self, script_name, *configs, **parameters):
		'''
		Creates a config object and runs the script using :func:`quick_run()` of the current project.

		Args:
			script_name: Name of the script to run (should be registered).
			*configs: Names of registered config files to load and merge (in order of precedence).
			**parameters: Manual config parameters to populate the config object with.

		Returns:
			Output of the script.

		'''
		return self.get_current_project().quick_run(script_name, *configs, **parameters)
	
	def cleanup(self, *args: Any, **kwargs: Any) -> None:
		'''
		Calls :func:`cleanup()` of the current project.

		Args:
			*args: Arguments to pass to the cleanup function.
			**kwargs: Keyword arguments to pass to the cleanup function.

		Returns:
			:code:`None`

		'''
		return self.get_current_project().cleanup(*args, **kwargs)

	# endregion
	
	def __str__(self):
		return f'{self.__class__.__name__}[{self.name}]({", ".join(self._loaded_projects)})'
	
	def extract_info(self, other: 'ProfileBase') -> None:
		'''
		Extract data from the provided profile instance and store it in self.

		Recommended to use if a project expects a custom profile different from the currently used one.

		Args:
			profile: Base profile instance.

		Returns:
			:code:`None`

		'''
		super().extract_info(other)
		self._loaded_projects = other._loaded_projects  # .copy()
		self._current_project_key = other._current_project_key
	
	def get_current_project(self) -> Project:
		'''
		Gets the current project instance.

		Returns:
			Current project instance.

		'''
		return self.get_project(self._current_project_key)
	
	def switch_project(self, ident=None) -> Project:
		'''
		Switches the current project to the one with the given identifier.

		Args:
			ident: Name of the project to switch to, defaults to the default project (with name: None).

		Returns:
			New current project instance.

		'''
		proj = self.get_project(ident)
		self._current_project_key = proj.name
		return proj
	
	def iterate_projects(self) -> Iterator[Project]:
		'''
		Iterates over all loaded projects.

		Returns:
			Iterator over all loaded project instances.

		'''
		yield from self._loaded_projects.values()



def get_profile() -> ProfileBase:
	'''Returns the current profile instance.'''
	return ProfileBase.get_profile()


	


