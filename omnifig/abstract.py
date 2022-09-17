from typing import Optional, Union, Any, Self
from omnibelt import unspecified_argument

from .mixins import Activatable


class Config: # TODO: copy, deepcopy, etc
	empty_default = unspecified_argument

	@property
	# TODO: use @abstractmethod here
	def project(self):
		raise NotImplementedError
	@project.setter
	def project(self, project):
		raise NotImplementedError

	def peek(self, query: str, default: Optional[Any] = empty_default, *, silent: Optional[bool] = False) -> 'Config':
		return self.peeks(query, default=default, silent=silent)

	def pull(self, query: str, default: Optional[Any] = empty_default, *, silent: Optional[bool] = False) -> Any:
		return self.pulls(query, default=default, silent=silent)

	def push_pull(self, addr: str, value: Any, overwrite: bool = True, *, silent: Optional[bool] = False) -> Any:
		self.push(addr, value, overwrite=overwrite, silent=silent)
		return self.pull(addr, silent=silent)

	def peeks(self, *queries, default: Optional[Any] = empty_default, silent: Optional[bool] = False) -> 'Config':
		raise NotImplementedError

	def pulls(self, *queries: str, default: Optional[Any] = empty_default, silent: Optional[bool] = False) -> Any:
		raise NotImplementedError

	def push(self, addr: str, value: Any, overwrite: bool = True, *, silent: Optional[bool] = False) -> bool:
		raise NotImplementedError

	def update(self, update: 'Config') -> Self:
		raise NotImplementedError



class Creator:
	# @classmethod
	# def trigger(cls, config: Config) -> Optional[Dict[str, Any]]:
	# 	raise NotImplementedError

	@classmethod
	def from_search(cls, search):
		raise NotImplementedError

	@classmethod
	def replace(cls, creator: 'Creator', config: Config, **kwargs):
		return cls(config, **kwargs)

	def __init__(self, config: Config, **kwargs):
		super().__init__(**kwargs)
		# self.config = config

	def validate(self, config) -> Union[Self, 'Creator']:
		return self

	def report(self, reporter, search=None):
		pass

	def create(self, config, args=None, kwargs=None) -> Any:
		raise NotImplementedError

	def silence(self, silent=True):
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

	def run(self, config, *, script_name=None, **meta):
		transfer = self.validate_run(config)
		if transfer is not None:
			return transfer.run(config, script_name=script_name)
		return self.run_local(config, script_name=script_name)

	def cleanup(self, *args, **kwargs):
		pass

	def validate_main(self, config) -> Optional['Run_Mode']:
		pass

	def validate_run(self, config) -> Optional['Run_Mode']:
		pass

	def parse_argv(self, argv, *, script_name=None) -> Config:
		raise NotImplementedError

	def run_local(self, config, *, script_name=None) -> Any:
		raise NotImplementedError



# class AbstractProject:
# 	def main(self, argv, script_name=None):
# 		raise NotImplementedError
#
# 	def run(self, script_name, config, **meta):
# 		raise NotImplementedError
#
# 	def quick_run(self, script_name, *parents, **args):
# 		raise NotImplementedError
#
# 	def cleanup(self, *args, **kwargs):
# 		raise NotImplementedError
#
# 	def get_config(self, *parents, **parameters):
# 		raise NotImplementedError
#
# 	def create_component(self, config):
# 		raise NotImplementedError

