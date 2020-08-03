
import sys, os

from .errors import NoValidProjectError
from .util import get_global_setting, resolve_order, spawn_path_options, set_global_setting
from .containers import Customizable_Infomation
from .external import include_files, include_configs, get_project_type

from .projects import Project

from omnibelt import get_printer, Registry

prt = get_printer(__name__)

_info_names = {
	'omni.fig', 'info.fig', '.omni.fig', '.info.fig',
	'fig.yaml', 'fig.yml', '.fig.yaml', '.fig.yml',
	'fig.info.yaml', 'fig.info.yml', '.fig.info.yaml', '.fig.info.yml',
	'fig_info.yaml', 'fig_info.yml', '.fig_info.yaml', '.fig_info.yml',
	'project.yaml', 'project.yml', '.project.yaml', '.project.yml',
}
_info_code = '.fig.yml'

_default_project_type = 'default'


class Profile(Customizable_Infomation):
	'''
	Generally all paths that the Profile deals with should be absolute paths as the profile operates system wide
	'''
	
	def import_info(self, raw):
		
		self.config_paths = raw.get('config_paths', [])
		self.src_paths = raw.get('src_paths', [])
		
		self.projects = {}
		self._project_paths = {}
		for name, path in raw.get('projects', {}).items():
			fixed = self.resolve_project_path(path)
			if fixed is not None:
				self.projects[name] = fixed
				self._project_paths[fixed] = name
			else:
				prt.warning(f'Invalid project path: {path}')
		self._loaded_projects = {}
		self._current_project = None
		
		self.default_ptype = raw.get('default_ptype', 'default')
		
		self.global_settings = raw.get('global_settings', {})
		
		self.active_projects = raw.get('active_projects', [])
		self.autoload_local = raw.get('autoload_local', True)
		
		super().import_info(raw)
		
	@staticmethod
	def is_valid_project_path(path):
		
		valid = lambda name: name is not None and (_info_code in name or name in _info_names)
		
		if os.path.isfile(path):
			base = os.path.basename(path)
			if valid(base):
				return path
			else:
				path = os.path.dirname(path)
		
		if os.path.isdir(path):
			for name in os.listdir(path):
				if valid(name):
					return os.path.join(path, name)
			
	
	def initialize(self, loc=None):
		self.update_global_settings()
		self.load_config()
		self.load_src()
		self.load_active_projects()
		if self.autoload_local:
			self.load_project(os.getcwd() if loc is None else loc)
		
	
	def update_global_settings(self):
		for item in self.global_settings.items():
			set_global_setting(*item)
	
	def load_src(self):
		include_files(*self.src_paths)
		
	def load_config(self):
		include_configs(*self.config_paths)
		
	def load_active_projects(self, load_related=True):
		for proj in self.active_projects:
			self.load_project(proj, load_related=load_related)
		
	def get_project(self, ident):
		
		if ident in self._loaded_projects:
			return self._loaded_projects[ident]
		
		path = self.resolve_project_path(ident)
		if path not in self._loaded_projects:
			self.load_project(path)
		return self._loaded_projects[path]
		
	def get_project_type(self, name):
		return get_project_type(name)
	
	def load_project(self, ident, load_related=True, all_related=False):
		'''

		:param ident: path or name of project (if name, then it must be profile.projects)
		:param load_related: also load related projects (before this one) (dont recursively load related)
		:param all_related: recursively load all related projects (trumps ``load_related``)
		:return: loaded project (or raises ``NoValidProjectError`` if none is found)
		'''
		
		path = self.resolve_project_path(ident)
		if path in self._loaded_projects:
			return self._loaded_projects[path]
		elif path is None:
			raise NoValidProjectError(ident)
		
		root = os.path.dirname(path)
		
		default_ptype = self.default_ptype
		default = self.get_project_type(default_ptype)
		
		info = default.load_raw_info(path)
		
		ptype = default.check_project_type(info)
		if ptype is None:
			ptype = default_ptype
		else:
			ptype, src_file = ptype
			if src_file is not None:
				include_files(src_file, os.path.join(root, src_file))
		
		proj_cls = self.get_project_type(ptype)
		
		project = proj_cls(raw=info)
		self._loaded_projects[path] = project
		
		if load_related or all_related:
			for related in project.get_related():
				self.load_project(related, load_related=all_related, all_related=all_related)
		
		self.set_current_project(project)
		project.initialize()
		
		return project
		
	def resolve_project_path(self, ident):
		'''
		
		:param ident: name or path to project
		:return:
		'''
		
		if not isinstance(ident, str):
			ident = ident.get_info_path()
		
		if ident in self.projects:
			return self.projects[ident]
		if ident in self._project_paths:
			return ident
		
		return self.is_valid_project_path(ident)
	
	def clear_loaded_projects(self):
		self._loaded_projects.clear()
	
	def contains_project(self, ident): # loaded project
		return ident in self._loaded_projects or self.resolve_project_path(ident) in self._loaded_projects
	
	def track_project_info(self, name, path):
		if name in self.projects:
			prt.warning(f'Projects already contains {name}, now overwriting')
		else:
			prt.debug(f'Registering {name} in profile projects')
		self.projects[name] = path
		self._project_paths[path] = name
		self._updated = True
	
	def track_project(self, project):
		return self.track_project_info(project.get_name(), project.get_info_path())
	
	def is_tracked(self, project):
		return project.get_name() in self.projects
	
	def include_project(self, project, track=True):
		if track:
			self.track_project(project)
			
		self._loaded_projects[project.get_info_path()] = project
	
	def add_active_project(self, project):
		name = project.get_name()
		self.active_projects.append(name)
		prt.info(f'Added active project set to {name}')
		self._updated = True
	
	def get_active_projects(self):
		return self.active_projects.copy()
	
	def set_current_project(self, project):
		
		if isinstance(project, str):
			project = self.get_project(project)
		
		self._current_project = project
		
		prt.info(f'Current project set to {None if project is None else project.get_name()}')
	
	def get_current_project(self):
		return self._current_project
	
	def get_config_paths(self):
		return self.config_paths


	
