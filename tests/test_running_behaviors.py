import sys
import io
from contextlib import redirect_stdout

import omnifig as fig

from _test_util import reset_profile

# def test_debug():
# 	pass
#
# def test_help():
# 	pass
#



def test_help():
	reset_profile()
	proj = fig.switch_project('example6')
	proj.activate()

	argv = ['-h', '--y', '99']

	print()
	out = fig.main(argv)

	assert out is None



def test_help2():
	reset_profile()
	proj = fig.switch_project('example6')
	proj.activate()

	argv = ['add', '-h', '--y', '99']

	print()
	out = fig.main(argv)

	assert out is None


def test_help3():
	reset_profile()
	fig.switch_project('example6')

	argv = ['repeater', '-h', '--y', '99']

	print()
	out = fig.main(argv)

	assert out is None



def test_help4():
	reset_profile()
	fig.switch_project('example6')

	argv = ['add', '-h', '--y', '99', '--_meta.help', 'no'] # you cant override the behavior manually

	print()
	out = fig.main(argv)

	assert out is None



def test_help5():
	reset_profile()
	fig.switch_project('example6')

	argv = ['-h', '--y', '99', '--verbose']

	print()
	out = fig.main(argv)

	assert out is None




def test_help6():
	reset_profile()
	fig.switch_project('example6')

	argv = ['-h', '--y', '99', '--verbose']

	print()
	out = fig.main(argv, 'is-quiet')

	assert out is None



def test_help7():
	reset_profile()
	proj = fig.switch_project('example6')

	argv = ['fig', 'mirror', '-h']

	print()
	old = sys.argv
	sys.argv = argv
	out = fig.entry()
	sys.argv = old

	assert out is None



def test_help8():
	reset_profile()
	proj = fig.switch_project('example6')

	argv = ['--y', '99', '-h']

	print()
	out = fig.main(argv)

	assert out is None




def test_debug():
	reset_profile()
	proj = fig.switch_project('example6')
	proj.activate()

	print()

	config = fig.create_config('c2', **{'_meta.debug': True})

	assert config.cro == ('c2', 'the-kids/kendall')
	assert config.bases == ('c2',)

	assert config.pull('_meta.debug', silent=True) is True
	assert config.pull('_meta.quiet', False, silent=True) is False

	out = fig.run_script('add', config)

	assert out == 3
	assert config.pull('_meta.quiet', False, silent=True) is True

	out = fig.run_script('add', config, 2, 2)

	assert out == 5 # a bit orwellian

	assert config.cro == ('debug', 'c1', 'c2', 'the-kids/kendall')
	assert config.bases == ('debug',)

	config.push('x', 3)
	out = fig.run_script('add', config, y=2)

	assert out == 5



def test_debug2():
	reset_profile()
	fig.switch_project('example5')

	print()
	out = fig.main(['add-1', '-d', '--a=99'])

	assert out == 100


def test_debug3():
	reset_profile()
	fig.switch_project('example6')

	argv = ['repeater', 'c2', '-d', '--y=99']

	out = fig.main(argv)

	assert out == (3, 11)

	old = sys.argv
	sys.argv = argv
	out = fig.entry('add')
	sys.argv = old

	assert out is None

	argv = ['repeater', 'c2', '--y=99']

	out = fig.main(argv)

	assert out == (104, 15)



def test_debug4():

	reset_profile()
	fig.switch_project('example6')

	out = fig.quick_run('repeater', 'c2', y=99, **{'_meta.debug': True})

	assert out == (3, 11)



def test_quiet():
	reset_profile()

	fig.initialize('example6')

	config = fig.parse_argv(['-q', '--b', 'baba', '--x=99'])

	assert not config.silent

	buf = io.StringIO()

	with redirect_stdout(buf):
		x, y, args, kwargs = fig.run_script('mirror', config, 'arg', z=100)

	assert buf.getvalue() == ''

	assert not config.silent
	assert x == 99
	assert y == 2
	assert args == ('arg',)
	assert kwargs == {'z': 100}



def test_quiet2():
	fig.initialize('example6')

	config = fig.parse_argv(['--b', 'baba', '--x=99'])

	assert not config.silent
	buf = io.StringIO()

	with redirect_stdout(buf):
		fig.run_script('mirror', config, 'arg', z=100)

	assert not config.silent
	assert buf.getvalue() != ''



def test_quiet3():
	fig.initialize('example6')

	config = fig.parse_argv(['-q', '--b', 'baba', '--x=99'])

	assert not config.silent
	config.push('_meta.quiet', False)

	buf = io.StringIO()

	with redirect_stdout(buf):
		fig.run_script('mirror', config, 'arg', z=100)

	assert not config.silent
	assert buf.getvalue() != ''



def test_quiet4():
	reset_profile()

	fig.initialize('example6')

	config = fig.parse_argv(['--b', 'baba', '--x=99'])

	config.silent = True
	assert config.silent

	buf = io.StringIO()

	with redirect_stdout(buf):
		x, y, args, kwargs = fig.run_script('mirror', config, 'arg', z=100)

	assert config.silent
	assert buf.getvalue() == ''



def test_quiet5():
	reset_profile()

	fig.initialize('example6')

	config = fig.parse_argv(['-q', '--b', 'baba', '--x=99'])

	config.silent = True
	assert config.silent

	buf = io.StringIO()

	with redirect_stdout(buf):
		x, y, args, kwargs = fig.run_script('mirror', config, 'arg', z=100)

	assert config.silent
	assert buf.getvalue() == ''



def test_quiet6():
	reset_profile()

	fig.initialize('example6')

	config = fig.parse_argv(['-q', '--b', 'baba', '--x=99'])

	assert fig.run_script('is-quiet', config) is True



def test_quiet7():
	reset_profile()

	fig.initialize('example6')

	config = fig.parse_argv(['--b', 'baba', '--x=99', '--_meta.quiet', 'yes'])

	assert fig.run_script('is-quiet', config) is True



