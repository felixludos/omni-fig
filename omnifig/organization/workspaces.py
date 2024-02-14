from typing import Optional, Union, Sequence, NamedTuple, Tuple, Any, Dict, List, Type, Iterator, Callable
import sys
from pathlib import Path
from tabulate import tabulate
from collections import OrderedDict
import inspect
from omnibelt import unspecified_argument, Class_Registry, Function_Registry, colorize, include_module

from .. import __logger__ as prt
from ..abstract import AbstractConfig, AbstractProject, AbstractBehavior, AbstractCustomArtifact
from ..config import ConfigManager



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
	def get_project_type(cls, ident: str, default: Optional[Any] = unspecified_argument) -> NamedTuple:
		'''Accesses the project type entry for the given identifier (from a registry).'''
		return cls.global_type_registry.find(ident, default=default)



class GeneralProject(ProjectBase, name='general'):
	'''Project class that includes basic functionality such as a script registry and config manager.'''

	info_file_names = {'.fig.project.yml', '.fig.project.yaml', 'fig.project.yml', 'fig.project.yaml',
	                   '.omnifig.yml', '.omnifig.yaml', 'omnifig.yml', 'omnifig.yaml'}


	def infer_path(self, path: Optional[Union[str, Path]] = None) -> Path:
		'''Infers the path of the project from the given path or the current working directory.'''
		if isinstance(path, str):
			path = Path(path)
		if path is None:
			path = Path()
		if path.is_file():
			return path
		if path.is_dir():
			for name in self.info_file_names:
				p = path / name
				if p.exists():
					return p
		# prt.warning(f'Could not infer project path from {path} (using blank project)')


	def _format_xray_entry(self, entry: NamedTuple) -> Tuple[List[str], Optional[str]]:
		'''Prints a single artifact entry (e.g. script) with pretty formatting (including color)'''

		desc = getattr(entry, 'description', None)

		key_fmt = colorize('{key}', color='green')

		proj = getattr(entry, 'project', None)

		item = getattr(entry, 'cls', None)
		if item is None:
			item = getattr(entry, 'fn', None)
		if isinstance(item, AbstractCustomArtifact):
			item = item.get_wrapped()
		bases = getattr(item, '__bases__', None)

		path = getattr(entry, 'path', None)

		terms = [
			proj.name if proj is not None else '',

		    key_fmt.format(key=entry.name)
		]

		if bases is not None:
			terms.append(colorize(item.__name__, color="blue"))

			terms.append(item.__module__)

			terms.append(f'<{", ".join([b.__name__ for b in item.__bases__])}>')

		elif item is not None:
			terms.append(colorize(item.__name__, color="blue"))

			terms.append(item.__module__)

			terms.append(f'{inspect.signature(item)}')

		elif path is not None: # config

			root = getattr(proj, 'root', None)

			if root is not None:
				try:
					extra = str(path.relative_to(root))
				except:
					extra = str(path)
				terms.append(extra)

			else:
				terms.append('')

		else:
			raise NotImplementedError(f'Unknown entry type: {entry}')

		return terms, desc


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
		terms = list(self.iterate_artifacts(artifact))

		if sort:
			terms.sort(key=lambda x: x.name)
		if reverse:
			terms.reverse()

		if as_list:
			return terms

		if len(terms):
			rows, descs = zip(*[self._format_xray_entry(t) for t in terms])
			descs = [None if d is None else f'\t[{d}]' for d in descs]

			table = tabulate(rows, tablefmt='simple')

			lines = [line for lines in zip(table.splitlines()[1:-1], descs) for line in lines if line is not None]
			print('\n'.join(lines))


	class Script_Registry(Function_Registry, components=['description', 'hidden', 'project']):
		'''Registry for scripts (functions) that can be run from the command line.'''
		pass


	Config_Manager = ConfigManager


	def __init__(self, path: Optional[Union[str, Path]], *, script_registry: Optional[Script_Registry] = None,
	             config_manager: Optional[Config_Manager] = None, **kwargs):
		if script_registry is None:
			script_registry = self.Script_Registry()
		if config_manager is None:
			config_manager = self.Config_Manager(self)
		path = self.infer_path(path)
		super().__init__(path, **kwargs)
		self._behaviors = None
		self._path = None if path is None else path.absolute()
		self._modules = OrderedDict()
		self.config_manager = config_manager
		self._artifact_registries = {
			'script': script_registry,
		}


	def load(self):
		'''
		Loads all dependencies for the project including config files/directories, packages, and source files
		based on the contents of the project's info file.

		Packages are imported (or reloaded) and source files are executed locally.

		Returns:
			Project: self

		'''
		if self.root is not None:
			# load any dependencies
			dep_dir = self.data.get('auto_dependency_dir', 'dependency')
			if dep_dir is not None:
				deps = self.data.get(dep_dir, [])
				if isinstance(deps, str):
					deps = [deps]
				for dep in deps:
					self._profile.get_project(dep).load()

			# config files/directories
			self.load_configs(self.data.get('configs', []))
			config_dir = self.data.get('auto_config_dir', 'config')
			if config_dir is not None:
				path = self.root / config_dir
				if path.is_dir():
					self.load_configs([path])

			# import modules
			module_dir = self.data.get('auto_module_dir', 'module')
			modules = []
			if module_dir is not None:
				modules = self.data.get(module_dir, [])
				if isinstance(modules, str):
					modules = [modules]

			# run source files
			src_dir = self.data.get('auto_src_dir', 'src')
			src = []
			if src_dir is not None:
				src = self.data.get(src_dir, [])
				if isinstance(src, str):
					src = [src]

			self._run_dependencies(src, modules)


	def unload(self):
		'''Unloads all dependencies for the project (opposite of :meth:`load`).'''
		for module, (mod, deps) in self._modules.items():
			for name, dep in deps.items():
				if name in sys.modules:
					del sys.modules[name]


	def _activate(self, *args, **kwargs):
		'''
		Activates the project including the info from the data file
		which includes registering all configs (keys: ``config`` and ``configs``)
		and source files (keys: ``packages``, ``package``, ``src``).
		'''
		super()._activate(*args, **kwargs)
		prt.info(f'Activating project {self.name} ({self.root})')
		with self._profile.project_context(self):
			self.load()


	def _deactivate(self, *args, **kwargs):
		'''Deactivates the project including unloading all dependencies.'''
		super()._deactivate(*args, **kwargs)
		prt.info(f'Deactivating project {self.name} ({self.root})')
		self.unload()

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
		for module in modules:
			# if module in self._modules:
			# 	mod, dependencies = self._modules[module]
			# 	sys.modules.update(dependencies)
			# else:
			mod, dependencies = include_module(module, root=self.root)

			root = str(Path(mod.__file__).parent.resolve())

			sub = {name: dep for name, dep in dependencies.items()
				   if str(Path(dep.__file__).resolve()).startswith(root)}
			self._modules[module] = mod, sub

		for owner, submodules in self._modules.values():
			for name, sub in submodules.items():
				del sys.modules[name] # remove any local modules from sys.modules

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


	def __repr__(self):
		name = self.name
		return f'{self.__class__.__name__}[{"default" if name is None else name}]({self.root})'


	def __eq__(self, other):
		if not isinstance(other, GeneralProject):
			return False
		return self.info_path == other.info_path


	def __hash__(self):
		return hash(self.info_path)


	@property
	def name(self):
		'''The name of the project'''
		return self.data.get('name', None)
	@name.setter
	def name(self, value: str):
		self.data['name'] = value


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


	def parse_argv(self, argv: Sequence[str], *, script_name: Optional[str] = unspecified_argument) -> AbstractConfig:
		'''Parses the given command line arguments into a config object.'''
		return self.config_manager.parse_argv(argv, script_name=script_name)


	def behaviors(self) -> Iterator[AbstractBehavior]:
		'''Iterates over all behaviors associated with this project.'''
		# return self._profile.iterate_behaviors()
		if self._behaviors is None:
			self._behaviors = [entry.cls(self) for entry in self._profile.iterate_behaviors()]
		yield from sorted(self._behaviors, reverse=True)


	def validate_run(self, config: AbstractConfig) -> Optional[AbstractProject]:
		'''
		Validates the project ``self`` using the given config object before running it.

		More specifically, this method calls :meth:`validate_project` on all behaviors associated with the project
		with the config object as argument. If any of the behaviors returns a new project, this project
		is returned (and used for the script execution instead). Otherwise, ``None`` is returned.

		Args:
			config: The config object to use for validation.

		Returns:
			The new project to use for the script execution or ``None`` if no new project was returned.

		'''
		for behavior in self.behaviors():
			out = behavior.validate_project(config)
			if out is not None:
				return out


	def main(self, argv: Sequence[str], script_name: Optional[str] = unspecified_argument) -> Any:
		'''
		Runs the script with the given arguments using the config object obtained by parsing ``argv``.

		More specifically, this method does the following:
			1. Activates the project (loads any specified source files or packages for the script, if not done yet).
			2. Instantiates all behaviors associated with the project.
			3. Parses the command line arguments into a config object.
			4. Validates the current project using the config object and behaviors (see :meth:`validate_run`).
			5. Runs the script using the config object (see :meth:`run_script`).
			6. Cleans up the project (see :meth:`cleanup`).

		Args:
			argv: List of top-level arguments (expected to be :code:`sys.argv[1:]`).
			script_name: specified name of the script
			(defaults to what is specified in argv when it is parsed into a config object).

		Returns:
			The output of the script.

		'''
		self.activate()  # load the project

		self._behaviors = None  # clear the behaviors cache
		behaviors = [behavior for behavior in self.behaviors()]  # instantiate all behaviors

		config = self.parse_argv(argv, script_name=script_name)

		transfer = self.validate_run(config)  # can update/modify the project based on the config
		if transfer is not None:
			return transfer.main(argv, script_name=script_name)

		output = self.run_script(script_name, config)  # run based on the config
		self.cleanup()  # cleanup
		return output  # return output


	def run_script(self, script_name: str, config: AbstractConfig, *args: Any, **kwargs: Any) -> Any:
		'''
		Runs the script with the given arguments using :func:`run()` of the current project.

		Args:
			script_name: The script name to run (must be registered).
			config: Config object to run the script with (must include the script under :code:`_meta.script_name`).
			args: Additional positional arguments to pass to the script.
			kwargs: Additional keyword arguments to pass to the script.

		Returns:
			The output of the script.

		'''
		if script_name not in {None, unspecified_argument}:
			config.push('_meta.script_name', script_name, overwrite=True, silent=True) # TODO: handle readonly configs
		return self.run(config, *args, **kwargs)


	class NoScriptError(ValueError):
		'''Raised when the script name is not specified.'''
		pass

	def run(self, config: AbstractConfig, *args: Any, **kwargs: Any) -> Any:
		'''
		Runs the given script with the given config using this project.

		Args:
			config: The config to use for running the script (must include the script under :code:`_meta.script_name`).
			args: Additional positional arguments to pass to the script.
			kwargs: Additional keyword arguments to pass to the script.

		Returns:
			The return value of the script.

		'''
		config.project = self
		meta = config.push_peek('_meta', {}, overwrite=False, silent=True) # TODO: handle readonly configs

		behaviors = [behavior for behavior in self.behaviors() if behavior.include(meta)]

		# pre run
		for behavior in behaviors:
			try:
				out = behavior.pre_run(meta, config)
			except self.TerminationFlag as e:
				return e.out
			except:
				prt.error(f'Error while running behavior {behavior!r} pre run')
				raise
			else:
				if out is not None:
					config = out

		script_name = meta.pull('script_name', None, silent=True)
		if script_name is None:
			raise self.NoScriptError
		entry = self.find_script(script_name)
		try:
			output = self._run(entry, config, args=args, kwargs=kwargs) # run script
		except Exception as exc:
			try:
				for behavior in behaviors:
					behavior.handle_exception(meta, config, exc)
			except self.TerminationFlag as e:
				return e.out
			except self.IgnoreException as e:
				output = e.out
			else:
				raise exc

		# post run
		for behavior in behaviors:
			try:
				out = behavior.post_run(meta, config, output)
			except self.TerminationFlag as e:
				return e.out
			except:
				prt.error(f'Error while running behavior {behavior!r} post run')
				raise
			else:
				if out is not None:
					output = out

		return output


	TerminationFlag = AbstractBehavior.TerminationFlag
	IgnoreException = AbstractBehavior.IgnoreException


	def _run(self, script_entry: Script_Registry.entry_cls, config: AbstractConfig, *,
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
			args = ()
		if kwargs is None:
			kwargs = {}

		fn = script_entry.fn
		if isinstance(fn, AbstractCustomArtifact):
			fn = fn.top
		return fn(config, *args, **kwargs)
	# endregion


	# region Registration
	class UnknownArtifactTypeError(KeyError):
		'''Raised when an unknown artifact type is encountered.'''
		pass


	def find_local_artifact(self, artifact_type: str, ident: str,
	                        default: Optional[Any] = unspecified_argument) -> Optional[NamedTuple]:
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
			try:
				return self.config_manager.find_local_config_entry(ident, default=default)
			except self.config_manager.ConfigNotRegistered:
				pass
		else:
			registry = self._artifact_registries.get(artifact_type)
			if registry is None:
				raise self.UnknownArtifactTypeError(artifact_type)
			try:
				return registry.find(ident, default=unspecified_argument)
			except registry.NotFoundError:
				pass
		if default is not unspecified_argument:
			return default
		raise self.UnknownArtifactError(artifact_type, ident)


	def find_artifact(self, artifact_type: str, ident: str,
	                  default: Optional[Any] = unspecified_argument) -> NamedTuple:
		'''
		Finds an artifact in the project's registries, including related and active base projects.
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
		return self.find_local_artifact(artifact_type, ident, default=default)


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
		if project is unspecified_argument or project is None:
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
		yield from self.iterate_artifacts('config')


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
		yield from self.iterate_artifacts('script')
	# endregion
	pass


