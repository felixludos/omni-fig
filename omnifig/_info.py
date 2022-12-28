

name = 'omnifig'
long_name = 'omni-fig'

version = '0.9.2'

url = 'https://github.com/felixludos/omni-fig'


description = 'Unleashing Project Management and Configuration'

author = 'Felix Leeb'
author_email = 'felixludos.info@gmail.com'

license = 'MIT'

readme = 'README.rst'

packages = ['omnifig']

logger_name = 'omnifig'

import os
try:
	with open(os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(__file__))), 'requirements.txt'), 'r') as f:
		install_requires = f.readlines()
except:
	install_requires = ['pyyaml', 'toml', 'C3Linearize', 'omnibelt', 'tabulate']
del os

entry_points = {'console_scripts': 'fig = omnifig.top:entry'}
