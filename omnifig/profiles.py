
import sys, os
from collections import OrderedDict

from .util import get_printer, get_global_setting, resolve_order, spawn_path_options
from .containers import Customizable_Infomation, Registry
from .preload import include_files


prt = get_printer(__name__)

class Profile(Customizable_Infomation):
	'''
	Generally all paths that the Profile deals with should be absolute paths as the profile operates system wide
	'''
	
	def import_info(self, raw):
		
		self.config_paths = raw.get('config_paths', [])
		self.src_paths = raw.get('src_paths', [])
		
		self.projects = raw.get('projects', {}) # maps name (id) to path
		self._project_paths = {path:name for name, path in self.projects.items()}
		self._loaded_projects = OrderedDict()
		self._loaded_project_paths = OrderedDict()
		
		self._active_project = None
		self.active_project = raw.get('active_project', None)
		
		super().import_info(raw)
	
	def prepare(self):
		self.load_src()
	
	def load_src(self):
		include_files(*self.src_paths)
		
	def spawn_path_options(self, ident):
		return spawn_path_options(ident)
		
	def resolve_project_path(self, ident):
		
		options = self.spawn_path_options(ident)
		for opt in options:
			if opt in self._project_paths:
				ident = self._project_paths[opt]
				break
		
		return self.projects.get(ident, None)
			
	def contains_project(self, ident): # loaded project
		proj = self._loaded_project_paths.get(ident, None)
		if proj is not None:
			return self._loaded_projects.get(proj, None)
	
	def include_project_path(self, name, path):

		if name in self.projects:
			prt.warning(f'Projects already contains {name}, now overwriting')
		else:
			prt.debug(f'Registering {name} in profile projects')
		self.projects[name] = path
		self._updated = True
		
	def include_project(self, proj, register=True):
		
		name = proj.get_name()
		path = proj.get_info_path()
		
		if register:
			self.include_project_path(name, path)
		self._loaded_projects[name] = proj
		self._loaded_project_paths[path] = name
	
	def set_active_project(self, project=None):
		self._active_project = project
		self.active_project = None if project is None else project.get_name()
		prt.info(f'Active project set to {self.active_project}')
		self._updated = True
	
	def get_active_project(self):
		return self._active_project
	
	def get_config_paths(self):
		return self.config_paths


	
