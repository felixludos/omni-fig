

import sys
import omnifig as fig


@fig.autocomponent('stdout')  # automatically pulls all arguments in signature before creating
def _get_stdout():  # in this case, we don't need any arguments
	return sys.stdout


@fig.autocomponent('file')
def _get_file(path):
	return open(path, 'a+')




