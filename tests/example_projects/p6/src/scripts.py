
import omnifig as fig



@fig.script('mirror')
def p2script(config, *args, **kwargs):

	x = config.pull('x', 1)
	y = config.pull('y', 2)

	return x, y, args, kwargs



@fig.script('project-me', description='Get the current project')
def p2script(config, *args, **kwargs):
	return fig.get_current_project()




