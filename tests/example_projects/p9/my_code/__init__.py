import omnifig as fig


@fig.script('cfg', description='returns and prints config')
def cfg_script(config):
	print(config.to_yaml())
	return config



@fig.component('cmp1', description='dont use this')
class Cmpn1(fig.Configurable):
	def __init__(self, a, b=2, c=3):
		self.a = a
		self.b = b
		self.c = c

@fig.component('cmp2', description='maybe use this one')
class Cmpn2(fig.Configurable):
	@fig.config_aliases(a=['e', 'f'], b='d')
	def __init__(self, a, b=20, c=30):
		self.a = a
		self.b = b
		self.c = c

@fig.component('cmp3', description='what is this')
class Cmpn3(Cmpn1):
	@fig.config_aliases(c='e')
	def __init__(self, a, b=-2, c=-3):
		super().__init__(a, b, c)

@fig.component('cmp4')
class Cmpn4(Cmpn1):
	def __init__(self, e=5):
		super().__init__(c=e)

@fig.component('cmp5')
class Cmpn5:
	def __init__(self, config, **kwargs):
		super().__init__(**kwargs)
		self.x = config.pull('x', 1)



@fig.modifier('mod1')
class Mod1(fig.Configurable):
	def __init__(self, a, b=None, c=5, **kwargs):
		if b is None:
			b = 99
		super().__init__(a, b=b, c=c, **kwargs)

@fig.modifier('mod2')
class Mod2(fig.Configurable):
	def __init__(self, a=-22, b=None, **kwargs):
		super().__init__(b=8, a=a, **kwargs)

@fig.modifier('mod3')
class Mod3(Mod1):
	@fig.config_aliases(a=['c'])
	def __init__(self, a=-88, b=None, **kwargs):
		super().__init__(a=a, b=10, **kwargs)


@fig.modifier('mod4')
class Mod4:
	def __init__(self, config, a=None, b='b', **kwargs):
		super().__init__(config, **kwargs)
		self.a = config.pull('a', a)
		self.b = config.pulls('b', 'bb', default=b)

@fig.modifier('mod5')
class Mod5:
	def __init__(self, config, **kwargs):
		super().__init__(config, **kwargs)
		self.b = config.pull('b', 'b')


@fig.modifier('mod6')
class Mod5(Mod4):
	def __init__(self, config, **kwargs):
		super().__init__(config, **kwargs)
		self.b = config.pull('b', 'b')





