
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


def test_current_project():
	profile = _reset_profile()
	proj = fig.get_current_project()
	assert proj.name == profile._default_project_name # 'default'

	_reset_profile()


def test_load_project():
	profile = _reset_profile()

	old = profile.get_current_project()

	proj = profile.switch_project('example1')

	new = profile.get_current_project()

	assert old is not None
	assert old is not new
	assert proj is new

	assert proj.name == 'example1'

	assert len(list(proj.iterate_configs())) == 0

	proj.activate()

	assert len(list(proj.iterate_configs())) == 1

	assert proj.create_config('just-one').pull('hello') == 'world'
	assert fig.create_config('just-one').pull('hello') == 'world'

	_reset_profile()


def test_load_missing_project():
	profile = _reset_profile()

	try:
		fig.get_project('does-not-exist')
	except profile.UnknownProjectError:
		pass
	else:
		assert False, 'should have raised an error'

	_reset_profile()


def test_new_profile():
	profile = _reset_profile()
	fig.get_current_project()
	assert len(list(profile.iterate_projects())) == 1

	_reset_profile()

	profile = fig.get_profile()
	assert len(list(profile.iterate_projects())) == 0

	_reset_profile()


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
	assert cmp.project is not proj
	assert cmp.project is profile.get_project('example2')















