
import sys, os
from pathlib import Path

TEST_PATH = Path(__file__).parent

CONFIG_PATH = TEST_PATH / 'example_configs'

PROFILES_PATH = TEST_PATH / 'example_profiles'

PROJECTS_PATH = TEST_PATH / 'example_profiles'

os.environ['FIG_PROFILE'] = str(PROFILES_PATH / 'base.yaml')



