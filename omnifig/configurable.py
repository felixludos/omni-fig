from typing import Any, Dict, List, Optional, Tuple, Union, Type, Sequence, Callable
from omnibelt import auto_init
import inspect

from .abstract import AbstractConfig, AbstractConfigurable



class Configurable(AbstractConfigurable, auto_init):
	_my_config = None

	@property
	def my_config(self) -> AbstractConfig:
		return self._my_config

	class _auto_method_arg_fixer(auto_init._auto_method_arg_fixer):
		def __init__(self, method: Callable, src: Type['Configurable'], obj: 'Configurable', **kwargs):
			super().__init__(method=method, src=src, obj=obj, **kwargs)
			self.config = obj.my_config
			self.aliases = getattr(method, '_my_config_aliases', {})

		def __call__(self, key: str, default: Optional[Any] = inspect.Parameter.empty) -> Any:
			if self.config is None:
				return super().__call__(key, default=default)
			if default is inspect.Parameter.empty:
				default = self.config.empty_default
			aliases = self.aliases.get(key, ())
			return self.config.pulls(key, *aliases, default=default)

	@classmethod
	def init_from_config(cls, config: AbstractConfig,
	                     args: Optional[Tuple] = None, kwargs: Optional[Dict[str, Any]] = None, *,
	                     silent: Optional[bool] = None):
		if args is None:
			args = ()
		if kwargs is None:
			kwargs = {}
		cls._my_config = config
		with config.silence(silent):
			obj = cls(*args, **kwargs)
		del cls._my_config
		obj._my_config = config
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



