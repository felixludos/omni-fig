from typing import Any, Dict, List, Optional, Tuple, Union, Type, Sequence, Callable
from omnibelt import auto_init, dynamic_capture, extract_function_signature
from contextlib import nullcontext
import sys
import traceback
import inspect

from .abstract import AbstractConfig, AbstractConfigurable


class Configurable(AbstractConfigurable):
	_my_config = None
	@property
	def my_config(self) -> AbstractConfig:
		return getattr(self, '_my_config', None)


	class _fill_config_args:
		def __init__(self, config, *, silent=None):
			self.config = config
			# self.args = args
			# self.kwargs = kwargs
			self.silent = silent

		@staticmethod
		def configurable_parents(cls) -> List[Type['Configurable']]:
			return [c for c in cls.mro() if issubclass(c, Configurable) and c is not Configurable]

		class MissingConfigError(Exception):
			def __init__(self, product, missing, config=None, msg=None):
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

		def find_missing_arg(self, name, default=inspect.Parameter.empty):
			if default is inspect.Parameter.empty:
				default = self.config.empty_default
			aliases = self.aliases.get(name, ())
			return self.config.pulls(name, *aliases, default=default)

		def fix_args(self, method, obj, args, kwargs):
			fixed_args, fixed_kwargs, missing = extract_function_signature(method, (obj, *args), kwargs,
			                                                               default_fn=self.find_missing_arg,
			                                                               include_missing=True)
			if len(missing):
				raise self.MissingConfigError(type(obj), missing, config=self.config)
			return fixed_args, fixed_kwargs


		def __call__(self, owner, method, obj, args, kwargs):
			obj._my_config = self.config
			self.aliases = getattr(method, '_my_config_aliases', {})

			fixed_args, fixed_kwargs = self.fix_args(method, obj, args, kwargs)
			return method(*fixed_args, **fixed_kwargs)


	@classmethod
	def init_from_config(cls, config: AbstractConfig,
	                     args: Optional[Tuple] = None, kwargs: Optional[Dict[str, Any]] = None, *,
	                     silent: Optional[bool] = None):
		if args is None:
			args = ()
		if kwargs is None:
			kwargs = {}



		init_capture = dynamic_capture(cls._fill_config_args.configurable_parents(cls),
		                               cls._fill_config_args(config, silent=silent), '__init__').activate()

		obj = cls(*args, **kwargs)

		init_capture.deactivate()
		return obj




class config_aliases: # methods decorator
	def __init__(self, **aliases: Union[Sequence[str], str]):
		self.aliases = aliases

	def __call__(self, fn: Callable):
		if not hasattr(fn, '_my_config_aliases'):
			setattr(fn, '_my_config_aliases', {})
		fn._my_config_aliases.update({key: ((val,) if isinstance(val, str) else tuple(val))
		                              for key, val in self.aliases.items()})
		return fn







################################################# old


# class Auto_Configurable(AbstractConfigurable, auto_init):
# 	_my_config = None
#
# 	@property
# 	def my_config(self) -> AbstractConfig:
# 		return getattr(self, '_my_config', None)
#
# 	class MissingConfigError(Exception):
# 		def __init__(self, product, missing, config=None, msg=None):
# 			config_key = ''
# 			if config is not None:
# 				trace = config.trace
# 				if trace is not None:
# 					config_key = f'{config.reporter.get_key(trace)}: '
# 			missing = [repr(p.name) for p in missing]
# 			if msg is None:
# 				msg = f'{config_key}{product.__name__} is missing {", ".join(missing)}'
# 			super().__init__(msg)
# 			self.product = product
# 			self.missing = missing
# 			self.config = config
#
# 	def _fix_missing_args(self, missing: List[inspect.Parameter], src: Type, method: Callable,
# 	                      args: Tuple, kwargs: Dict[str, Any]):
# 		raise self.MissingConfigError(type(self), missing, self.my_config)
#
# 	class _auto_method_arg_fixer(auto_init._auto_method_arg_fixer):
# 		def __init__(self, method: Callable, src: Type['Configurable'], obj: 'Configurable', **kwargs):
# 			super().__init__(method=method, src=src, obj=obj, **kwargs)
# 			self.config = obj.my_config
# 			self.aliases = getattr(method, '_my_config_aliases', {})
#
# 		def __call__(self, key: str, default: Optional[Any] = inspect.Parameter.empty) -> Any:
# 			if self.config is None:
# 				return super().__call__(key, default=default)
# 			if default is inspect.Parameter.empty:
# 				default = self.config.empty_default
# 			aliases = self.aliases.get(key, ())
# 			return self.config.pulls(key, *aliases, default=default)
#
# 	@classmethod
# 	def init_from_config(cls, config: AbstractConfig,
# 	                     args: Optional[Tuple] = None, kwargs: Optional[Dict[str, Any]] = None, *,
# 	                     silent: Optional[bool] = None):
# 		if args is None:
# 			args = ()
# 		if kwargs is None:
# 			kwargs = {}
# 		cls._my_config = config
# 		with config.silence(silent):
# 			obj = cls(*args, **kwargs)
# 		del cls._my_config
# 		obj._my_config = config
# 		return obj




# class OldConfigurable:
# 	'''
# 	Removes the config object `A` from the __init__() to clean up the init stream.
#
# 	This class should be subclassed when creating components/modifiers,
# 	especially when those components/modifiers also subclass types that
# 	do not use the config object.
# 	'''
# 	def __init__(self, A, _req_args=unspecified_argument,
# 	             _req_kwargs=unspecified_argument, **kwargs):
#
# 		if _req_args is unspecified_argument:
# 			_req_args = A.pull('_req_args', (), silent=True)
# 		if _req_kwargs is unspecified_argument:
# 			_req_kwargs = A.pull('_req_kwargs', {}, silent=True)
#
# 		# if _req_kwargs is None:
# 		# 	_req_kwargs = kwargs
#
# 		try:
# 			walled = isinstance(self, InitWall)
# 		except ValueError:
# 			walled = True
#
# 		if walled:
# 			super().__init__(_req_args=_req_args, _req_kwargs=_req_kwargs, **kwargs)
# 		else:
# 			kwargs.update(_req_kwargs)
# 			super().__init__(**kwargs)
# 			# super().__init__(*_req_args, **_req_kwargs)



