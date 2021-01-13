
from omnibelt import InitWall, unspecified_argument

class Configurable:
	def __init__(self, A, _req_args=unspecified_argument,
	             _req_kwargs=unspecified_argument, **kwargs):

		if _req_args is unspecified_argument:
			_req_args = A.pull('_req_args', (), silent=True)
		if _req_kwargs is unspecified_argument:
			_req_kwargs = A.pull('_req_kwargs', {}, silent=True)

		if isinstance(self, InitWall):
			super().__init__(_req_args=_req_args, _req_kwargs=_req_kwargs, **kwargs)
		else:
			super().__init__(*_req_args, **_req_kwargs)
		
