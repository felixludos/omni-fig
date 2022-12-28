
import sys, os

import _test_util as tu


import omnifig as fig

def _reset_profile(name='base'):
	os.environ['FIG_PROFILE'] = str(tu.PROFILES_PATH / f'{name}.yaml')
	fig.ProfileBase._profile = None
	return fig.get_profile()


def test_base_profile():
	profile = _reset_profile()
	assert profile.name == 'base-profile'
	assert profile.path == tu.PROFILES_PATH / 'base.yaml'
	assert profile is fig.ProfileBase._profile


def test_missing_profile():
	profile = _reset_profile('does-not-exist')
	assert profile.name == ''


def test_bad_profile():
	profile = _reset_profile('bad')
	assert profile.name == ''


def test_current_project():
	profile = _reset_profile()
	proj = fig.get_current_project()
	assert proj.name == profile._default_project_name # 'default'


def test_load_project():
	profile = _reset_profile()

	old = profile.get_current_project()

	proj = profile.switch_project('example1')

	new = profile.get_current_project()

	assert old is not None
	assert old is not new
	assert proj is new

	assert proj.name == 'project1' # name is specified in project info file

	assert not proj.is_activated
	proj.activate()
	assert proj.is_activated

	assert len(list(proj.iterate_configs())) == 1

	assert proj.create_config('just-one').pull('hello') == 'world'
	assert fig.create_config('just-one').pull('hello') == 'world'


def test_load_missing_project():
	profile = _reset_profile()

	try:
		fig.get_project('does-not-exist')
	except profile.UnknownProjectError:
		pass
	else:
		assert False, 'should have raised an UnknownProjectError'


def test_new_profile():
	profile = _reset_profile()
	fig.get_current_project()
	assert len(list(profile.iterate_projects())) == 1

	_reset_profile()

	profile = fig.get_profile()
	assert len(list(profile.iterate_projects())) == 0


def test_ambiguous_project_name():
	profile = _reset_profile()

	proj = profile.get_project('example1')
	assert not proj.is_activated

	assert proj.name == 'project1' # name is specified in project info file
	assert proj is profile.get_project('project1')
	assert proj is profile.get_project('example1')

	proj = profile.get_project('example2')
	assert not proj.is_activated

	assert proj.name == 'example2' # no name is specified in project info file
	assert proj is profile.get_project('example2')



def test_active_project():
	assert not getattr(fig, '_loaded_p2', False) # flag
	profile = _reset_profile('active')
	assert getattr(fig, '_loaded_p2', False) # means p2 source code was run
	del fig._loaded_p2

	assert profile.name == 'active-profile'

	proj = fig.get_current_project()

	assert proj.name == 'default'

	cmp = proj.find_component('cmp1', None)

	assert cmp is not None
	assert cmp.cls.__name__ == 'Cmpn1'
	assert cmp.cls.__module__ == 'my_code'
	assert cmp.project is not proj
	assert cmp.project is profile.get_project('example2')


def test_explicit_project_file():

	profile = _reset_profile('multi')

	proj = profile.get_current_project()
	assert proj.name == 'default'

	proj3 = profile.get_project('example3')
	assert proj3.name == 'example3'

	assert len(list(profile.iterate_projects())) == 2

	proj3a = profile.get_project('example3-alt')
	assert proj3a.name == 'other-p3'

	assert len(list(profile.iterate_projects())) == 3

	assert not proj3.is_activated
	assert not getattr(fig, '_loaded_p3', False)

	proj3.activate()
	assert proj3.is_activated

	assert getattr(fig, '_loaded_p3_util', 0) == 1
	assert getattr(fig, '_loaded_p3_script', 0) == 1
	assert getattr(fig, '_loaded_p3_script2', 0) == 0

	assert len(list(proj3.iterate_components())) == 2

	assert sorted(entry.cls.__name__ for entry in proj3.iterate_components()) == ['P3C1', 'UtilComponent']

	proj3a.activate()

	assert getattr(fig, '_loaded_p3_util', 0) == 2
	assert getattr(fig, '_loaded_p3_script', 0) == 2
	assert getattr(fig, '_loaded_p3_script2', 0) == 1

	assert len(list(proj3a.iterate_components())) == 3

	assert sorted(entry.cls.__name__ for entry in proj3a.iterate_components()) == ['P3C1', 'P3aC1', 'UtilComponent']



# def test_hijack_project(): # "hijack" project contents
# 	pass



def test_xray():
	profile = _reset_profile()

	proj = profile.get_project('example2')

	print()
	proj.xray('component')
	assert len(list(proj.iterate_components())) == 4

	print()
	proj.xray('modifier')
	assert len(list(proj.iterate_modifiers())) == 3


#
# def test_related():
# 	pass
#
#
# def test_profile_initialize():
# 	pass



# TEST: explicit project artifact ":" syntax - not related or base

# TEST: artifact descriptions/xraying


# TEST: modifying with and without configurable modifiers/components

# TEST: meta rules







