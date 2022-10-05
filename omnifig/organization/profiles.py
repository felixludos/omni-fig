from typing import List, Dict, Tuple, Optional, Union, Any, Hashable, Sequence, Callable, Generator, Type, Iterable, \
	Iterator
import sys, os
from pathlib import Path
from collections import OrderedDict
from omnibelt import get_printer, Function_Registry

from ..abstract import AbstractConfig, AbstractProject, AbstractProfile, AbstractMetaRule
from .workspaces import ProjectBase
from ..mixins import Activatable, FileInfo

prt = get_printer(__name__)



class _MetaRule_Registry(Function_Registry, components=['code', 'priority', 'num_args', 'description']):
	pass


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
	def register_meta_rule(cls, name: str, func: Callable[[AbstractConfig, Dict[str, Any]], Optional[AbstractConfig]],
	                       *, code: str, description: Optional[str] = None, priority: Optional[int] = 0,
	                       num_args: Optional[int] = 0) -> None:
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



def get_profile():
	return ProfileBase.get_profile()


	


