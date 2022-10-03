from typing import Optional
from omnibelt import get_printer

from ..abstract import AbstractConfig
from .. import meta_rule


prt = get_printer(__name__)


# @Meta_Rule(NAME, priority=10, code=NAME, description='Set config to silent')
# def quiet_rule(meta, config):

@meta_rule(name='quiet', code='q', priority=10, num_args=0, description='Set config to silent')
def quiet_rule(config: AbstractConfig, meta: AbstractConfig) -> Optional[AbstractConfig]:
	'''
	When activated, this rule sets the config object to silent mode, which means pulls/pushes are not printed to stdout

	:param meta: meta config object
	:param config: full config object
	:return: possibly silenced config object
	'''

	quiet = meta.pull('quiet', False, silent=True)
	if quiet:
		config.silent = True
