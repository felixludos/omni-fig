import util
import pandas

import omnifig as fig

fig._loaded_p3_script = 1 + getattr(fig, '_loaded_p3_script', 0)


@fig.component('cmp1')
class P3C1(fig.Configurable):
	def __init__(self, a='project3'):
		self.a = a
