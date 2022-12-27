import omnifig as fig

fig._loaded_p3_util = 1 + getattr(fig, '_loaded_p3_util', 0)


@fig.component('p3util')
class UtilComponent:
	def __init__(self, A, **kwargs):
		self.A = A
		self.kwargs = kwargs

