
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

		try:
			walled = isinstance(self, InitWall)
		except ValueError:
			walled = True
			
		if walled:
			super().__init__(_req_args=_req_args, _req_kwargs=_req_kwargs, **kwargs)
		else:
			super().__init__(*_req_args, **_req_kwargs)
