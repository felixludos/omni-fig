import util

import omnifig as fig

fig._loaded_p3_script2 = 1 + getattr(fig, '_loaded_p3_script2', 0)


@fig.component('p3a-cmp1')
class P3aC1(fig.Configurable):
	def __init__(self, a=-15):
		self.a = a
