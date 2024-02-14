from typing import Dict, Optional, Union, Any, Iterator, NamedTuple, Type, List
import os
from itertools import chain
from collections import deque
from pathlib import Path
from tabulate import tabulate
from omnibelt import unspecified_argument, Class_Registry, colorize

from .. import __logger__ as prt
from ..abstract import AbstractProject, AbstractCreator

from .profiles import ProfileBase
from .workspaces import ProjectBase, GeneralProject


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
	
	def __init__(self, path: Optional[Union[str, Path]] = None, *,
	             creator_registry: Optional[Creator_Registry] = None,
	             component_registry: Optional[Component_Registry] = None,
	             modifier_registry: Optional[Modifier_Registry] = None,
	             **kwargs):
		if path is None:
			path = Path().cwd()
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
	
	def nonlocal_projects(self) -> Iterator[NamedTuple]:
		'''
		Iterator over all projects that are related to this one, followed by all active base projects
		of the profile (without repeating any projects).

		Returns:
			An iterator over all projects that are related to this one, followed by all active base projects

		'''
		past = {self}
		for proj in chain(self.related(), self._profile.iterate_base_projects()):
			if proj in past:
				continue
			yield proj
			past.add(proj)
	
	def xray(self, artifact: str, *, include_nonlocal: Optional[bool] = True, as_list: Optional[bool] = False,
	         sort: Optional[bool] = False, reverse: Optional[bool] = False) -> Optional[List[NamedTuple]]:
		'''
		Prints a list of all artifacts of the given type accessible from this project
		(including related and active base projects).

		Args:
			artifact: artifact type (e.g. 'script', 'config')
			include_nonlocal: whether to include artifacts from non-local projects
				(related and active base projects)
			as_list: instead of printing, return the list of artifacts
			sort: sort the list of artifacts by name
			reverse: reverse the order of the list of artifacts

		Returns:
			list: if as_list is True, returns a list of artifacts

		Raises:
			UnknownArtifactTypeError: if the given artifact type does not exist

		'''
		if not include_nonlocal:
			return super().xray(artifact, as_list=as_list, sort=sort, reverse=reverse)
		
		local = super().xray(artifact, reverse=False, as_list=True, sort=sort)
		
		vocab = {e.name for e in local}
		full = [(entry, False) for entry in local]
		
		for proj in self.nonlocal_projects():
			for entry in proj.xray(artifact, include_nonlocal=False, reverse=False, as_list=True, sort=sort):
				name = entry.name
				full.append((entry, name in vocab))
				vocab.add(name)
		
		if sort:
			full.sort(key=lambda e: e[0].name)
		if reverse:
			full.reverse()
		
		if as_list:
			return [e[0] for e in full]
		
		if len(full):
			rows, descs = zip(*[self._format_xray_entry(t) for t, _ in full])
			for row, (entry, is_dup) in zip(rows, full):
				if is_dup:
					row[0] = colorize(row[0], color="red")
			descs = [None if d is None else f'\t[{d}]' for d in descs]
			
			table = tabulate(rows, tablefmt='simple')
			
			lines = [line for lines in zip(table.splitlines()[1:-1], descs) for line in lines if line is not None]
			print('\n'.join(lines))
	
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



class Profile(ProfileBase, default_profile=True):
	Project = Project
	
	_profile_env_variable = 'OMNIFIG_PROFILE'


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


	def initialize(self, *projects: str, **kwargs: Any) -> None:
		'''
		Initializes the profile by activating it and then activating all projects specified, also adds the
		projects to the profile's active base projects.

		Args:
			*projects: The names of projects to activate and add to the active base projects.
			**kwargs: Additional keyword arguments to pass to the project initialization methods.

		Returns:
			None

		'''
		super().initialize(*projects, **kwargs)
		self._base_projects.extend(projects)


	def iterate_base_projects(self) -> Iterator[Project]:
		'''
		Iterates through the active base projects in the profile.

		The active base projects are those specified in the profile's ``active-projects`` list, and are
		expected to be fallback projects for the current project for finding artifacts.

		Returns:
			An iterator over the active base projects.

		'''
		past = set()
		for base in self._base_projects:
			proj = self.get_project(base)
			if proj not in past:
				past.add(proj)
				yield proj


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
				past.add(project)
				yield project


	class UnknownProjectError(KeyError):
		'''Raised when trying to get a project with an invalid path.'''
		pass


	def _infer_project_path(self, ident: Union[str, Path, None]) -> Optional[Union[Path, str]]:
		'''
		Checks if the directory (current working directory by default) is inside a known project directory,
		and if so, returns that project.

		Args:
			ident: of the project to get (expected to be None usually).

		Returns:

		'''
		# path = ident
		if ident is None:
			ident = Path().cwd()

		contents = set(os.listdir(ident))
		for fname in self.Project.info_file_names:
			if fname in contents:
				return ident

		known = {path: name for name, path in self.data.get('projects', {}).items()}
		if str(ident) in known:
			return ident

		if len(ident.parts) > 1:
			return self._infer_project_path(ident.parent)


	def get_project(self, ident: Union[str, Path] = None, is_current: Optional[bool] = None) -> AbstractProject:
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
		# if is_current is None:
		# 	is_current = self._current_project_key is None

		if ident is None:
			if self._current_project_key is not None:
				return self._loaded_projects[self._current_project_key]

			ident = self._infer_project_path(ident)

		if ident in self._loaded_projects:
			return self._loaded_projects[ident]

		if isinstance(ident, ProjectBase):
			proj = ident
			ident = proj.data.get('name', None)
		else:
			# create new
			path = ident
			if ident in self.data.get('projects', {}):
				path = self.data['projects'][ident]

			if path is not None and not os.path.exists(path):
				raise self.UnknownProjectError(path)

			proj = self.Project(path, profile=self)
			proj = proj.validate()

		if 'name' not in proj.data and ident is not None:
			proj.data['name'] = ident.stem if isinstance(ident, Path) else ident

		if self._loaded_projects.get(proj.name, proj) is not proj:
			# raise ValueError(f'Project with name {proj.name} already exists!')
			prt.warning(f'project name already loaded: {proj.name} (will now overwrite)')

		if ident is not None:
			if not isinstance(ident, Path) and ident != proj.name:
				if self.data.get('projects', {}).get(proj.name) is not None:
					raise ValueError('project name already exists: %s', ident)
				prt.warning(f'project name does not match profiles name for it: {ident} != {proj.name}')

			if self._loaded_projects.get(ident, proj) is not proj:
				# raise ValueError(f'Project with name {proj.name} already exists!')
				prt.warning(f'project name already loaded: {ident} (will now overwrite)')
			self._loaded_projects[ident] = proj

		self._loaded_projects[proj.name] = proj
		if is_current:
			self._current_project_key = proj.name
		return proj




