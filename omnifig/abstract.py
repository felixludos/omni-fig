from typing import List, Dict, Tuple, Optional, Union, Any, Hashable, Sequence, Callable, Generator, Type, Iterable, \
	Iterator, NamedTuple, ContextManager
import abc
from pathlib import Path
from omnibelt import unspecified_argument, Class_Registry, Primitive, JSONABLE

from .mixins import Activatable, FileInfo

class AbstractConfig: # TODO: copy, deepcopy, etc
	empty_default = unspecified_argument

	@property
	@abc.abstractmethod
	def project(self) -> 'AbstractProject':
		raise NotImplementedError
	@project.setter
	@abc.abstractmethod
	def project(self, project: 'AbstractProject'):
		raise NotImplementedError

	def peek(self, query: Optional[str] = None, default: Optional[Any] = empty_default, *,
	         silent: Optional[bool] = False) -> 'AbstractConfig':
		return self.peeks(query, default=default, silent=silent)

	def pull(self, query: Optional[str] = None, default: Optional[Any] = empty_default, *,
	         silent: Optional[bool] = False) -> Any:
		return self.pulls(query, default=default, silent=silent)

	def push_pull(self, addr: str, value: Any, overwrite: bool = True, *, silent: Optional[bool] = False) -> Any:
		self.push(addr, value, overwrite=overwrite, silent=silent)
		return self.pull(addr, silent=silent)

	def peeks(self, *queries, default: Optional[Any] = empty_default,
	          silent: Optional[bool] = False) -> 'AbstractConfig':
		raise NotImplementedError

	def pulls(self, *queries: str, default: Optional[Any] = empty_default, silent: Optional[bool] = False) -> Any:
		raise NotImplementedError

	def push(self, addr: str, value: Any, overwrite: bool = True, *, silent: Optional[bool] = False) -> bool:
		raise NotImplementedError

	def update(self, update: 'AbstractConfig') -> 'AbstractConfig':
		raise NotImplementedError
	
	def silence(self, silent: bool = True) -> ContextManager:
		raise NotImplementedError


class AbstractConfigurable:
	@classmethod
	def init_from_config(cls, config: AbstractConfig, args=None, kwargs=None, *, silent=None):
		raise NotImplementedError


class AbstractConfigManager:
	def register_config(self, name: str, path: Union[str, Path], **kwargs):
		raise NotImplementedError

	def register_config_dir(self, root: Union[str, Path]):
		raise NotImplementedError

	def find_config_entry(self, name: str):
		raise NotImplementedError

	def find_config_path(self, name: str) -> Path:
		raise NotImplementedError

	def parse_argv(self, argv: Sequence[str], script_name: Optional[str] = unspecified_argument) -> AbstractConfig:
		raise NotImplementedError

	def create_config(self, configs: Optional[Sequence[str]] = None, data: Optional[JSONABLE] = None) -> AbstractConfig:
		raise NotImplementedError
	
	ConfigNode = None
	
	def load_raw_config(self, path: Union[str, Path]) -> AbstractConfig:
		raise NotImplementedError
	
	def configurize(self, raw: Any):
		raise NotImplementedError
	
	def merge_configs(self, *configs: AbstractConfig) -> AbstractConfig:
		raise NotImplementedError

	@staticmethod
	def update_config(base: AbstractConfig, update: AbstractConfig) -> AbstractConfig:
		raise NotImplementedError


class AbstractScript:
	def __call__(self, config: AbstractConfig):
		raise NotImplementedError


class AbstractComponent:
	pass


class AbstractModifier:
	pass


class AbstractCreator:
	_creator_name = None
	@classmethod
	def replace(cls, creator: 'AbstractCreator', config: AbstractConfig, **kwargs):
		return cls(config, **kwargs)

	def __init__(self, config: AbstractConfig, **kwargs):
		super().__init__(**kwargs)
		# self.config = config

	def report(self, reporter, search=None):
		pass

	def create(self, config, args=None, kwargs=None) -> Any:
		raise NotImplementedError



class AbstractRunMode(Activatable):
	def main(self, argv, *, script_name=None):
		config = self.parse_argv(argv, script_name=script_name)
		transfer = self.validate_main(config) # can update/modify the project based on the config
		if transfer is not None:
			return transfer.main(argv, script_name=script_name)
		self.activate() # load the project
		out = self.run(config, script_name=script_name) # run based on the config
		self.cleanup() # (optional) cleanup
		return out # return output

	def run(self, config, *, script_name=None, args: Optional[Tuple] = None,
	        kwargs: Optional[Dict[str, Any]] = None, **meta: Any) -> Any:
		transfer = self.validate_run(config)
		if transfer is not None:
			return transfer.run(config, script_name=script_name)
		return self.run_local(config, script_name=script_name, args=args, kwargs=kwargs, meta=meta)

	def cleanup(self, *args, **kwargs):
		pass

	def validate_main(self, config) -> Optional['Run_Mode']:
		pass

	def validate_run(self, config) -> Optional['Run_Mode']:
		pass

	def parse_argv(self, argv, *, script_name=None) -> AbstractConfig:
		raise NotImplementedError

	def run_local(self, config, *, script_name=None, args: Optional[Tuple] = None,
	        kwargs: Optional[Dict[str, Any]] = None, meta: Optional[Dict[str, Any]] = None) -> Any:
		raise NotImplementedError



_ArtifactEntry = NamedTuple('ArtifactEntry', [('name', str), ('value', Type)])
MetaRuleFunction = Callable[[AbstractConfig, Dict[str, Any]], Optional[AbstractConfig]]
# _MetaRuleEntry = NamedTuple('MetaRuleEntry', 'fn:MetaRuleFunction code:str priority:int num_args:int')



class AbstractProject(AbstractRunMode, FileInfo): # generally you should extend organization.workspaces.ProjectBase
	def __init__(self, path: Optional[Union[str, Path]] = None, profile: 'AbstractProfile' = None, **kwargs):
		super().__init__(path, **kwargs)
		self._profile = profile

	def __eq__(self, other: 'AbstractProject') -> bool:
		return self.data['info_path'] == other.data['info_path']

	@property
	def profile(self) -> 'AbstractProfile':
		return self._profile


	def iterate_meta_rules(self) -> Iterator:
		return self._profile.iterate_meta_rules()
	
	class UnknownArtifactError(Exception):
		def __init__(self, artifact_type, ident):
			super().__init__(f'{artifact_type} {ident!r} not found')
			self.artifact_type = artifact_type
			self.ident = ident
	
	def find_artifact(self, artifact_type: str, ident: str,
	                  default: Optional[Any] = unspecified_argument) -> _ArtifactEntry:
		raise self.UnknownArtifactError(artifact_type, ident)

	def register_artifact(self, artifact_type: str, ident: str, artifact: Union[Type, Callable],
	                      **kwargs: Any) -> None:
		raise NotImplementedError

	def iterate_artifacts(self, artifact_type: str) -> Iterator[_ArtifactEntry]:
		raise NotImplementedError


	def create_config(self, *parents: str, **parameters: Primitive) -> AbstractConfig:
		raise NotImplementedError

	def quick_run(self, script_name: str, *parents: str, **parameters: JSONABLE) -> Any:
		config = self.create_config(*parents, **parameters)
		return self.run(config, script_name=script_name)



_ProjectTypeEntry = NamedTuple('ProjectTypeEntry', [('name', str), ('cls', Type[AbstractProject])])



class AbstractProfile(FileInfo): # generally you should extend organization.workspaces.ProfileBase
	@classmethod
	def get_project_type(cls, ident: str) -> _ProjectTypeEntry:
		raise NotImplementedError

	@classmethod
	def replace_profile(cls, profile: 'AbstractProfile') -> 'AbstractProfile':
		raise NotImplementedError

	@classmethod
	def get_profile(cls) -> 'AbstractProfile':
		raise NotImplementedError

	@classmethod
	def register_meta_rule(cls, name: str, func: MetaRuleFunction, code: str,
	                       priority: Optional[int] = 0, num_args: Optional[int] = 0) -> None:
		raise NotImplementedError

	@classmethod
	def get_meta_rule(cls, name: str):
		raise NotImplementedError

	@classmethod
	def iterate_meta_rules(cls) -> Iterator:
		raise NotImplementedError


	def entry(self, script_name=None) -> None:
		raise NotImplementedError

	def initialize(self, *projects: str, **kwargs) -> None:
		raise NotImplementedError

	def main(self, argv: Sequence[str], *, script_name: Optional[str] = None) -> Any:
		raise NotImplementedError

	def run(self, config, *, script_name=None, args: Optional[Tuple] = None,
	        kwargs: Optional[Dict[str, Any]] = None, meta: Optional[Dict[str, Any]] = None) -> Any:
		raise NotImplementedError

	def quick_run(self, script_name: str, *parents: str, **args: Any) -> Any:
		raise NotImplementedError

	def cleanup(self, *args, **kwargs) -> None:
		raise NotImplementedError


	def extract_info(self, other: 'AbstractProfile') -> None:
		raise NotImplementedError

	def get_current_project(self) -> AbstractProject:
		raise NotImplementedError

	def switch_project(self, ident: Optional[str] = None) -> AbstractProject:
		raise NotImplementedError

	def iterate_projects(self) -> Iterator[AbstractProject]:
		raise NotImplementedError

	def get_project(self, ident: Optional[str] = None) -> AbstractProject:
		raise NotImplementedError



class AbstractMetaRule:
	class TerminationFlag(KeyboardInterrupt): pass

	@classmethod
	def run(cls, config: AbstractConfig, meta: Dict[str, Any]) -> Optional[AbstractConfig]:
		raise NotImplementedError












