
import inspect
from collections import OrderedDict

from omnifig.containers import Registry
from omnifig.util import get_printer, autofill_args
from omnifig.registry import get_script

prt = get_printer(__name__)

_run_mode_registry = Registry()

def get_run_mode(name):
	return _run_mode_registry.get(name, Run_Mode)


class Run_Mode: # TODO: maybe upgrade to a Customizable_Information subclass (?)
	'''
	Every run mode is also an independent registry for meta args that are supported
	'''
	name = None
	meta_args = None
	
	def __init_subclass__(cls, name=None, supports=[]):
		if name is not None:
			_run_mode_registry.new(name, cls)
		cls.name = name
		cls.meta_args = Registry()
		for arg in supports:
			cls.register_meta_arg(arg)
	
	@classmethod
	def register_meta_arg(cls, arg):
		if isinstance(arg, str):
			val = meta_arg_registry.get(arg, None)
			if val is None:
				prt.error(f'Meta arg {arg} not found, has it been registered?')
			else:
				arg = val
		if not isinstance(arg, Meta_Argument):
			prt.warning(f'Registering an unexpected object {arg} as a meta argument for the run mode {cls.get_name()}')
		elif not meta_arg_registry.is_registered(arg):
			prt.warning(f'Note that {arg} is not registered in the global Meta_Arg registry '
			            f'(so it cant be autodetected)')
		
		cls.meta_args.new(arg.get_code(), arg)
	
	@classmethod
	def get_name(cls):
		return cls.name
	
	def __init__(self, meta, config, auto_meta_args=[]):
		'''
		This is called initially for any required initial start up of the run_mode
		(should be independent of the config)

		:param meta: meta config
		:return: None
		'''
		
		meta_args = OrderedDict()
		for marg in auto_meta_args:
			meta_args[marg.get_name()] = marg
		if self.meta_args is not None:
			for name, marg in self.meta_args.items():
				if name not in meta_args:
					meta_args[name] = marg(meta, config)
		self.meta_args = meta_args
	
	def get_meta_args(self):
		return self.meta_args.values()
	
	def find_meta_arg(self, code):
		return self.meta_args.get(code, None)
	
	def prepare(self, meta, config):
		'''
		Called before run() allowing meta and config to be modified,
		including the script name found in meta.script_name
		
		Generally, meta_args cannot be added after "prepare()"

		:param meta: meta config
		:param config: config object for script
		:return: meta, config
		'''

		for arg in sorted(self.meta_args.values(), key=lambda m: getattr(m, 'priority', 0), reverse=True):
			meta, config = arg.run(meta, config)
	
	def run(self, script_info, meta, config):
		'''
		When called this should actually execute the `script_fn` using `config`
		If need be, the additional behavior according to the meta args can affect how/when the script is called

		:param script_info: entry with callable in ".fn"
		:param meta: meta args, in case some modify the subsequent behavior
		:param config: config for script_fn
		:return: whatever the script_fn returns (possibly modified according to meta_args and `meta`)
		'''
		
		script_fn = script_info.fn
		
		if script_info.use_config:
			return script_fn(config)
		return autofill_args(script_fn, config)
		

class Meta_Arg_Registry(Registry):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		
		self._bycode = {} # simple dict to sort meta args by code
		
	def new(self, arg):
		name = arg.get_name()
		code = arg.get_code()
		if code in self._bycode:
			prt.warning(f'A meta arg with code {code} already exists ({self._bycode[code].get_name()}, '
			            f'now {name} is default')
		
		if code is not None:
			self._bycode[code] = arg
		
		super().new(name, arg)

	def find_code(self, code):
		return self._bycode.get(code, None)

meta_arg_registry = Meta_Arg_Registry()

class Meta_Argument: # TODO: possibly upgrade to a Customizable_Infomation subclass ?
	'''
	Subclasses are not usually instantiated (so everything should be
	'''
	name = None
	code = None
	priority = 0
	num_params = 0
	
	def __init_subclass__(cls, name=None, code=None, priority=0, num_params=0):
		
		cls.name = name
		cls.code = code
		cls.priority = priority
		cls.num_params = num_params
		
		if name is None:
			prt.error(f'This meta argument does not have a name, so it cant be used in a Run Mode')
		else:
			meta_arg_registry.new(cls)
	
	def __init__(self, meta, config):
		pass
	
	@classmethod
	def get_name(cls):
		return cls.name
	
	@classmethod
	def get_code(cls):
		return cls.code
	
	@classmethod
	def get_priority(cls):
		return cls.priority
	
	@classmethod
	def get_num_params(cls):
		return cls.num_params
	
	def __str__(self):
		return self.get_name()
	
	def __repr__(self):
		return f'MetaArg:{self.get_name()}'
	
	def run(self, meta, config):
		return meta, config
	
_help_msg = '''fig -[meta-args...] <script> [configs...] --[args...]
Please specify a script (and optionally meta-args/args)'''


_help_script_msg = '''fig -[meta-args...] {} [configs...] --[args...]
Script documentation:
{}'''

_help_script_sig_msg = '''fig -[meta-args...] {} [configs...] --[args...]
Signature: {}
Script documentation:
{}'''

class Help_Arg(Meta_Argument, name='help', code='h'):
	
	def __init__(self, meta, config):
		super().__init__(meta, config)
		
		hlp = meta.pull('help', False)
		sname = meta.pull('script_name', None)
		
		if hlp:
			if sname is None:
				sinfo = get_script(sname)
				if sinfo.use_config:
					print(_help_script_msg.format(sname, sinfo.fn.__doc__))
				else:
					print(_help_script_sig_msg.format(sname, str(inspect.signature(sinfo.fn)), sinfo.fn.__doc__))
			else:
				print(_help_msg)
			quit()
