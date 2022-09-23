from typing import List, Dict, Tuple, Optional, Union, Any, Hashable, Sequence, Callable, Generator, Type, Iterable, \
	Iterator
import sys, os
from pathlib import Path
from collections import OrderedDict
from omnibelt import get_printer, Function_Registry

from ..abstract import AbstractConfig, AbstractProject, AbstractProfile, AbstractMetaRule, MetaRuleFunction
from .workspaces import ProjectBase
from ..mixins import Activatable, FileInfo

prt = get_printer(__name__)



class _MetaRule_Registry(Function_Registry, components=['code', 'priority', 'num_args', 'description']):
	pass
# MetaRuleFunction = Callable[[Config, Dict[str, Any]], Config]



class ProfileBase(AbstractProfile):  # profile that should be extended
	meta_rule_registry = _MetaRule_Registry()
	_default_profile_cls = None
	_profile = None
	
	def __init_subclass__(cls, default_profile=False, **kwargs):
		super().__init_subclass__(**kwargs)
		cls._profile = None
		if default_profile is not None:
			ProfileBase._default_profile_cls = cls
	
	# region Class Methods
	Project: ProjectBase = ProjectBase
	
	@classmethod
	def get_project_type(cls, ident: str) -> ProjectBase.global_type_registry.entry_cls:
		return cls.Project.get_project_type(ident)
	
	@classmethod
	def replace_profile(cls, profile: 'ProfileBase' = None) -> 'ProfileBase':
		if profile is None:
			profile = cls()
		ProfileBase._profile = profile
		old = cls._profile
		cls._profile = profile
		return old
	
	@classmethod
	def get_profile(cls) -> 'ProfileBase':
		if cls._profile is None:
			cls._profile = cls._default_profile_cls()
			cls._profile.activate()
		return cls._profile
	
	@classmethod
	def register_meta_rule(cls, name: str, func: MetaRuleFunction, *, code: str, description: Optional[str] = None,
	                       priority: Optional[int] = 0, num_args: Optional[int] = 0) -> None:
		cls.meta_rule_registry.new(name, func, code=code, priority=priority, num_args=num_args,
		                           description=description)
	
	@classmethod
	def get_meta_rule(cls, name) -> _MetaRule_Registry.entry_cls:
		return cls.meta_rule_registry.find(name)
	
	@classmethod
	def iterate_meta_rules(cls) -> Iterator[_MetaRule_Registry.entry_cls]:
		entries = list(cls.meta_rule_registry.values())
		for entry in sorted(entries, key=lambda e: (e.priority, e.name), reverse=True):
			yield entry
	
	# @classmethod
	# def iterate_meta_rule_fns(cls):
	# 	for entry in cls.iterate_meta_rules():
	# 		yield entry.fn
	
	# endregion
	
	def __init__(self, data: Dict[str, Any] = None) -> None:
		super().__init__(data)
		self._loaded_projects = OrderedDict()
		self._current_project_key = None
	
	# region Top Level Methods
	def entry(self, script_name: Optional[str] = None) -> None:
		argv = sys.argv[1:]
		self.main(argv, script_name=script_name)
	
	def initialize(self, *projects: str, **kwargs: Any) -> None:
		self.activate(**kwargs)
		for project in projects:
			self.get_project(project)
	
	def main(self, argv: Sequence[str], *, script_name: str = None) -> None:
		return self.get_current_project().main(argv, script_name=script_name)
	
	def run(self, config, *, script_name=None, args: Optional[Tuple] = None,
	        kwargs: Optional[Dict[str, Any]] = None):
		return self.get_current_project().run(config, script_name=script_name, args=args, kwargs=kwargs)
	
	def quick_run(self, script_name, *parents, **args):
		return self.get_current_project().quick_run(script_name, *parents, **args)
	
	def cleanup(self, *args: Any, **kwargs: Any) -> None:
		return self.get_current_project().cleanup(*args, **kwargs)
	
	# def find_artifact(self, artifact_type, ident, **kwargs):
	# 	return self.get_current_project().find_artifact(artifact_type, ident, **kwargs)
	#
	# def register_artifact(self, artifact_type, ident, artifact, **kwargs):
	# 	return self.get_current_project().register_artifact(artifact_type, ident, artifact, **kwargs)
	#
	# def iterate_artifacts(self, artifact_type):
	# 	return self.get_current_project().iterate_artifacts(artifact_type)
	# endregion
	
	def __str__(self):
		return f'{self.__class__.__name__}[{self.name}]({", ".join(self._loaded_projects)})'
	
	def extract_info(self, other: 'ProfileBase') -> None:
		super().extract_info(other)
		self._loaded_projects = other._loaded_projects  # .copy()
		self._current_project_key = other._current_project_key
	
	def get_current_project(self) -> ProjectBase:
		return self.get_project(self._current_project_key)
	
	def switch_project(self, ident=None) -> ProjectBase:
		proj = self.get_project(ident)
		self._current_project_key = proj.name
		return proj
	
	def iterate_projects(self) -> Iterator[ProjectBase]:
		yield from self._loaded_projects.values()


# register_meta_rule = ProfileBase.meta_rule_registry.get_decorator(
# 	defaults={'priority': 0, 'num_args': 0, 'description': None})



def get_profile():
	return ProfileBase.get_profile()




# class Profile(Workspace):
# 	'''
# 	Generally all paths that the Profile deals with should be absolute paths as the profile operates system wide
# 	'''
#
# 	def __init__(self, **kwargs):
# 		super().__init__(**kwargs)
#
# 		self.set_current_project()
#
# 	def _process(self, raw):
# 		'''
# 		Processes the data from a yaml file and saves it to ``self``
# 		:param raw: data from a yaml file
# 		:return: None
# 		'''
#
# 		self.projects = {}
# 		self._project_paths = {}
# 		for name, path in raw .get('projects', {}).items():
# 			fixed = self.resolve_project_path(path)
# 			if fixed is not None:
# 				self.projects[name] = fixed
# 				self._project_paths[fixed] = name
# 			else:
# 				prt.warning(f'Invalid project path: {path}')
# 		self._loaded_projects = {}
# 		self._current_project = None
#
# 		self.default_ptype = raw.get('default_ptype', 'default')
#
# 		self.global_settings = raw.get('global_settings', {})
#
# 		self.active_projects = raw.get('active_projects', [])
# 		self.autoload_local = raw.get('autoload_local', True)
#
# 		self.save_projects_on_cleanup = raw.get('save_projects_on_cleanup', False)
#
# 		super()._process(raw)
#
# 	@staticmethod
# 	def is_valid_project_path(path):
# 		'''Check if a path points to a project directory'''
#
# 		# valid = lambda name: name is not None and (_info_code in name or name in _info_names)
# 		valid = lambda name: name is not None and (name in _info_names or _info_code in name)
#
# 		if os.path.isfile(path):
# 			base = os.path.basename(path)
# 			if valid(base):
# 				return path
# 			else:
# 				path = os.path.dirname(path)
#
# 		if os.path.isdir(path):
# 			for name in os.listdir(path):
# 				if valid(name):
# 					return os.path.join(path, name)
#
# 		raise NoValidProjectError(path)
#
#
# 	def initialize(self, loc=None):
# 		'''
# 		Steps to execute during initialization including: updating global settings, loading configs,
# 		running any specified source files, loading active projects, and possibly the local project.
#
# 		:param loc: absolute path to current working directory (default comes from :func:`os.getcwd()`)
# 		:return: None
# 		'''
# 		self.update_global_settings()
#
# 		super().initialize()
#
# 		self.load_active_projects()
# 		if self.autoload_local:
# 			try:
# 				self.load_project(os.getcwd() if loc is None else loc)
# 			except NoValidProjectError:
# 				pass
#
# 	def update_global_settings(self):
# 		'''Updates global settings with items in :attr:`self.global_settings`'''
# 		for item in self.global_settings.items():
# 			set_global_setting(*item)
#
# 	def load_active_projects(self, load_related=True):
# 		'''
# 		Load active projects in :attr:`self.active_projects` in order,
# 		and potentially all related projects as well
#
# 		:param load_related: load directly related projects
# 		:param all_related: recursively load all related projects
# 		:return: None
# 		'''
# 		for proj in self.get_active_projects():
# 			self.load_project(proj, load_related=load_related, all_related=False)
#
# 	def get_project(self, ident=None, load_related=True, all_related=False):
# 		'''
# 		Gets project if already loaded, otherwise tries to find the project path,
# 		and then loads the missing project
#
# 		:param ident: project name or path
# 		:param load_related: also load related projects (before this one) (dont recursively load related)
# 		:param all_related: recursively load all related projects (trumps ``load_related``)
# 		:return: project object
# 		'''
#
# 		if ident is None:
# 			ident = os.getcwd()
#
# 		if ident in self._loaded_projects:
# 			return self._loaded_projects[ident]
#
# 		path = self.resolve_project_path(ident)
# 		if path not in self._loaded_projects:
# 			self.load_project(path, load_related=load_related, all_related=all_related)
# 		return self._loaded_projects[path]
#
# 	def get_project_type(self, name):
# 		'''Gets the project type registered with the given name'''
# 		return get_project_type(name)
#
# 	def load_project(self, ident, load_related=True, all_related=False):
# 		'''
#
# 		:param ident: path or name of project (if name, then it must be profile.projects)
# 		:param load_related: also load related projects (before this one) (dont recursively load related)
# 		:param all_related: recursively load all related projects (trumps ``load_related``)
# 		:return: loaded project (or raises ``NoValidProjectError`` if none is found)
# 		'''
#
# 		path = self.resolve_project_path(ident)
# 		if path in self._loaded_projects:
# 			return self._loaded_projects[path]
# 		elif path is None:
# 			raise NoValidProjectError(ident)
#
# 		root = os.path.dirname(path)
#
# 		default_ptype = self.default_ptype
# 		default = self.get_project_type(default_ptype)
#
# 		info = default.load_raw_info(path)
#
# 		ptype = default.check_project_type(info)
# 		if ptype is None:
# 			ptype = default_ptype
# 		else:
# 			ptype, src_file = ptype
# 			if src_file is not None:
# 				include_files(src_file, os.path.join(root, src_file))
#
# 		proj_cls = self.get_project_type(ptype)
# 		if proj_cls is None:
# 			raise ValueError(f'No project type registered with name: {ptype!r}')
#
# 		project = proj_cls(raw=info, profile=self)
#
# 		self.projects[project.get_name()] = path
# 		self._loaded_projects[path] = project
#
# 		if load_related or all_related:
# 			for related in project.get_related():
# 				try:
# 					self.load_project(related, load_related=all_related, all_related=all_related)
# 				except NoValidProjectError:
# 					prt.error(f'Project {ident} is needs a related project which can\'t be found: {related}')
#
# 		self.set_current_project(project)
# 		project.initialize()
#
# 		return project
#
# 	def resolve_project_path(self, ident):
# 		'''
# 		Map/complete/fix given identifier to the project path
#
# 		:param ident: name or path to project
# 		:return: correct project path or None
# 		'''
#
# 		if ident is None:
# 			return
#
# 		if not isinstance(ident, str):
# 			ident = ident.get_info_path()
#
# 		if ident in self.projects:
# 			return self.projects[ident]
# 		if ident in self._project_paths:
# 			return ident
#
# 		return self.is_valid_project_path(ident)
#
# 	def clear_loaded_projects(self):
# 		'''
# 		Clear all loaded projects from memory
# 		(this does not affect registered components or configs)
# 		'''
# 		self._loaded_projects.clear()
#
# 	def contains_project(self, ident): # loaded project
# 		return ident in self._loaded_projects or self.resolve_project_path(ident) in self._loaded_projects
#
# 	def track_project_info(self, name, path):
# 		'''Add project info to projects table :attr:`self.projects`'''
# 		if name in self.projects:
# 			prt.info(f'Projects already contains {name}, now overwriting')
# 		else:
# 			prt.debug(f'Registering {name} in profile projects')
# 		self.projects[name] = path
# 		self._project_paths[path] = name
# 		self._updated = True
#
# 	def track_project(self, project):
# 		'''Add project to projects table :attr:`self.projects`'''
# 		return self.track_project_info(project.get_name(), project.get_info_path())
#
# 	def is_tracked(self, project):
# 		'''Check if a project is contained in projects table :attr:`self.projects`'''
# 		return project.get_name() in self.projects
#
# 	def include_project(self, project, track=True):
# 		'''
# 		Include a project instance in loaded projects table managed by this project
# 		and optionally track a project persistently.
# 		'''
# 		if track:
# 			self.track_project(project)
#
# 		self._loaded_projects[project.get_info_path()] = project
#
# 	def add_active_project(self, project):
# 		'''Add a project to the list of active projects'''
# 		name = project.get_name()
# 		self.active_projects.append(name)
# 		prt.info(f'Added active project set to {name}')
# 		self._updated = True
#
# 	def get_active_projects(self):
# 		'''Get a list of all projects specified as "active"'''
# 		return self.active_projects.copy()
#
# 	def set_current_project(self, project=None):
# 		'''Set the current project'''
# 		if isinstance(project, str):
# 			project = self.get_project(project)
#
# 		self._current_project = project
#
# 		prt.info(f'Current project set to {None if project is None else project.get_name()}')
#
# 	def get_current_project(self):
# 		'''Get the current project (usually loaded last and local),'''
#
# 		current = self._current_project
#
# 		if current is None:
# 			return self
#
# 		return self._current_project
#
# 	def find_artifact(self, atype, name):
# 		'''
# 		Search for a registered artifact from the name either in a loaded project or in the profile (global) registries
#
# 		:param atype: component, modifier, script, or config
# 		:param name: registered artifact name, can use prefix to specify project (separated with ":")
# 		:return: artifact entry (namedtuple)
# 		'''
# 		if ':' in name:
#
# 			pname, *idents = name.split(':')
#
# 			if os.name != 'nt' or len(pname) > 1 or (len(pname) == 1 and name[2:4] == r'\\'):
# 				name = ':'.join(idents)
# 				proj = self.get_project(pname)
# 				return proj.find_artifact(atype, name)
#
# 		return super().find_artifact(atype, name)
#
# 	def has_artifact(self, atype, name):
# 		'''
# 		Check if a registered artifact of type `atype` with name `name` exists
#
# 		:param atype: component, modifier, script, or config
# 		:param name: registered artifact name, can use prefix to specify project (separated with ":")
# 		:return: True iff an entry for `name` exists
# 		'''
# 		if ':' in name:
# 			pname, *idents = name.split(':')
# 			name = ':'.join(idents)
# 			proj = self.get_project(pname)
# 			return proj.has_artifact(atype, name)
#
# 		return super().has_artifact(atype, name)
#
# 	def cleanup(self):
# 		'''
# 		Saves project data if some has changed, and possibly also
# 		updates the project files of all loaded projects if they have changed.
# 		'''
# 		if self.save_projects_on_cleanup:
# 			for project in self._loaded_projects.values():
# 				project.cleanup()
# 		super().cleanup()
	
	
	


