
if __name__ == '__main__':

	import sys, os
	import omnifig as fig
	from omnifig.config import EmptyElement
	
	import _test_util as tu
	
	
	fig.register_config_dir(os.path.join(tu.TEST_PATH, 'example', 'config'), recursive=True)
	
	A = fig.get_config('test1')
	
	# child pushes
	a = A.push('arg2.a.b', [-1, 10])
	assert a[0] == -1
	assert A.pull('arg2.a')['b'][1] == 10
	assert A.pull('arg2.a.b.1') == 10
	
	# when parent exists
	a = A.push('deep.unknown', 'gooder')
	assert a == 'gooder'
	assert A.pull('unknown') == 'bad'
	assert A.pull('deep.qwerty.1.t.unknown') == 'good'
	assert A.pull('deep.unknown') == 'gooder'
	
	# push to list (append and indexed)
	a = A.push('fruit._', 'yummy')
	assert a == 'yummy'
	assert A.pull('fruit.1') == 'yummy'
	a = A.push('fruit.2', 'blueberry')
	assert a == 'blueberry'
	assert len(A.pull('fruit')) == 3
	assert A.pull('fruit.2') == 'blueberry'
	
	a = A.push('fruit.10', 'veggies')
	assert a == 'veggies'
	assert A.pull('fruit.3') is EmptyElement
	assert A.pull('fruit.7') is EmptyElement
	assert A.pull('fruit.10') == 'veggies'
	assert A.pull('fruit.11', 'nope') == 'nope'
	assert A.pull('fruit.20', 'no way') == 'no way'