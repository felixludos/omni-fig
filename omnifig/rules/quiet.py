from typing import Optional

from ..abstract import AbstractConfig
from ..registration import meta_rule


@meta_rule(name='quiet', code='q', priority=10, num_args=0, description='Set config to silent')
def quiet_rule(config: AbstractConfig, meta: AbstractConfig) -> None:
	'''
	When activated, this rule sets the config object to silent mode,
	which means pulls/pushes are not printed to stdout

	Args:
		config: The config object to be modified
		meta: The meta config object (not used)

	'''

	quiet = meta.pull('quiet', False, silent=True)
	if quiet:
		config.silent = True
