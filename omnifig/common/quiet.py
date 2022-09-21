from typing import Optional
from omnibelt import get_printer

from ..abstract import AbstractConfig
from .. import Meta_Rule


prt = get_printer(__name__)


# @Meta_Rule(NAME, priority=10, code=NAME, description='Set config to silent')
# def quiet_rule(meta, config):
class Debug_Rule(Meta_Rule, name='quiet', code='q', priority=10, num_args=0, description='Set config to silent'):
	'''
	When activated, this rule sets the config object to silent mode, which means pulls/pushes are not printed to stdout

	:param meta: meta config object
	:param config: full config object
	:return: possibly silenced config object
	'''
	
	def __call__(self, config: AbstractConfig, meta: AbstractConfig) -> Optional[AbstractConfig]:
		quiet = meta.pull('quiet', False, silent=True)
		if quiet:
			config.silent = True
