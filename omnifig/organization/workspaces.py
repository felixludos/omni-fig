from typing import Optional, Union, Sequence, NamedTuple, Tuple, Any, Dict, List, Type, Iterator, Callable
from pathlib import Path
import inspect
from collections import OrderedDict
from omnibelt import unspecified_argument, get_printer, Class_Registry, Function_Registry, colorize, include_modules


from ..abstract import AbstractConfig, AbstractProject, AbstractMetaRule, AbstractCustomArtifact
from ..config import ConfigManager


from .. import __info__
prt = get_printer(__info__.get('logger_name'))


class ProjectBase(AbstractProject):
	'''
	Generally, each workspace (e.g. repo, directory, package) should define its own project,
	which keeps track of all the configs and artifacts defined therein.

	Projects don't just contain all the project specific registries, but can also modify the behavior
	of the top-level methods such as (such as :func:`main()`, :func:`run()`, etc.).

	It is recommended to subclass this class to create a custom project class with expected functionality
	(unlike :class:`AbstractProject`) and automatically register it to the global project type registry.
	'''

	global_type_registry = Class_Registry()
	'''Global registry for project types (usually used by the profile to create custom project types).'''

	def __init_subclass__(cls, name: Optional[str] = None, **kwargs):
		super().__init_subclass__()
		cls._type_name = name
		if name is not None:
			cls.global_type_registry.new(name, cls)

	@classmethod
	def get_project_type(cls, ident: str) -> NamedTuple:
		'''Accesses the project type entry for the given identifier (from a registry).'''
		return cls.global_type_registry.find(ident)



class GeneralProject(ProjectBase, name='general'):
	'''Project class that includes basic functionality such as a script registry and config manager.'''

	_info_file_names = {'.fig.project.yml', '.fig.project.yaml', 'fig.project.yml', 'fig.project.yaml'}

	def infer_path(self, path: Optional[Union[str, Path]] = None) -> Path:
		'''Infers the path of the project from the given path or the current working directory.'''
		if isinstance(path, str):
			path = Path(path)
		if path is None:
			path = Path()
		if path.is_file():
			return path
		if path.is_dir():
			for name in self._info_file_names:
				p = path / name
				if p.exists():
					return p
		# raise FileNotFoundError(f'path does not exist: {path}')
		prt.warning(f'Could not infer project path from {path} (using blank project)')


	@staticmethod
	def _print_artifact_entry(entry):
		'''Prints a single artifact entry (e.g. script) with pretty formatting (including color)'''

		desc = getattr(entry, 'description', None)

		key_fmt = colorize('{key}', color='green')

		item = getattr(entry, 'cls', None)
		if item is None:
			item = getattr(entry, 'fn', None)
		suffix = ''
		if isinstance(item, AbstractCustomArtifact):
			item = item.get_wrapped()
			suffix = ' (auto)'
		bases = getattr(item, '__bases__', None)
		if bases is not None:
			# bases = [f'{b.__module__}.{b.__name__}' for b in item.__bases__]
			bases = [b.__name__ for b in item.__bases__]
			lines = [f'{key_fmt.format(key=entry.name)}: {item.__module__}.{colorize(item.__name__, color="blue")} '
			         f'({", ".join(bases)}){suffix}']

		elif item is not None:
			lines = [f'{key_fmt.format(key=entry.name)}: {item.__module__}.{colorize(item.__name__, color="blue")}'
			         f'{inspect.signature(item)}{suffix}']

		else:
			raise NotImplementedError(entry)

		if desc is not None and len(desc):
			lines.append(desc)

		return '\n\t'.join(lines)


	def xray(self, artifact: str, *, sort: Optional[bool] = False, reverse: Optional[bool] = False,
	         as_dict: Optional[bool] = False) -> Optional[Dict[str, NamedTuple]]:
		'''
		Prints a list of all artifacts registered to the project of the given type.

		Args:
			artifact: artifact type (e.g. 'script', 'config')
			sort: sort the list of artifacts by name
			reverse: reverse the order of the list of artifacts
			as_dict: instead of printing, return the list of artifacts as a dictionary[artifact_name] = artifact_entry

		Returns:
			dict: if as_dict is True, returns a dictionary of the artifact entries

		Raises:
			UnknownArtifactTypeError: if the given artifact type does not exist

		'''
		self.activate()
		registry = self._artifact_registries.get(artifact)
		if registry is None:
			raise self.UnknownArtifactTypeError(artifact)

		keys = list(registry.keys())
		if sort:
			keys = sorted(keys, reverse=reverse)
		elif reverse:
			keys = reversed(keys)

		table = OrderedDict([(k, registry[k]) for k in keys])

		if as_dict:
			return table

		lines = [self._print_artifact_entry(entry) for entry in table.values()]
		print('\n'.join(lines))


	class Script_Registry(Function_Registry, components=['description', 'hidden', 'project']):
		'''Registry for scripts (functions) that can be run from the command line.'''
		pass

	Config_Manager = ConfigManager
	'''Default Config Manager'''

	def __init__(self, path: Optional[Union[str, Path]], *, script_registry: Optional[Script_Registry] = None,
	             config_manager: Optional[Config_Manager] = None, **kwargs):
		if script_registry is None:
			script_registry = self.Script_Registry()
		if config_manager is None:
			config_manager = self.Config_Manager(self)
		path = self.infer_path(path)
		super().__init__(path, **kwargs)
		self._path = None if path is None else path.absolute()
		self.config_manager = config_manager
		self._artifact_registries = {
			'script': script_registry,
		}


	def load_dependencies(self):
		'''
		Loads all dependencies for the project including config files/directories, packages, and source files
		based on the contents of the project's info file.

		Packages are imported (or reloaded) and source files are executed locally.

		Returns:
			Project: self

		'''
		if self.root is not None:
			# config files/directories
			self.load_configs(self.data.get('configs', []))
			if self.data.get('auto_config', True):
				for dname in ['config', 'configs']:
					path = self.root / dname
					if path.is_dir():
						self.load_configs([path])

			# packages
			pkgs = []
			if 'package' in self.data:
				pkgs = [self.data['package']] + pkgs
			if 'packages' in self.data:
				pkgs = self.data['packages'] + pkgs

			# source files
			src = self.data.get('src', [])
			if isinstance(src, str):
				src = [src]
			self._run_dependencies(src, pkgs)

	def _activate(self, *args, **kwargs):
		'''
		Activates the project including the info from the data file
		which includes registering all configs (keys: ``config`` and ``configs``)
		and source files (keys: ``packages``, ``package``, ``src``).
		'''
		super()._activate(*args, **kwargs)
		prt.info(f'Activating project {self.name} ({self.root})')
		with self._profile.project_context(self):
			self.load_dependencies()

	def load_configs(self, paths: Sequence[Union[str ,Path]] = ()) -> None:
		'''Registers all specified config files and directories'''
		for path in paths:
			path = Path(path)
			if path.is_file():
				raise NotImplementedError
			elif path.is_dir():
				self.register_config_dir(path, recursive=True)

	def _run_dependencies(self, srcs: Optional[Sequence[Union[str , Path]]] = (),
	                      packages: Optional[Sequence[str]] = ()) -> None:
		'''Imports all specified packages and runs the specified python files'''

		modules = [*map(Path,srcs), *packages]
		if len(modules):
			include_modules(*modules, root=self.root)

	# region Organization
	def extract_info(self, other: 'GeneralProject') -> None:
		'''Extracts the info from the given project into this project.'''
		super().extract_info(other)
		self._path = other._path
		self._profile = other._profile
		self.config_manager = other.config_manager
		self._artifact_registries = other._artifact_registries

	def validate(self) -> AbstractProject:
		'''Validates the project and returns a new project with the validated info.'''
		requested_type = self.data.get('type', None)
		if requested_type is not None and requested_type != self._type_name:
			prt.info(f'Replacing project type {self._type_name!r} with {requested_type!r}')
			entry = self._profile.get_project_type(requested_type)
			proj = entry.cls(self.info_path, profile=self._profile)
			proj.extract_info(self)
			return proj
		return self

	def __str__(self):
		return f'{self.__class__.__name__}[{self.name}]({self.root})'
	
	def __repr__(self):
		return f'{self.__class__.__name__}[{self.name}]({self.root})'

	def __eq__(self, other):
		if not isinstance(other, GeneralProject):
			return False
		return self.info_path == other.info_path

	def __hash__(self):
		return hash(self.info_path)

	@property
	def name(self):
		'''The name of the project'''
		return self.data.get('name', '')

	@property
	def root(self) -> Path:
		'''The root directory of the project.'''
		if self._path is not None:
			return self._path.parent

	@property
	def info_path(self) -> Path:
		'''The path to the info file.'''
		return self._path
	# endregion

	# region Running/Ops
	def create_config(self, *parents: str, **parameters):
		'''Creates a config with the given parameters using the config manager.'''
		return self.config_manager.create_config(parents, parameters)

	def parse_argv(self, argv, *, script_name=None) -> AbstractConfig:
		'''Parses the given command line arguments into a config object.'''
		return self.config_manager.parse_argv(argv, script_name=script_name)

	def iterate_meta_rules(self) -> Iterator[NamedTuple]:
		'''Iterates over all meta rules in the associated profile.'''
		return self._profile.iterate_meta_rules()

	TerminationFlag = AbstractMetaRule.TerminationFlag
	def _check_meta_rules(self, config: AbstractConfig, meta: AbstractConfig) -> Optional[AbstractConfig]:
		'''
		Applies the meta rules (registered in the profile) in order of priority using the meta config.

		Args:
			config: Config object that will be used to run the script.
			meta: Meta config object for meta rules.

		Returns:
			The potentially modified config object to use for running the script.

		Raises:
			:code:`TerminationFlag` if a meta rule requests termination.

		'''
		for rule in self.iterate_meta_rules():
			try:
				out = rule.fn(config, meta)
			except self.TerminationFlag:
				raise
			except:
				prt.error(f'Error while running meta rule {rule.name!r}')
				raise
			else:
				if out is not None:
					config = out
		return config

	def _run(self, script_entry: Script_Registry.entry_cls, config: AbstractConfig,
	         args: Optional[Tuple] = None, kwargs: Optional[Dict[str, Any]] = None) -> Any:
		'''
		Runs the given script with the given config.

		Args:
			script_entry: The script entry to run.
			config: The config to use for running the script.
			args: Additional positional arguments to pass to the script.
			kwargs: Additional keyword arguments to pass to the script.

		Returns:
			The return value of the script.

		'''
		if args is None:
			args = []
		if kwargs is None:
			kwargs = {}

		fn = script_entry.fn
		if isinstance(fn, AbstractCustomArtifact):
			item = fn.top
		return item(config, *args, **kwargs)

	def run_local(self, config: AbstractConfig, *, script_name: Optional[str] = None,
	              args: Optional[Tuple] = None, kwargs: Optional[Dict[str, Any]] = None,
	              meta: Optional[AbstractConfig] = None) -> Any:
		'''
		Runs the given script with the given config using this project.

		Args:
			config: The config to use for running the script.
			script_name: The script name to run (infer from config if None).
			args: Additional positional arguments to pass to the script.
			kwargs: Additional keyword arguments to pass to the script.
			meta: Meta config object for meta rules.

		Returns:
			The return value of the script.

		'''
		config.project = self
		if meta is not None:
			config.push('_meta', meta, silent=True)
		if script_name is not None:
			config.push('_meta.script_name', script_name, overwrite=True, silent=True)

		meta = config.peek('_meta', {}, silent=True)
		if script_name is None:
			script_name = meta.pull('script_name', silent=True)

		try:
			config = self._check_meta_rules(config, meta)
		except self.TerminationFlag:
			return

		entry = self.find_script(script_name)
		return self._run(entry, config, args, kwargs)
	# endregion

	# region Registration
	class UnknownArtifactTypeError(KeyError):
		'''Raised when an unknown artifact type is encountered.'''
		pass
	def find_artifact(self, artifact_type: str, ident: str,
	                  default: Optional[Any] = unspecified_argument) -> NamedTuple:
		'''
		Finds the artifact of the given type and registered with the given identifier.

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
		self.activate()
		if artifact_type == 'config':
			return self.config_manager.find_config_entry(ident)
		registry = self._artifact_registries.get(artifact_type)
		if registry is None:
			raise self.UnknownArtifactTypeError(artifact_type)
		try:
			return registry.find(ident, default=unspecified_argument)
		except registry.NotFoundError:
			pass
		raise self.UnknownArtifactError(artifact_type, ident)

	def register_artifact(self, artifact_type, ident: str, artifact: Union[str, Type, Callable], *,
	                      project: Optional[AbstractProject] = unspecified_argument, **kwargs) -> NamedTuple:
		'''
		Registers the given artifact with the given type and identifier and any additional info.

		Args:
			artifact_type: The type of artifact to register.
			ident: The identifier of the artifact to register.
			artifact: The artifact to register (usually a type or config file path).
			project: The project to register the artifact for (defaults to this project).
			kwargs: Additional keyword arguments to pass to the registry.

		Returns:
			The artifact entry from the registry corresponding to the given type.

		Raises:
			UnknownArtifactTypeError: If the artifact type does not exist.

		'''
		if project is unspecified_argument:
			project = self
		if artifact_type == 'config':
			return self.config_manager.register_config(ident, artifact, project=project)
		registry = self._artifact_registries.get(artifact_type)
		if registry is None:
			raise self.UnknownArtifactTypeError(artifact_type)
		return registry.new(ident, artifact, project=project, **kwargs)

	def iterate_artifacts(self, artifact_type: str) -> Iterator[NamedTuple]:
		'''
		Iterates over all artifacts of the given type.

		Args:
			artifact_type: The type of artifact to iterate over (e.g. 'script', 'config').

		Returns:
			An iterator over all artifacts of the given type.

		Raises:
			UnknownArtifactTypeError: If the artifact type does not exist.

		'''
		self.activate()
		if artifact_type == 'config':
			yield from self.config_manager.iterate_configs()
		elif artifact_type not in self._artifact_registries:
			raise self.UnknownArtifactTypeError(artifact_type)
		else:
			yield from self._artifact_registries[artifact_type].values()


	def find_config(self, name: str, default: Optional[Any] = unspecified_argument) -> NamedTuple:
		'''
		Finds the config with the given name.

		Args:
			name: name the config was registered with.
			default: default value to return if the config is not found.

		Returns:
			The config entry corresponding to the given name.

		Raises:
			UnknownArtifactError: If the config is not found and no default is given.

		'''
		return self.find_artifact('config', name, default=default)

	def register_config(self, name: Union[str, Path], path: Union[str, Path] = None, **kwargs) -> NamedTuple:
		'''
		Registers a config file with the given name.

		Note:
			It is generally not recommended to register configs manually, but rather to use the ``register_config_dir``
			method to register all configs in a directory at once.

		Args:
			name: to register the config under
			path: of the config file (if not provided, the provided name is assumed to be a path)
			**kwargs: Other arguments to pass to the ``Path_Registry.register`` method

		Returns:
			The entry of the config file that was registered

		'''
		return self.register_artifact('config', name, path, **kwargs)

	def iterate_configs(self) -> Iterator[NamedTuple]:
		'''
		Iterates over all registered config file entries.

		Returns:
			An iterator over all registered config file entries.

		'''
		return self.iterate_artifacts('config')

	def register_config_dir(self, path: Union[str, Path], *, recursive: Optional[bool] = True,
	                        prefix: Optional[str] = None, delimiter: Optional[str] = None) -> List[NamedTuple]:
		'''
		Registers all yaml files found in the given directory (possibly recursively)

		When recusively checking all directories inside, the internal folder hierarchy is preserved
		in the name of the config registered, so for example if the given ``path`` points to a
		directory that contains a directory ``a`` and two files ``f1.yaml`` and ``f2.yaml``:

		Contents of ``path`` and corresponding registered names:

			- ``f1.yaml`` => ``f1``
			- ``f2.yaml`` => ``f2``
			- ``a/f3.yaml`` => ``a/f3``
			- ``a/b/f4.yaml`` => ``a/b/f3``

		If a ``prefix`` is provided, it is appended to the beginning of the registered names

		Args:
			path: path to root directory to search through
			recursive: search recursively through subdirectories for more config yaml files
			prefix: prefix for names of configs found herein
			delimiter: string to merge directories when recursively searching (default ``/``)

		Returns:
			A list of all config entries that were registered.

		'''
		return self.config_manager.register_config_dir(path, recursive=recursive, prefix=prefix, delimiter=delimiter)


	def find_script(self, name: str, default: Optional[Any] = unspecified_argument) -> NamedTuple:
		'''
		Finds the script with the given name.

		Args:
			name: the script was registered with.
			default: default value to return if the script is not found.

		Returns:
			The script entry corresponding to the given name.

		Raises:
			UnknownArtifactError: If the script is not found and no default is given.

		'''
		return self.find_artifact('script', name, default=default)

	def register_script(self, name: str, fn: Callable[[AbstractConfig], Any], *, description: Optional[str] = None,
	                    hidden: Optional[bool] = None) -> NamedTuple:
		'''
		Register a script with the given name.

		Args:
			name: to register the script under
			fn: the script function (should expect the first positional argument to be the config object)
			description: description of the script
			hidden: whether to hide the script from the list of available scripts
			(defaults to whether the name starts with an underscore)

		Returns:
			The entry of the script that was registered

		'''
		return self.register_artifact('script', name, fn, description=description, hidden=hidden)

	def iterate_scripts(self) -> Iterator[NamedTuple]:
		'''
		Iterates over all registered script entries.

		Returns:
			An iterator over all registered script entries.

		'''
		return self.iterate_artifacts('script')
	# endregion
	pass


