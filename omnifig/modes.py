
from .errors import MissingScriptError
# from .registry import Component, get_script
from .top import find_script
from .decorators import Component
from .util import autofill_args

from omnibelt import get_printer

prt = get_printer(__name__)


@Component('run_mode/default')
class Run_Mode:
	'''
	Run modes are used to actually execute the script specified by the user in the run command.
	
	It is recommended to register all run_modes with a ``run_mode/`` prefix, but not required.
	'''
	def __init__(self, A):
		self.silent = A.pull('silent', True, silent=True)
	
	@staticmethod
	def get_script_info(script_name):
		'''Given the name of the registered script, this returns the corresponding entry in the registry'''
		return find_script(script_name)
	
	
	def run(self, meta, config):
		'''
		When called this should actually execute the registered script whose name is specified under meta.script_name.

		:param meta: meta config - contains script_name
		:param config: config for script
		:return: output of script
		'''
		
		script_name = meta.pull('script_name', silent=self.silent)
		script_info = self.get_script_info(script_name)
		
		if script_info is None:
			raise MissingScriptError(script_name)
		
		script_fn = script_info.fn
		
		if script_info.use_config:
			return script_fn(config)
		return autofill_args(script_fn, config)
