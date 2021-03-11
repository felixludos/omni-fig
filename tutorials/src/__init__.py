
import omnifig as fig

@fig.Component('simple-model')
class Simple_Model:
	def __init__(self, config):
		# pull paramaters from config object
		self.name = config.pull('name')
		self.save_root = config.pull('save-root', '<>root', None)
		self.size = config.pull('size', 4)
		self.log_results = config.pull('log-results', False)

	
	def __str__(self):
		return self.name


	def learn(self, sample):
		# do something
		return sample * 10 + self.size
	
	
	def log(self, results):
		if self.log_results:
			# do something
			print(f'Logged {len(results)} results')
			pass
		
		
		
@fig.Component('variant-model')
class Complex_Model(Simple_Model):
	def __init__(self, config):
		super().__init__(config)
		
		self.special = config.pull('special-sauce', -1)


	def learn(self, sample):
		intermediate = super().learn(sample)
		# do something complex
		return intermediate + self.special

	def log(self, results):
		print('Complex logging')


@fig.AutoModifier('improved')
class Improved(Simple_Model):
	def __init__(self, config):
		super().__init__(config)
		
		self.size += 2
		
		self.device = config.pull('device', None)
	
		# do something
	
	def __str__(self):
		return f'Improved-{super().__str__()}[{self.device}]'
	
	def learn(self, sample):
		print('Using improved learning method')
		return super().learn(sample)
	
	

@fig.Script('fake-training-script')
def simple_script(config):
	
	print('Running "fake-training-script"')
	
	model = config.pull('model', None, ref=True)
	
	if model is None:
		print('No model found')

	data = config.pull('data', [1,2,3])
	
	result = []
	
	for	sample in data:
		out = model.learn(sample)
		result.append(out)
		
	model.log(result)
	model.save()
	
	print(f'Trained {model} with {len(data)} samples')
	
	return result
	
	

@fig.AutoScript('select-model')
def show_model(model, epochs=10, device=None):
	print(f'Selected model: {model} (epochs={epochs}, device={device})')
	
	# do something
	
	return model

