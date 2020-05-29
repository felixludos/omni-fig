import os
from setuptools import setup
from omnifig import _lib_info as info

with open('README.md', 'r') as f:
      lines = f.readlines()

readme = []
valid = False
for line in lines:
      if valid:
            if 'end-setup-marker-do-not-remove' in line:
                  valid = False
            else:
                  readme.append(line)
      elif 'setup-marker-do-not-remove' in line:
            valid = True

README = '\n'.join(readme)

setup(name=info.name,
      version=info.version,
      description=info.description,
      long_description=README,
      url=info.url,
      author=info.author,
      author_email=info.author_email,
      license=info.license,
      packages=info.packages,
      scripts=info.scripts,
      install_requires=info.install_requires,
      zip_safe=False
      )
