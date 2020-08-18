
import omnifig as fig
from . import util

@fig.AutoComponent('net') # for AutoComponents the arguments are automatically extracted from the config object
class DeepNet:
	def __init__(self, input_dim, output_dim, # arguments without a default must appear in the config object
	             layers=[64 ,64], name=None, use_gpu=False, nonlin='relu',
	             logger=None, ): # some arguments may include subcomponents that are automatically created
		self.name = name
		self.use_gpu = use_gpu
		
		self.layers = util.create_nn(input_dim, output_dim, layers,
		                             nonlin=nonlin, use_gpu=use_gpu)
		
		self.logger = logger
	
	def forward(self, x):
		return self.layers(x)
	
	def parameters(self):
		return self.layers.parameters()

@fig.Component('sgd-optim')
class Optim:
	def __init__(self, A):
		self.learning_rate = A.pull('learning_rate', 1e-3)
		self.parameters = []
	
	def include_parameters(self, parameters):
		self.parameters.extend(parameters)

