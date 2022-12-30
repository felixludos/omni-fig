
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
