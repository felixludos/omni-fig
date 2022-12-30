from typing import Optional, Any
from omnibelt import get_printer

from ..abstract import AbstractConfig, AbstractProject

from .base import Behavior


from .. import __info__
prt = get_printer(__info__.get('logger_name'))


class Debug(Behavior, name='debug', code='d', priority=100, description='Switch to debug mode'):
	'''
	When activated, this behavior updates the config object with the config file ``debug``.
	If for any reason the config file ``debug`` has already been loaded, this behavior will do nothing.
	'''
	def __init__(self, project: AbstractProject, **kwargs: Any):
		'''
		Sets up the debug behavior, including setting up a flag to make sure the debug config is only loaded once.

		Args:
			project: used to create the debug config
			**kwargs: passed to super
		'''
		super().__init__(project=project, **kwargs)
		self.project = project
		self._debug_done = False


	def pre_run(self, meta: AbstractConfig, config: AbstractConfig) -> Optional[AbstractConfig]:
		'''
		When activated, this behavior updates the config object with the config file ``debug``.

		If for any reason the config file ``debug`` has already been loaded, this behavior will do nothing.

		Args:
			meta: The meta config object (used to check if the behavior is activated with the ``debug`` key)
			config: Config object which will be passed to the script.

		Returns:
			the config object possibly updated with the ``debug`` config file

		Raises:
			:exc:`ConfigNotFoundError`: if the config file ``debug`` does not exist

		'''
		if meta.pull('debug', False, silent=True) and not self._debug_done:
			self._debug_done = True
			config.update(self.project.create_config('debug'))
			prt.info('Using debug mode')
			return config


