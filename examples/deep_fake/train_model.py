import omnifig as fig

# note you don't even have to import anything from the src/ here


@fig.script('build-model', description='Build model')
def build_model(config, input_dim=None, output_dim=None): # registered helper function
	'''
	Builds the model and optimizer for training or evaluation.

	Parameters: -- will be extracted from the config
		model: to be instantiated
		optim: defaults to "sgd-optim"

	Returns:
		tuple of model and optimizer

	'''
	if input_dim is None:
		input_dim = config.pull('input_dim')
	if output_dim is None:
		output_dim = config.pull('output_dim')

	# automatically creates the component "model" specified with "model._type", and pass arguments with process
	model = config.peek_process('model', input_dim=input_dim, output_dim=output_dim)

	config.push('optim._type', 'sgd-optim', overwrite=False) # add new arguments (with/out overwriting existing ones)
	# if the "optim" node doesn't exist, it will automatically be created
	
	# The "_type" key is special as it must refer to a registered component,
	# which is created when the node is pulled

	optim = config.pull('optim')
	optim.include_parameters(model.parameters())
	
	return model, optim


@fig.script('train', description='Creates and trains a model') # registers a new script called "train"
def run_train_model(config): # config object containing all necessary config info
	'''
	This script will create a train a model.
	Will create the model using the build-model script.

	Parameters: -- will be extracted from the config
		dataset: default "mnist"
		model: instantiated in the "build-model" script
		optim: instantiated in the "build-model" script

	Returns:
		trained model

	'''
	print('Running train!')

	config.push('dataset._type', 'mnist', overwrite=False)
	dataset = config.pull('dataset') # pull without a default value -> required argument

	print(f'Using dataset: {dataset.name} (len={len(dataset)})')

	model, optim = fig.run_script('build-model', config, # run the "build-model" script including arguments
	                       input_dim=dataset.input_dim, output_dim=dataset.output_dim)
	print(f'Using Model: {model.name}')

	loss = float('inf')

	for x,y in dataset:
		pred = model(x)
		loss = optim.step(y, pred)

	print(f'Final loss: {loss:.3f}')

	return model # return any output that may be useful


if __name__ == '__main__':
	fig.entry('train') # automatically runs "train" script when called directly
	# fig.entry() alone has the same effect as executing the "fig" command from the terminal


