from typing import Any, Dict, List, Optional, Tuple, Union, Type, Sequence, Callable
import inspect
from omnibelt import dynamic_capture, extract_function_signature, Modifiable

from .abstract import AbstractConfig, AbstractConfigurable, AbstractCertifiable



class Configurable(AbstractConfigurable, Modifiable):
	'''
	Mix-in class for objects that can be constructed with a config object.

	It is strongly recommended that components and modifiers inherit from this class
	to seamlessly fill in missing arguments with the config object.
	'''
	_my_config = None
	# @property
	# def my_config(self) -> AbstractConfig:
	# 	'''The config object that this object is associated with'''
	# 	return getattr(self, '_my_config', None)


	# @classmethod
	# def inject_mods(cls, *mods, name=None):
	# 	'''
	# 	Mods should be types that are used to modify the cls. The order of the mods corresponds to the order
	# 	in which the cls is "modified", so for example:
	#
	# 	```python
	#
	# 	class A(Configurable): pass
	# 	class B: pass
	# 	class C: pass
	#
	# 	out = A.inject_mods(C, B)
	# 	assert out.mro() == [out, C, B, A, Modifiable, object]
	# 	assert out.__name__ == 'C_B_A' # default name
	# 	```
	# 	'''
	# 	return super().inject_mods(*reversed(mods), name=name)


	class _config_builder_type:
		'''Replaces the regular method and fills in the missing arguments from the config'''
		def __init__(self, product: 'Configurable', config: AbstractConfig, *, silent: Optional[bool] = None):
			self.product = product
			self.config = config
			self.silent = silent


		@staticmethod
		def configurable_parents(cls: Type) -> List[Type['Configurable']]:
			'''Returns a list of all the parent classes that are Configurable'''
			return [c for c in cls.mro() if issubclass(c, Configurable) and c is not Configurable]


		class MissingConfigError(Exception):
			'''Raised when a method is missing arguments from the config'''
			def __init__(self, product: Any, missing: List[inspect.Parameter], config: Optional[AbstractConfig] = None,
			             msg: Optional[str] = None):
				config_key = ''
				if config is not None:
					trace = config.trace
					if trace is not None:
						config_key = f'<{config.reporter.get_key(trace)}> '
				missing = [repr(p.name) for p in missing]
				if msg is None:
					s = 's' if len(missing) > 1 else ''
					msg = f'{config_key}{product.__name__} is missing {len(missing)} arg{s}: {", ".join(missing)}'
				super().__init__(msg)
				self.product = product
				self.missing = missing
				self.config = config


		def find_missing_arg(self, name: str, default: Optional[Any] = inspect.Parameter.empty) -> Any:
			'''
			Finds the missing argument in the config (including aliases)

			Args:
				name: Name of the argument
				default: Default specified in the method signature

			Returns:
				The value of the argument from the config

			'''
			if default is inspect.Parameter.empty:
				default = self.config._empty_default
			aliases = self.aliases.get(name, ())
			silent = self.silent
			if self.silences is not None and name in self.silences:
				silent = True
			out = self.config.pulls(name, *aliases, default=default, silent=silent)
			return out


		def fix_args(self, method: Callable, obj: Any, args: Tuple, kwargs: Dict[str, Any]) \
				-> Tuple[Tuple, Dict[str, Any]]:
			'''
			Fills in the missing arguments from the config given the method signature

			Args:
				method: Method to fill in the arguments for
				obj: Object that the method is being called on
				args: Manually specified arguments
				kwargs: Manually specified keyword arguments

			Returns:
				The arguments and keyword arguments filled in from the config and the manually specified ones

			'''
			fixed_args, fixed_kwargs, missing = extract_function_signature(method, (obj, *args), kwargs,
			                                                               default_fn=self.find_missing_arg,
			                                                               include_missing=True)
			if len(missing):
				raise self.MissingConfigError(type(obj), missing, config=self.config)
			return fixed_args, fixed_kwargs


		def fixer(self, owner: Type, method: Callable, obj: Any, args: Tuple, kwargs: Dict[str, Any]) -> Any:
			'''
			Called by the capture to replace the original method call

			See ``omnibelt.tricks.dynamic_capture`` for more details.

			Args:
				owner: Class where the method is defined
				method: Method to call
				obj: Owner object (self in the method)
				args: Manually specified arguments
				kwargs: Manually specified keyword arguments

			Returns:
				The return value of the method

			'''
			self.aliases = getattr(method, '_my_config_aliases', {})
			self.silences = getattr(method, '_my_silent_config', None)

			fixed_args, fixed_kwargs = self.fix_args(method, obj, args, kwargs)
			return method(*fixed_args, **fixed_kwargs)


		def build(self, *args, **kwargs):

			init_capture = dynamic_capture(self.configurable_parents(self.product), self.fixer, '__init__').activate()

			self.product._my_config = self.config

			obj = self.product(*args, **kwargs)

			del self.product._my_config
			obj._my_config = self.config

			init_capture.deactivate()
			return obj


	@classmethod
	def _config_builder(cls, config, silent=None):
		return cls._config_builder_type(cls, config, silent=silent)


	@classmethod
	def init_from_config(cls, config: AbstractConfig,
	                     args: Optional[Tuple] = None, kwargs: Optional[Dict[str, Any]] = None, *,
	                     silent: Optional[bool] = None) -> Any:
		'''
		Constructor to initialize a class informed by the config object `config`. This will run the usual constructor
		``__init__``, except any arguments that are missing from the signature will be filled in from the config.

		Args:
			config: Config object to use
			args: Manually specified arguments
			kwargs: Manually specified keyword arguments
			silent: If True, no messages are reported when querying the config object.

		Returns:
			The initialized object

		'''
		if args is None:
			args = ()
		if kwargs is None:
			kwargs = {}
		return cls._config_builder(config, silent=silent).build(*args, **kwargs)



class Certifiable(Configurable, AbstractCertifiable):
	'''
	Simple mix-in to make the initialization of classes through the config a two-stage process.
	The first stage calls the ``__init__`` method, and then after that is complete, the ``__certify__`` method
	is called, which can return a new object to replace the original one.

	Note, that ``__certify__`` is only called if the object is initialized through the config (e.g. through ``pull()``).
	'''
	def __certify__(self, config: AbstractConfig, **kwargs):
		return self



class silent_config_args:
	'''Decorator to silence the config when extracting arguments from the config'''
	def __init__(self, *args: str):
		self.args = args


	def __call__(self, fn: Callable) -> Callable:
		if not hasattr(fn, '_my_silent_config'):
			setattr(fn, '_my_silent_config', set())
		fn._my_silent_config.update(self.args)
		return fn



class config_aliases:
	'''Method decorator to add aliases to the config arguments of a method'''
	def __init__(self, **aliases: Union[Sequence[str], str]):
		'''
		Config aliases to store for the method

		Args:
			**aliases: Mapping of aliases: keys should be the name of the argument in the method signature,
			and the values should be the name of the argument to query in the config object.
		'''
		self.aliases = aliases


	def __call__(self, fn: Callable) -> Callable:
		'''Decorator to add aliases to the config arguments of a method'''
		if not hasattr(fn, '_my_config_aliases'):
			setattr(fn, '_my_config_aliases', {})
		fn._my_config_aliases.update({key: ((val,) if isinstance(val, str) else tuple(val))
		                              for key, val in self.aliases.items()})
		return fn




