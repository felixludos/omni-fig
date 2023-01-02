
import sys, os
from pathlib import Path

TEST_PATH = Path(__file__).parent

CONFIG_PATH = TEST_PATH / 'example_configs'

PROFILES_PATH = TEST_PATH / 'example_profiles'

PROJECTS_PATH = TEST_PATH / 'example_projects'

os.environ['OMNIFIG_PROFILE'] = str(PROFILES_PATH / 'base.yaml')


import omnifig as fig


def reset_profile(name='base'):
	os.environ['OMNIFIG_PROFILE'] = str(PROFILES_PATH / f'{name}.yaml')
	fig.ProfileBase._profile = None
	return fig.get_profile()

