
import omnifig as fig



@fig.script('mirror')
def p2script(config, *args, **kwargs):

	x = config.pull('x', 1)
	y = config.pull('y', 2)

	return x, y, args, kwargs



@fig.script('project-me', description='Get the current project')
def p2script2(config, *args, **kwargs):
	return fig.get_current_project()



@fig.script('is-quiet', description='check quiet')
def get_silence(config, *args, **kwargs):
	'''checks if the config is silent'''
	return config.silent



@fig.autoscript('add', description='it just adds stuff.')
def check_something(x=5, y=-5):
	return x + y + int(x == y == 2)



@fig.script('repeater')
def repeat_add(config):
	'''
	Heres a docstring about how this script, ``repeater``, is the best
	Args:
		config: thanks to omnifig

	Returns:
		something sometimes

	'''

	out = fig.run_script('add', config)

	config.push('y', 10)

	out2 = fig.run_script('add', config)

	return out, out2

