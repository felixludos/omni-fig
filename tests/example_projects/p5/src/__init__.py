import omnifig as fig



@fig.component('cmp5')
class P5C5(fig.Configurable):
	def __init__(self, a, b=100, c=3):
		self.a = a
		self.b = b
		self.c = c



@fig.component('cmp3')
class P5C3(fig.Configurable):
	pass