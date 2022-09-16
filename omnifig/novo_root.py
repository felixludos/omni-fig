from typing import List, Dict, Tuple, Optional, Union, Any, Hashable, Sequence, Callable, Generator, Type, Iterable, \
	Iterator
import sys, os
from pathlib import Path
from collections import OrderedDict
from omnibelt import get_printer, load_yaml, agnosticmethod, Class_Registry, Function_Registry, Path_Registry
from omnibelt import unspecified_argument

from .config import ConfigManager, Config


prt = get_printer(__name__)


class Activatable:
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._is_activated = False

	@property
	def is_activated(self):
		return self._is_activated

	def activate(self, *args, **kwargs):
		if self._is_activated:
			return
		self._activate(*args, **kwargs)
		self._is_activated = True

	def _activate(self, *args, **kwargs):
		pass

	def deactivate(self, *args, **kwargs):
		if not self._is_activated:
			return
		self._deactivate(*args, **kwargs)
		self._is_activated = False

	def _deactivate(self, *args, **kwargs):
		pass



class FileInfo(Activatable):
	@staticmethod
	def load_raw_info(path: Path):
		'''Loads the info yaml file'''
		raw = load_yaml(path, ordered=True) if path.exists() else None
		if raw is None:
			raw = {}
		raw['info_path'] = str(path) # automatically set info_path to the path
		raw['info_dir'] = str(path.parent)
		return raw

	def __init__(self, data=None, **kwargs):
		super().__init__(**kwargs)
		if isinstance(data, str):
			data = Path(data)
		if isinstance(data, Path):
			data = self.load_raw_info(data)
		if data is None:
			data = OrderedDict()
		self.data = data

	@property
	def name(self):
		return self.data.get('name', '-no-name-')

	def __repr__(self):
		return f'{self.__class__.__name__}({self.name})'

	def __str__(self):
		return f'{self.__class__.__name__}[{self.name}]({", ".join(self.data.keys())})'

	def extract_info(self, other: 'FileInfo'):
		self.data = other.data



class AbstractProject:
	def main(self, argv, script_name=None):
		raise NotImplementedError

	def run(self, script_name, config, **meta):
		raise NotImplementedError

	def quick_run(self, script_name, *parents, **args):
		raise NotImplementedError

	def cleanup(self, *args, **kwargs):
		raise NotImplementedError

	def get_config(self, *parents, **parameters):
		raise NotImplementedError

	def create_component(self, config):
		raise NotImplementedError


class AbstractRunMode(Activatable):
	def main(self, argv, *, script_name=None):
		config = self.parse_argv(argv, script_name=script_name)
		transfer = self.validate_main(config) # can update/modify the project based on the config
		if transfer is not None:
			return transfer.main(argv, script_name=script_name)
		self.activate() # load the project
		out = self.run(config, script_name=script_name) # run based on the config
		self.cleanup() # (optional) cleanup
		return out # return output

	def run(self, config, *, script_name=None):
		transfer = self.validate_run(config)
		if transfer is not None:
			return transfer.run(config, script_name=script_name)
		return self.run_local(config, script_name=script_name)

	def cleanup(self, *args, **kwargs):
		pass

	def validate_main(self, config) -> Optional['Run_Mode']:
		pass

	def validate_run(self, config) -> Optional['Run_Mode']:
		pass

	def parse_argv(self, argv, *, script_name=None) -> Config:
		raise NotImplementedError

	def run_local(self, config, *, script_name=None) -> Any:
		raise NotImplementedError



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



class MetaRule_Registry(Function_Registry, components=['priority', 'num_args']):
	pass



class ProfileBase(FileInfo): # profile that should be extended
	meta_rule_registry = MetaRule_Registry()
	_profile = None
	def __init_subclass__(cls, **kwargs):
		super().__init_subclass__(**kwargs)
		cls._profile = None

	# region Class Methods

	Project = ProjectBase
	@classmethod
	def get_project_type(cls, ident):
		return cls.Project.get_project_type(ident)

	@classmethod
	def replace_profile(cls, profile=None):
		if profile is None:
			profile = cls()
		Profile._profile = profile
		cls._profile = profile

	@classmethod
	def get_profile(cls):
		if cls._profile is None:
			cls._profile = cls()
			cls._profile.activate()
		return cls._profile

	@classmethod
	def register_meta_rule(cls, name, func, priority=0, num_args=0):
		cls.meta_rule_registry.new(name, func, priority=priority, num_args=num_args)

	@classmethod
	def get_meta_rule(cls, name):
		return cls.meta_rule_registry.find(name)

	@classmethod
	def iterate_meta_rules(cls):
		entries = list(cls.meta_rule_registry.values())
		for entry in sorted(entries, key=lambda e: (e.priority, e.name)):
			yield entry

	@classmethod
	def iterate_meta_rule_fns(cls):
		for entry in cls.iterate_meta_rules():
			yield entry.fn

	# endregion


	def __init__(self, data=None):
		super().__init__(data)
		self._loaded_projects = OrderedDict()
		self._current_project_key = None

	# region Top Level Methods

	def entry(self, script_name=None):
		argv = sys.argv[1:]
		self.main(argv, script_name=script_name)

	def main(self, argv, *, script_name=None):
		return self.get_current_project().main(argv, script_name=script_name)

	def run(self, config, *, script_name=None, **meta):
		return self.get_current_project().run(config, script_name=script_name, **meta)

	def quick_run(self, script_name, *parents, **args):
		return self.get_current_project().quick_run(script_name, *parents, **args)

	def cleanup(self, *args, **kwargs):
		return self.get_current_project().cleanup(*args, **kwargs)

	def find_artifact(self, artifact_type, ident, **kwargs):
		return self.get_current_project().find_artifact(artifact_type, ident, **kwargs)

	def register_artifact(self, artifact_type, ident, artifact, **kwargs):
		return self.get_current_project().register_artifact(artifact_type, ident, artifact, **kwargs)

	def iterate_artifacts(self, artifact_type):
		return self.get_current_project().iterate_artifacts(artifact_type)

	# endregion

	def __str__(self):
		return f'{self.__class__.__name__}[{self.name}]({", ".join(self._loaded_projects)})'

	def extract_info(self, other: 'ProfileBase'):
		super().extract_info(other)
		self._loaded_projects = other._loaded_projects#.copy()
		self._current_project_key = other._current_project_key

	def get_current_project(self) -> ProjectBase:
		return self.get_project(self._current_project_key)

	def switch_project(self, ident=None):
		proj = self.get_project(ident)
		self._current_project_key = proj.name
		return proj

	def iterate_projects(self):
		yield from self._loaded_projects.values()

	def get_project(self, ident=None):
		raise NotImplementedError

Meta_Rule = ProfileBase.meta_rule_registry.get_decorator(detaults={'priority': 0, 'num_args': 0})


class TerminationFlag(KeyboardInterrupt):
	pass


class GeneralProject(ProjectBase, name='simple'):
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
		prt.warning(f'Could not infer project path from {path} (using blank project)')
		# raise FileNotFoundError(f'path does not exist: {path}')


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

	def create_config(self, *parents, **parameters):
		return self.config_manager.create_config(*parents, **parameters)

	def parse_argv(self, argv, *, script_name=None) -> Config:
		return self.config_manager.parse_argv(argv, script_name=script_name)

	TerminationFlag = TerminationFlag
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
		return registry.new(ident, artifact, **kwargs)

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

	def register_config_dir(self, name, path, *, recursive=True, prefix=None, delimiter='/'):
		return self.config_manager.register_config_dir(name, path, recursive=recursive, project=self,
		                                               prefix=prefix, delimiter=delimiter)


	def find_script(self, name, default=unspecified_argument):
		return self.find_artifact('script', name, default=default)

	def register_script(self, name, fn, *, description=None):
		return self.register_artifact('script', name, fn, description=description)

	def iterate_scripts(self):
		return self.iterate_artifacts('script')



class Profile(ProfileBase):
	class Project(GeneralProject, name='default'):

		Creator_Registry = Function_Registry
		Component_Registry = Class_Registry
		Modifier_Registry = Class_Registry

		def __init__(self, path, *, creator_registry=None, component_registry=None, modifier_registry=None, **kwargs):
			if creator_registry is None:
				creator_registry = self.Creator_Registry()
			if component_registry is None:
				component_registry = self.Component_Registry()
			if modifier_registry is None:
				modifier_registry = self.Modifier_Registry()
			super().__init__(path, **kwargs)
			self._artifact_registries = {
				'creator': creator_registry,
				'component': component_registry,
				'modifier': modifier_registry,
			}


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
	def __init__(self, data=None):
		if data is None:
			data = os.environ.get(self._profile_env_variable, None)
		super().__init__(data)


	def _activate(self):
		active_projects = self.data.get('active_projects', [])
		for project in active_projects:
			self.get_project(project)


	def get_project(self, ident=None):
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


	def create_config(self, *parents, **parameters):
		return self.get_current_project().create_config(*parents, **parameters)

	def create_component(self, config):
		return self.get_current_project().create_component(config)


	# def register_rule(self, name, rule):
	# 	return self.get_current_project().register_rule(name, rule)
	#
	# def register_script(self, name, fn, description=None, **kwargs):
	# 	return self.get_current_project().register_script(name, fn, description=description, **kwargs)
	#
	# def register_component(self, name, fn, **kwargs):
	# 	return self.get_current_project().register_component(name, fn, **kwargs)
	#
	# def register_modifier(self, name, fn, **kwargs):
	# 	return self.get_current_project().register_modifier(name, fn, **kwargs)
	#
	# def register_config(self, name, path, **kwargs):
	# 	return self.get_current_project().register_config(name, path, **kwargs)
	#
	# def register_config_dir(self, path, recursive=True, prefix=None, delimiter='/', **kwargs):
	# 	return self.get_current_project().register_config_dir(path, recursive=recursive, prefix=prefix,
	# 	                                                      delimiter=delimiter, **kwargs)

























