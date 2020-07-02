
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
		
		super().__init__(meta, config, auto_meta_args=auto_meta_args)
	


