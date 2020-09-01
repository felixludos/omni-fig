
import sys, os
import yaml
from argparse import Namespace

from .containers import Customizable_Infomation
from .external import include_files, register_project_type, include_configs, include_package

from omnibelt import get_printer, get_now

prt = get_printer(__name__)

class Project(Customizable_Infomation):
	'''
	Projects are used to group code into packets with specific config files that should be
	loaded all together. A project must contain a yaml file named ``.fig.yml`` in the
	root directory of the project (aka the "project directory"), and all paths in
	that yaml file should be relative to the project directory.
	
	Generally there are two kinds of projects: "packages" and "loose" projects.
	Package projects are meant to be installed and used as a library, while loose
	projects may just be a series of python files.
	
	This class may also be subclassed to change the behavior of projects (such as changing the loading),
	in fact, any subclasses of this class can automatically be registered when providing a name for the
	project type in the class definition.
	'''

	# required_attrs = ['name', 'author', 'info_path']
	# recommended_attrs = ['url', 'version', 'license', 'description']
	
	def __init_subclass__(cls, ptype=None):
		'''Subclasses can automatically be registered if a ``ptype`` for the registry is provided'''
		cls.ptype = ptype
		register_project_type(ptype, cls)
	
	def __str__(self):
		return self.get_name()
	
	def __repr__(self):
		return f'Project({self.get_name()})'
	
	def get_name(self):
		'''Gets the project name'''
		return self.name
	def get_info_path(self):
		'''Gets the project directory'''
		return self.info_path
	
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
		
		self.add_to_path = raw.get('add_to_path', True)
		
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
		self.conda_env = raw.get('conda', None) # TODO
		
		self.config_paths = raw.get('configs', [])
		src = raw.get('src', None)
		self.src_paths = raw.get('src_paths', [])
		if src is not None:
			self.src_paths = self.src_paths + [src]
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
		'''
		This loads the project, primarily by registering any specified config files,
		importing specified packages, and finally running any provided source files
		
		:return: None
		'''
		if self.add_to_path:
			sys.path.append(self.root)
			
		origin = os.getcwd()
		os.chdir(self.root)
		
		self.load_configs()
		self.load_src()
		
		os.chdir(origin)
		
	def load_configs(self):
		'''Registers all specified config files and directories'''
		if len(self.config_paths):
			include_configs(*self.config_paths, project=self)
			
	def load_src(self):
		'''Imports all specified packages and runs the specified python files'''
		include_package(*self.src_packages)
		include_files(*[os.path.join(self.root, src) for src in self.src_paths])
	
	def get_related(self):
		'''Returns a list of project names of all projects that should be loaded prior to this one'''
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
		'''Adds the specified script name to this project for record keeping'''
		if name not in self.scripts:
			self.scripts.append(name)
		self._updated = True

	def new_config(self, name):
		'''Adds the specified config file to this project for record keeping'''
		if name not in self.configs:
			self.configs.append(name)
		self._updated = True
	
	def new_component(self, name):
		'''Adds the specified component name to this project for record keeping'''
		if name not in self.components:
			self.components.append(name)
		self._updated = True
	
	def new_modifier(self, name):
		'''Adds the specified modifier name to this project for record keeping'''
		if name not in self.modifiers:
			self.modifiers.append(name)
		self._updated = True

register_project_type('default', Project)
