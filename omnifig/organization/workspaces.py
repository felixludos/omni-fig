from typing import Optional, Union, Sequence
from pathlib import Path
from omnibelt import unspecified_argument, get_printer, Class_Registry

from ..abstract import AbstractConfig, AbstractProject
from .external import include_package, include_files
from .profiles import Meta_Rule

prt = get_printer(__name__)


class ProjectBase(AbstractProject): # extend this item
	global_type_registry = Class_Registry()

	def __init_subclass__(cls, name: Optional[str] = None, **kwargs):
		super().__init_subclass__()
		cls._type_name = name
		if name is not None:
			cls.global_type_registry.new(name, cls)

	@classmethod
	def get_project_type(cls, ident: str) -> global_type_registry.entry_cls:
		return cls.global_type_registry.find(ident)



class GeneralProject(ProjectBase, name='general'):
	_info_file_names = {
		'omni.fig', 'info.fig', '.omni.fig', '.info.fig',
		'fig.yaml', 'fig.yml', '.fig.yaml', '.fig.yml',
		'fig.info.yaml', 'fig.info.yml', '.fig.info.yaml', '.fig.info.yml',
		'fig_info.yaml', 'fig_info.yml', '.fig_info.yaml', '.fig_info.yml',
		'project.yaml', 'project.yml', '.project.yaml', '.project.yml',
	}

	def infer_path(self, path=None):
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


	class Script_Registry(Class_Registry, components=['description', 'project']): pass
	Config_Manager = None#ConfigManager

	def __init__(self, path, *, script_registry=None, config_manager=None, **kwargs):
		if script_registry is None:
			script_registry = self.Script_Registry()
		if config_manager is None:
			config_manager = self.Config_Manager(self)
		path = self.infer_path(path)
		super().__init__(path, **kwargs)
		self._path = path
		self.config_manager = config_manager
		self._artifact_registries = {
			'script': script_registry,
		}

	def _activate(self, *args, **kwargs):
		super()._activate(*args, **kwargs)
		self.load_configs(self.data.get('configs', []))
		self.load_src(self.data.get('src', []), self.data.get('packages', []))

	def load_configs(self, paths: Sequence[Union[str ,Path]] = ()):
		'''Registers all specified config files and directories'''
		for path in paths:
			path = Path(path)
			if path.is_file():
				raise NotImplementedError
			elif path.is_dir():
				self.register_config_dir(path, recursive=True)

	def load_src(self, srcs: Optional[Sequence[Union[str ,Path]]] = (), packages: Optional[Sequence[str] ] =()):
		'''Imports all specified packages and runs the specified python files'''
		include_package(*packages)
		include_files(*[src for src in srcs], )  # project_name=self.get_name())

	# region Organization
	def extract_info(self, other: 'GeneralProject'):
		super().extract_info(other)
		self._path = other._path
		self._profile = other._profile
		self.config_manager = other.config_manager
		self._artifact_registries = other._artifact_registries  # .copy()

	def validate(self) -> AbstractProject:
		requested_type = self.data.get('type', None)
		if requested_type is not None and requested_type != self._type_name:
			prt.info(f'Replacing project type {self._type_name!r} with {requested_type!r}')
			entry = self._profile.get_project_type(requested_type)
			proj = entry.cls(self.info_path, profile=self._profile)
			proj.extract_info(self)
			return proj
		return self

	@property
	def root(self) -> Path:
		return self._path.parent

	@property
	def info_path(self) -> Path:
		return self._path
	# endregion

	# region Running/Ops
	def create_config(self, *parents, **parameters):
		return self.config_manager.create_config(*parents, **parameters)

	def parse_argv(self, argv, *, script_name=None) -> AbstractConfig:
		return self.config_manager.parse_argv(argv, script_name=script_name)

	TerminationFlag = Meta_Rule.TerminationFlag
	def _check_meta_rules(self, config, meta):
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

	def _run(self, script_entry, config):
		return script_entry.fn(config)

	def run_local(self, config, *, script_name=None, **meta):
		config.set_project(self)
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
		return self._run(entry, config)
	# endregion

	# region Registration
	class UnknownArtifactTypeError(KeyError): pass
	def find_artifact(self, artifact_type, ident, default=unspecified_argument):
		if artifact_type == 'config':
			return self.config_manager.find_config(ident)
		registry = self._artifact_registries.get(artifact_type)
		if registry is None:
			raise self.UnknownArtifactTypeError(artifact_type)
		try:
			return registry.find(ident, default=unspecified_argument)
		except registry.NotFoundError:
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
		if artifact_type not in self._artifact_registries:
			raise self.UnknownArtifactTypeError(artifact_type)
		yield from self._artifact_registries[artifact_type].values()


	def find_config(self, name, default=unspecified_argument):
		return self.find_artifact('config', name, default=default)

	def register_config(self, name, path):
		return self.register_artifact('config', name, path)

	def iterate_configs(self):
		return self.iterate_artifacts('config')

	def register_config_dir(self, path, *, recursive=True, prefix=None, delimiter='/'):
		return self.config_manager.register_config_dir(path, recursive=recursive, project=self,
		                                               prefix=prefix, delimiter=delimiter)


	def find_script(self, name, default=unspecified_argument):
		return self.find_artifact('script', name, default=default)

	def register_script(self, name, fn, *, description=None):
		return self.register_artifact('script', name, fn, description=description)

	def iterate_scripts(self):
		return self.iterate_artifacts('script')
	# endregion
	pass


