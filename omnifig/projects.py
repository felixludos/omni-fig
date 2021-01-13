
import sys, os
from pathlib import Path

from .errors import MissingConfigError, MissingArtifactError
from .organization import Workspace
from .external import include_files, register_project_type, include_package


from omnibelt import get_printer

prt = get_printer(__name__)

class Project(Workspace):
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
	
	def __init_subclass__(cls, name=None):
		'''Subclasses can automatically be registered if a ``ptype`` for the registry is provided'''
		cls.ptype = name
		register_project_type(name, cls)
	
	def __init__(self, profile=None, **kwargs):
		super().__init__(**kwargs)
		
		self._profile = profile
	
	# region Getters
	
	def get_profile(self):
		return self._profile
	def get_path(self):
		'''Gets the path to the project directory'''
		return self.root
	def get_related(self):
		'''Returns a list of project names of all projects that should be loaded prior to this one'''
		return self.related
	
	# endregion
	
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
	
	def _process(self, raw):
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
		
		super()._process(raw)
		
		# region related
		
		self.related = raw.get('related', []) # should be a list of idents (paths or names in profile)
		# self.dependenies = raw.get('dependency', []) # names of projects that must be loaded before this one
		
		# endregion
		# region components
		
		self.last_update = raw.get('last_update', None)
		self.conda_env = raw.get('conda', None) # TODO
		
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
		
		
	def initialize(self):
		root = self.get_path()
		
		if self.add_to_path:
			sys.path.append(root)
			
		origin = os.getcwd()
		os.chdir(root)
		
		super().initialize()
		
		os.chdir(origin)
	
	# region Registration
	
	def register_artifact(self, atype, name, info, include_global=True):
		info['project'] = self
		super().register_artifact(atype, name=name, info=info)
		if include_global:
			self.get_profile().register_artifact(atype, name=name, info=info)
	
	# endregion
	
	# region Artifacts
	
	def has_artifact(self, atype, name, check_global=True):
		
		if ':' in name:
			return self.get_profile().has_artifact(atype, name)
	
		if super().has_artifact(atype, name):
			return True
		return not check_global or self.get_profile().has_artifact(atype, name)
	
	def find_artifact(self, atype, name, check_global=True):
		
		if ':' in name:
			return self.get_profile().find_artifact(atype, name)
		
		try:
			artifact = super().find_artifact(atype, name)
		except MissingArtifactError:
			if not check_global:
				raise
			artifact = self.get_profile().find_artifact(atype, name)
			
		return artifact
	
	def has_config(self, name):
		if super().has_config(name):
			return True
		path = self.get_path() / Path(name)
		return path.suffix in {'.yaml', '.yml'} and path.is_file()
	
	def find_config(self, name):
		try:
			path = super().find_config(name)
		except MissingConfigError:
			path = self.get_path() / Path(name)
			if path.suffix in {'.yaml', '.yml'} and path.is_file():
				return str(path)
			raise
		else:
			return path

	def view_artifacts(self, atype):
		glob = self.get_profile().view_artifacts(atype)
		glob.update(super().view_artifacts(atype))
		return glob

	# endregion
	

register_project_type('default', Project)
