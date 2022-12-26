
import omnifig as fig

@fig.Component('cmp1')
class Cmpn1:
	def __init__(self, A):
		self.a = A.pull('simple')
		self.b = A.pull('default', 'worked')
		self.c = A.pull('not_there', '<>alias_option')
		self.d = A.pull('n1', '<>n2', True)

		self.e = A.pull('unseen', silent=True)
		
@fig.AutoModifier('mod1')
class Modded:
	def __init__(self, A):
		
		pass


