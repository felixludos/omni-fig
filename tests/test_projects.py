
import sys, os
from pathlib import Path

from omnibelt import cwd

import _test_util as tu
from _test_util import reset_profile


import omnifig as fig



def test_base_profile():
	profile = reset_profile()
	assert profile.name == 'base-profile'
	assert profile.path == tu.PROFILES_PATH / 'base.yaml'
	assert profile is fig.ProfileBase._profile



def test_missing_profile():
	profile = reset_profile('does-not-exist')
	assert profile.name == ''



def test_bad_profile():
	profile = reset_profile('bad')
	assert profile.name == ''



def test_current_project():
	profile = reset_profile()
	proj = fig.get_current_project()
	# assert proj.name == 'omni-fig' # inferred
	assert proj.name is None



def test_current_project2():
	profile = reset_profile()
	with cwd(Path('/')):
		proj = fig.get_current_project()
	assert proj.name is None



def test_load_project():
	profile = reset_profile()

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
	profile = reset_profile()

	try:
		fig.get_project('does-not-exist')
	except profile.UnknownProjectError:
		pass
	else:
		assert False, 'should have raised an UnknownProjectError'



def test_new_profile():
	profile = reset_profile()
	fig.get_current_project()
	assert len(list(profile.iterate_projects())) == 1

	reset_profile()

	profile = fig.get_profile()
	assert len(list(profile.iterate_projects())) == 0



def test_ambiguous_project_name():
	profile = reset_profile()

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
	profile = reset_profile('active')
	assert getattr(fig, '_loaded_p2', False) # means p2 source code was run
	del fig._loaded_p2

	assert profile.name == 'active-profile'

	proj = fig.get_current_project()

	# assert proj.name == 'omni-fig'
	assert proj.name is None

	cmp = proj.find_component('cmp1', None)

	assert cmp is not None
	assert cmp.cls.__name__ == 'Cmpn1'
	assert cmp.cls.__module__ == 'my_code'
	assert cmp.project is not proj
	assert cmp.project is profile.get_project('example2')



def test_parent_is_project():
	profile = reset_profile('does-not-exist')

	with cwd(tu.PROJECTS_PATH / 'p8' / 'some-dir' / 'deep'):
		fig.initialize()

		assert fig.get_current_project().name == 'p8'



def test_explicit_project_file():

	profile = reset_profile('multi')

	proj = profile.get_current_project()
	# assert proj.name == 'omni-fig'
	assert proj.name is None

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



def test_load_noncurrent_project(): # "hijack" project contents
	reset_profile()

	# default = fig.get_current_project()
	default = fig.get_profile().create_project('test-project')

	# assert default.name == 'omni-fig'
	assert default.name == 'test-project'
	assert not default.is_activated

	proj = fig.get_project('example2')

	# assert fig.get_current_project().name == 'omni-fig'
	assert fig.get_current_project().name == 'test-project'
	assert not default.is_activated

	proj.load()

	# assert fig.get_current_project().name == 'omni-fig'
	assert fig.get_current_project().name == 'test-project'
	assert not default.is_activated
	assert not proj.is_activated

	assert len(list(default.iterate_components())) == 4

	# assert fig.get_current_project().name == 'omni-fig'
	assert fig.get_current_project().name == 'test-project'
	assert default.is_activated
	assert not proj.is_activated

	proj.activate()

	assert len(list(proj.iterate_components())) == 4

	assert [e.cls.__name__ for e in proj.iterate_components()] \
	       == [e.cls.__name__ for e in default.iterate_components()]



def test_infer_project():

	profile = reset_profile()
	profile.data['projects'] = {name: str(Path(path).absolute()) for name, path in profile.data['projects'].items()}

	old = os.getcwd()
	os.chdir(str(tu.PROJECTS_PATH / 'p1' / 'some' / 'sub-dir'))

	proj = fig.get_current_project()

	assert proj.name == 'project1'

	os.chdir(old)



def test_xray():
	profile = reset_profile()

	proj = profile.get_project('example2')

	print()
	proj.xray('script')

	print()
	proj.xray('component')

	print()
	proj.xray('modifier')

	print()
	proj.xray('creator')

	print()
	proj.xray('config')

	assert len(proj.xray('script', as_list=True)) == 1
	assert len(proj.xray('component', as_list=True)) == 4
	assert len(proj.xray('modifier', as_list=True)) == 3
	assert len(proj.xray('creator', as_list=True)) == 0
	assert len(proj.xray('config', as_list=True)) == 3



def test_xray_related():
	profile = reset_profile('active')

	fig.initialize('example3')

	proj = profile.switch_project('example4')

	print()
	proj.xray('script')

	print()
	proj.xray('component')

	print()
	proj.xray('modifier')

	print()
	proj.xray('creator')

	print()
	proj.xray('config')

	assert len(proj.xray('script', as_list=True)) == 2
	assert len(proj.xray('component', as_list=True)) == 11
	assert len(proj.xray('modifier', as_list=True)) == 4
	assert len(proj.xray('creator', as_list=True)) == 1
	assert len(proj.xray('config', as_list=True)) == 3



def test_find_base_projects():
	reset_profile()

	fig.initialize('example2', 'example4')

	assert fig.get_current_project().name is None

	proj = fig.get_project()
	p2 = fig.get_project('example2')
	p4 = fig.get_project('example4')

	assert proj.find_component('cmp1').cls.__name__ == 'Cmpn1'
	assert proj.find_component('example4:cmp1').cls.__name__ == 'P4C1'
	assert p2.find_component('cmp1').cls.__name__ == 'Cmpn1'
	assert p4.find_component('cmp1').cls.__name__ == 'P4C1'

	@fig.component('cmp1')
	class MyCmpn1:
		pass

	assert proj.find_component('cmp1').cls.__name__ == 'MyCmpn1'
	assert proj.find_component('example2:cmp1').cls.__name__ == 'Cmpn1'
	assert proj.find_component('example4:cmp1').cls.__name__ == 'P4C1'
	assert p2.find_component('cmp1').cls.__name__ == 'Cmpn1'
	assert p4.find_component('cmp1').cls.__name__ == 'P4C1'

	assert proj.find_component('cmp100').cls.__name__ == 'P4C100'
	assert p2.find_component('cmp100').cls.__name__ == 'P4C100'

	assert proj.find_component('cmp2').cls.__name__ == 'Cmpn2'
	assert p2.find_component('cmp2').cls.__name__ == 'Cmpn2'
	assert p4.find_component('cmp2').cls.__name__ == 'Cmpn2'



def test_related():
	profile = reset_profile()
	assert len(list(profile.iterate_projects())) == 0

	fig.initialize('example2')
	assert len(list(profile.iterate_projects())) == 2

	assert fig.get_current_project().name is None

	proj = fig.switch_project('example4')
	assert len(list(profile.iterate_projects())) == 3

	proj.activate()

	assert len(list(profile.iterate_projects())) == 3
	assert fig.get_current_project() is proj
	assert proj.is_activated

	p1 = fig.get_project('example1')
	assert not p1.is_activated

	p2 = fig.get_project('example2')
	assert p2.is_activated

	assert len(list(profile.iterate_projects())) == 4
	assert 'example5' not in profile._loaded_projects

	try:
		proj.find_component('cmp6')
	except proj.UnknownArtifactError:
		pass
	else:
		assert False, 'expected exception'

	assert 'example5' in profile._loaded_projects
	assert len(list(profile.iterate_projects())) == 5

	p5 = fig.get_project('example5')

	assert p5.is_activated
	assert proj.find_component('cmp5').cls.__name__ == 'P5C5'

	assert proj.find_component('cmp3').cls.__name__ == 'P5C3'
	assert proj.find_component('example2:cmp3').cls.__name__ == 'Cmpn3'

	assert proj.find_component('cmp1').cls.__name__ == 'P4C1'
	assert proj.find_component('example2:cmp1').cls.__name__ == 'Cmpn1'

	assert proj.find_component('cmp4').cls.__name__ == 'Cmpn4'



def test_infer_project2():
	profile = reset_profile('does-not-exist')

	with cwd(tu.PROJECTS_PATH / 'p1'):
		profile = reset_profile()

		print()
		fig.main(['-h'])

		assert fig.get_current_project().name == 'project1'


