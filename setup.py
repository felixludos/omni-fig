import os
from setuptools import setup, find_packages

info = {'__file__':os.path.join(os.path.abspath(os.path.dirname(__file__)), 'omnifig', '_info.py')}
with open(info['__file__'], 'r') as f:
	exec(f.read(), info)
del info['__file__']

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
      # long_description_content_type=info.get('desc_content_type', 'text/x-rst'),
      url=info.get('url', None),
      author=info.get('author', None),
      author_email=info.get('author_email', None),
      license=info.get('license', None),
      packages=find_packages(),
      entry_points=info.get('entry_points', {}),
      install_requires=info.get('install_requires', []),
      zip_safe=info.get('zip_safe', False),
      )