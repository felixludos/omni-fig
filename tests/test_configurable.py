import omnifig as fig
from _test_util import reset_profile



def test_configurable1():
	reset_profile()
	fig.initialize('example9')


	cfg = fig.create_config('c1', a=20)

	obj = cfg.pull('o1')
	assert isinstance(obj, fig.Configurable)
	assert type(obj).__name__ == 'Cmpn1'
	assert obj.a == 20
	assert obj.b == 2

	cfg = fig.create_config('c1')

	obj = cfg.pull('o1')
	assert isinstance(obj, fig.Configurable)
	assert type(obj).__name__ == 'Cmpn1'
	assert obj.a == 10
	assert obj.b == 2



def test_configurable2():
	reset_profile()
	fig.initialize('example9')

	C = fig.create_config('c2')

	obj = C.pull('obj1')
	assert isinstance(obj, fig.Configurable)
	assert type(obj).__name__ == 'Cmpn3'
	assert obj.a == -1
	assert obj.b == -2
	assert obj.c == 5

	obj = C.pull('obj2')
	assert isinstance(obj, fig.Configurable)
	assert type(obj).__name__ == 'Cmpn3'
	assert obj.a == -1
	assert obj.b == 100
	assert obj.c == 4

	obj = C.peek('obj3').process(a=-100)
	assert isinstance(obj, fig.Configurable)
	assert type(obj).__name__ == 'Cmpn3'
	assert obj.a == -100
	assert obj.b == -2
	assert obj.c == -3

	obj = C.pull('obj4')
	assert isinstance(obj, fig.Configurable)
	assert type(obj).__name__ == 'Cmpn2'
	assert obj.a == 0
	assert obj.b == 20
	assert obj.c == 30



def test_mod_configurable():
	reset_profile()
	fig.initialize('example9')

	C = fig.create_config('c3')

	obj = C.peek_process('obj1', None, -2)
	assert isinstance(obj, fig.Configurable)
	assert type(obj).__name__ == 'Mod1_Cmpn1'
	assert obj.a == -2
	assert obj.b == 99
	assert obj.c == 5

	obj = C.pull('obj2')
	assert isinstance(obj, fig.Configurable)
	assert type(obj).__name__ == 'Mod3_Cmpn1'
	assert obj.a == 9
	assert obj.b == 10
	assert obj.c == 9

	obj = C.pull('obj3')
	assert isinstance(obj, fig.Configurable)
	assert type(obj).__name__ == 'Mod3_Cmpn1'
	assert obj.a == -88
	assert obj.b == 10
	assert obj.c == 5

	obj = C.pull('obj4')
	assert isinstance(obj, fig.Configurable)
	assert type(obj).__name__ == 'Mod2_Mod3_Cmpn1'
	assert obj.a == -22
	assert obj.b == 10
	assert obj.c == 5

	obj = C.pull('obj5')
	assert isinstance(obj, fig.Configurable)
	assert type(obj).__name__ == 'Mod3_Mod2_Cmpn1'
	assert obj.a == -88
	assert obj.b == 8
	assert obj.c == 5



def test_key_error():
	@fig.component('something')
	class Something(fig.Configurable):
		def __init__(self, a=1, b={}):
			self.a = a
			self.b = b
			print(b['nonexistent'])

	cfg = fig.create_config(_type='something')

	try:
		cfg.create()
	except KeyError as e:
		assert e.args[0] == 'nonexistent'
	else:
		assert False, 'KeyError not raised'



def test_nested_configurable():
	@fig.component('parent')
	class Parent(fig.Configurable):
		def __init__(self, a: int = 10, b: int = 1):
			self.a = a
			self.b = b

	@fig.component('child1')
	class Child1(Parent):
		def __init__(self, sibling: 'Child2' = None, a: int = -10, b: str = 'hello'):
			super().__init__(a=a)
			self.sibling = sibling
			self.b = b

	@fig.component('child2')
	class Child2(Parent):
		def __init__(self, a: int = -1, c: str = 'other'):
			super().__init__(a=a)
			self.c = c

	cfg = fig.create_config(**{'_type': 'child1', 'a': 5,
							   'sibling._type': 'child2', 'sibling.a': 2, 'sibling.c': 3})

	obj = cfg.create()

	assert obj.a == 5
	assert obj.sibling.a == 2

	assert obj.b == 'hello'
	assert obj.sibling.b == 1

	assert obj.sibling.c == 3





