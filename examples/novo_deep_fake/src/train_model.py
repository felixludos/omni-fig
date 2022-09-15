
import omnifig as fig

def build_model(A): # un registered helper function
	
	model = A.pull('model') # automatically creates the component "model" refers to based on "model._type"
	
	A.push('optim._type', 'sgd-optim', overwrite=False) # add new arguments (with/out overwriting existing ones)
	# if the "optim" node doesn't exist, it will automatically be created
	
	# The "_type" key is special as it must refer to a registered component,
	# which is created when the node is pulled

	optim = A.pull('optim')
	optim.include_parameters(model.parameters())
	
	return model, optim


@fig.Script('train', description='Creates and trains a model') # registers a new script called "train"
def run_train_model(A): # config object containing all necessary config info
	print('Running train!')

	model, optim = build_model(A)

	A.push('dataset._type', 'mnist', overwrite=False)
	dataset = A.pull('dataset') # pull without a default value -> required argument

	print(f'Using dataset: {dataset.name} (len={len(dataset)})')

	print(f'Using Model: {model.name}')

	for x,y in dataset:
		
		pred = model(x)
		loss = optim.step(y, pred)

	print(f'Final loss: {loss:.3f}')

	return model # return any output that may be useful


if __name__ == '__main__':
	fig.entry('train') # automatically runs "train" script when called directly
	# fig.entry() alone has the same effect as executing the "fig" command from the terminal


