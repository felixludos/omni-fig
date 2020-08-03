
import sys, os
from collections import OrderedDict

from .util import get_printer, get_global_setting, resolve_order, spawn_path_options
from .external import get_project_type, get_project_assoc, include_files
from .profiles import Profile
from .projects import Project

prt = get_printer(__name__)

# region Profiles

_profile_cls = Profile


def set_profile_cls(cls):
	global _profile_cls
	prt.debug(f'Profile cls used: {_profile_cls.__name__}')
	_profile_cls = cls

def get_profile_cls():
	return _profile_cls

_profile = None
def set_profile(profile):
	global _profile
	prt.debug(f'Profile set to: {profile}')
	_profile = profile

def load_profile(**overrides):
	global _profile
	
	# prt.debug(f'Initializing profile')
	allow_profile_src = get_global_setting('allow_profile_sources')
	if allow_profile_src:
		profile_src_path = resolve_order(get_global_setting('profile_src_env_var'),
		                                 overrides, os.environ, get_global_setting)
		if profile_src_path is not None:
			include_files(profile_src_path)
	
	profile_path = resolve_order(get_global_setting('profile_env_var'),
	                             overrides, os.environ, get_global_setting)
	
	_profile = _profile_cls(path=profile_path)
	
	if profile_path is None:
		prt.info('No profile path found')
	
	return _profile

def get_profile():
	return _profile


# endregion


# region Project

_info_names = {
	'omni.fig', 'info.fig', '.omni.fig', '.info.fig',
	'fig.yaml', 'fig.yml', '.fig.yaml', '.fig.yml',
	'fig.info.yaml', 'fig.info.yml', '.fig.info.yaml', '.fig.info.yml',
	'fig_info.yaml', 'fig_info.yml', '.fig_info.yaml', '.fig_info.yml',
	'project.yaml', 'project.yml', '.project.yaml', '.project.yml',
}
_info_code = '.fig.info.yaml'

def get_project(ident=None, auto_include=True, set_active=True):
	'''
	Finds and possibly loads project info given name or path to info yaml file
	
	:param ident:
	:param auto_include: If the project is not already tracked in the profile, it will be included
	:param set_active: Automatically set this project to the active one after loading
	:return:
	'''
	
	profile = get_profile()
	if profile is None:
		prt.warning('No profile has been loaded, generally a profile should be loaded before loading projects')
		raise Exception('Profile must be loaded before loading a project')
	
	if ident is None:
		active = profile.get_active_project()
		if active is not None:
			return active
		ident = os.getcwd()
	
	# region Loaded
	
	project = profile.contains_project(ident)
	
	if project is not None:
		prt.debug(f'Project {ident} was found already loaded')
		return project
	
	# endregion
	# region Local

	todo = []
	if os.path.isdir(ident):  # ident is a dir possibly containing multiple projects
		contents = os.listdir(ident)
		
		for fname in contents:
			if fname in _info_names or _info_code in fname:
				todo.append(os.path.join(ident, fname))
	elif os.path.isfile(ident) and (os.path.basename(ident) in _info_names
	                                or _info_code in os.path.basename(ident)):
		todo.append(ident)

	if len(todo):
		prt.debug(f'Project location options found in local dir: {ident}')
	
	# endregion
	# region Profile
	
	loc = profile.resolve_project_path(ident)
	if loc is not None:
		prt.debug(f'Project location found in profile {loc}')
		todo.append(loc)
	
	# endregion
	# region Create
	
	while len(todo):
		info_path = todo.pop()
		if os.path.isfile(info_path) and not profile.contains_project(info_path):
			project = _create_project(info_path)
			
			for related in project.get_related():
				get_project(related, auto_include=auto_include)
			
			profile.include_project(project, register=auto_include)
			if set_active:
				set_active_project(project)
				
			with set_active_project(project):
				project.prepare()
		
	# endregion
	
	if project is None:
		prt.debug(f'No project found for {ident}')
	
	return project

def _create_project(info_path):
	assert os.path.isfile(info_path), f'Invalid path: {info_path}'
	project_root = os.path.dirname(info_path)
	
	default_ptype = get_global_setting('default_ptype')
	default = get_project_type(default_ptype)
	
	info = {} if info_path is None else default.load_raw_info(info_path)
	name = default.check_project_name(info)
	
	ptype = default.check_project_type(info)
	if ptype is None:
		ptype = get_project_assoc(name)
	else:
		ptype, src_file = ptype
		if src_file is not None:
			include_files(src_file, os.path.join(project_root, src_file))
	
	if ptype is None or ptype == default_ptype:
		prt.info(f'Project {name} using default project type: {default_ptype}')
		proj_cls = default
	else:
		prt.info(f'Project {name} using project type: {ptype}')
		proj_cls = get_project_type(ptype)
	
	proj = proj_cls(raw=info)

	return proj

	
class set_active_project:
	def __init__(self, project=None):
		self.prev = get_active_project()
		self.new = project
		
		profile = get_profile()
		profile.set_active_project(project)
		
	def __enter__(self):
		pass
	
	def __exit__(self, exc_type, exc_value, exc_traceback):
		set_active_project(self.prev)
	
	
def clear_active_project():
	set_active_project()
	
	
def get_active_project():
	profile = get_profile()
	if profile is not None:
		return profile.get_active_project()
	
# endregion



