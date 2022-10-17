
from typing import Dict, Optional, Union, Any
import os
from pathlib import Path
from omnibelt import unspecified_argument, get_printer, Class_Registry, Function_Registry, JSONABLE

from ..abstract import AbstractConfig

from .profiles import ProfileBase
from .workspaces import ProjectBase, GeneralProject

prt = get_printer(__name__)



class Profile(ProfileBase, default_profile=True):
	class Project(GeneralProject, name='default'):
		class Creator_Registry(Class_Registry, components=['project', 'description']): pass
		class Component_Registry(Class_Registry, components=['creator', 'project', 'description']): pass
		class Modifier_Registry(Class_Registry, components=['project', 'description']): pass

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


		def validate_main(self, config: AbstractConfig) -> 'ProjectBase':
			runner = config.pull('_meta.main_runner', None, silent=True)
			if runner is not None:
				return runner

		def validate_run(self, config: AbstractConfig) -> 'ProjectBase':
			runner = config.pull('_meta.runner', None, silent=True)
			if runner is not None:
				return runner

		def run_local(self, config, *, script_name=None, args=None, kwargs=None, meta=None): # derives meta from config under "_meta"
			config.project = self

			if script_name is not None:
				config.push('_meta.script_name', script_name, overwrite=True, silent=True)
			if meta is not None:
				for k, v in meta.items():
					config.push(f'_meta.{k}', v, overwrite=True, silent=True)

			meta = config.peek('_meta', {}, silent=True)
			try:
				config = self._check_meta_rules(config, meta)
			except self.TerminationFlag:
				return

			entry = self.find_artifact('script', config.pull('_meta.script_name', silent=True))
			return self._run(entry, config, args, kwargs)

		# region Registration
		def find_creator(self, name, default=unspecified_argument):
			return self.find_artifact('creator', name, default=default)

		def register_creator(self, name, fn, *, description=None):
			return self.register_artifact('creator', name, fn, description=description)

		def iterate_creators(self):
			return self.iterate_artifacts('creator')


		def find_component(self, name, default=unspecified_argument):
			return self.find_artifact('component', name, default=default)

		def register_component(self, name, cls, *, creator=None, description=None):
			return self.register_artifact('component', name, cls, creator=creator, description=description)

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
					if proj != self:
						try:
							return proj.find_artifact(artifact_type, ident)
						except proj.UnknownArtifactError:
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
			self.get_project(project, is_current=False)


	def get_project(self, ident: Union[str, Path] = None, is_current: bool = True) -> Project:
		if ident is None:
			if self._current_project_key is not None:
				return self._loaded_projects[self._current_project_key]

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

			proj = self.Project(path, profile=self)
			proj = proj.validate()
			if proj.name in self._loaded_projects:
				prt.warning('project name already loaded: %s (will now overwrite)', proj.name)

		if ident is not None: # TODO: fix error handling
			assert proj.name == ident, 'project name does not match profiles name for it: ' \
			                           '%s != %s' % (proj.name, ident)
		# self._loaded_projects[ident] = proj.name
		self._loaded_projects[proj.name] = proj
		if is_current:
			self._current_project_key = proj.name
		return proj


	def create_config(self, *parents: str, **parameters: JSONABLE) -> AbstractConfig:
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
		return self.get_current_project().script(name, fn, description=description)

	def iterate_scripts(self):
		return self.get_current_project().iterate_scripts()


	def find_creator(self, name, default=unspecified_argument):
		return self.get_current_project().find_creator(name, default=default)

	def register_creator(self, name, fn, *, description=None):
		return self.get_current_project().creator(name, fn, description=description)

	def iterate_creators(self):
		return self.get_current_project().iterate_creators()

	def find_component(self, name, default=unspecified_argument):
		return self.get_current_project().find_component(name, default=default)

	def register_component(self, name, cls, *, description=None):
		return self.get_current_project().component(name, cls, description=description)

	def iterate_components(self):
		return self.get_current_project().iterate_components()

	def find_modifier(self, name, default=unspecified_argument):
		return self.get_current_project().find_modifier(name, default=default)

	def register_modifier(self, name, cls, *, description=None):
		return self.get_current_project().modifier(name, cls, description=description)

	def iterate_modifiers(self):
		return self.get_current_project().iterate_modifiers()
	# endregion

	pass
















