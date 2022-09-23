

import sys
import omnifig as fig


@fig.autocomponent('stdout')  # automatically pulls all arguments in signature before creating
def _get_stdout():  # in this case, we don't need any arguments
	return sys.stdout


@fig.autocomponent('file')
def _get_file(path):
	return open(path, 'a+')


@fig.autocomponent('nn')
def create_nn(input_dim, output_dim, layers, nonlin='relu', use_gpu=True):
	on_gpu = ' (on gpu)' if use_gpu else ''
	return f'Net({input_dim} -> {nonlin} layers:{layers}{on_gpu} -> {output_dim})'




