
import omnifig as fig
from . import util


class Module:
	def forward(self, *args, **kwargs):
		raise NotImplementedError

	def __call__(self, *args, **kwargs):
		return self.forward(*args, **kwargs)

	def parameters(self):
		return []


@fig.component('nn')
class NeuralNetwork(fig.Configurable, Module):
	@fig.config_aliases(input_dim='input_shape', output_dim='output_shape')
	def __init__(self, input_dim, output_dim, layers, nonlin='relu', use_gpu=True):
		on_gpu = ' (on gpu)' if use_gpu else ''
		self.info = f'Net({input_dim} -> {nonlin} layers:{layers}{on_gpu} -> {output_dim})'
		self.layers = layers

	def forward(self, x):
		return len(self.layers) * x

	def parameters(self):
		return [self.info]


@fig.component('net')
class DeepModel(fig.Configurable, Module):
	@fig.config_aliases(input_dim='input_shape', output_dim='output_shape')
	def __init__(self, input_dim, output_dim, # arguments without a default must appear in the config object
	             layers=[64, 64], name=None, use_gpu=False, nonlin='relu',
	             logger=None, **kwargs):  # some arguments may include subcomponents that are automatically created
		super().__init__(**kwargs)
		self.name = name
		self.use_gpu = use_gpu

		# although it is not recommended, you can of course also manually create components
		# (but this will hard code their use)
		self.net = NeuralNetwork(input_dim, output_dim, layers, nonlin=nonlin, use_gpu=use_gpu)

		self.logger = logger
	
	def forward(self, x):
		return self.net(x)
	
	def parameters(self):
		return self.net.parameters()


@fig.component('sgd-optim')
class Optim(fig.Configurable):
	def __init__(self, *args, learning_rate=1e-3, **kwargs):
		self.learning_rate = learning_rate
		self.parameters = []
	
	def include_parameters(self, parameters):
		self.parameters.extend(parameters)

	def step(self, y, pred):
		return 0.001

