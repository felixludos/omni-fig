
import sys, os

from .profiles import Profile
from .util import global_settings

from omnibelt import get_printer, resolve_order

prt = get_printer(__name__)


PROFILE_NAME = 'FIG_PROFILE'


_profile_cls = Profile

def set_profile_cls(cls):
	'''Set the class used when loading the profile'''
	prt.debug(f'Profile cls set to: {cls.__name__}')
	global_settings['profile_cls'] = cls
set_profile_cls(Profile) # default

def get_profile_cls():
	'''Get the class used when loading the profile'''
	return global_settings['profile_cls']


_profile = None
def set_profile(profile):
	'''Set the loaded profile object'''
	global _profile
	prt.debug(f'Profile set to: {profile}')
	_profile = profile


def load_profile(**overrides):
	'''
	Load the profile with the yaml file with the path found
	with the environment variable ``FIG_PROFILE``
	
	:param overrides: Any additional overrides to use instead of checking the environment variables
	:return: loaded profile object
	'''
	global _profile
	
	profile_path = resolve_order(PROFILE_NAME, overrides, os.environ)
	if profile_path is None:
		prt.warning(f'No profile path provided (can be set with environment variable: {PROFILE_NAME})')
	
	# profile_path = None # testing
	_profile = _profile_cls(path=profile_path)
	
	if profile_path is None:
		prt.info('No profile path found')
	
	return _profile

def get_profile(**overrides):
	'''Returns current profile (which gets loaded if there is None)'''
	if _profile is None:
		load_profile(**overrides)
	return _profile

class set_current_project:
	'''Context manager to change set the current project in the context'''
	def __init__(self, project=None):
		profile = get_profile()

		self.prev = profile.get_current_project()
		self.new = project if project is None else profile.get_project(project)
		
		profile.set_active_project(self.new)
	
	def __enter__(self):
		pass
	
	def __exit__(self, exc_type, exc_value, exc_traceback):
		set_current_project(self.prev)

def clear_current_project():
	'''Unset the current project (setting it to None)'''
	set_current_project()



