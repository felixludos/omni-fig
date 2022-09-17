from typing import List, Dict, Tuple, Optional, Union, Any, Hashable, Sequence, Callable, Generator, Type, Iterable, \
	Iterator
from pathlib import Path
from collections import OrderedDict
from omnibelt import unspecified_argument, load_yaml




class Activatable:
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._is_activated = False

	@property
	def is_activated(self):
		return self._is_activated

	def activate(self, *args, **kwargs):
		if self._is_activated:
			return
		self._activate(*args, **kwargs)
		self._is_activated = True

	def _activate(self, *args, **kwargs):
		pass

	def deactivate(self, *args, **kwargs):
		if not self._is_activated:
			return
		self._deactivate(*args, **kwargs)
		self._is_activated = False

	def _deactivate(self, *args, **kwargs):
		pass



class FileInfo(Activatable):
	@staticmethod
	def load_raw_info(path: Path):
		'''Loads the info yaml file'''
		raw = load_yaml(path, ordered=True) if path.exists() else None
		if raw is None:
			raw = {}
		raw['info_path'] = str(path) # automatically set info_path to the path
		raw['info_dir'] = str(path.parent)
		return raw

	def __init__(self, data=None, **kwargs):
		super().__init__(**kwargs)
		if isinstance(data, str):
			data = Path(data)
		if isinstance(data, Path):
			data = self.load_raw_info(data)
		if data is None:
			data = OrderedDict()
		self.data = data

	@property
	def name(self):
		return self.data.get('name', '-no-name-')

	def __repr__(self):
		return f'{self.__class__.__name__}({self.name})'

	def __str__(self):
		return f'{self.__class__.__name__}[{self.name}]({", ".join(self.data.keys())})'

	def extract_info(self, other: 'FileInfo'):
		self.data = other.data













