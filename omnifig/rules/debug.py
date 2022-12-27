from typing import Optional
from omnibelt import get_printer

from ..abstract import AbstractConfig
from .. import meta_rule, create_config


from .. import __info__
prt = get_printer(__info__.get('logger_name'))


@meta_rule(name='debug', code='d', priority=100, num_args=0, description='Switch to debug mode')
def debug_rule(config: AbstractConfig, meta: AbstractConfig) -> Optional[AbstractConfig]:
	'''
	When activated, this rule updates the config object with the config file ``debug``.

	If for any reason the config file ``debug`` has already been loaded, this rule will do nothing.

	Args:
		config: The config object to be modified
		meta: The meta config object (used to check if the rule is activated)

	Returns:
		the config object possibly updated with the ``debug`` config file

	Raises:
		:exc:`ConfigNotFoundError`: if the config file ``debug`` does not exist

	'''
	
	debug = meta.pull('debug', False, silent=True)
	_debug_done = meta.pull('_debug_done', False, silent=True)
	if debug is not None and debug and not _debug_done:
		debug_config = create_config('debug', project=config.project)
		config.update(debug_config)
		meta.push('_debug_done', True, silent=True)
		prt.info('Using debug mode')
		return config


