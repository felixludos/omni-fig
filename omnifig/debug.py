
import sys, os
import traceback

from .config import get_config
from .modes import Run_Mode, Meta_Argument

DEBUG_MODE_NAME = 'debug'

class Debug_Arg(Meta_Argument, name=DEBUG_MODE_NAME, code='d'):
	def __init__(self, meta, config):
		super().__init__(meta, config)
		
		meta.mode = DEBUG_MODE_NAME

class Debug_Mode(Run_Mode, name=DEBUG_MODE_NAME):
	
	def __init__(self, meta, config, auto_meta_args=[]):
		
		debug = get_config(DEBUG_MODE_NAME)
		
		debug.update(config)
		config.clear()
		config.update(debug)
		
		meta.update(config._meta)
		

	def run(self, script_info, meta, config):
		
		try:
			return super().run(script_info, meta, config)
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
		
	


