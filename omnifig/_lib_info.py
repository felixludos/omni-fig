

long_name = 'omni-fig'
name = 'omnifig'

version = '0.1'

description = 'Universal configuration system for common execution environments'

url = 'https://github.com/felixludos/'

author = 'Felix Leeb'
author_email = 'felixludos.info@gmail.com'

license = 'GPL3'

packages = ['omnifig']

# Automatically get list of requirements from requirements.txt
import os
path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
install_requires = []
if 'requirements.txt' not in os.listdir(path):
    print('WARNING: no requirements.txt found')
    install_requires = ['pyyaml']
    # raise FileNotFoundError('requirements.txt not found, this usually happens if part of this library is missing')
else:
    with open(os.path.join(path, 'requirements.txt'), 'r') as f:
        install_requires = [pk[:-1] for pk in f.readlines() if len(pk)]

