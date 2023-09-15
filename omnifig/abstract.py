from typing import List, Dict, Tuple, Optional, Union, Any, Sequence, Callable, Type, \
	Iterator, NamedTuple, ContextManager
# import abc
from pathlib import Path
from omnibelt import unspecified_argument, Registry, Primitive, JSONABLE

from .mixins import Activatable, FileInfo



class AbstractConfig:
	'''Abstract class for config objects'''

	# TODO: copy, deepcopy

	_empty_default = unspecified_argument


	class SearchFailed(KeyError):
		'''Raised when a search fails'''
		pass


	@property
	def cro(self) -> Tuple[str, ...]:
		'''
		Returns the list of all config files that were composed to produce this config tree.
		Analogous to the method resolution order (``mro``) for classes.
		'''
		raise NotImplementedError


	@property
	def bases(self) -> Tuple[str, ...]:
		'''
		Returns the list of config files that were explicitly mentioned to produce this config tree.
		Analogous to ``__bases__`` for classes.
		'''
		raise NotImplementedError


	@property
	def project(self) -> 'AbstractProject':
		'''Returns the project object associated with this config'''
		raise NotImplementedError
	@project.setter
	def project(self, project: 'AbstractProject'):
		'''Sets the project object associated with this config'''
		raise NotImplementedError


	@property
	def root(self) -> 'AbstractConfig':
		'''Returns the root node of the config object'''
		raise NotImplementedError


	def export(self, name: Union[str, Path], *, root: Optional[Union[str, Path]] = None,
			   fmt: Optional[str] = None) -> Optional[Path]:
		'''
		Exports the config object to the given path.

		Args:
			name: Name/path to export the config object to.
			root: Path to use as the root of the config object (defaults to the current working directory).
			fmt: Format to export the config object in (if None, will be inferred from the path).

		'''
		raise NotImplementedError


	def peek(self, query: Optional[str] = None, default: Optional[Any] = _empty_default, *,
	         silent: Optional[bool] = None) -> 'AbstractConfig':
		'''
		Returns a config object given by searching for the query in the config object.

		Args:
			query: The query to search for. If None, returns self.
			default: The default value to return if the query is not found.
			silent: If True, no message is reported based on the search.

		Returns:
			The config object found by the query, or the default value if the query is not found,
			and returns self if no query is provided.

		'''
		return self.peeks(query, default=default, silent=silent)


	def pull(self, query: Optional[str] = None, default: Optional[Any] = _empty_default, *,
	         silent: Optional[bool] = None) -> Any:
		'''
		Returns the value found by searching for the query in the config object.

		Args:
			query: The query to search for. If None, returns default.
			default: The default value to return if the query is not found.
			silent: If True, no message is reported based on the search.

		Returns:
			The value found by the query, or the default value if the query is not found,
			and returns the value of self if no query is provided.

		'''
		return self.pulls(query, default=default, silent=silent)


	def push_pull(self, addr: str, value: Any, *, overwrite: bool = True, silent: Optional[bool] = None) -> Any:
		'''
		Composes the push and pull methods into a single method. Can be used to set a value if none exists,
		and otherwise pull the existing value.

		Args:
			addr: The address to push/pull from.
			value: The value to push to the address.
			overwrite: If True, the value is pushed to the address even if it already exists.
			silent: If True, no message is reported.

		Returns:
			The value found at the address.

		'''
		self.push(addr, value, overwrite=overwrite, silent=silent)
		return self.pull(addr, silent=silent)


	def push_peek(self, addr: str, value: Any, *, overwrite: bool = True, silent: Optional[bool] = None) \
			-> 'AbstractConfig':
		'''
		Composes the push and peek methods into a single method. Can be used to set a value if none exists,
		and otherwise peek the existing value.

		Args:
			addr: The address to push/peek from.
			value: The value to push to the address.
			overwrite: If True, the value is pushed to the address even if it already exists.
			silent: If True, no message is reported.

		Returns:
			The value found at the address.

		'''
		self.push(addr, value, overwrite=overwrite, silent=silent)
		return self.peek(addr, silent=silent)


	def peeks(self, *queries, default: Optional[Any] = _empty_default,
	          silent: Optional[bool] = None) -> 'AbstractConfig':
		'''
		Returns a config object given by searching for the queries in the config object.
		If multiple queries are provided, each query is searched if the previous query fails.

		Args:
			*queries: Any number of queries to search for.
			default: The default value to return if none of the queries are not found.
			silent: If True, no message is reported based on the search.

		Returns:
			The config object found by the query, or the default value if none of the queries are found.

		'''
		raise NotImplementedError


	def pulls(self, *queries: str, default: Optional[Any] = _empty_default, silent: Optional[bool] = None) -> Any:
		'''
		Returns the value found by searching for the queries in the config object.

		Args:
			*queries: Any number of queries to search for.
			default: The default value to return if none of the queries are not found.
			silent: If True, no message is reported based on the search.

		Returns:
			The value found by the query, or the default value if none of the queries are found.

		'''
		raise NotImplementedError


	def push(self, addr: str, value: Any, overwrite: bool = True, *, silent: Optional[bool] = None) -> bool:
		'''
		Sets the value at the given address.

		Args:
			addr: The address to set the value at.
			value: The value to set.
			overwrite: If True, the value is set even if it already exists.
			silent: If True, no message is reported.

		Returns:
			True if the value was set, False if the value was not set.

		'''
		raise NotImplementedError


	def update(self, update: 'AbstractConfig') -> 'AbstractConfig':
		'''
		Updates the config object with the given config object (recursively overwriting common keys).

		Args:
			update: Config object to update with.

		Returns:
			The updated config object (self).

		'''
		raise NotImplementedError


	def silence(self, silent: bool = True) -> ContextManager:
		'''
		Context manager to silence the config object.

		Args:
			silent: If True, no messages are reported when querying the config object.

		Returns:
			Context manager to silence the config object.

		'''
		raise NotImplementedError


	def peek_named_children(self, *, silent: Optional[bool] = None) -> Iterator[Tuple[str, 'AbstractConfig']]:
		'''
		Returns an iterator of the child config objects of self together with their keys.

		Args:
			silent: If True, no messages are reported.

		Returns:
			An iterator of the child config objects of self together with their keys.

		'''
		raise NotImplementedError


	def peek_children(self, *, silent: Optional[bool] = None) -> Iterator['AbstractConfig']:
		'''
		Returns an iterator of the child config objects of self.

		Args:
			silent: If True, no messages are reported.

		Returns:
			An iterator of the child config objects of self.

		'''
		raise NotImplementedError


	def pull_named_children(self, *, force_create: Optional[bool] = False, silent: Optional[bool] = None) \
			-> Iterator[Tuple[str, Any]]:
		'''
		Returns an iterator of the child values of self together with their keys.

		Args:
			force_create: If True, creates new child values even if they already exist.
			silent: If True, no messages are reported.

		Returns:
			An iterator of the child values of self together with their keys.

		'''
		raise NotImplementedError


	def pull_children(self, *, force_create: Optional[bool] = False, silent: Optional[bool] = None) -> Iterator[Any]:
		'''
		Returns an iterator of the child values of self.

		Args:
			force_create: If True, creates new child values even if they already exist.
			silent: If True, no messages are reported.

		Returns:
			An iterator of the child values of self.

		'''
		raise NotImplementedError


	def create(self, *args: Any, **kwargs: Any) -> Any:
		'''
		Creates a new value based on the contents of self.

		Args:
			*args: Manual arguments to pass to the value constructor.
			**kwargs: Manual keyword arguments to pass to the value constructor.

		Returns:
			The newly created value.

		'''
		raise NotImplementedError


	def create_silent(self, *args: Any, **kwargs: Any) -> Any:
		'''
		Creates a new value based on the contents of self silently.

		Args:
			*args: Manual arguments to pass to the value constructor.
			**kwargs: Manual keyword arguments to pass to the value constructor.

		Returns:
			The newly created value.

		'''
		raise NotImplementedError


	def peek_create(self, query, default: Optional[Any] = _empty_default, *args, **kwargs):
		'''
		Composes the peek and create methods into a single method.

		Can be used to create a value using the config object found with the query.

		Args:
			query: The query to search for.
			default: If provided, the value is created using the default config object.
			*args: Manual arguments to pass to the value constructor.
			**kwargs: Manual keyword arguments to pass to the value constructor.

		Returns:
			The newly created value or `default` if the query is not found.

		'''
		raise NotImplementedError


	def process(self, *args: Any, **kwargs: Any) -> Any:
		'''
		Processes the config object using the contents of self.

		If a value for this config object has already been created, it is returned instead of creating a new one.

		Args:
			*args: Manual arguments to pass to the value constructor. (ignored if a value has already been created)
			**kwargs: Manual keyword arguments to pass to the value constructor.
			(ignored if a value has already been created)

		Returns:
			The processed value.

		'''
		raise NotImplementedError


	def peek_process(self, query, default: Optional[Any] = _empty_default, *args, **kwargs):
		'''
		Composes the peek and process methods into a single method.

		Args:
			query: The query to search for.
			default: If provided, the value is processed using the default config object.
			*args: Manual arguments to pass to the value constructor. (ignored if a value has already been created)
			**kwargs: Manual keyword arguments to pass to the value constructor.
			(ignored if a value has already been created)

		Returns:
			The processed value or `default` if the query is not found.

		'''
		raise NotImplementedError



class AbstractConfigurable:
	'''Abstract mix-in for objects that can be constructed using a config object.'''

	@classmethod
	def init_from_config(cls, config: AbstractConfig, args: Tuple = None, kwargs: Dict[str, Any] = None, *,
	                     silent: Optional[bool] = None) -> 'AbstractConfigurable':
		'''
		Constructor to initialize a class informed by the config object `config`.

		It is recommended that this should be a parent of any class that is registered as a component or modifier.

		Args:
			config: Config object to fill in any needed parameters.
			args: Manually specified arguments to pass to the constructor.
			kwargs: Manually specified keyword arguments to pass to the constructor.
			silent: If True, no messages are reported when querying the config object.

		Returns:
			Initialized instance of this class.

		'''
		raise NotImplementedError



class AbstractCertifiable(AbstractConfigurable):
	'''Abstract mix-in for objects that can must be certified after intialization.'''

	def __certify__(self, config: AbstractConfig) -> Optional[Any]:
		'''
		Certifies the object.

		Args:
			silent: If True, no messages are reported.

		'''
		return self



class AbstractConfigManager:
	'''Abstract class for config managers.'''


	class ConfigNotRegistered(KeyError):
		'''A config was not registered'''
		pass


	ConfigNode = None


	def register_config(self, name: str, path: Union[str, Path]) -> NamedTuple:
		'''
		Registers a path as a config file with the given name.

		Args:
			name: Name to register the config file under.
			path: Path to the config file.

		Returns:
			The entry that was registered (should contain at least the attributes for the name and path).

		'''
		raise NotImplementedError


	def register_config_dir(self, root: Union[str, Path]) -> List[NamedTuple]:
		'''
		Recursively registers all config files found in the given directory.

		Args:
			root: Path to the directory of the config files that should be registered.

		Returns:
			A list of the names of the registered config files.

		'''
		raise NotImplementedError


	def iterate_configs(self) -> Iterator[NamedTuple]:
		'''
		Iterates over all registered config files.

		Returns:
			An iterator over all registered config files.

		'''
		raise NotImplementedError


	def find_local_config_entry(self, name: str, default: Optional[Any] = unspecified_argument) -> NamedTuple:
		'''
		Finds the entry for the config file with the given name in the registry.

		Args:
			name: Name of the config file to find.
			default: Default value to return if the artifact is not found.

		Returns:
			The entry for the config file with the given name.

		Raises:
			:class:`KeyError`: If the config file is not registered.

		'''
		raise NotImplementedError


	def find_project_config_entry(self, name: str, default: Optional[Any] = unspecified_argument) -> NamedTuple:
		'''
		Finds the entry for a config by name. Including checking the nonlocal projects.

		Args:
			name: of the config file used to register the config
			default: Default value to return if the artifact is not found.

		Returns:
			The entry for the config

		Raises:
			ConfigNotFoundError: if the config is not registered

		'''
		raise NotImplementedError


	def find_config_path(self, name: str, default: Optional[Any] = unspecified_argument) -> Path:
		'''
		Finds the path to the config file with the given name in the registry.

		Args:
			name: Name of the config file to find.
			default: Default value to return if the artifact is not found.

		Returns:
			The path to the config file with the given name.

		Raises:
			:class:`KeyError`: If the config file is not registered.

		'''
		raise NotImplementedError


	def parse_argv(self, argv: Sequence[str], script_name: Optional[str] = unspecified_argument) -> AbstractConfig:
		'''
		Parses the given arguments and returns a config object.

		Arguments are expected in the following order (all of which are optional):
			1. Meta rules to modify the config loading process and run mode.
			2. Name of the script to run.
			3. Names of registered config files that should be loaded and merged (in order of precedence).
			4. Manual config parameters (usually keys, prefixed by :code:`--` and corresponding values)

		Args:
			argv: List of arguments to parse (expected to be :code:`sys.argv[1:]`).
			script_name: Manually specified name of the script (defaults to what is specified in the resulting config).

		Returns:
			Config object containing the parsed arguments.

		'''
		raise NotImplementedError


	def create_config(self, configs: Optional[Sequence[str]] = None, data: Optional[JSONABLE] = None) -> AbstractConfig:
		'''
		Creates a config object from the given config file names and provided arguments.

		Args:
			configs: Names of registered config files to load and merge (in order of precedence).
			data: Manual config parameters to populate the config object with.

		Returns:
			Config object resulting from loading/merging `configs` and including `data`.

		'''
		raise NotImplementedError


	def load_raw_config(self, path: Union[str, Path]) -> JSONABLE:
		'''
		Loads a config file from the given path and returns the raw config data
		(made up of standard python objects, such as :py:class:`dict` and :py:class:`list`).

		Args:
			path: Path to the config file to load.

		Returns:
			Config data loaded from the given path.

		Raises:
			:class:`FileNotFoundError`: If the config file does not exist.
			:class:`ValueError`: If the config file cannot be loaded.

		'''
		raise NotImplementedError


	def configurize(self, raw: JSONABLE) -> AbstractConfig:
		'''
		Converts the given raw config data into a config object.

		Raw config data can include primitives, lists, and dicts (including OrderedDict or tuples),
		but should not include any other types.

		Args:
			raw: Raw config data to convert into a config object.

		Returns:
			Config object created from the given raw config data.

		'''
		raise NotImplementedError


	def merge_configs(self, *configs: AbstractConfig) -> AbstractConfig:
		'''
		Merges the given config objects into a single config object.

		Including recursively merging any nested config objects and overwriting any duplicate keys
		in reverse provided order (so the configs should be provided in order of precedence).

		Args:
			*configs: Provided config objects to merge.

		Returns:
			Config object resulting from merging the given config objects.

		'''
		raise NotImplementedError


	@staticmethod
	def update_config(base: AbstractConfig, update: AbstractConfig) -> AbstractConfig:
		'''
		Updates the config object with the given config object (recursively overwriting common keys).

		Args:
			base: Config object to update.
			update: Config object to update `base` with.

		Returns:
			The updated config object `base`.

		'''
		raise NotImplementedError



class AbstractCustomArtifact:
	@staticmethod
	def top(config: AbstractConfig, *args: Any, **kwargs: Any) -> Any:
		raise NotImplementedError


	def get_wrapped(self) -> Union[Callable, Type]:
		raise NotImplementedError



class AbstractCreator:
	'''Abstract class for creators.'''

	_creator_name = None

	@classmethod
	def replace(cls, creator: 'AbstractCreator', config: AbstractConfig, **kwargs) -> 'AbstractCreator':
		'''
		Extracts any required information from the required `creator` to create and return a new creator.

		Args:
			creator: base creator to extract information from.
			config: config object to initialize the new creator with.
			**kwargs: other keyword arguments to pass to the new creator initialization.

		Returns:
			New creator created from the given `creator` and `config`.

		'''
		return cls(config, **kwargs)


	def __init__(self, config: AbstractConfig, **kwargs: Any):
		super().__init__(**kwargs)


	def create(self, config: AbstractConfig, *args: Any, **kwargs: Any) -> Any:
		'''
		Creates an object from the given config node and other arguments.

		Args:
			config: Config node to create the object from.
			*args: Manual arguments to pass to the object.
			**kwargs: Manual keyword arguments to pass to the object.

		Returns:
			Object created from the given config node and other arguments.

		'''
		return self.create_product(config, args=args, kwargs=kwargs)


	def create_product(self, config: AbstractConfig, args: Optional[Tuple] = None,
	                   kwargs: Optional[Dict[str,Any]] = None) -> Any:
		'''
		Creates an object from the given config node and other arguments.

		Args:
			config: Config node to create the object from.
			args: Manual arguments to pass to the object.
			kwargs: Manual keyword arguments to pass to the object.

		Returns:
			Object created from the given config node and other arguments.

		'''
		raise NotImplementedError



class AbstractRunMode(Activatable):
	'''Abstract class for run modes. Run modes include Projects and Profiles'''

	def main(self, argv: Sequence[str], script_name: Optional[str] = None) -> Any:
		'''
		Runs the script with the given arguments using the config object obtained by parsing ``argv``.

		Args:
			argv: List of top-level arguments (expected to be :code:`sys.argv[1:]`).
			script_name: specified name of the script
			(defaults to what is specified in argv when it is parsed into a config object).

		Returns:
			The output of the script.

		'''
		raise NotImplementedError


	def run_script(self, script_name: str, config: AbstractConfig, *args: Any, **kwargs: Any) -> Any:
		'''
		Runs the script with the given arguments using :func:`run()` of the current project.

		Args:
			script_name: The script name to run (must be registered).
			config: Config object to run the script with (must include the script under :code:`_meta.script_name`).
			*args: Manual arguments to pass to the script.
			**kwargs: Manual keyword arguments to pass to the script.

		Returns:
			The output of the script.

		'''
		raise NotImplementedError


	def run(self, config: AbstractConfig, *args: Any, **kwargs: Any) -> Any:
		'''
		Runs a script with the given config object and other arguments.

		Before running the script using :func:`run_local()`, the config object is validated with :func:`validate_run()`,
		which can modify the run mode.

		Args:
			config: Config object to run the script with (must include the script under :code:`_meta.script_name`).
			args: Manual arguments to pass to the script.
			kwargs: Manual keyword arguments to pass to the script.

		Returns:
			The output of the script.

		'''
		raise NotImplementedError


	def cleanup(self):
		'''
		After running the script through :func:`main()`, this method is called
		to clean up any resources used by the run mode.

		Returns:
			:code:`None`

		'''
		for behavior in self.behaviors():
			behavior.cleanup()


	def behaviors(self) -> Iterator['AbstractBehavior']:
		'''Iterates over all behaviors associated with this project.'''
		raise NotImplementedError


	def validate_run(self, config: AbstractConfig) -> Optional['AbstractRunMode']:
		'''
		Validates the config object before running the script.

		Args:
			config: Config object to validate.

		Returns:
			:code:`None` if the config is valid, otherwise the run mode to transfer to.

		'''
		pass


	def parse_argv(self, argv: Sequence[str], *, script_name: Optional[str] = None) -> AbstractConfig:
		'''
		Parses the given arguments and returns a config object.

		Arguments are expected in the following order (all of which are optional):
			1. Meta rules to modify the config loading process and run mode.
			2. Name of the script to run.
			3. Names of registered config files that should be loaded and merged (in order of precedence).
			4. Manual config parameters (usually keys, prefixed by :code:`--` and corresponding values)

		Args:
			argv: List of arguments to parse (expected to be :code:`sys.argv[1:]`).
			script_name: Manually specified name of the script (defaults to what is specified in the resulting config).

		Returns:
			Config object containing the parsed arguments.

		'''
		raise NotImplementedError



class AbstractProject(AbstractRunMode, FileInfo, Activatable):
	'''
	Abstract class for projects. Projects track artifacts (eg. configs and components) in registries
	and manage loading configs and running scripts.
	'''
	def __init__(self, path: Optional[Union[str, Path]] = None, profile: 'AbstractProfile' = None, **kwargs):
		super().__init__(path, **kwargs)
		self._profile = profile


	def __eq__(self, other: 'AbstractProject') -> bool:
		'''
		Compares two projects based on their paths.

		Args:
			other: Another project object.

		Returns:
			:code:`True` if the projects have the same path, otherwise :code:`False`.

		'''
		return self.data['info_path'] == other.data['info_path']


	@property
	def profile(self) -> 'AbstractProfile':
		'''
		Profile object that the project is associated with.

		Returns:
			Profile object.

		'''
		return self._profile


	def nonlocal_projects(self) -> Iterator[NamedTuple]:
		'''
		Iterator over all projects that are related to this one, followed by all active base projects
		of the profile (without repeating any projects).

		Returns:
			An iterator over all projects that are related to this one, followed by all active base projects

		'''
		raise NotImplementedError


	def behaviors(self) -> Iterator[NamedTuple]:
		'''
		Iterates over all behavior instances associated with this project.

		By default, this creates an instance for all behaviors in the profile.

		Returns:
			Iterator over meta rules in order of priority (highest -> least).

		'''
		raise NotImplementedError


	class UnknownArtifactError(Registry.NotFoundError):
		'''Raised when trying to find an artifact that is not registered.'''
		def __init__(self, artifact_type: str, ident: str):
			super().__init__(f'{artifact_type} {ident!r} not found')
			self.artifact_type = artifact_type
			self.ident = ident


	def xray(self, artifact: str, *, sort: Optional[bool] = False, reverse: Optional[bool] = False,
	         as_list: Optional[bool] = False) -> Optional[List[NamedTuple]]:
		'''
		Prints a list of all artifacts of the given type accessible from this project
		(including related and active base projects).

		Args:
			artifact: artifact type (e.g. 'script', 'config')
			sort: sort the list of artifacts by name
			reverse: reverse the order of the list of artifacts
			as_list: instead of printing, return the list of artifacts

		Returns:
			list: if as_list is True, returns a list of artifacts

		Raises:
			UnknownArtifactTypeError: if the given artifact type does not exist

		'''
		raise NotImplementedError


	def find_local_artifact(self, artifact_type: str, ident: str,
	                        default: Optional[Any] = unspecified_argument) -> Optional[NamedTuple]:
		'''
		Finds the artifact with the given type and identifier in ``self``
		without checking related projects or active projects in the profile.

		Args:
			artifact_type: The type of artifact to find.
			ident: The identifier of the artifact to find.
			default: The default value to return if the artifact is not found.

		Returns:
			The artifact entry from the registry corresponding to the given type.

		Raises:
			UnknownArtifactTypeError: If the artifact type is not registered.
			UnknownArtifactError: If the artifact is not found and no default is given.

			'''
		raise self.UnknownArtifactError(artifact_type, ident)


	def find_artifact(self, artifact_type: str, ident: str,
	                  default: Optional[Any] = unspecified_argument) -> NamedTuple:
		'''
		Finds an artifact in the project's registries.
		Artifacts are data or functionality such as configs and components.

		Args:
			artifact_type: Type of artifact to find (eg. 'config' or 'component').
			ident: Name of the artifact that was registered.
			default: Default value to return if the artifact is not found.

		Returns:
			Artifact object, or, if a default value is given and artifact is not found.

		Raises:
			:class:`UnknownArtifactError`: if the artifact is not found and no default is specified.

		'''
		raise self.UnknownArtifactError(artifact_type, ident)


	def register_artifact(self, artifact_type: str, ident: str, artifact: Union[Type, Callable],
	                      **kwargs: Any) -> NamedTuple:
		'''
		Registers a new artifact in the project's registries.
		Overwrites any existing artifact with the same name.

		Args:
			artifact_type: Type of artifact to register (eg. 'config' or 'component').
			ident: Name of the artifact to be registered.
			artifact: Artifact object to register (usually a function, type, or path).
			**kwargs: Optional additional parameters to store with the artifact.

		Returns:
			Registration entry for the artifact.

		'''
		raise NotImplementedError


	def iterate_artifacts(self, artifact_type: str) -> Iterator[NamedTuple]:
		'''
		Iterates over all artifacts of the given type in the project's registries.

		Args:
			artifact_type: Type of artifact to iterate (eg. 'config' or 'component').

		Returns:
			Iterator over all artifacts of the given type.

		'''
		raise NotImplementedError


	def create_config(self, *configs: str, **parameters: Primitive) -> AbstractConfig:
		'''
		Creates a new config object with the given parameters.Creates a config object from
		the given config file names and provided parameters.

		Args:
			*configs: Names of registered config files to load and merge (in order of precedence).
			**parameters: Manual config parameters to populate the config object with.

		Returns:
			Config object.

		'''
		raise NotImplementedError


	def quick_run(self, script_name: str, *configs: str, **parameters: JSONABLE) -> Any:
		'''
		Composes :func:`create_config() and :func:`run_script()` into a single method to
		first create a config object and then run the specified script.

		Args:
			script_name: Name of the script to run (should be registered).
			*configs: Names of registered config files to load and merge (in order of precedence).
			**parameters: Manual config parameters to populate the config object with.

		Returns:
			Output of the script.

		'''
		config = self.create_config(*configs, **parameters)
		return self.run_script(script_name, config)



class AbstractProfile(FileInfo, Activatable): # generally you should extend organization.workspaces.ProfileBase
	'''
	Abstract classes for profiles. Profiles manage projects and provide meta rules. Unlike projects,
	generally a runtime should only use a single global instance of a profile.
	'''

	@classmethod
	def get_project_type(cls, ident: str) -> NamedTuple:
		'''
		Gets the project type entry for the given identifier (from a registry).

		Args:
			ident: Name of the registered project type.

		Returns:
			Project type entry.

		'''
		raise NotImplementedError


	@classmethod
	def replace_profile(cls, profile: 'AbstractProfile') -> 'AbstractProfile':
		'''
		Replaces the current profile instance with the given profile. This is used to set the global profile.

		Args:
			profile: New profile instance.

		Returns:
			Old profile instance (which is now replaced).

		'''
		raise NotImplementedError


	@classmethod
	def get_profile(cls) -> 'AbstractProfile':
		'''
		Gets the current profile instance of the runtime environment.

		Returns:
			Profile instance.

		'''
		raise NotImplementedError


	@classmethod
	def register_behavior(cls, name: str, typ: Type['AbstractBehavior'], *,
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
		raise NotImplementedError


	@classmethod
	def get_behavior(cls, name: str) -> NamedTuple:
		'''
		Gets the behavior entry for the given identifier (from the registry).

		Args:
			name: Name of the registered behavior.

		Returns:
			Behavior entry.

		'''
		raise NotImplementedError


	@classmethod
	def iterate_behaviors(cls) -> Iterator[NamedTuple]:
		'''
		Iterates over all registered behaviors.

		Returns:
			Iterator over all behavior entries.

		'''
		raise NotImplementedError


	def entry(self, script_name: Optional[str] = None) -> None:
		'''
		Primary entry point for the profile. This method is called when using the :command:`fig` command.

		Args:
			script_name: Manually specified script name to run (if not provided, will be parsed from :code:`sys.argv`).

		Returns:
			:code:`None`

		'''
		raise NotImplementedError


	def initialize(self, *projects: str) -> None:
		'''
		Initializes the specified projects (including activating them, which generally registers
		all associated configs and imports files and packages)

		Args:
			*projects: Identifiers of projects to initialize (activates the current project only, if none is provided).

		Returns:
			:code:`None`

		'''
		raise NotImplementedError


	def main(self, argv: Sequence[str], *, script_name: Optional[str] = None) -> Any:
		'''
		Runs the script with the given arguments using :func:`main()` of the current project.

		Args:
			argv: List of top-level arguments (expected to be :code:`sys.argv[1:]`).
			script_name: specified name of the script
			(defaults to what is specified in argv when it is parsed into a config object).

		Returns:
			The output of the script.

		'''
		raise NotImplementedError


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
		raise NotImplementedError


	def run(self, config: AbstractConfig, *,
	        args: Optional[Tuple] = None, kwargs: Optional[Dict[str, Any]] = None) -> Any:
		'''
		Runs the script with the given arguments using :func:`run()` of the current project.

		This method assumes the script_name is already contained in the config, otherwise use :func:`run_script()`.

		Args:
			config: Config object to run the script with (must include the script under :code:`_meta.script_name`).
			args: Manual arguments to pass to the script.
			kwargs: Manual keyword arguments to pass to the script.

		Returns:
			The output of the script.

		'''
		raise NotImplementedError


	def quick_run(self, script_name: str, *configs: str, **parameters: Any) -> Any:
		'''
		Creates a config object and runs the script using :func:`quick_run()` of the current project.

		Args:
			script_name: Name of the script to run (must be registered).
			*configs: Names of registered config files to load and merge (in order of precedence).
			**parameters: Manual config parameters to populate the config object with.

		Returns:
			Output of the script.

		'''
		raise NotImplementedError


	def cleanup(self) -> None:
		'''
		Calls :func:`cleanup()` of the current project. Generally not needed to be called manually.

		Returns:
			:code:`None`

		'''
		raise NotImplementedError


	def create_config(self, *configs: str, **parameters: JSONABLE) -> AbstractConfig:
		'''
		Process the provided data to create a config object (using the current project).

		Args:
			configs: usually a list of parent configs to be merged
			parameters: any manual parameters to include in the config object

		Returns:
			Config object resulting from loading/merging `configs` and including `data`.
		'''
		raise NotImplementedError


	def parse_argv(self, argv: Sequence[str], script_name=None) -> AbstractConfig:
		'''
		Parses the given arguments and returns a config object.

		Arguments are expected in the following order (all of which are optional):
			1. Meta rules to modify the config loading process and run mode.
			2. Name of the script to run.
			3. Names of registered config files that should be loaded and merged (in order of precedence).
			4. Manual config parameters (usually keys, prefixed by :code:`--` and corresponding values)

		Args:
			argv: List of arguments to parse (expected to be :code:`sys.argv[1:]`).
			script_name: Manually specified name of the script (defaults to what is specified in the resulting config).

		Returns:
			Config object containing the parsed arguments.

		'''
		raise NotImplementedError


	def extract_info(self, other: 'AbstractProfile') -> None:
		'''
		Extract data from the provided profile instance and store it in self.

		Recommended to use if a project expects a custom profile different from the currently used one.

		Args:
			profile: Base profile instance.

		Returns:
			:code:`None`

		'''
		return super().extract_info(other)


	def get_current_project(self) -> AbstractProject:
		'''
		Gets the current project instance.

		Returns:
			Current project instance.

		'''
		raise NotImplementedError


	def switch_project(self, ident: Optional[str] = None) -> AbstractProject:
		'''
		Switches the current project to the one with the given identifier.

		Args:
			ident: Name of the project to switch to, defaults to the default project (with name: None).

		Returns:
			New current project instance.

		'''
		raise NotImplementedError


	def project_context(self, ident: Optional[Union[str, AbstractProject]] = None) -> ContextManager[AbstractProject]:
		'''
		Context manager to temporarily switch to a different current project.

		Args:
			ident: Name of the project to switch to, defaults to the default project (with name: None).

		Returns:
			Context manager to switch to the specified project.

		'''
		raise NotImplementedError


	def iterate_projects(self) -> Iterator[AbstractProject]:
		'''
		Iterates over all loaded projects.

		Returns:
			Iterator over all loaded project instances.

		'''
		raise NotImplementedError


	def get_project(self, ident: Optional[str] = None) -> AbstractProject:
		'''
		Gets the project with the given identifier, if the project is not already loaded, it will be loaded.

		Args:
			ident: Name of the project to get, defaults to the default project (with name: None).

		Returns:
			Project instance.

		'''
		raise NotImplementedError



class AbstractBehavior:
	'''Interface for meta rules.'''

	def __init__(self, project: AbstractProject, **kwargs: Any):
		'''
		Behaviors are usually instantiated by the project at the beginning :meth:`main()` method.

		Otherwise, if :meth:`main()` is not used, the behaviors are instantiated in :meth:`run()`
		right before the behaviors are filtered using :meth:`include()`.

		Args:
			project: Project of this behavior instance.
			**kwargs: Additional keyword arguments (unused).

		'''
		super().__init__(**kwargs)


	class TerminationFlag(KeyboardInterrupt): # TODO: can decide the output
		'''Raised if the subsequent script should not be run.'''

		out = None
		def __init__(self, out: Any = None):
			'''
			Prevents the subsequent script from being run.

			Args:
				out: User-defined output to be returned instead of the output of the script.
			'''
			super().__init__()
			self.out = out


	@staticmethod
	def parse_argv(meta: Dict[str, Any], argv: List[str], script_name: Optional[str] = None) -> Optional[List[str]]:
		'''
		Optionally modifies the arguments when the project's :meth:`main()` is called.

		Args:
			meta: Meta-data extracted from the argv so far (can be modified here).
			argv: List of arguments to parse (expected to be :code:`sys.argv[1:]`).
			script_name: Manually specified name of the script (if not provided, it will be parsed from argv).

		Returns:
			Modified list of arguments (or :code:`None` if no modification is needed).

		'''
		pass

	@staticmethod
	def validate_project(config: AbstractConfig) -> Optional[AbstractProject]:
		'''
		Validates the project (provided in constructor) using the given config object before running it.

		If a different project should be used, it can be returned here.

		Args:
			config: The config object to use for validation.

		Returns:
			The new project to use for the script execution or ``None`` if no new project was returned.

		'''
		pass


	@staticmethod
	def include(meta: AbstractConfig) -> bool:
		'''
		Checks if the current behavior should be included in the subsequent script execution.

		Args:
			meta: Meta config to configure behavior and script execution.

		Returns:
			:code:`True` if the behavior should be included, :code:`False` otherwise.

		'''
		return True


	@staticmethod
	def pre_run(meta: AbstractConfig, config: AbstractConfig) -> Optional[AbstractConfig]:
		'''
		Runs before the script is executed, within the project :meth:`run()`.

		Args:
			meta: Meta config to configure behavior and script execution.
			config: Config object which will be passed to the script.

		Returns:
			New config object to pass to the script instead (or None to use the original config).

		Raises:
			:exc:`TerminationFlag`: If the subsequent script should not be run.

		'''
		pass


	class IgnoreException(Exception):
		'''Raised if the underlying exception raised while running the script should be ignored.'''
		def __init__(self, out: Any = None):
			'''
			Instead of raising the exception, ``out`` will be returned.

			Args:
				out: User-defined output to be returned instead of raising the exception.
			'''
			super().__init__()
			self.out = out


	@staticmethod
	def handle_exception(meta: AbstractConfig, config: AbstractConfig, exc: Exception) -> None:
		'''
		Runs if the script raises an exception.

		Args:
			meta: Meta config to configure behavior and script execution.
			config: Config object to run the script with.
			exc: Exception that was raised.

		Returns:
			:code:`None`

		Raises:
			:exc:`IgnoreException`: If the exception should be ignored.
			:exc:`TerminationFlag`: If the subsequent behaviors should not be run.

		'''
		pass


	@staticmethod
	def post_run(meta: AbstractConfig, config: AbstractConfig, output: Any) -> Optional[Any]:
		'''
		Function called after the script is run.
		If the function returns a value, it will be used as the output of the script.

		Args:
			meta: Meta config to configure behavior and script execution.
			config: Config object used to run the script with.
			output: Output of the script.

		Returns:
			New output of the script, or :code:`None` to use the original output.

		Raises:
			:exc:`TerminationFlag`: If the subsequent behaviors should not be run.

		'''
		pass


	@staticmethod
	def cleanup():
		'''
		Function called at the end of the project :meth:`main()` during cleanup.

		Note that this is only called if the project :meth:`main()`. To define a cleanup function for
		the behavior that is called every time a script is run, use :meth:`post_run()`.

		Returns:
			:code:`None`

		'''
		pass


	def __cmp__(self, other):
		'''Compares the behavior to another behavior for ordering.'''
		raise NotImplementedError

