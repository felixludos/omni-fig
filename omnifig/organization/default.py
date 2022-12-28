
from typing import Dict, Optional, Union, Any, Iterator, NamedTuple, Type, List
import os
from collections import deque
from pathlib import Path
from omnibelt import unspecified_argument, get_printer, Class_Registry

from ..abstract import AbstractConfig, AbstractProject, AbstractCreator

from .profiles import ProfileBase
from .workspaces import ProjectBase, GeneralProject

from .. import __info__
prt = get_printer(__info__.get('logger_name'))



class Profile(ProfileBase, default_profile=True):
	class Project(GeneralProject, name='default'):
		class Creator_Registry(Class_Registry, components=['project', 'description']):
			'''Registry for creators which determine how components are instantiated from the config.'''
			pass
		class Component_Registry(Class_Registry, components=['creator', 'project', 'description']):
			'''Registry for components (classes) which can be instantiated through the config.'''
			pass
		class Modifier_Registry(Class_Registry, components=['project', 'description']):
			'''
			Registry for modifiers (classes) which can modify components through the config
			by dynamically defining subclasses.
			'''
			pass


		def __init__(self, path: Optional[Union[str, Path]], *,
		             creator_registry: Optional[Creator_Registry] = None,
		             component_registry: Optional[Component_Registry] = None,
		             modifier_registry: Optional[Modifier_Registry] = None,
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


		def related(self) -> Iterator[AbstractProject]:
			'''
			Iterate over all projects related to this one (based on ``related`` in the project info file).

			Returns:
				An iterator over all projects related to this one.

			'''
			for ident in self.data.get('related', []):
				try:
					yield self._profile.get_project(ident)
				except self._profile.UnknownProjectError:
					pass


		def missing_related(self) -> Iterator[str]:
			'''
			Iterate over all projects related to this one that cannot be found by the current profile.

			Returns:
				An iterator over all projects related to this one that cannot be found by the current profile.

			'''
			for ident in self.data.get('related', []):
				try:
					self._profile.get_project(ident)
				except self._profile.UnknownProjectError:
					yield ident


		def validate_main(self, config: AbstractConfig) -> Optional['ProjectBase']:
			'''
			Validate the current project (``self``) with the given config for ``main()``.

			This enables the config to specify a different project before the current one is even activated.

			Args:
				config: the config object

			Returns:
				The project that according to the config should run ``main()``, defaults to ``self``.

			'''
			runner = config.pull('_meta.main_runner', None, silent=True)
			if runner is not None:
				return runner


		def validate_run(self, config: AbstractConfig) -> Optional['ProjectBase']:
			'''
			Validate the current project (``self``) with the given config for ``run()``.

			This enables the config to specify a different project to run the script.

			Args:
				config: the config object

			Returns:
				The project that according to the config should run ``run()``, defaults to ``self``.

			'''
			runner = config.pull('_meta.runner', None, silent=True)
			if runner is not None:
				return runner


		# region Registration
		def find_creator(self, name: str, default: Optional[Any] = unspecified_argument) -> NamedTuple:
			'''
			Finds the creator with the given name.

			Args:
				name: the creator was registered with.
				default: default value to return if the creator is not found.

			Returns:
				The creator entry corresponding to the given name.

			Raises:
				UnknownArtifactError: If the creator is not found and no default is given.

			'''
			return self.find_artifact('creator', name, default=default)


		def register_creator(self, name: str, typ: Type[AbstractCreator], *,
		                     description: Optional[str] = None) -> NamedTuple:
			'''
			Register a creator with the given name.

			Args:
				name: to register the script under
				typ: the creator type (should be a subclass of :class:`AbstractCreator`)
				description: description of the creator

			Returns:
				The entry of the creator that was registered

			'''
			return self.register_artifact('creator', name, typ, description=description)


		def iterate_creators(self) -> Iterator[NamedTuple]:
			'''
			Iterates over all registered creator entries.

			Returns:
				An iterator over all registered creator entries.

			'''
			return self.iterate_artifacts('creator')


		def find_component(self, name: str, default: Optional[Any] = unspecified_argument) -> NamedTuple:
			'''
			Finds the component with the given name.

			Args:
				name: the component was registered with.
				default: default value to return if the component is not found.

			Returns:
				The component entry corresponding to the given name.

			Raises:
				UnknownArtifactError: If the component is not found and no default is given.

			'''
			return self.find_artifact('component', name, default=default)


		def register_component(self, name: str, typ: Type, *, creator: Union[str, AbstractCreator] = None,
		                       description: Optional[str] = None) -> NamedTuple:
			'''
			Register a component with the given name.

			Args:
				name: to register the component under
				typ: the component type (recommended to be a subclass of :class:`Configurable`)
				creator: the creator to use for this component (if none is specified in the config)
				description: description of the component

			Returns:
				The entry of the component that was registered

			'''
			return self.register_artifact('component', name, typ, creator=creator, description=description)


		def iterate_components(self) -> Iterator[NamedTuple]:
			'''
			Iterates over all registered component entries.

			Returns:
				An iterator over all registered component entries.

			'''
			return self.iterate_artifacts('component')


		def find_modifier(self, name: str, default: Optional[Any] = unspecified_argument) -> NamedTuple:
			'''
			Finds the modifier with the given name.

			Args:
				name: the modifier was registered with.
				default: default value to return if the modifier is not found.

			Returns:
				The modifier entry corresponding to the given name.

			Raises:
				UnknownArtifactError: If the modifier is not found and no default is given.

			'''
			return self.find_artifact('modifier', name, default=default)


		def register_modifier(self, name: str, typ: Type, *, description: Optional[str] = None) -> NamedTuple:
			'''
			Register a modifier with the given name.

			Args:
				name: to register the modifier under
				typ: the modifier type (recommended to be a subclass of :class:`Configurable`)
				description: description of the modifier

			Returns:
				The entry of the modifier that was registered

			'''
			return self.register_artifact('modifier', name, typ, description=description)


		def iterate_modifiers(self) -> Iterator[NamedTuple]:
			'''
			Iterates over all registered modifiers entries.

			Returns:
				An iterator over all registered modifier entries.

			'''
			return self.iterate_artifacts('modifier')
		# endregion


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
			return super().find_artifact(artifact_type, ident, default=default)


		def _find_nonlocal_artifact(self, artifact_type: str, ident: str) -> Optional[NamedTuple]:
			'''
			Finds the artifact with the given type and identifier in the related projects and,
			if that fails, then the active projects in the profile. Note that this starts by
			searching through the graph related projects in breadth-first order, followed by
			any active base projects in the profile (that haven't already been checked).

			Args:
				artifact_type: The type of artifact to find.
				ident: The identifier of the artifact to find.

			Returns:
				The artifact entry from the registry corresponding to the given type.

			Raises:
				UnknownArtifactTypeError: If the artifact type is not registered.
				UnknownArtifactError: If the artifact is not found and no default is given.

			'''
			past = {self}
			new = deque(self.related())
			while len(new):
				proj = new.popleft()
				past.add(proj)
				try:
					if isinstance(proj, Profile.Project):
						new.extend(p for p in proj.related() if p not in past)
						return proj.find_local_artifact(artifact_type, ident)
					return proj.find_artifact(artifact_type, ident)
				except self.UnknownArtifactError:
					pass

			for proj in self._profile.iterate_base_projects():
				if proj not in past:
					try:
						if isinstance(proj, Profile.Project):
							new.extend(p for p in proj.related() if p not in past)
							return proj.find_local_artifact(artifact_type, ident)
						return proj.find_artifact(artifact_type, ident)
					except self.UnknownArtifactError:
						pass

			raise self.UnknownArtifactError(artifact_type, ident)


		def find_artifact(self, artifact_type: str, ident: str,
		                  default: Optional[Any] = unspecified_argument) -> NamedTuple:
			'''
			Finds the artifact of the given type and registered with the given identifier by searching
			first in the current project, then any related projects, and finally any active base projects
			specified by the profile. Note, that if the artifact ident may specify a project to search in
			by prefixing the ident with the project name and a colon (e.g. ``proj:ident``).

			Args:
				artifact_type: The type of artifact to find.
				ident: The identifier of the artifact to find.
				default: The default value to return if the artifact is not found.

			Returns:
				The artifact entry from the registry corresponding to the given type.

			Raises:
				UnknownArtifactTypeError: If the artifact type is not registered.
				UnknownArtifactError: If the artifact is not found and no default is given.
				UnknownProjectError: If the project specified in the artifact ident is not found.

			'''
			if ':' in ident:
				proj, ident = ident.split(':', 1)
				return self._profile.get_project(proj).find_artifact(artifact_type, ident)
			try:
				return self.find_local_artifact(artifact_type, ident)
			except self.UnknownArtifactError:
				try:
					return self._find_nonlocal_artifact(artifact_type, ident)
				except self.UnknownArtifactError:
					pass
				if default is unspecified_argument:
					raise
				return default


	_profile_env_variable = 'FIG_PROFILE'


	def __init__(self, data: Union[str, Path, Dict, None] = None):
		if data is None:
			data = os.environ.get(self._profile_env_variable, None)
		super().__init__(data)
		self._base_projects = []


	@property
	def projects(self) -> List[Project]:
		'''Convenience property for accessing the projects in the profile. Recemmended for debugging only.'''
		return self._loaded_projects


	def _activate(self) -> None:
		'''
		Activates the profile by loading all projects and base projects specified in the profile.

		Returns:
			None

		'''
		active_projects = self.data.get('active-projects', [])
		for project in active_projects:
			proj = self.get_project(project)
			proj.activate()
			self._base_projects.append(proj)
		self._current_project_key = None


	def iterate_base_projects(self) -> Iterator[Project]:
		'''
		Iterates through the active base projects in the profile.

		The active base projects are those specified in the profile's ``active-projects`` list, and are
		expected to be fallback projects for the current project for finding artifacts.

		Returns:
			An iterator over the active base projects.

		'''
		return iter(self._base_projects)


	def iterate_projects(self) -> Iterator[Project]:
		'''
		Iterates through the projects in the profile in the order they were created.
		Note that this iterator will not include duplicates, even if the same project
		is loaded under multiple names.

		Returns:
			An iterator over the projects in the profile.

		'''
		past = set()
		for project in self._loaded_projects.values():
			if project not in past:
				yield project
			past.add(project)


	class UnknownProjectError(KeyError):
		'''Raised when trying to get a project with an invalid path.'''
		pass


	_default_project_name = 'default'


	def get_project(self, ident: Union[str, Path] = None, is_current: Optional[bool] = None) -> Project:
		'''
		Gets the project with the given name/path. If no name/path is given, then the current project is returned.
		If the specified project has not been initialized, then it is created using the profile's Project class
		(but it is not activated).

		If a name is given, it must be the name of a project that has already been loaded, or it must be a key in the
		dict `projects` the profile's info file where the value is the corresponding path.

		If a path is given, the path may either be a yaml file (interpretted as the project's info file)
		or a directory (in which case the project's info file is assumed to be named `.fig.project.yaml`).

		Args:
			ident: of the project to get. If not given, then the current project is returned.
			is_current: if True, then the project is set as the current project.

		Returns:
			The project with the given name/path.

		Raises:
			UnknownProjectError: If the project is not found.
			ValueError: If the project is found, but it has a name that a different project is already using.

		'''
		if is_current is None:
			is_current = self._current_project_key is None
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

			if path is not None and not os.path.exists(path):
				raise self.UnknownProjectError(path)

			proj = self.Project(path, profile=self)
			proj = proj.validate()
			if ident is None:
				ident = self._default_project_name
			if 'name' not in proj.data:
				proj.data['name'] = ident
			if proj.name in self._loaded_projects:
				prt.warning('project name already loaded: %s (will now overwrite)', proj.name)

		if ident is not None and ident != proj.name:
			if self.data.get('projects', {}).get(proj.name) is not None:
				raise ValueError('project name already exists: %s', ident)
			prt.warning('project name does not match profiles name for it: %s != %s', ident, proj.name)
			self._loaded_projects[ident] = proj
		self._loaded_projects[proj.name] = proj
		if is_current:
			self._current_project_key = proj.name
		return proj




