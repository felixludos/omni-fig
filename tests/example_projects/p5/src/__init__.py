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



@fig.creator('super-creator', description='this is a super creator')
class super_creator(fig.Configurable):
	def __init__(self, a, b=100, c=3):
		self.a = a
		self.b = b
		self.c = c

@fig.component('the-component', description='this is a component', creator='super-creator')
class the_component(fig.Configurable):
	pass


@fig.script('add-1', description='add 1 to a number')
def add_1(config, a=None, b=1):
	if a is None:
		a = config.pull('a', 0)
	return a + b


