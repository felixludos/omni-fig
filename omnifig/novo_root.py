from typing import List, Dict, Tuple, Optional, Union, Any, Hashable, Sequence, Callable, Generator, Type, Iterable, \
	Iterator
import sys, os
from pathlib import Path
from collections import OrderedDict
from omnibelt import get_printer, load_yaml, agnosticmethod, Class_Registry, Function_Registry, Path_Registry
from omnibelt import unspecified_argument

from .mixins import FileInfo
from .abstract import AbstractRunMode, Config
from .config import ConfigManager
from .external import include_package, include_files

prt = get_printer(__name__)


class ProjectBase(AbstractRunMode, FileInfo): # project that should be extended
	global_type_registry = Class_Registry()
	def __init_subclass__(cls, name=None, **kwargs):
		super().__init_subclass__()
		cls._type_name = name
		if name is not None:
			cls.global_type_registry.new(name, cls)

	def __init__(self, path=None, profile=None, **kwargs):
		super().__init__(path, **kwargs)
		self._profile = profile


	@classmethod
	def get_project_type(cls, ident):
		return cls.global_type_registry.find(ident)


	class UnknownArtifactError(KeyError):
		def __init__(self, artifact_type, ident):
			super().__init__(f'{artifact_type} {ident!r} not found')
			self.artifact_type = artifact_type
			self.ident = ident
	def find_artifact(self, artifact_type, ident, default=unspecified_argument):
		raise self.UnknownArtifactError(artifact_type, ident)

	def register_artifact(self, artifact_type, ident, artifact, **kwargs):
		raise NotImplementedError

	def iterate_artifacts(self, artifact_type):
		raise NotImplementedError


	def create_config(self, *parents, **parameters):
		raise NotImplementedError

	def quick_run(self, script_name, *parents, **parameters):
		config = self.create_config(*parents, **parameters)
		return self.run(config, script_name=script_name)




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
	Config_Manager = ConfigManager

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

	def load_configs(self, paths: Sequence[Union[str,Path]] = ()):
		'''Registers all specified config files and directories'''
		for path in paths:
			path = Path(path)
			if path.is_file():
				raise NotImplementedError
			elif path.is_dir():
				self.register_config_dir(path, recursive=True)

	def load_src(self, srcs: Optional[Sequence[Union[str,Path]]] = (), packages: Optional[Sequence[str]]=()):
		'''Imports all specified packages and runs the specified python files'''
		include_package(*packages)
		include_files(*[src for src in srcs], )  # project_name=self.get_name())

	# region Organization
	def extract_info(self, other: 'GeneralProject'):
		super().extract_info(other)
		self._path = other._path
		self._profile = other._profile
		self.config_manager = other.config_manager
		self._artifact_registries = other._artifact_registries#.copy()

	def validate(self) -> ProjectBase:
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

	def parse_argv(self, argv, *, script_name=None) -> Config:
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
		if script_name is None:
			script_name = config.pull('script_name', silent=True)

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


class Profile(ProfileBase):
	class Project(GeneralProject, name='default'):
		class Creator_Registry(Function_Registry, components=['project']): pass
		class Component_Registry(Class_Registry, components=['project']): pass
		class Modifier_Registry(Class_Registry, components=['project']): pass

		def __init__(self, path, *, creator_registry=None, component_registry=None, modifier_registry=None,
		             **kwargs):
			if creator_registry is None:
				creator_registry = self.Creator_Registry()
			if component_registry is None:
				component_registry = self.Component_Registry()
			if modifier_registry is None:
				modifier_registry = self.Modifier_Registry()
			super().__init__(path, **kwargs)
			self._artifact_registries.update({
				'creator': creator_registry,
				'component': component_registry,
				'modifier': modifier_registry,
			})

		def _activate(self, *args, **kwargs):
			raise NotImplementedError

		def validate_main(self, config: Config) -> 'ProjectBase':
			runner = config.pull('_meta.main_runner', None, silent=True)
			if runner is not None:
				return runner

		def validate_run(self, config: Config) -> 'ProjectBase':
			runner = config.pull('_meta.runner', None, silent=True)
			if runner is not None:
				return runner

		def run_local(self, config, *, script_name=None, **meta): # derives meta from config under "_meta"
			config.set_project(self)

			if script_name is not None:
				config.push('_meta.script_name', script_name, overwrite=True, silent=True)
			for k, v in meta.items():
				config.push(f'_meta.{k}', v, overwrite=True, silent=True)

			meta = config.pull('_meta', {}, silent=True)
			try:
				config = self._check_meta_rules(config, meta)
			except self.TerminationFlag:
				return

			entry = self.find_artifact('script', config.pull('_meta.script_name', silent=True))
			return self._run(entry, config)
		
		# region Registration
		def find_creator(self, name, default=unspecified_argument):
			return self.find_artifact('creator', name, default=default)
		
		def register_creator(self, name, fn, *, description=None):
			return self.register_artifact('creator', name, fn, description=description)
		
		def iterate_creators(self):
			return self.iterate_artifacts('creator')


		def find_component(self, name, default=unspecified_argument):
			return self.find_artifact('component', name, default=default)
		
		def register_component(self, name, cls, *, creator=None):
			return self.register_artifact('component', name, cls, creator=creator)
		
		def iterate_components(self):
			return self.iterate_artifacts('component')
		
		
		def find_modifier(self, name, default=unspecified_argument):
			return self.find_artifact('modifier', name, default=default)
		
		def register_modifier(self, name, cls, *, description=None):
			return self.register_artifact('modifier', name, cls, description=description)
		
		def iterate_modifiers(self):
			return self.iterate_artifacts('modifier')
		# endregion
		
		def find_artifact(self, artifact_type, ident, default=unspecified_argument):
			try:
				return super().find_artifact(artifact_type, ident)
			except self.UnknownArtifactError:
				for proj in self._profile.iterate_projects():
					try:
						return proj.find_artifact(artifact_type, ident)
					except proj.ArtifactNotFoundError:
						pass
				if default is unspecified_argument:
					raise
				return default


	_profile_env_variable = 'FIG_PROFILE'
	def __init__(self, data: Dict = None):
		if data is None:
			data = os.environ.get(self._profile_env_variable, None)
		super().__init__(data)


	def _activate(self) -> None:
		active_projects = self.data.get('active_projects', [])
		for project in active_projects:
			self.get_project(project)


	def get_project(self, ident: Union[str, Path] = None) -> Project:
		if ident is None:
			if self._current_project_key is not None:
				return self.get_current_project()

		if ident in self._loaded_projects:
			return self._loaded_projects[ident]

		if isinstance(ident, ProjectBase):
			proj = ident
			ident = proj.name
		else:
			# create new
			path = ident
			if ident in self.data.get('projects', {}):
				path = self.data['projects'][ident]

			proj = self.Project(path)
			proj = proj.validate()
			if proj.name in self._loaded_projects:
				prt.warning('project name already loaded: %s (will now overwrite)', proj.name)

		assert proj.name == ident, 'project name does not match profiles name for it: %s != %s' % (proj.name, ident)
		# self._loaded_projects[ident] = proj.name
		self._loaded_projects[proj.name] = proj
		if self._current_project_key is None:
			self._current_project_key = ident
		return proj


	def create_config(self, *parents: str, **parameters: Any) -> Config:
		return self.get_current_project().create_config(*parents, **parameters)


	# region Registration
	def find_config(self, name: str, default: Optional[Any] = unspecified_argument) \
			-> 'GeneralProject.Config_Manager.Config_Registry.entry_cls':
		return self.get_current_project().find_config(name, default=default)

	def register_config(self, name, path):
		return self.get_current_project().register_config(name, path)

	def iterate_configs(self):
		return self.get_current_project().iterate_configs()

	def register_config_dir(self, name, path, *, recursive=True, prefix=None, delimiter='/'):
		return self.get_current_project().register_config_dir(name, path, recursive=recursive,
		                                                      prefix=prefix, delimiter=delimiter)

	def find_script(self, name, default=unspecified_argument):
		return self.get_current_project().find_script(name, default=default)

	def register_script(self, name, fn, *, description=None):
		return self.get_current_project().register_script(name, fn, description=description)

	def iterate_scripts(self):
		return self.get_current_project().iterate_scripts()


	def find_creator(self, name, default=unspecified_argument):
		return self.get_current_project().find_creator(name, default=default)

	def register_creator(self, name, fn, *, description=None):
		return self.get_current_project().register_creator(name, fn, description=description)

	def iterate_creators(self):
		return self.get_current_project().iterate_creators()

	def find_component(self, name, default=unspecified_argument):
		return self.get_current_project().find_component(name, default=default)

	def register_component(self, name, cls, *, description=None):
		return self.get_current_project().register_component(name, cls, description=description)

	def iterate_components(self):
		return self.get_current_project().iterate_components()

	def find_modifier(self, name, default=unspecified_argument):
		return self.get_current_project().find_modifier(name, default=default)

	def register_modifier(self, name, cls, *, description=None):
		return self.get_current_project().register_modifier(name, cls, description=description)

	def iterate_modifiers(self):
		return self.get_current_project().iterate_modifiers()
	# endregion

	pass



def get_profile():
	return ProfileBase.get_profile()















