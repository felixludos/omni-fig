import sys, os
import omnifig as fig

import _test_util as tu

def test_create_obj():
	
	A = fig.get_config()
	
	A.a.b.c = 10
	
	assert 'a' in A
	assert 'b' in A.a
	assert 'c' in A.a.b
	assert type(A) == type(A.a)
	assert A.a.b.c == 10

def test_register_load_config():
	
	fig.register_config_dir(os.path.join(tu.TEST_PATH, 'example', 'config'))

	C = fig.get_config('test')
	
	assert C.arg1 == 'test'

def test_raw_param():
	
	C = fig.get_config('--b', 'baba', '--a', '''{"r":10, "b":100}''', '--c', '''["asdf", 10, 4e-4]''')
	
	assert id(C.a.get_parent()) == id(C)
	
	assert C.b == 'baba'
	assert C.a.b == 100
	assert C.a.r == 10
	assert C.c[0] == 'asdf'
	assert C.c[-1] == 4e-4


def test_pull():
	
	A = fig.get_config('test2')
	
	a = A.pull('simple')
	assert a == 'p'
	
	b = A.pull('default', 'worked')
	assert b == 'worked'
	
	c = A.pull('not_there', '<>try_again', '<>alias_option')
	assert c == 'found'
	
	d = A.pull('n1', '<>n2', 2.5)
	assert d == 2.5
	
	e = A.pull('unseen', silent=True)
	assert e == 45

	f = A.pull('a.b')
	assert f == 'inside'

	g = A.pull('x.y')
	assert g == 'hello'

	h = A.pull('x.list', '<>x')
	h = h['z']
	assert len(h) == 2 and h[0] == 1 and h[1] == 2
	
	i = A.pull('veggies', '<>fruit')
	assert len(i) == 3 and i[0] == 'apples'
	assert type(i) == tuple
	
	j = A.pull('others')
	assert type(j) == tuple and len(j) == 3 and j[2]['not']['mickey'] == 'mouse'
	
	k = A.pull('costs')
	assert type(k) == dict and len(k) == 5 and 'rubies' in k['gems'] and k['steel'] > 1000
	
	

