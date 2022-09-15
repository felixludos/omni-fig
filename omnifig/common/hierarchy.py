from typing import Any, Dict, List, Optional, Tuple, Union
from omnibelt import InitWall, unspecified_argument

class Configurable:
	'''
	Removes the config object `A` from the __init__() to clean up the init stream.
	
	This class should be subclassed when creating components/modifiers,
	especially when those components/modifiers also subclass types that
	do not use the config object.
	'''
	def __init__(self, A, _req_args=unspecified_argument,
	             _req_kwargs=unspecified_argument, **kwargs):

		if _req_args is unspecified_argument:
			_req_args = A.pull('_req_args', (), silent=True)
		if _req_kwargs is unspecified_argument:
			_req_kwargs = A.pull('_req_kwargs', {}, silent=True)

		# if _req_kwargs is None:
		# 	_req_kwargs = kwargs

		try:
			walled = isinstance(self, InitWall)
		except ValueError:
			walled = True
			
		if walled:
			super().__init__(_req_args=_req_args, _req_kwargs=_req_kwargs, **kwargs)
		else:
			kwargs.update(_req_kwargs)
			super().__init__(**kwargs)
			# super().__init__(*_req_args, **_req_kwargs)

from ..config import Config


class Creator:

	pass


class Configurable:
	_my_config = None

	@property
	def my_config(self):
		return self._my_config


	@classmethod
	def create_from_config(cls, config: Config,
	                       args: Optional[Tuple[...]] = None, kwargs: Optional[Dict[str, Any]] = None,
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



class AutoConfiguarable(Configurable):

	pass


