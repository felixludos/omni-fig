from typing import Any
from ..abstract import AbstractConfig, AbstractProject
from .base import Behavior



class Quiet(Behavior, name='quiet', code='q', priority=10, num_args=0, description='Set config to silent'):
	'''
	When activated, this behavior sets the config object to silent mode,
	which means pulls/pushes are not printed to stdout
	'''
	def __init__(self, project: AbstractProject, **kwargs):
		'''Sets the attribute to keep track of what the previous value of ``config.silent`` was'''
		super().__init__(project, **kwargs)
		self.previous = None


	def pre_run(self, meta: AbstractConfig, config: AbstractConfig) -> None:
		'''
		When activated, this will set the config object to silent mode

		Args:
			meta: The meta config object (used to check if the rule is activated with the ``quiet`` key)
			config: The config object to be modified

		Returns:
			``None``

		'''
		if meta.pull('quiet', False, silent=True):
			self.previous = config.silent
			config.silent = True


	def post_run(self, meta: AbstractConfig, config: AbstractConfig, output: Any) -> None:
		'''
		When activated, this rule sets the config back to its previous value

		Args:
			meta: The meta config object (not used)
			config: Config object used to run the script.
			output: Output of the script.

		Returns:
			``None``

		'''
		if self.previous is not None:
			config.silent = self.previous