import os
from yaml import safe_load
from setuptools import setup

with open('.fig.yaml', 'r') as f:
	info = safe_load(f)

if 'readme' in info:
	with open(info['readme'], 'r') as f:
		lines = f.readlines()
	
	readme = []
	valid = 'md' in info['readme']
	for line in lines:
		if valid:
			if 'end-setup-marker-do-not-remove' in line:
				valid = False
			else:
				readme.append(line)
		elif 'setup-marker-do-not-remove' in line:
			valid = True
	
	README = '\n'.join(readme)
else:
	README = ''

setup(name=info.get('name', None),
      version=info.get('version', None),
      description=info.get('description', None),
      long_description=README,
      url=info.get('url', None),
      author=info.get('author', None),
      author_email=info.get('author_email', None),
      license=info.get('license', None),
      packages=info.get('packages', [info['name']]),
      entry_points=info.get('entry_points', {}),
      install_requires=info.get('install_requires', []),
      zip_safe=info.get('zip_safe', False),
      )