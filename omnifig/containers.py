
import sys, os
import yaml
from collections import namedtuple, OrderedDict

from omnibelt import get_printer, get_now

prt = get_printer(__name__)


class WrongInfoContainerType(Exception):
	def __init__(self, mtype, mtype_src=None):
		super().__init__(f'Reload manager using custom subclass: {mtype}')
		self.mtype = mtype
		self.mtype_src = mtype_src
	
	def get_mtype(self):
		return self.mtype
	
	def get_mtype_src(self):
		return self.mtype_src

class Customizable_Infomation:
	'''
	Keeps track of some data extracted from a yaml.
	Consequently a manager is entirely defined by a path to the yaml file
	which holds the source data, however managers can be subclassed to define
	custom behavior in how that data is used.
	
	Main uses include projects and profiles.
	
	Generally any attribute holds data that can be exported,
	however attributes that start with "_" are skipped
	
	'''
	register = None
	mtype = None
	
	required_attrs = []
	recommended_attrs = []
	
	def __init_subclass__(cls, mtype=None):
		cls.mtype = mtype
		if cls.register is not None:
			cls.register.new(mtype, cls)
	
	# @classmethod
	# def get_mtype(cls):
	# 	return cls.mtype
	
	def __init__(self, name=None, raw=None, path=None):
		self._updated = False
		
		if raw is None and path is not None:
			raw = self.load_raw_info(path)
		
		if raw is None:
			raw = {}
		
		self.import_info(raw)
			
		if name is not None:
		# 	prt.warning(f'No name provided for the profile')
		# else:
			self.name = name
	
	@staticmethod
	def find_manager_type(raw):
		'''
		Based on the raw info, confirm that this is the right type to use as the manager.
		This enables using custom subclasses of Manager
		
		:param raw: src info (usually from some yaml file)
		:return: must throw a WrongManager exception if a different one should be used
		'''
		
		mtype = raw.get('type', None)
		
		if mtype is not None:
			mtype_src = raw.get('type_src', None)
			raise WrongInfoContainerType(mtype, mtype_src)
		
	@staticmethod
	def load_raw_info(path):
		with open(path, 'r') as f:
			raw = yaml.safe_load(f)
		raw['info_path'] = path # automatically set info_path to the path
		raw['info_dir'] = os.path.dirname(path)
		return raw
	
	def get_name(self):
		return self.name
	
	def __str__(self):
		return f'{self.get_name()}'
	
	def __repr__(self):
		return f'{self.get_mtype()}:{self.get_name()}'
	
	def get_info_path(self):
		return getattr(self, 'info_path', None)
	
	def import_info(self, raw={}):
		self.find_manager_type(raw)
		
		for key in raw:
			if key not in self.__dict__:
				setattr(self, key, raw[key])
		
		for key in self.required_attrs:
			if getattr(self, key) is None:
				prt.error(f'{key} not found in {self.__class__.__name__} {self}')

		for key in self.recommended_attrs:
			if getattr(self, key) is None:
				prt.warning(f'{key} not found in {self.__class__.__name__} {self}')
	
	def export_info(self, path=None):
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
		
		with open(path, 'w') as f:
			yaml.dump(data, f)
		
		prt.debug(f'Exported {repr(self)} to {path}')
		return path
	
	def cleanup(self):
		if self._updated:
			self.export_info()
	