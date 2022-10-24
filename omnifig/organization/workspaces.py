from typing import Optional, Union, Sequence, NamedTuple, Tuple, Any, Dict, List
from pathlib import Path
import inspect
from collections import OrderedDict
from omnibelt import unspecified_argument, get_printer, Class_Registry, Function_Registry, colorize

from ..abstract import AbstractConfig, AbstractProject, AbstractMetaRule, AbstractCustomArtifact
from .external import include_package, include_files
from ..config import ConfigManager
# from .profiles import Meta_Rule

prt = get_printer(__name__)


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

	_info_file_names = {
		'omni.fig', 'info.fig', '.omni.fig', '.info.fig',
		'fig.yaml', 'fig.yml', '.fig.yaml', '.fig.yml',
		'fig.info.yaml', 'fig.info.yml', '.fig.info.yaml', '.fig.info.yml',
		'fig_info.yaml', 'fig_info.yml', '.fig_info.yaml', '.fig_info.yml',
		'project.yaml', 'project.yml', '.project.yaml', '.project.yml',
	}

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


	def xray(self, artifact, sort=False, reverse=False, as_dict=False):
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

	def _activate(self, *args, **kwargs):
		'''
		Activates the project including the info from the data file
		which includes registering all configs (keys: ``config`` and ``configs``)
		and source files (keys: ``packages``, ``package``, ``src``).
		'''
		super()._activate(*args, **kwargs)
		print(f'Activating project {self.name} ({self.root})')
		if self.root is not None:
			self.load_configs(self.data.get('configs', []))
			if self.data.get('auto_config', True):
				for dname in ['config', 'configs']:
					path = self.root / dname
					if path.is_dir():
						self.load_configs([path])
						
			pkgs = self.data.get('modules', [])
			if 'module' in self.data:
				pkgs = [self.data['module']] + pkgs
			if 'package' in self.data:
				pkgs = [self.data['package']] + pkgs
			if 'packages' in self.data:
				pkgs = self.data['packages'] + pkgs
			self.load_src(self.data.get('src', []), pkgs)

	def load_configs(self, paths: Sequence[Union[str ,Path]] = ()) -> None:
		'''Registers all specified config files and directories'''
		for path in paths:
			path = Path(path)
			if path.is_file():
				raise NotImplementedError
			elif path.is_dir():
				self.register_config_dir(path, recursive=True)

	def load_src(self, srcs: Optional[Sequence[Union[str ,Path]]] = (),
	             packages: Optional[Sequence[str]] = ()) -> None:
		'''Imports all specified packages and runs the specified python files'''
		src_files = []
		for src in srcs:
			path = Path(src) if self.root is None else self.root / src
			if path.is_file():
				src_files.append(str(path))
		include_package(*packages)
		include_files(*src_files)

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

	@property
	def name(self):
		if self.root is not None:
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

	TerminationFlag = AbstractMetaRule.TerminationFlag
	def _check_meta_rules(self, config: AbstractConfig, meta: AbstractConfig) -> Optional[AbstractConfig]:
		'''
		Applies the meta rules (registered in the profile) in order of priority using the meta config.

		Args:
			config: Config object that will be used to run the script.
			meta: Meta config object for meta rules.

		Returns:
			The potentially modified config object to use for running the script.

		'''
		for rule in self._profile.iterate_meta_rules():
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
		'''Runs the given script with the given config.'''
		if args is None:
			args = []
		if kwargs is None:
			kwargs = {}

		fn = script_entry.fn
		if isinstance(fn, AbstractCustomArtifact):
			item = fn.top
		return item(config, *args, **kwargs)

	def run_local(self, config, *, script_name=None, args=None, kwargs=None, meta=None):
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
	class UnknownArtifactTypeError(KeyError): pass
	def find_artifact(self, artifact_type, ident, default=unspecified_argument):
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

	def register_artifact(self, artifact_type, ident, artifact, project=None, **kwargs):
		if project is None:
			project = self
		if artifact_type == 'config':
			return self.config_manager.register_config(ident, artifact, project=project)
		registry = self._artifact_registries.get(artifact_type)
		if registry is None:
			raise self.UnknownArtifactTypeError(artifact_type)
		return registry.new(ident, artifact, project=project, **kwargs)

	def iterate_artifacts(self, artifact_type):
		if artifact_type == 'config':
			yield from self.config_manager.iterate_configs()
			return
		if artifact_type not in self._artifact_registries:
			raise self.UnknownArtifactTypeError(artifact_type)
		yield from self._artifact_registries[artifact_type].values()


	def find_config(self, name, default=unspecified_argument):
		return self.find_artifact('config', name, default=default)

	def register_config(self, name, path):
		return self.register_artifact('config', name, path)

	def iterate_configs(self):
		return self.iterate_artifacts('config')

	def register_config_dir(self, path, *, recursive=True, prefix=None, delimiter=None):
		return self.config_manager.register_config_dir(path, recursive=recursive, prefix=prefix, delimiter=delimiter)


	def find_script(self, name, default=unspecified_argument):
		return self.find_artifact('script', name, default=default)

	def register_script(self, name, fn, *, description=None, hidden=None):
		return self.register_artifact('script', name, fn, description=description, hidden=hidden)

	def iterate_scripts(self):
		return self.iterate_artifacts('script')
	# endregion
	pass


