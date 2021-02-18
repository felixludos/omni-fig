
import sys, os
import yaml

from omnibelt import get_printer, get_now, save_yaml, load_yaml

from .errors import WrongInfoContainerType

prt = get_printer(__name__)



class Container:
	'''
	Keeps track of some data extracted from a yaml.
	Consequently a manager is entirely defined by a path to the yaml file
	which holds the source data, however managers can be subclassed to define
	custom behavior in how that data is used.
	
	Main uses include projects and profiles.
	
	Generally any attribute holds data that can be exported,
	however attributes that start with "_" are skipped
	
	'''
	required_attrs = []
	recommended_attrs = []
	
	def __init__(self, name=None, path=None, raw=None):
		self._updated = False
		
		self.name = name
		
		if path is not None:
			raw = self.load_raw_info(path)
			
		self.process(raw)
		
	
	@staticmethod
	def find_container_type(raw):
		'''
		Based on the raw info, confirm that this is the right type to use as the manager.
		This enables using custom subclasses of Manager
		
		:param raw: src info (usually from some yaml file)
		:return: must throw a WrongManager exception if a different one should be used
		'''
		
		ctype = raw.get('type', None)
		
		if ctype is not None:
			ctype_src = raw.get('type_src', None)
			raise WrongInfoContainerType(ctype, ctype_src)
		
	@staticmethod
	def load_raw_info(path):
		'''Loads the info yaml file'''
		raw = load_yaml(path) if os.path.isfile(path) else None
		if raw is None:
			raw = {}
		raw['info_path'] = path # automatically set info_path to the path
		raw['info_dir'] = os.path.dirname(path)
		return raw
	
	# region Getters
	
	def get_name(self):
		'''Gets the container name'''
		return self.name
	def get_info_path(self):
		'''Gets the path to the info file'''
		return getattr(self, 'info_path', None)
	
	# endregion
	
	def __str__(self):
		return f'{self.get_name()}'
	
	def __repr__(self):
		return f'{self.__class__.__name__}({self.get_name()})'
	
	
	def _process(self, raw):
		'''
		Extracts/formats information from the loaded info file.
		
		:param raw: loaded yaml file with contents
		:return:
		'''
		pass
	
	def process(self, raw=None):
		'''
		Extracts/formats information from the loaded info file.
		Calls `_process()` which should be overridden by subclasses.
		
		:param raw: loaded yaml file with contents
		:return:
		'''
		if raw is None:
			raw = {}
		
		self.find_container_type(raw)
		
		self._process(raw)
		
		for key in raw:
			if key not in self.__dict__:
				setattr(self, key, raw[key])
		
		for key in self.required_attrs:
			if getattr(self, key) is None:
				prt.error(f'{key} not found in {self.__class__.__name__} {self}')

		for key in self.recommended_attrs:
			if getattr(self, key) is None:
				prt.warning(f'{key} not found in {self.__class__.__name__} {self}')
	
	
	
	def export(self, path=None):
		'''
		Saves info to yaml (by default where it was loaded from)

		Filters out any entries with keys that start with '_' or have no value (None)
		
		:return: path to export if one is provided, otherwise all the data that would have been exported as a dict
		'''
		
		if path is None:
			path = self.get_info_path()
		
		data = {}
		for k, v in self.__dict__.items():
			if v is not None and k[0] != '_':
				data[k] = v
		
		if self._updated: # something was changed
			data['last_update'] = get_now()
		
		if path is None:
			prt.warning('No export path found, so there is nowhere to save the info')
			return
		
		save_yaml(data, path)
		
		prt.debug(f'Exported {repr(self)} to {path}')
		return path
	
	def cleanup(self):
		if self._updated:
			self.export()
	
