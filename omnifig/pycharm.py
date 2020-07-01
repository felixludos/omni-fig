
from .config import get_config
from .modes import Run_Mode, Meta_Argument

DEBUG_MODE_NAME = 'debug'

class Pycharm_Arg(Meta_Argument, name='pycharm', code='p'):
	def __init__(self, meta, config):
		super().__init__(meta, config)
		
		meta.mode = DEBUG_MODE_NAME

class Debug_Mode(Run_Mode, name=DEBUG_MODE_NAME):
	
	def __init__(self, meta, config, auto_meta_args=[]):
		
		pycharm = get_config('pycharm')
		
		pycharm.update(config)
		config.clear()
		config.update(pycharm)
		
		meta.update(config._meta)
		
		super().__init__(meta, config, auto_meta_args=auto_meta_args)
	


