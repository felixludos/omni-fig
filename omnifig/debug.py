
import sys
import traceback

from .config import get_config
from .modes import Run_Mode
from .rules import Meta_Rule
from .registry import Component

DEBUG_CODE = 'd'
DEBUG_NAME = 'debug'
DEBUG_MODE_NAME = f'run_mode/{DEBUG_NAME}'

@Meta_Rule(DEBUG_NAME, priority=100, code=DEBUG_CODE, description='Switch to debug mode')
def debug_rule(meta, config):
	
	debug = meta.pull(DEBUG_NAME, False, silent=True)
	if debug:
		meta.push('_type', DEBUG_MODE_NAME, silent=True)
		print('Switched to debug run mode')
	
		debug = get_config(DEBUG_NAME)
		config.update(debug)

	return config


@Component(DEBUG_MODE_NAME)
class Debug_Mode(Run_Mode):

	def run(self, meta, config):
		
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
		
	


