
from pathlib import Path

from _test_util import reset_profile

import omnifig as fig



def test_initialize_empty():
	profile = reset_profile()

	default = fig.get_current_project()

	assert default.name == 'default'
	assert not default.is_activated

	assert len(list(profile.iterate_projects())) == 1

	fig.initialize()

	assert len(list(profile.iterate_projects())) == 1
	assert default.is_activated

	assert default is fig.get_current_project()



def test_initialize():
	profile = reset_profile()

	default = fig.get_current_project()

	assert default.name == 'default'
	assert not default.is_activated

	fig.initialize('example2')

	assert len(list(profile.iterate_projects())) == 2

	proj = fig.get_project('example2')

	assert proj.is_activated
	assert default.is_activated

	assert len(list(default.iterate_components())) == 0
	assert fig.get_current_project().name == 'default'

	assert proj.name == 'example2'
	assert len(list(proj.iterate_components())) == 4



def test_initialize_multi():
	profile = reset_profile()

	default = fig.get_current_project()

	assert default.name == 'default'
	assert not default.is_activated

	assert len(list(profile.iterate_projects())) == 1

	fig.initialize('example2', 'example4')

	assert len(list(profile.iterate_projects())) == 3

	assert default is fig.get_current_project()
	assert len(list(profile.iterate_projects())) == 3
	assert [True, True, True] == [p.is_activated for p in profile.iterate_projects()]

	assert len(list(default.iterate_components())) == 0

	proj = fig.get_project('example2')
	assert len(list(proj.iterate_components())) == 4

	proj = fig.get_project('example4')
	assert len(list(proj.iterate_components())) == 2



def test_parse_argv():
	C = fig.parse_argv(['-q', '--b', 'baba', '--a', '''{"r":10, "b":100}''',
	                    '--c', '''["asdf", 10, 4.e-4]''', '--x=99'], script_name='some-script')

	assert C.peek('a').parent is C
	assert C.root is C

	assert C.pull('b') == 'baba'
	assert C.pull('a.b') == 100
	assert C.pull('a.r') == 10
	assert C.pull('c')[0] == 'asdf'
	assert C.pull('c')[-1] == 4e-4

	assert C.peek('x').process() == 99



def test_parse_argv_meta():
	C = fig.parse_argv(['-q', '--b', 'baba', '--x=99'], script_name='some-script')

	assert C.pull('_meta.script_name') == 'some-script'
	assert C.pull('_meta.quiet')
	assert C.pull('_meta.debug', False) is False

	C = fig.parse_argv(['-q', '--b', 'baba', '--x=99', '-q'], script_name='some-script')

	assert C.pull('_meta.script_name') == 'some-script'
	assert C.pull('_meta.quiet')
	assert C.pull('_meta.debug', False) is False

	C = fig.parse_argv(['-q', '-d', '--b', 'baba', '--x=99'], script_name='some-script')

	assert C.pull('_meta.script_name') == 'some-script'
	assert C.pull('_meta.quiet')
	assert C.pull('_meta.debug')

	C = fig.parse_argv(['-q', '--b', 'baba', '--x=99', '-d'], script_name='some-script')

	assert C.pull('_meta.script_name') == 'some-script'
	assert C.pull('_meta.quiet')
	assert C.pull('_meta.debug')

	C = fig.parse_argv(['-q', '-h', '--b', 'baba', '-d', '--x=99'], script_name='some-script')

	assert C.pull('_meta.script_name') == 'some-script'
	assert C.pull('_meta.quiet')
	assert C.pull('_meta.debug')
	assert C.pull('_meta.help')




# TEST: entry, main, run, quick_run


