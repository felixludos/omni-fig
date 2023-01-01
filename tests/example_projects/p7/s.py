

import omnifig as fig


@fig.script('get-config', description='get the config or something')
def p7script(config):
	print('Config:')
	print(config.to_yaml())
	return config



@fig.script('script2', description='does something else')
def a_different_script(config):
	print('Config:')
	print(config.to_yaml())
	return config



if __name__ == '__main__':
	fig.entry('get-config')

