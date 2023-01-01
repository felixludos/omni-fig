from typing import Dict, Union, Any
import yaml
from pathlib import Path
from collections import OrderedDict
from omnibelt import load_yaml

from . import __logger__ as prt



class Activatable:
	'''
	Mix-in class for objects that can be activated and deactivated.

	Once activated, the object is in a usable state, and cannot be activated again
	(and the object can only be deactivated if it is already activated).

	Primarily used by :class:`omnifig.abstract.AbstractProfile` and :class:`omnifig.abstract.AbstractProject`.

	'''
	def __init__(self, *args: Any, **kwargs: Any):
		super().__init__(*args, **kwargs)
		self._is_activated = False


	@property
	def is_activated(self) -> bool:
		'''Flag whether the object is currently activated'''
		return self._is_activated


	def activate(self, *args: Any, **kwargs: Any) -> None:
		'''
		Top-level method to activate the object.

		Args:
			*args: Arguments to pass to the :func:`_activate` method
			**kwargs: Keyword arguments to pass to the :func:`_activate` method

		Returns:
			:code:`None`

		'''
		if self._is_activated:
			return
		self._is_activated = True
		self._activate(*args, **kwargs)


	def _activate(self, *args: Any, **kwargs: Any) -> None:
		'''
		Internal method to activate the object. This should be overridden by subclasses.

		This method will only be called once, and only if the object is not already activated.

		Args:
			*args: Any arguments passed to the :func:`activate()` method
			**kwargs: Keyword arguments passed to the :func:`activate()` method

		Returns:
			:code:`None`

		'''
		pass


	def deactivate(self, *args, **kwargs):
		'''
		Top-level method to deactivate the object.

		Args:
			*args: Arguments to pass to the :func:`_deactivate()` method
			**kwargs: Keyword arguments to pass to the :func:`_deactivate()` method

		Returns:
			:code:`None`

		'''
		if not self._is_activated:
			return
		self._deactivate(*args, **kwargs)
		self._is_activated = False


	def _deactivate(self, *args, **kwargs):
		'''
		Internal method to deactivate the object. This should be overridden by subclasses.

		This method will only be called once, and only if the object is currently activated.

		Args:
			*args: Any arguments passed to the :func:`deactivate()` method
			**kwargs: Keyword arguments passed to the :func:`deactivate()` method

		Returns:
			:code:`None`

		'''
		pass



class FileInfo:
	'''Mix-in class for objects that loads and stores information from a file.'''


	@staticmethod
	def load_raw_info(path: Path) -> Dict[str, Any]:
		'''
		Loads the info yaml file at the given path.

		Args:
			path: File path containing the info yaml file

		Returns:
			:code:`dict` containing the loaded info

		'''
		raw = None
		try:
			if path.exists():
				raw = load_yaml(path, ordered=True)
		except yaml.YAMLError:
			prt.error(f'Error loading yaml file: {path}')
		if raw is None:
			raw = {}
		raw['info_path'] = str(path) # automatically set info_path to the path
		raw['info_dir'] = str(path.parent)
		return raw


	def __init__(self, data: Union[str, Path, Dict[str, Any]] = None, **kwargs: Any):
		'''
		Loads the info if the provided `data` is a file path.

		Args:
			data: A file path to a yaml file, or a dictionary containing the info
			**kwargs: Other arguments passed on to ``super()``
		'''
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
		'''The name of the object, as specified in the info file.'''
		return self.data.get('name', '')


	def __repr__(self):
		return f'{self.__class__.__name__}({self.name})'


	def __str__(self):
		return f'{self.__class__.__name__}[{self.name}]({", ".join(self.data.keys())})'


	def extract_info(self, other: 'FileInfo'):
		'''
		Extracts the info from the given object and stores it in this object.

		Usually used to replace :code:`other` with :code:`self`.

		Args:
			other: The source object to extract the info from

		Returns:
			:code:`None`

		'''
		self.data = other.data













