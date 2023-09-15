import sys, os, shutil
from omnibelt import load_export

import _test_util as tu

import omnifig as fig
# from omnifig.config import EmptyElement, ConfigType

import _test_objs
# NOTE: due to the registration when this gets imported (and the profile getting resetted in the other test scripts),
# this test must be run before any other

def test_create_obj():
	A = fig.create_config()
	A.push('a.b.c', 10)

	assert A.pull('a.b.c') == 10
	assert str(A) == 'a:\n  b: {c: 10}\n'

def test_register_load_config():
	fig.get_current_project().register_config_dir(tu.CONFIG_PATH, recursive=True)

	C = fig.create_config('test1')
	assert C.pull('arg1') == 'test'
	
	C = fig.create_config('t/h/e')
	assert C.pull('nothing') == 'special'


def test_hierarchy():
	A = fig.create_config('test2', abc=10.0)
	
	assert A.pull('a.b') == 'inside'
	assert A.pull('abc') == 10.0
	assert 'a123' not in A
	assert A.pull('fruit')[0] == 'apples'
	assert A.pull('fruit')[1] == 'bananas'
	assert 'arg1' not in A
	
	
	B = fig.create_config('test1', 'test2')
	
	assert B.pull('a.b') == 10
	assert 'a123' in B
	assert B.pull('fruit')[0] == 'tomato'
	assert B.pull('fruit')[1] == 'bananas'
	assert B.pull('arg1') == 'test'
	
	
	C = fig.parse_argv(['test1', 'test2', '--x', '''{"r":10, "z":100}''',
	                   '--arg1', 'xx',
	                   '--a.b', '11'], script_name=None)
	
	assert C.pull('a.b') == 11
	assert len(C.pull('x')) == 3
	assert C.pull('x.r') == 10
	assert C.pull('x.y') == 'hello'
	assert C.pull('x.z') == 100
	assert C.pull('arg1') == 'xx'
	
	
	D = fig.create_config('test2', fruit=["strawberries"])
	
	assert len(D.pull('fruit')) == 3
	assert D.pull('fruit')[0] == 'strawberries'
	assert D.pull('fruit')[-1] == 'peaches'


def test_deep_hierarchy():

	A = fig.create_config('test3')
	
	assert A.pull('tree') == 'nodes'
	
	assert A.pull('all')[0] == 0
	print(A.cro)
	print(type(A.cro))
	assert A.cro[0] == 'test3'
	
	order = tuple(A.cro[1:])
	assert order == ('t/n0', 't/n1', 't/n3', 't/n5', 't/n2', 't/n4', 't/n6', 't/n7')


def test_pull_simple():
	
	A = fig.create_config('test2', **{'roman.greek': 'linguistics'})
	
	assert A.pull('roman.greek') == 'linguistics'
	
	assert A.pull('simple') == 'p'
	
	assert A.pull('default', 'worked') == 'worked'
	
	assert A.pulls('not_there', 'try_again', 'alias_option') == 'found'
	
	assert A.pulls('n1', 'n2', default=2.5) == 2.5
	
	assert A.pull('unseen', silent=True) == 45

	assert A.pull('a.b') == 'inside'

	assert A.pull('x.y') == 'hello'

	a = A.peeks('x.list', 'x')
	a = a.peek('z').pull()
	assert len(a) == 2 and a[0] == 1 and a[1] == 2
	
	a = A.pulls('veggies', 'fruit')
	assert len(a) == 3 and a[0] == 'apples'
	assert type(a) == list
	
	a = A.pull('others')
	assert type(a) == list and len(a) == 3 and a[2]['not']['mickey'] == 'mouse'
	
	a = A.pull('costs')
	assert type(a) == dict and len(a) == 5 and 'rubies' in a['gems'] and a['steel'] > 1000
	
	assert A.pulls('others.2.not.mickey') == 'mouse'
	assert A.pulls('others.3', 'others.1') == 'jerry'
	assert A.pulls('others.2.not.goofy', 'fruit.0.apples', 'others.2.not')['mickey'] == 'mouse'
	
	
def test_sub():
	
	A = fig.create_config('test1')
	
	# making subs
	D = A.peek('deep')
	
	assert D.pull('x1') == 10
	assert D.pull('fruit')[0] == 'tomato'
	assert D.pull('x2.a') == 1.2
	assert D.pull('plus1') == 10
	assert D.pull('arg1') == 'test'
	
	# sub past a list
	B = A.peek('deep.qwerty.1.t')
	
	assert B.pull('d') == 2
	assert B.pull('check.1.H') == 'asdf'
	assert B.pull('x5') == 10
	assert B.pull('2.for.q')
	# assert B.pull('check.2.for.q')
	assert B.pull('difficult') == 'good'
	
	
def test_push1():
	
	A = fig.create_config('test1')
	
	assert A.pull('arg1') == 'test'
	
	a = A.push_pull('arg1', 'another')
	assert a == 'another'
	
	assert A.pull('arg1') == 'another'
	
	a = A.push_pull('a.d', 'one')
	assert a == 'one'
	assert A.pull('a.d') == 'one'
	
	a = A.push_pull('a.c.c', 123)
	assert a == 123
	assert A.pull('a.c.c') == 123


def test_push2():
	A = fig.create_config('test1')
	
	assert A.pull('fruit.0') == 'tomato'
	
	a = A.pull('fruit')
	assert len(a) == 1 and a[0] == 'tomato'
	a = A.push_pull('new_fruit', a)
	assert len(a) == 1 and a[0] == 'tomato'
	
	a = A.push_pull('new_fruit', 'no')
	assert a == 'no'
	assert A.pull('new_fruit.0', 'failed') == 'failed'
	assert A.pull('new_fruit') == 'no'
	
	assert A.pull('a.b', 10)
	a = A.push_pull('a.b', 11)
	assert a == 11
	assert A.pull('a.b') == 11
	# a = A.push('a.b.c', 0.25)
	# assert a == 0.25
	# assert A.pull('a.b')['c'] == 0.25
	
	a = A.push_pull('a123', 'removed')
	assert a == 'removed'
	
	a = A.push_pull('new', [1,2,4])
	assert a[-1] == 4
	assert A.pull('new.0') == 1
	
	a = A.push_pull('nd', ['no', {'k':[0]}])
	assert a[0] == 'no'
	assert 'k' in a[1]
	a = A.pull('nd')
	assert len(a) == 2 and a[0] == 'no' and a[1]['k'][0] == 0
	assert A.pull('nd.0') == 'no'
	assert A.pull('nd.o', 'w') == 'w'
	assert A.pulls('nd.1.j', 'nd.0') == 'no'
	assert A.pulls('deep.x1.qwer.asdf', 'nd.1.k.0') == 0


def test_push3():
	A = fig.create_config('test1')
	
	# child pushes
	a = A.push_pull('arg2.a.b', [-1,10])
	assert a[0] == -1
	assert A.pull('arg2.a')['b'][1] == 10
	assert A.pull('arg2.a.b.1') == 10
	
	# when parent exists
	a = A.push_pull('deep.unknown', 'gooder')
	assert a == 'gooder'
	assert A.pull('unknown') == 'bad'
	assert A.pull('deep.qwerty.1.t.unknown') == 'good'
	assert A.pull('deep.unknown') == 'gooder'
	
	# push to list (append and indexed)
	a = A.push_pull('fruit.1', 'yummy')
	assert a == 'yummy'
	assert A.pull('fruit.1') == 'yummy'
	a = A.push_pull('fruit.2', 'blueberry')
	assert a == 'blueberry'
	assert len(A.pull('fruit')) == 3
	assert A.pull('fruit.2') == 'blueberry'
	
	a = A.push_pull('fruit.10', 'veggies')
	assert a == 'veggies'
	assert A.pull('fruit.3') == A.empty_value
	assert A.pull('fruit.7') == A.empty_value
	assert A.pull('fruit.10') == 'veggies'
	assert A.pull('fruit.11', 'nope') == 'nope'
	assert A.pull('fruit.20', 'no way') == 'no way'


def test_push4():
	A = fig.create_config('test1')
	
	a = A.push_pull('test', 'not me')
	assert a == 'not me'
	assert A.pull('deep.x1') == 10
	assert A.pull('deep')['x1'] == 10
	
	a = A.push_pull('deep.qwerty.0', {'x1': 11})
	assert a['x1'] == 11
	
	assert A.pull('deep.qwerty.0')['x1'] == 11
	assert A.pull('deep.qwerty.0.x1') == 11
	assert A.pulls('deep.qwerty.1.x1', 'deep.x1') == 10
	
	assert A.pull('deep.x1') == 10
	assert A.pull('deep')['x1'] == 10
	# assert A.pull('deep.qwerty.x1') == 10
	
	a = A.push_pull('deep.qwerty.2', 'no more')
	assert a == 'no more'
	assert A.pull('deep.qwerty.2') == 'no more'
	
	a = A.push_pull('deep.qwerty.3', [100])
	assert len(a) == 1 and a[0] == 100
	assert A.pull('deep.qwerty.3.0') == 100
	
	# with/out overwriting
	a = A.push_pull('deep.qwerty.4', 23, overwrite=False)
	assert a == 23
	assert A.pull('deep.qwerty.4') == 23
	
	a = A.push_pull('a.x', 2, overwrite=False)
	assert a == 1
	assert A.pull('a.x') == 1


def test_create_silent():
	import io, contextlib

	buffer = io.StringIO()
	with contextlib.redirect_stdout(buffer):
		A = fig.create_config(arg1='test')

		node = A.peek('arg1')
		assert node.create_silent() == 'test'

	printed = buffer.getvalue()
	assert printed == ''



def test_aliases():
	
	A = fig.create_config('test4')
	B = A.peek('l4.l5')
	
	assert A.pull('s1') == 'f1'
	assert B.pull('s2') == 'f2'


def test_update_sub():
	
	A = fig.create_config('test1')
	
	# update with config (check parents)
	
	B = fig.create_config()
	B.push('a', {'x':10, 'c': 20})
	B.push('fruit', 'not a list')
	B.push('a123', ['pears', 'raspberries'])

	assert B.pull('a123.0') == 'pears'
	assert A.pull('a123.0') == 1
	
	assert A.pull('a.x') == 1
	assert B.pull('a.x') == 10
	
	B.push('a.d.a', 'micro')
	assert B.pull('a.d.a')
	
	B.push('q', {'y': {'m': {'c': {'a': 'hey'}}}})
	B.push('alpha', [-9,2.1,{'beta':[-4,{'gamma'}]}])

	b = B.pull('alpha.2.beta.1')
	assert type(b) is set and 'gamma' in b
	
	A.update(B)
	
	assert A.pull('a.x') == 10
	assert A.pull('q.y.m.c.a') == 'hey'
	assert A.pull('fruit') == 'not a list'
	assert A.pull('a123.0') == 'pears'
	assert A.pull('a123.1') == 'raspberries'
	assert A.pull('a123.2') == 'another'
	assert 'gamma' in B.pull('alpha.2.beta.1')
	
	C = A.peek('q.y.m.c')
	
	assert C.pull('a') == 'hey'
	assert C.pull('unknown') == 'bad'
	assert C.pull('c.a') == 'hey'
	
	c = C.push_pull('m', 'tick')
	assert c == 'tick'
	assert C.pull('m') == 'tick'
	assert C.pull('y.m')['c']['a'] == 'hey'
	
	D = A.peek('alpha.2.beta')
	
	assert D.pull('0') == -4
	assert D.pull('alpha.0') == -9
	assert D.pull('unknown') == 'bad'


def test_repeat_create():
	raw = ['tomato']
	A = fig.create_config(fruit=raw)

	node = A.peek('fruit')
	fruit = node.create()

	assert raw is not fruit
	assert isinstance(fruit, list) and len(fruit) == 1 and fruit[0] == 'tomato'

	cached = node.pull()
	assert cached is not fruit
	cached2 = node.process()
	assert cached is cached2
	cached3 = A.pull('fruit')
	assert cached is cached3

	fruit2 = node.create()
	assert fruit2 is not fruit
	assert fruit2 == fruit

	fruit3 = node.create()
	assert fruit3 is not fruit2
	assert fruit3 == fruit2

	
def test_update_dict():

	A = fig.create_config('test1')
	
	assert A.pull('a.x') == 1
	
	A.update(A.from_raw({'y': {'m': {'c': {'a': 'hey'}}}, 'a': {'x':12}}))
	
	assert A.pull('a.x') == 12
	assert A.pull('y.m.c.a') == 'hey'
	
	C = A.peek('y.m.c')
	
	assert C.pull('a') == 'hey'
	assert C.pull('unknown') == 'bad'
	assert C.pull('c.a') == 'hey'
	
	A.update(A.from_raw({'alpha':[-9,2.1,{'beta':[-4,{'gamma'}]}]}))
	
	assert A.pull('alpha.0') == -9
	assert tuple(A.pull('alpha.2.beta.1')) == ('gamma',)
	
	D = A.peek('alpha.2.beta')
	
	assert D.pull('0') == -4
	assert D.pull('alpha.0') == -9
	assert D.pull('unknown') == 'bad'


def test_export():
	fig.get_current_project().register_config_dir(tu.CONFIG_PATH, recursive=True)

	# load/change/export
	A = fig.create_config('test2', **{'a.d': 50})

	A.push('count', [40,40])

	# path = os.path.join(tu.TEST_PATH, 'save.yaml')
	root = tu.TEST_PATH / 'temp-exports'
	root.mkdir(exist_ok=True)
	path = root / 'save.yaml'
	A.export(path)

	# reload from path (rel and abs) check for change

	B = fig.create_config(path)

	assert B.pull('a.b') == 'inside'
	assert B.pull('unseen') == 45
	assert B.pull('count.0') == 40
	assert B.pull('a.d') == 50
	assert B.pull('others.2.not.mickey') == 'mouse'

	B.push('a.d', 100)

	path = B.export('save2', root=root)

	C = load_export(path)

	assert C.pull('a.b') == 'inside'
	assert C.pull('unseen') == 45
	assert C.pull('count.0') == 40
	assert C.pull('a.d') == 100
	assert C.pull('others.2.not.mickey') == 'mouse'

	if root.exists():
		shutil.rmtree(root)
	

def test_components():
	A = fig.create_config('test5')
	
	# create
	c = A.peek('a7').create()
	
	assert c.a2 == 'worked'
	assert c.a4_a6 == 2
	assert c.a10_0 == '0'
	assert c.x is None
	assert c.a14 == 'success'
	assert c.a14b == 'next'
	
	assert c.f(10) == 11
	
	# create nested
	A.push('a7.mn._type', 'c2')
	A.push('a7.mn.a3', 'billion')
	
	d = A.pull('a7')
	
	assert d.x is not None
	assert d.x.a1 == 1
	assert d.x.a2 == 'worked'
	assert d.x.a3 == 'billion'
	
	d.delta = 1234
	
	# reuse
	e = A.pull('a7')
	
	assert id(e) == id(d)
	assert id(d.x) == id(e.x)
	assert e.delta == d.delta
	assert e.delta == 1234
	
def test_modifiers():
	
	A = fig.create_config('test6', 'test5')
	
	# simple auto modifiers
	
	c = A.pull('a7')
	
	assert type(c).__name__ == 'M2_M1_C1'
	assert c.f(1) == 500
	assert c.g(2) == 998
	assert c.h() == 502
	assert c.x is None
	
	# multiple auto modifiers
	
	A.push('a7._mod', 'm1')
	
	d = A.peek('a7').create()
	
	assert type(d).__name__ == 'M1_C1'
	assert d.f(1) == 0
	assert d.g(10) == -11
	assert d.h() == 2
	
	
	# modifications
	
	# A.push('a7._mod', 'm3')
	#
	# e = A.peek('a7').create()
	#
	# assert type(e).__name__ == 'C1'
	# assert e.a == 'still worked'
	
	
def test_iteration():
	
	A = fig.create_config('test2')
	
	# iterate through a list with as_iter
	
	# itr = A.pull('others', as_iter=True)
	node = A.peek('others')
	itr = node.pull_children()
	
	assert len(node) == 3
	assert next(itr) == 'tom'
	# assert len(itr) == 2
	assert next(itr) == 'jerry'
	assert next(itr)['not']['mickey'] == 'mouse'
	
	# iterate through a dict with as_iter
	
	A.push('costs.gems', '_x_')
	
	answers = A.peek('costs').create()

	node = A.peek('costs')
	itr = node.pull_named_children()
	
	assert len(node) == 4
	for _ in range(len(node)):
		k,v = next(itr)
		
		assert k in answers
		assert answers[k] == v
	
	# auto iterate a list with seq
	
	node = A.peek('others')
	itr = node.peek_children()
	
	assert len(node) == 3
	assert next(itr).create() == 'tom'
	# assert len(itr) == 2
	# assert next(itr).create() == 'jerry'
	assert next(itr).parent == node
	assert next(itr).create()['not']['mickey'] == 'mouse'
	

	# auto iterate a dict with seq
	
	node = A.peek('costs')
	itr = node.peek_named_children()
	
	assert len(node) == 4
	for _ in range(len(node)):
		k, v = next(itr)
		
		assert k in answers
		assert v.parent == node
		assert answers[k] == v.create()
	
	
def test_removing():
	
	A = fig.create_config('test2')
	
	assert A.pull('papageno') == 10
	assert A.pull('papagena', 'missing') == 'missing'
	
	A.push('vogel.papagena', '_x_')
	
	node = A.peek('vogel')
	itr = node.pull_named_children()
	
	assert len(node) == 1
	assert tuple(next(itr)) == ('papagei', 'parrot')
	

def test_raw_and_cousins():
	
	A = fig.create_config('test5')
	
	raw = A.peek('a7')
	assert isinstance(raw, type(A))
	
	A.push('pocket.a7', raw)
	A.push('a2', '_x_')
	A.push('a7', '_x_')
	A.push('a7.a2', 'cousin')
	A.push('pocket.a7.a2', '_x_')
	
	A.settings['allow_cousins'] = True
	
	pocket = A.peek('pocket')
	
	# create
	c = pocket.pull('a7')
	
	assert c.a2 == 'cousin'
	assert c.a4_a6 == 2
	assert c.a10_0 == '0'
	assert c.x is None
	assert c.a14 == 'success'
	assert c.a14b == 'next'

	# testing printing

	print(A)
	print()
	print(fig.create_config('test3'))
	
	
# TODO: unit tests checking the printed output when pulling/pushing objects


def test_pull_cycle():

	A = fig.create_config()

	A.push('a', ['<>a'])

	try:
		out = A.pull('a')
	except A.CycleError as e:
		assert e.config.my_address() == ('a',)
	else:
		assert False, 'CycleError not raised'


def test_underscores():

	# NOTE: dashes default to underscores (but not vice versa)
	# so, in general, queries should use dashes, configs should use underscores

	A = fig.create_config(a_b=1, _b=2, **{'-c': 3, 'd-e': 4, '--f': 5})

	assert A.pull('a_b') == 1
	assert A.pull('_b') == 2
	# assert A.pull('_c') == 3
	# assert A.pull('d_e') == 4
	# assert A.pull('__f') == 5

	assert A.pull('a-b') == 1
	assert A.pull('-b') == 2
	assert A.pull('-c') == 3
	assert A.pull('d-e') == 4
	assert A.pull('--f') == 5

	print()
	print(A)


def test_underscores2():
	data = {'-x':1, '_y': '-a_'}
	A = fig.create_config(a_b=data, _b=2, **{'-c': data, 'd-e': 4, '--f': 5})

	assert A.pull('a_b') == data
	assert A.pull('a-b') == data
	assert A.pull('-c') == data

	assert A.pull('a_b.-x') == 1
	assert A.pull('a_b._y') == '-a_'

	assert A.pull('a-b.-x') == 1
	assert A.pull('a-b._y') == '-a_'

	assert A.pull('-c.-x') == 1
	assert A.pull('-c.-y') == '-a_'







