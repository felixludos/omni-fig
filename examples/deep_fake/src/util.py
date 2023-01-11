

import sys
import omnifig as fig

@fig.script('print-config', description='Prints out the config (for debugging)')
def print_config(config): # just prints out the config
	'''
	Here's the doc string of the "config" script

	Args:
		config: object created by omni-fig

	Returns:
		the config object

	'''

	print('This is the config:')
	print(config)

	return config


@fig.autocomponent('stdout')  # automatically pulls all arguments in signature before creating
def _get_stdout():  # in this case, we don't need any arguments
	return sys.stdout


@fig.autocomponent('file')
def _get_file(path):
	return open(path, 'a+')




