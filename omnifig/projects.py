
import sys, os
import yaml
from argparse import Namespace

from .containers import Customizable_Infomation
from .external import include_files, register_project_type, include_configs, include_package

from omnibelt import get_printer, get_now

prt = get_printer(__name__)

class Project(Customizable_Infomation):

	required_attrs = ['name', 'author', 'info_path']
	recommended_attrs = ['url', 'version', 'license', 'description']
	
	def __init_subclass__(cls, ptype=None):
		cls.ptype = ptype
		register_project_type(ptype, cls)
	
	@classmethod
	def get_project_type(cls):
		return getattr(cls, 'ptype', None)
	
	def __str__(self):
		return self.name
	
	def __repr__(self):
		return f'Project({self.name})'
	
	def get_name(self):
		return self.name
	def get_info_path(self):
		return self.info_path
	
	@staticmethod
	def check_project_name(raw):
		if 'name' not in raw:
			prt.error('No name found in project info')
		return raw['name'] # must be included
	
	@staticmethod
	def check_project_type(raw):
		'''
		Based on raw project info, check if this project expects a certain project type, if so
		optionally provide a path to the source file of the project type.

		:param raw: raw project info
		:return: None or tuple with project type identifier and path to source file (or None)
		'''
		ptype = raw.get('project_type', None)
		if ptype is not None:
			return ptype, raw.get('ptype_src_file', None)
	
	def import_info(self, raw):
		'''
		Given the raw info loaded from a yaml file, this function checks integrates the information into
		the project object (self).
		
		:param raw: dictionary of info (usually loaded from a yaml)
		'''
		
		
		# region path
		
		self.info_path = raw['info_path']
		self.root = os.path.dirname(self.info_path)
		
		# endregion
		
		if 'py_info' in raw:
			info = {'__file__': os.path.join(self.root, raw['py_info'])}
			with open(info['__file__'], 'r') as f:
				exec(f.read(), info)
			del info['__file__']
			raw.update(info)
		
		# region info
		
		self.name = raw.get('name', None)
		
		self.author = raw.get('author', None)
		self.authors = raw.get('authors', None)
		if self.authors is None and self.author is not None:
			self.authors = [self.author]
		
		self.github = raw.get('github', None)
		self.url = raw.get('url', None)
		if self.github is not None and self.url is None:
			self.url = f'https://github.com/{self.github}'
		
		self.version = raw.get('version', None)
		self.license = raw.get('license', None)
		self.use = raw.get('use', 'leaf') # {leaf, package}
		
		self.description = raw.get('description', None)
		
		for key in raw:
			if key not in self.__dict__:
				prt.info(f'Found optional project info: {key}')
				setattr(self, key, raw[key])
		
		# endregion
		# region related
		
		self.related = raw.get('related', []) # should be a list of idents (paths or names in profile)
		# self.dependenies = raw.get('dependency', []) # names of projects that must be loaded before this one
		
		# endregion
		# region components
		
		self.last_update = raw.get('last_update', None)
		self.conda_env = raw.get('conda', None)
		
		self.config_paths = raw.get('configs', [])
		src = raw.get('src', None)
		self.src_paths = raw.get('src_paths', [])
		if src is not None:
			self.src_paths = [src] + self.src_paths
		self.src_packages = raw.get('src_packages', [])
		
		self.scripts = raw.get('scripts', []) # TODO: maybe track contents
		self.configs = raw.get('configs', [])
		self.components = raw.get('components', [])
		self.modifiers = raw.get('modifiers', [])
		
		self.no_auto_config = raw.get('no_auto_config', None)
		if self.no_auto_config is None or not self.no_auto_config:
			contents = set(os.listdir(self.root))
			auto_names = {'config', 'configs'}
			for aname in auto_names:
				if aname in contents:
					auto_config = os.path.join(self.root, aname)
					if os.path.isdir(auto_config) and auto_config not in self.config_paths:
						self.config_paths.append(auto_config)
			
		# endregion
		
		prt.debug(f'Finished loading project info for {self.name} ({self.info_path})')
		
		super().import_info(raw)
		
	def initialize(self):
		self.load_configs()
		self.load_src()
		
	def load_configs(self):
		if len(self.config_paths):
			include_configs(*self.config_paths, project=self)
			
	def load_src(self):
		include_files(*self.src_paths)
		include_package(*self.src_packages)
	
	def get_related(self):
		return self.related
		
	def export_info(self, path=None):
		'''
		Saves info to yaml (by default where it was loaded from)
		
		Filters out any entries with keys that start with '_' or have no value (None)
		'''
		
		data = {}
		for k,v in self.__dict__.items():
			if v is not None and k[0] != '_':
				data[k] = v
				
		if self._updated:
			data['last_update'] = get_now()
		
		if path is None:
			assert 'info_path' in data and data['info_path'] is not None, 'No path for export found'
			path = data['info_path']
		data['info_path'] = path
		
		with open(path, 'w') as f:
			yaml.dump(data, f)
	
		prt.debug(f'Finished exporting project info of {self.name} to {self.info_path}')

	def new_script(self, name):
		if name not in self.scripts:
			self.scripts.append(name)
		self._updated = True

	def new_config(self, name):
		if name not in self.configs:
			self.configs.append(name)
		self._updated = True
	
	def new_component(self, name):
		if name not in self.components:
			self.components.append(name)
		self._updated = True
	
	def new_modifier(self, name):
		if name not in self.modifiers:
			self.modifiers.append(name)
		self._updated = True

register_project_type('default', Project)
