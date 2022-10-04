from typing import List, Dict, Tuple, Optional, Union, Any, Hashable, Sequence, Callable, Generator, Type, Iterable, \
	Iterator, NamedTuple, ContextManager
import abc
from pathlib import Path
from omnibelt import unspecified_argument, Class_Registry, Primitive, JSONABLE

from .mixins import Activatable, FileInfo

class AbstractConfig: # TODO: copy, deepcopy, etc
	'''Abstract class for config objects'''

	_empty_default = unspecified_argument

	@property
	@abc.abstractmethod
	def project(self) -> 'AbstractProject':
		'''Returns the project object associated with this config'''
		raise NotImplementedError
	@project.setter
	@abc.abstractmethod
	def project(self, project: 'AbstractProject'):
		'''Sets the project object associated with this config'''
		raise NotImplementedError

	@property
	@abc.abstractmethod
	def root(self) -> 'AbstractConfig':
		'''Returns the root node of the config object'''
		raise NotImplementedError

	def peek(self, query: Optional[str] = None, default: Optional[Any] = _empty_default, *,
	         silent: Optional[bool] = False) -> 'AbstractConfig':
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
	         silent: Optional[bool] = False) -> Any:
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

	def push_pull(self, addr: str, value: Any, *, overwrite: bool = True, silent: Optional[bool] = False) -> Any:
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

	def push_peek(self, addr: str, value: Any, *, overwrite: bool = True, silent: Optional[bool] = False) \
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
	          silent: Optional[bool] = False) -> 'AbstractConfig':
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

	def pulls(self, *queries: str, default: Optional[Any] = _empty_default, silent: Optional[bool] = False) -> Any:
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

	def push(self, addr: str, value: Any, overwrite: bool = True, *, silent: Optional[bool] = False) -> bool:
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


class AbstractConfigManager:
	'''Abstract class for config managers.'''

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

	def find_config_entry(self, name: str) -> NamedTuple:
		'''
		Finds the entry for the config file with the given name in the registry.

		Args:
			name: Name of the config file to find.

		Returns:
			The entry for the config file with the given name.

		Raises:
			KeyError: If the config file is not registered.

		'''
		raise NotImplementedError

	def find_config_path(self, name: str) -> Path:
		'''
		Finds the path to the config file with the given name in the registry.

		Args:
			name: Name of the config file to find.

		Returns:
			The path to the config file with the given name.

		Raises:
			KeyError: If the config file is not registered.

		'''
		raise NotImplementedError

	def parse_argv(self, argv: Sequence[str], script_name: Optional[str] = unspecified_argument) -> AbstractConfig:
		'''
		Parses the given arguments and returns a config object.

		Arguments are expected in the following order (all of which are optional):
			1. Meta rules to modify the config loading process and run mode.
			2. Name of the script to run.
			3. Names of registered config files that should be loaded and merged (in order of precedence).
			4. Manual config parameters (usually keys, prefixed by "--" and corresponding values)

		Args:
			argv: List of arguments to parse (expected to be sys.argv[1:]).
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
		(made up of standard python objects, such as `dict` and `list`).

		Args:
			path: Path to the config file to load.

		Returns:
			Config data loaded from the given path.

		Raises:
			FileNotFoundError: If the config file does not exist.
			ValueError: If the config file cannot be loaded.

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


class AbstractScript:
	'''Abstract class for scripts. (generally doesn't have to be used)'''
	def __call__(self, config: AbstractConfig):
		raise NotImplementedError


class AbstractComponent:
	'''Abstract class for components. (generally doesn't have to be used)'''
	pass


class AbstractModifier:
	'''Abstract class for modifiers. (generally doesn't have to be used)'''
	pass


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

	def main(self, argv: Sequence[str], *, script_name: Optional[str] = None) -> Any:
		'''
		Runs the script with the given arguments. First the arguments are parsed into a config object, and then
		the specified script is run with the config object using `run()`.

		After parsing the arguments, the config object is validated with `validate_main()`,
		which can modify the run mode. Before running the script, `self` is activated with `activate()`
		(which usually loads any required files or packages for the script).

		Args:
			argv: List of top-level arguments (expected to be sys.argv[1:]).
			script_name: specified name of the script
			(defaults to what is specified in argv when it is parsed into a config object).

		Returns:
			The output of the script.

		'''
		config = self.parse_argv(argv, script_name=script_name)
		transfer = self.validate_main(config) # can update/modify the project based on the config
		if transfer is not None:
			return transfer.main(argv, script_name=script_name)
		self.activate() # load the project
		out = self.run(config, script_name=script_name) # run based on the config
		self.cleanup() # (optional) cleanup
		return out # return output

	def run(self, config: AbstractConfig, *, script_name: Optional[str] = None,
	        args: Optional[Tuple] = None, kwargs: Optional[Dict[str, Any]] = None, **meta: Any) -> Any:
		'''
		Runs a script with the given config object and other arguments.

		Before running the script using `run_local()`, the config object is validated with `validate_run()`,
		which can modify the run mode.

		Args:
			config: Config object to run the script with.
			script_name: Name of the script to run (usually must be registered beforehand to find the function).
			args: Manual arguments to pass to the script.
			kwargs: Manual keyword arguments to pass to the script.
			**meta: Meta arguments to modify the run mode (generally not recommended).

		Returns:
			The output of the script.

		'''
		transfer = self.validate_run(config)
		if transfer is not None:
			return transfer.run(config, script_name=script_name)
		return self.run_local(config, script_name=script_name, args=args, kwargs=kwargs, meta=meta)

	def cleanup(self, *args, **kwargs):
		'''
		After running the script through `main()`, this method is called to clean up any resources used by the run mode.

		Args:
			*args: usually unused
			**kwargs: usually unused

		Returns:

		'''
		pass

	def validate_main(self, config: AbstractConfig) -> Optional['AbstractRunMode']:
		'''
		Validates the config object after parsing the arguments and before activating `self`
		(usually loading missing files and packages).

		Args:
			config: Config object to validate.

		Returns:
			`None` if the config is valid, otherwise the run mode to transfer to.

		'''
		pass

	def validate_run(self, config: AbstractConfig) -> Optional['AbstractRunMode']:
		'''
		Validates the config object before running the script.

		Args:
			config: Config object to validate.

		Returns:
			`None` if the config is valid, otherwise the run mode to transfer to.

		'''
		pass

	def parse_argv(self, argv: Sequence[str], *, script_name: Optional[str] = None) -> AbstractConfig:
		'''
		Parses the given arguments and returns a config object.

		Arguments are expected in the following order (all of which are optional):
			1. Meta rules to modify the config loading process and run mode.
			2. Name of the script to run.
			3. Names of registered config files that should be loaded and merged (in order of precedence).
			4. Manual config parameters (usually keys, prefixed by "--" and corresponding values)

		Args:
			argv: List of arguments to parse (expected to be sys.argv[1:]).
			script_name: Manually specified name of the script (defaults to what is specified in the resulting config).

		Returns:
			Config object containing the parsed arguments.

		'''
		raise NotImplementedError

	def run_local(self, config: AbstractConfig, *, script_name: Optional[str] = None, args: Optional[Tuple] = None,
	        kwargs: Optional[Dict[str, Any]] = None, meta: Optional[Dict[str, Any]] = None) -> Any:
		'''
		Runs a script with the given config object and other arguments.

		Args:
			config: Config object to run the script with.
			script_name: Manually specified name of the script (defaults to what is specified in the resulting config).
			args: Manual arguments to pass to the script.
			kwargs: Manual keyword arguments to pass to the script.
			meta: Meta arguments to modify how the script is run (generally not recommended).

		Returns:
			The output of the script.

		'''
		raise NotImplementedError



# _ArtifactEntry = NamedTuple('ArtifactEntry', [('name', str), ('value', Type)])
MetaRuleFunction = Callable[[AbstractConfig, Dict[str, Any]], Optional[AbstractConfig]]
# _MetaRuleEntry = NamedTuple('MetaRuleEntry', 'fn:MetaRuleFunction code:str priority:int num_args:int')



class AbstractProject(AbstractRunMode, FileInfo): # generally you should extend organization.workspaces.ProjectBase
	def __init__(self, path: Optional[Union[str, Path]] = None, profile: 'AbstractProfile' = None, **kwargs):
		super().__init__(path, **kwargs)
		self._profile = profile

	def __eq__(self, other: 'AbstractProject') -> bool:
		return self.data['info_path'] == other.data['info_path']

	@property
	def profile(self) -> 'AbstractProfile':
		return self._profile


	def iterate_meta_rules(self) -> Iterator:
		return self._profile.iterate_meta_rules()
	
	class UnknownArtifactError(Exception):
		def __init__(self, artifact_type, ident):
			super().__init__(f'{artifact_type} {ident!r} not found')
			self.artifact_type = artifact_type
			self.ident = ident
	
	def find_artifact(self, artifact_type: str, ident: str,
	                  default: Optional[Any] = unspecified_argument) -> NamedTuple:
		raise self.UnknownArtifactError(artifact_type, ident)

	def register_artifact(self, artifact_type: str, ident: str, artifact: Union[Type, Callable],
	                      **kwargs: Any) -> None:
		raise NotImplementedError

	def iterate_artifacts(self, artifact_type: str) -> Iterator[NamedTuple]:
		raise NotImplementedError


	def create_config(self, *parents: str, **parameters: Primitive) -> AbstractConfig:
		raise NotImplementedError

	def quick_run(self, script_name: str, *parents: str, **parameters: JSONABLE) -> Any:
		config = self.create_config(*parents, **parameters)
		return self.run(config, script_name=script_name)



# _ProjectTypeEntry = NamedTuple('ProjectTypeEntry', [('name', str), ('cls', Type[AbstractProject])])



class AbstractProfile(FileInfo): # generally you should extend organization.workspaces.ProfileBase
	@classmethod
	def get_project_type(cls, ident: str) -> NamedTuple:
		raise NotImplementedError

	@classmethod
	def replace_profile(cls, profile: 'AbstractProfile') -> 'AbstractProfile':
		raise NotImplementedError

	@classmethod
	def get_profile(cls) -> 'AbstractProfile':
		raise NotImplementedError

	@classmethod
	def register_meta_rule(cls, name: str, func: MetaRuleFunction, code: str,
	                       priority: Optional[int] = 0, num_args: Optional[int] = 0) -> None:
		raise NotImplementedError

	@classmethod
	def get_meta_rule(cls, name: str):
		raise NotImplementedError

	@classmethod
	def iterate_meta_rules(cls) -> Iterator:
		raise NotImplementedError


	def entry(self, script_name=None) -> None:
		raise NotImplementedError

	def initialize(self, *projects: str, **kwargs) -> None:
		raise NotImplementedError

	def main(self, argv: Sequence[str], *, script_name: Optional[str] = None) -> Any:
		raise NotImplementedError

	def run(self, config, *, script_name=None, args: Optional[Tuple] = None,
	        kwargs: Optional[Dict[str, Any]] = None, meta: Optional[Dict[str, Any]] = None) -> Any:
		raise NotImplementedError

	def quick_run(self, script_name: str, *parents: str, **args: Any) -> Any:
		raise NotImplementedError

	def cleanup(self, *args, **kwargs) -> None:
		raise NotImplementedError


	def extract_info(self, other: 'AbstractProfile') -> None:
		raise NotImplementedError

	def get_current_project(self) -> AbstractProject:
		raise NotImplementedError

	def switch_project(self, ident: Optional[str] = None) -> AbstractProject:
		raise NotImplementedError

	def iterate_projects(self) -> Iterator[AbstractProject]:
		raise NotImplementedError

	def get_project(self, ident: Optional[str] = None) -> AbstractProject:
		raise NotImplementedError



class AbstractMetaRule:
	class TerminationFlag(KeyboardInterrupt): pass

	@classmethod
	def run(cls, config: AbstractConfig, meta: Dict[str, Any]) -> Optional[AbstractConfig]:
		raise NotImplementedError












