from typing import Dict, Optional, Any, Sequence, Iterator, NamedTuple, Union, ContextManager, Type
from pathlib import Path
import sys
from collections import OrderedDict
from omnibelt import Class_Registry, JSONABLE, unspecified_argument

from ..abstract import AbstractConfig, AbstractProfile, AbstractProject, AbstractBehavior
from .workspaces import ProjectBase



class ProfileBase(AbstractProfile):
	'''
	Generally, a run environment uses a single profile to keep track of loading projects,
	and invoking the top level methods (such as :func:`entry()`, :func:`main()`, :func:`run()`,
	:func:`quick_run`, etc.).

	It is recommended to subclass this class to create a custom profile classes with expected functionality
	(unlike :class:`AbstractProfile`).

	'''

	class _Behavior_Registry(Class_Registry, components=['description']):
		'''The registry for behaviors (used by projects to modify the behavior when running scripts).'''
		pass
	behavior_registry = _Behavior_Registry() # one global instance (even independent of the profile instance)


	_default_profile_cls = None
	_profile = None


	def __init_subclass__(cls, default_profile: Optional[bool] = False, **kwargs):
		super().__init_subclass__(**kwargs)
		cls._profile = None
		if default_profile is not None:
			ProfileBase._default_profile_cls = cls


	# region Class Methods
	Project: ProjectBase = ProjectBase


	@classmethod
	def get_project_type(cls, ident: str, default: Optional[Any] = unspecified_argument) -> NamedTuple:
		'''
		Gets the project type entry for the given identifier (from a registry).

		Args:
			ident: Name of the registered project type.
			default: Default value to return if the identifier is not found.

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
	def register_behavior(cls, name: str, typ: Type[AbstractBehavior], *,
	                      description: Optional[str] = None) -> NamedTuple:
		'''
		Registers a new behavior in the profile.

		Behaviors are classes which are instantiated and managed by .

		Args:
			name: Name of the behavior.
			typ: Behavior class (recommended to subclass :class:`AbstractBehavior`).
			description: Description of the behavior.

		Returns:
			Registration entry for the behavior.

		'''
		cls.behavior_registry.new(name, typ, description=description)


	@classmethod
	def get_behavior(cls, name: str) -> NamedTuple:
		'''
		Gets the behavior entry for the given identifier (from the registry).

		Args:
			name: Name of the registered behavior.

		Returns:
			Behavior entry.

		'''
		return cls.behavior_registry.find(name)


	@classmethod
	def iterate_behaviors(cls) -> Iterator[NamedTuple]:
		'''
		Iterates over all registered behaviors.

		Returns:
			Iterator over all behavior entries.

		'''
		yield from cls.behavior_registry.values()
	# endregion

	
	def __init__(self, data: Dict[str, Any] = None) -> None:
		super().__init__(data)
		self._loaded_projects = OrderedDict()
		self._current_project_key = None


	@property
	def path(self):
		path = self.data.get('info_path', None)
		if path is not None:
			return Path(path)


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
		self.get_current_project().activate()
		if len(projects):
			for project in projects:
				self.get_project(project).activate()


	def main(self, argv: Sequence[str], script_name: Optional[str] = unspecified_argument) -> None:
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


	def run_script(self, script_name: str, config: AbstractConfig, *args: Any, **kwargs: Any) -> Any:
		'''
		Runs the script registered with the given name and the given arguments using
		:func:`run_script()` of the current project.

		Args:
			script_name: Name of the script to run (must be registered).
			config: Config object to run the script with.
			*args: Manual arguments to pass to the script.
			**kwargs: Manual keyword arguments to pass to the script.

		Returns:
			The output of the script.

		'''
		return self.get_current_project().run_script(script_name, config, *args, **kwargs)


	def run(self, config: AbstractConfig, *args: Any, **kwargs: Any):
		'''
		Runs the script with the given arguments using :func:`run()` of the current project.

		Args:
			config: Config object to run the script with.
			*args: Manual arguments to pass to the script.
			**kwargs: Manual keyword arguments to pass to the script.

		Returns:
			The output of the script.

		'''
		return self.get_current_project().run(config, *args, **kwargs)


	def quick_run(self, script_name: str, *configs: str, **parameters: Any):
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


	def create_config(self, *configs: str, **parameters: JSONABLE) -> AbstractConfig:
		'''
		Process the provided data to create a config object (using the current project).

		Args:
			configs: usually a list of parent configs to be merged
			parameters: any manual parameters to include in the config object

		Returns:
			Config object resulting from loading/merging `configs` and including `data`.
		'''
		return self.get_current_project().create_config(*configs, **parameters)


	def parse_argv(self, argv: Sequence[str], script_name=None) -> AbstractConfig:
		'''
		Parses the given arguments and returns a config object.

		Arguments are expected in the following order (all of which are optional):
			1. Behaviors to modify the config loading process and script execution.
			2. Name of the script to run.
			3. Names of registered config files that should be loaded and merged (in order of precedence).
			4. Manual config parameters (usually keys, prefixed by :code:`--` and corresponding values)

		Args:
			argv: List of arguments to parse (expected to be :code:`sys.argv[1:]`).
			script_name: Manually specified name of the script (defaults to what is specified in the resulting config).

		Returns:
			Config object containing the parsed arguments.

		'''
		return self.get_current_project().parse_argv(argv, script_name=script_name)



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


	def create_project(self, name: str, path: Path = None, set_as_current: bool = True) -> AbstractProject:
		'''
		Creates a new project instance and registers it.

		Args:
			name: Name of the project.
			path: Path to the project (defaults to the current working directory).
			set_as_current: If True, sets the new project as the current project.

		Returns:
			New project instance.

		'''
		proj = self.Project(path, profile=self)
		proj.name = name
		self._loaded_projects[name] = proj
		if set_as_current:
			self._current_project_key = name
		return proj


	def switch_project(self, ident: Union[str, AbstractProject] = None) -> AbstractProject:
		'''
		Switches the current project to the one with the given identifier.

		Args:
			ident: Name of the project to switch to, defaults to the default project (with name: None).

		Returns:
			New current project instance.

		'''
		proj = self.get_project(ident)
		# current = self.get_current_project()
		# if proj is not current:
		# 	# current.deactivate()
		# 	proj.activate()
		# 	self._current_project_key = proj.name
		self._current_project_key = proj.name
		return proj


	def iterate_projects(self) -> Iterator[AbstractProject]:
		'''
		Iterates over all loaded projects.

		Returns:
			Iterator over all loaded project instances.

		'''
		yield from self._loaded_projects.values()


	def project_context(self, ident: Union[str, AbstractProject] = None) -> ContextManager[AbstractProject]:
		'''
		Context manager to temporarily switch to a different current project.

		Args:
			ident: Name of the project to switch to, defaults to the default project (with name: None).

		Returns:
			Context manager to switch to the specified project.

		'''
		return self._project_context(self, ident)


	class _project_context:
		'''
		Context manager for temporarily switching the current project.

		Args:
			ident: name or path of project to switch to

		'''

		def __init__(self, profile: AbstractProfile, ident: Union[str, Path] = None):
			self.profile = profile
			self.ident = ident
			self.old_project = None

		def __enter__(self):
			self.old_project = self.profile.get_current_project()
			self.profile.switch_project(self.ident)

		def __exit__(self, exc_type, exc_val, exc_tb):
			self.profile.switch_project(self.old_project)



def get_profile() -> ProfileBase:
	'''Returns the current profile instance.'''
	return ProfileBase.get_profile()


	


