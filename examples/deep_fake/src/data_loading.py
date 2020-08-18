
from functools import reduce
import random

import omnifig as fig

class Toy_Dataset:
	def __init__(self, A):

		self.dataroot = A.pull('dataroot')
		
		self.name = A.pull('name', 'unknown dataset')
		
		input_dim = A.pull('input_dim', '<>input_shape', silent=True)
		if isinstance(input_dim, (list, tuple)):
			input_dim = reduce((lambda x, y: x * y), input_dim)
		
		output_dim = A.pull('output_dim', '<>output_shape', silent=True)
		if isinstance(output_dim, (list, tuple)):
			output_dim = reduce((lambda x, y: x * y), output_dim)
		
		self.labeled = A.pull('labeled', True)
		
		self.num_categories = A.pull('num_categories', output_dim)
		
		self.input_dim = input_dim
		self.output_dim = output_dim if output_dim is not None and self.labeled else input_dim
		
		self.samples = list(range(A.pull('num_samples', 1000)))
		self.idx = 0
		
	def get_io(self):
		return self.input_dim, self.output_dim
		
	def __len__(self):
		return len(self.samples)
		
	def __getitem__(self, idx):
		val = self.samples[idx]
		return val**0.8, val % self.num_categories # doesn't look much like MNIST or CIFAR :)
		
	def __next__(self):
		if self.idx == len(self):
			raise StopIteration
		
		x,y = self[self.idx]
		
		self.idx += 1
		
		return x,y
		
	def __iter__(self):
		self.idx = 0
		return self
		
@fig.Component('mnist')
class MNIST(Toy_Dataset):
	def __init__(self, A):
		A.push('name', 'mnist')
		A.push('input_shape', (28, 28, 1))
		A.push('output_dim', 10)
		super().__init__(A)

@fig.Component('cifar')
class CIFAR(Toy_Dataset):
	def __init__(self, A):
		A.push('name', 'cifar')
		
		in_shape = 32, 32, 3
		
		in_color = A.pull('in_color', True)
		if not in_color:
			self._make_grayscale()
			in_shape = 32, 32, 1
		
		num_categories = A.pull('num_categories', 10, silent=True)
		assert num_categories in {10, 100}, f'CIFAR image dataset has either 10 or 100 categories, ' \
		                                    f'not {num_categories}'
		
		A.push('input_shape', in_shape)
		A.push('output_dim', num_categories)
		super().__init__(A)
		
		
	def _make_grayscale(self):
		pass # do something
	
	
@fig.AutoModifier('even')
class Even:
	def __init__(self, A):
		super().__init__()
		self.samples = [x for x in self.samples if x % 2 == 0]
		
@fig.AutoModifier('noisy')
class Noisy:
	def __init__(self, A):
		super().__init__(A)
		
		self.noise_weight = A.pull('noise_weight', None)

	def __next__(self):
		x, y = super().__next__()
		
		if self.noise_weight is not None and self.noise_weight > 0:
			x += random.gauss(0,self.noise_weight)

		return x, y

@fig.AutoModifier('rotate')
class Rotated:
	def __init__(self, A):
		super().__init__(A)
		
		self.rotation_prob = A.pull('rotation_prob', '<>prob', 0.5)
	
	def __next__(self):
		x, y = super().__next__()
		if random.random() < self.rotation_prob:
			x = x * 1j
		return x, y
	
@fig.AutoModifier('shuffled')
class Shuffled:
	def __init__(self, A):
		super().__init__(A)
		
		if A.pull('shuffle', True):
			random.shuffle(self.samples)



@fig.Modification('subset')
def get_subset(dataset, A):
	
	limit = A.pull('limit', len(dataset))
	
	if limit < len(dataset):
		dataset.samples = dataset.samples[:limit]
	
	return dataset


