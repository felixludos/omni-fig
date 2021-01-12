
from omnibelt import InitWall

class Configurable:
	def __init__(self, A, _req_kwargs={}, **kwargs):
		_req_kwargs = A.pull('_req_kwargs', _req_kwargs, silent=True)
		if isinstance(self, InitWall):
			super().__init__(_req_kwargs=_req_kwargs, **kwargs)
		else:
			super().__init__(**_req_kwargs)
		
