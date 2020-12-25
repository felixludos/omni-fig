


class Configurable:
	def __init__(self, A, _req_kwargs={}, **kwargs):
		only_req = A.pull('only-req', True, silent=True)
		if only_req:
			super().__init__(**_req_kwargs)
		else:
			super().__init__(**kwargs)
		
