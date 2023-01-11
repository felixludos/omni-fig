import omnifig as fig


@fig.component('cmp1', description='dont use this')
class Cmpn1(fig.Configurable):
	def __init__(self, a, b=2, c=3):
		self.a = a
		self.b = b
		self.c = c

@fig.component('cmp2', description='maybe use this one')
class Cmpn2(fig.Configurable):
	@fig.config_aliases(a=['e', 'f'], b='d')
	def __init__(self, a, b=2, c=3):
		self.a = a
		self.b = b
		self.c = c

@fig.component('cmp3', description='what is this')
class Cmpn3(Cmpn1):
	@fig.config_aliases(c='e')
	def __init__(self, a, b=2, c=3):
		super().__init__(a, b, c)

@fig.component('cmp4')
class Cmpn4(Cmpn1):
	def __init__(self, e=5):
		super().__init__(c=e)



@fig.modifier('mod1', description='mods are pretty cool')
class Mod1(fig.Configurable):
	def __init__(self, a, c=5, **kwargs):
		super().__init__(a, c=c, **kwargs)

@fig.modifier('mod2')
class Mod2(fig.Configurable):
	def __init__(self):
		super().__init__(b=10)

@fig.modifier('mod3')
class Mod3(Mod1):
	@fig.config_aliases(a=['c'])
	def __init__(self, a=1):
		super().__init__(a=a, b=10)


