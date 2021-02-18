
import sys
import traceback

from omnibelt import get_printer

from ..errors import ConfigNotFoundError

from ..top import get_config, find_config
from ..decorators import Component

from ..modes import Run_Mode
from ..rules import Meta_Rule



DEBUG_CODE = 'd'
DEBUG_NAME = 'debug'
DEBUG_MODE_NAME = f'run_mode/{DEBUG_NAME}'

prt = get_printer(__name__)

@Meta_Rule(DEBUG_NAME, priority=100, code=DEBUG_CODE, description='Switch to debug mode')
def debug_rule(meta, config):
	'''
	When activated, this rule changes the run mode to ``run_mode/debug`` and updates the config to include
	
	:param meta: meta config object
	:param config: full config object
	:return: config object updated with debug config (if available)
	'''
	
	debug = meta.pull(DEBUG_NAME, False, silent=True)
	if debug:
		meta.push('_type', DEBUG_MODE_NAME, silent=True)
		print('Switched to debug run mode')
		
		try:
			find_config(DEBUG_NAME)
		except ConfigNotFoundError:
			if not meta.pull('silent', False, silent=True):
				prt.warning('No config "debug" was found')
		else:
			config.update(get_config(DEBUG_NAME))
	
		meta.push('debug', False, silent=True) # to prevent running this rule multiple times for the same config

	return config


@Component(DEBUG_MODE_NAME)
class Debug_Mode(Run_Mode):
	'''
	Behaves just like the default run mode, excapt if the script raises an exception,
	either the ``ipdb`` :func:`post_mortem` debugger is activated, or if this is already
	running in a debugger (checked using :code:`sys.gettrace() is not None`) then
	``ipdb`` is not activated.
	'''

	def run(self, meta, config):
		'''Calls ``ipdb`` to activate debugger if an exception is raised when running the script.'''
		
		try:
			return super().run(meta, config)
		except KeyboardInterrupt:
			extype, value, tb = sys.exc_info()
			traceback.print_exc()

		except Exception as e:
			if sys.gettrace() is None:
				import ipdb
				extype, value, tb = sys.exc_info()
				traceback.print_exc()
				ipdb.post_mortem(tb)
			else:
				print('[Skipping debug]')
				raise e
		
	


