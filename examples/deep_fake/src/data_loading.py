
from functools import reduce
import random

import omnifig as fig

class Toy_Dataset(fig.Configurable):
	def __init__(self, dataroot, input_dim, output_dim, name='unknown dataset',
	             labeled=True, num_categories=None, num_samples=1000, **kwargs):

		# input_dim = A.pull('input_dim', '<>input_shape', silent=True)
		if isinstance(input_dim, (list, tuple)):
			input_dim = reduce((lambda x, y: x * y), input_dim)

		# output_dim = A.pull('output_dim', '<>output_shape', silent=True)
		if isinstance(output_dim, (list, tuple)):
			output_dim = reduce((lambda x, y: x * y), output_dim)

		if num_categories is None:
			num_categories = output_dim

		super().__init__(**kwargs)

		self.dataroot = dataroot
		self.name = name

		self.labeled = labeled
		self.num_categories = num_categories
		
		self.input_dim = input_dim
		self.output_dim = output_dim if output_dim is not None and self.labeled else input_dim
		
		self.samples = list(range(num_samples))
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


@fig.component('mnist')
class MNIST(Toy_Dataset):
	def __init__(self, name='mnist', input_dim=(28, 28, 1), output_dim=10, **kwargs):
		super().__init__(name=name, input_dim=input_dim, output_dim=output_dim, **kwargs)


@fig.component('cifar')
class CIFAR(Toy_Dataset):
	def __init__(self, name='cifar', in_color=True, input_dim=None, output_dim=None, num_categories=10, **kwargs):
		if input_dim is None:
			input_dim = (32, 32, 3) if in_color else (32, 32, 1)
		if output_dim is None:
			output_dim = num_categories
		assert num_categories in {10, 100}, f'CIFAR image dataset has either 10 or 100 categories, ' \
		                                    f'not {num_categories}'
		super().__init__(name=name, input_dim=input_dim, output_dim=output_dim, num_categories=num_categories, **kwargs)
		
		
	def _make_grayscale(self):
		pass # do something
	
	
@fig.modifier('even')
class Even(Toy_Dataset):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.samples = [x for x in self.samples if x % 2 == 0]


@fig.modifier('noisy')
class Noisy(Toy_Dataset):
	def __init__(self, *args, noise_weight=None, **kwargs):
		super().__init__(*args, **kwargs)
		self.noise_weight = noise_weight

	def __next__(self):
		x, y = super().__next__()
		
		if self.noise_weight is not None and self.noise_weight > 0:
			x += random.gauss(0,self.noise_weight)

		return x, y


@fig.modifier('rotate')
class Rotated(Toy_Dataset):
	@fig.config_aliases(rotation_prob='prob')
	def __init__(self, *args, rotation_prob=0.5, **kwargs):
		super().__init__(*args, **kwargs)
		self.rotation_prob = rotation_prob

	def __next__(self):
		x, y = super().__next__()
		if random.random() < self.rotation_prob:
			x = x * 1j
		return x, y


@fig.modifier('shuffled')
class Shuffled(Toy_Dataset):
	def __init__(self, *args, shuffle=True, **kwargs):
		super().__init__(*args, **kwargs)
		if shuffle:
			random.shuffle(self.samples)


@fig.modifier('subset')
class Subset(Toy_Dataset):
	def __init__(self, *args, limit=None, **kwargs):
		super().__init__(*args, **kwargs)
		if limit < len(self):
			self.samples = self.samples[:limit]






