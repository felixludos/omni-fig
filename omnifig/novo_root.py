from typing import List, Dict, Tuple, Optional, Union, Any, Hashable, Sequence, Callable, Generator, Type, Iterable, \
	Iterator
import sys, os
from pathlib import Path
from collections import OrderedDict
from omnibelt import get_printer, load_yaml, agnosticmethod, Class_Registry

prt = get_printer(__name__)


class FileInfo:
	@staticmethod
	def load_raw_info(path: Path):
		'''Loads the info yaml file'''
		raw = load_yaml(path) if path.exists() else None
		if raw is None:
			raw = {}
		raw['info_path'] = str(path) # automatically set info_path to the path
		raw['info_dir'] = str(path.parent)
		return raw


	def __init__(self, data=None):
		if isinstance(data, str):
			data = Path(data)
		if isinstance(data, Path):
			data = self.load_raw_info(data)
		if data is None:
			data = {}
		self.data = data

	@property
	def name(self):
		return self.data.get('name', '-no-name-')

	def __repr__(self):
		return f'{self.__class__.__name__}({self.name})'

	def __str__(self):
		return f'{self.__class__.__name__}[{self.name}]({", ".join(self._loaded_projects)})'


class AbstractProject:
	def main(self, argv, script_name=None):
		raise NotImplementedError


class Project(AbstractProject, FileInfo):
	_registry = Class_Registry()
	def __init_subclass__(cls, name=None, **kwargs):
		super().__init_subclass__()
		if name is not None:
			cls._registry.new(name, cls)


class Profile(FileInfo):
	_profile = None
	def __init_subclass__(cls, **kwargs):
		super().__init_subclass__(**kwargs)
		cls._profile = None

	class Project(Project, name='default'):

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
				for name in self._project_info_file_names:
					p = path / name
					if p.exists():
						return p
			raise FileNotFoundError(f'path does not exist: {path}')


		def __init__(self, path, profile=None):
			path = self.infer_path(path)
			super().__init__(path)
			self._path = path
			self._profile = profile

		@property
		def root(self):
			return self._path.parent

		@property
		def info_path(self):
			return self._path




	_profile_env_variable = 'FIG_PROFILE'

	def __init__(self, data=None):
		if data is None:
			data = os.environ.get(self._profile_env_variable, None)
		super().__init__(data)
		self._loaded_projects = OrderedDict()
		self._current_project_key = None

	def initialize(self):
		active_projects = self.data.get('active_projects', [])
		for project in active_projects:
			self.get_project(project)

	@classmethod
	def get_profile(cls):
		if cls._profile is None:
			cls._profile = cls()
			cls._profile.initialize()
		return cls._profile

	def entry(self, script_name=None):
		argv = sys.argv[1:]
		self.main(argv, script_name=script_name)

	def main(self, argv, script_name=None):
		return self.get_current_project().main(argv, script_name=script_name)

	def switch_project(self, ident=None):
		proj = self.get_project(ident)
		self._current_project_key = proj.name
		return proj


	def get_current_project(self):
		return self.get_project(self._current_project_key)


	def get_project(self, ident=None):
		if ident is None:
			if self._current_project_key is not None:
				return self.get_current_project()

		if ident in self._loaded_projects:
			return self._loaded_projects[ident]

		if isinstance(ident, Project):
			proj = ident
			ident = proj.name
		else:
			# create new
			path = ident
			if ident in self.data.get('projects', {}):
				path = self.data['projects'][ident]

			proj = self.Project(path)
			if proj.name in self._loaded_projects:
				prt.warning('project name already loaded: %s (will now overwrite)', proj.name)

		assert proj.name == ident, 'project name does not match profiles name for it: %s != %s' % (proj.name, ident)
		# self._loaded_projects[ident] = proj.name
		self._loaded_projects[proj.name] = proj
		if self._current_project_key is None:
			self._current_project_key = ident
		return proj



class Workspace:
	pass























