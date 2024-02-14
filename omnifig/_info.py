
name = 'omnifig'
long_name = 'omni-fig'

version = '1.0.5'

url = 'https://github.com/felixludos/omni-fig'

description = 'Unleashing Project Configuration and Organization'

author = 'Felix Leeb'
author_email = 'felixludos@hotmail.com'

license = 'MIT'

readme = 'README.rst'

packages = ['omnifig']

logger_name = 'omnifig'

import os
try:
	with open(os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(__file__))), 'requirements.txt'), 'r') as f:
		install_requires = f.readlines()
except:
	install_requires = ['pyyaml', 'toml', 'omnibelt>=0.8.3', 'tabulate']

entry_points = {'console_scripts': 'fig = omnifig.top:entry'}

lib_path = os.path.abspath(os.path.dirname(__file__))


__info__ = dict(locals())
for k in ['f', 'os', '__name__', '__file__', '__doc__', '__package__', '__loader__', '__spec__', '__annotations__',
          '__builtins__', '__cached__']:
	if k in __info__:
		del __info__[k]


__author__ = __info__['author']
__version__ = __info__['version']


import logging
__logger__ = logging.getLogger(__info__.get('logger_name', __name__))
del logging

