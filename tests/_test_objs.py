import omnifig as fig



@fig.component('c1')
class C1:
	def __init__(self, A):

		self.a2 = A.pull('a2')
		self.a10_0 = A.pull('a10.0')
		self.a4_a6 = A.pull('a4.a6')
		self.a14 = A.pull('a12.a13')
		self.a14b = A.pull('a12.a15')

		self.x = A.pull('mn', None)

		self.a = A.pull('a11')

	def f(self, x):
		return self.a + x

	def m(self):
		return self.x


@fig.autocomponent('c2')
class C2:
	def __init__(self, a1, a2, a3, b2=16):
		
		self.a1 = a1
		self.a2 = a2
		self.a3 = a3
		
		self.b2 = b2


@fig.modifier('m1')
class M1:
	def __init__(self, A):
		super().__init__(A)

		self.b = A.pull('a4.a6') + self.a
		self.a = A.pull('a10.1')

	def h(self):
		return self.a + self.b

	def g(self, y):
		return self.a - y

@fig.modifier('m2')
class M2:
	def __init__(self, A):
		super().__init__(A)

		self.a = A.pull('a8.a9') + self.a
		
	def g(self, y):
		return self.a * y

