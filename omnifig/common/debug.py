from typing import Dict, Any, Optional
import sys
import traceback
from omnibelt import get_printer

from ..abstract import AbstractConfig
from .. import meta_rule, create_config

prt = get_printer(__name__)


@meta_rule(name='debug', code='d', priority=100, num_args=0, description='Switch to debug mode')
class Debug_Rule:
	'''
	When activated, this rule changes the run mode to ``run_mode/debug`` and updates the config to include

	:param meta: meta config object
	:param config: full config object
	:return: config object updated with debug config (if available)
	'''
	def __call__(self, config: AbstractConfig, meta: AbstractConfig) -> Optional[AbstractConfig]:
		debug = meta.pull('debug', False, silent=True)
		silent = meta.pull('silent', True, silent=True)
		if debug is not None:
			try:
				debug_config = create_config('debug')
			except KeyError:
				if not silent:
					prt.warning('No config "debug" was found')
			else:
				config.update(debug_config)
				prt.info('Using debug mode')
				return config



# @Component(DEBUG_MODE_NAME)
# class Debug_Mode(Run_Mode):
# 	'''
# 	Behaves just like the default run mode, excapt if the script raises an exception,
# 	either the ``ipdb`` :func:`post_mortem` debugger is activated, or if this is already
# 	running in a debugger (checked using :code:`sys.gettrace() is not None`) then
# 	``ipdb`` is not activated.
# 	'''
#
# 	def run(self, meta, config):
# 		'''Calls ``ipdb`` to activate debugger if an exception is raised when running the script.'''
#
# 		try:
# 			return super().run(meta, config)
# 		except KeyboardInterrupt:
# 			extype, value, tb = sys.exc_info()
# 			traceback.print_exc()
#
# 		except Exception as e:
# 			if sys.gettrace() is None:
# 				import ipdb
# 				extype, value, tb = sys.exc_info()
# 				traceback.print_exc()
# 				ipdb.post_mortem(tb)
# 			else:
# 				print('[Skipping debug]')
# 				raise e
		
	


