
import sys, os

from .profiles import Profile

from omnibelt import get_printer, resolve_order

prt = get_printer(__name__)


PROFILE_NAME = 'FIG_PROFILE'


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
	
	profile_path = resolve_order(PROFILE_NAME, overrides, os.environ)
	if profile_path is None:
		prt.warning(f'No profile path provided (can be set with environment variable: {PROFILE_NAME})')
	
	_profile = _profile_cls(path=profile_path)
	
	if profile_path is None:
		prt.info('No profile path found')
	
	return _profile


def get_profile(**overrides):
	if _profile is None:
		load_profile(**overrides)
	return _profile

def get_project(ident):
	profile = get_profile()
	if profile is not None:
		return profile.get_project(ident)


class set_current_project:
	def __init__(self, project=None):
		self.prev = get_current_project()
		self.new = project
		
		profile = get_profile()
		profile.set_active_project(project)
	
	def __enter__(self):
		pass
	
	def __exit__(self, exc_type, exc_value, exc_traceback):
		set_current_project(self.prev)


def clear_current_project():
	set_current_project()


def get_current_project():
	profile = get_profile()
	if profile is not None:
		return profile.get_current_project()





