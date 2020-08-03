
import sys, os
import humpack as hp
import yaml, json
from collections import defaultdict
from c3linearize import linearize

from omnibelt import load_yaml, get_printer

from .util import primitives
from .errors import YamlifyError, ParsingError, NoConfigFound, MissingConfigError
from .external import find_config_path
from .registry import create_component, _appendable_keys, Component

nones = {'None', 'none', '_none', '_None', 'null', 'nil', }

prt = get_printer(__name__)

def configurize(data, parent_defaults=True):
	'''
	Transform data container to use config objects (ConfigDict/ConfigList)
	
	:param data: dict/list data
	:param parents_defaults: set parent for each config object in tree
	:return: deep copy of data using ConfigDict/ConfigList
	'''
	if isinstance(data, ConfigType):
		return data
	if isinstance(data, dict):
		d = ConfigDict()
		d.update({k: configurize(v, parent_defaults=parent_defaults) for k, v in data.items()},
		         parent_defaults=parent_defaults)
		return d
	if isinstance(data, list):
		l = ConfigList()
		l.update([configurize(x, parent_defaults=parent_defaults) for x in data],
		         parent_defaults=parent_defaults)
		return l
	if isinstance(data, str) and data in nones:
		return None
	return data


def yamlify(data): # TODO: allow adding yamlify rules for custom objects
	'''
	Transform data container into regular dicts/lists to export to yaml file
	
	:param data: Config object
	:return: deep copy of data using dict/list
	'''
	if data is None:
		return '_None'
	if isinstance(data, dict):
		return {k: yamlify(v) for k, v in data.items() if not k.startswith('__')}
	if isinstance(data, (list, tuple, set)):
		return [yamlify(x) for x in data]
	if isinstance(data, primitives):
		return data
	
	raise YamlifyError(data)


def load_config_from_path(path, process=True):
	'''
	Load the yaml file and transform data to a config object
	
	:param path: must be the full path to a yaml file
	:param process: if False, the loaded yaml data is passed without converting to a config object
	:return: loaded data from path (usually as a config object)
	'''
	# path = find_config_path(path)
	data = load_yaml(path)
	
	if data is None:
		data = {}
	
	if process:
		return configurize(data)
	return data

def process_single_config(data, process=True, parents=None):  # data can either be an existing config or a path to a config
	'''
	This loads the data (if a path or name is provided) and then checks for parents and loads those as well
	
	:param data: config name or path or raw data (dict/list) or config object
	:param process: configurize loaded data
	:param parents: if None, no parents are loaded, otherwise it must be a dict where the keys are the absolute paths
	to the config (yaml) file and values are the loaded data
	:return: loaded data (as a config object or raw)
	'''
	
	if isinstance(data, str):
		data = find_config_path(data)
		data = load_config_from_path(data, process=process)
	
	if parents is not None and 'parents' in data:
		todo = []
		for parent in data.parents:  # prep new parents
			# ppath = _config_registry[parent] if parent in _config_registry else parent
			ppath = find_config_path(parent)
			if ppath not in parents:
				todo.append(ppath)
				parents[ppath] = None
		for ppath in todo:  # load parents
			parents[ppath] = process_single_config(ppath, parents=parents)
	
	return data

def merge_configs(configs, parent_defaults=True):
	'''
	configs should be ordered from oldest to newest (ie. parents first, children last)
	'''
	
	if not len(configs):
		return ConfigDict()
	
	child = configs.pop()
	merged = merge_configs(configs, parent_defaults=parent_defaults)
	
	# load = child.load if 'load' in child else None
	merged.update(child)
	
	return merged


def get_config(*contents, parent_defaults=True, include_load_history=True):  # Top level function
	'''
	Top level function for users. This is the best way to load/create a config object.

	All registered config names or paths must precede any manual entries.
	For manual entries, "--" must be added to the key, followed by the value (``True`` if no value is given)
	
	:param contents: registered configs or paths or manual entries (like in terminal)
	:param parent_defaults: use the parents as defaults when a key is not found
	:param include_load_history: save load ordered history (parents) under the key `_history`
	:return: config object
	'''
	root = ConfigDict()
	if len(contents) == 0:
		return root

	reg = []
	terms = {}
	allow_reg = True
	waiting_key = None
	
	for term in contents:
		
		if term.startswith('--'):
			allow_reg = False
			if waiting_key is not None:
				terms[waiting_key] = True
			waiting_key = term[2:]
		
		elif waiting_key is not None:
			terms[waiting_key] = process_raw_argv(term)
			waiting_key = None
			
		elif allow_reg:
			reg.append(term)
		
		else:
			raise Exception(f'Parsing error: {term} in {contents}')
		
	root.update(configurize(terms))
	
	if len(reg) == 0:
		return root

	parents = {}
	
	root.parents = ConfigList(reg)
	root = process_single_config(root, parents=parents)

	pnames = []
	if len(parents):  # topo sort parents
		
		root_id = ' root'
		src = defaultdict(list)
		src[root_id] = list(find_config_path(p) for p in root.parents) if 'parents' in root else []
		
		for n, data in parents.items():
			src[n] = [find_config_path(p) for p in data.parents] if 'parents' in data else []
		
		order = linearize(src, heads=[root_id], order=True)[root_id]
		order = [root] + [parents[p] for p in order[1:]]
		
		# for analysis, record the history of all loaded parents
		
		order = list(reversed(order))
		
		for p in order:
			if 'parents' in p:
				for prt in p.parents:
					if len(pnames) == 0 or prt not in pnames:
						pnames.append(prt)
		pnames = list(reversed(pnames))
	
	else:  # TODO: clean up
		order = [root]
	
	root = merge_configs(order,
	                     parent_defaults=parent_defaults)  # update to connect parents and children in tree and remove reversed - see Config.update
	
	if include_load_history:
		root._history = pnames
	
	return root


class _Silent_Config:
	def __init__(self, config, setting):
		self.config = config
		self.setting = setting
		self.prev = config.get_silent()
	
	def __enter__(self):
		self.config.set_silent(self.setting)
		return self.config
	
	def __exit__(self, exc_type, exc_val, exc_tb):
		self.config.set_silent(self.prev)

_printing_instance = None
class Config_Printing:
	def __new__(cls, *args, **kwargs): # singleton
		global _printing_instance
		if _printing_instance is None:
			_printing_instance = super().__new__(cls)
		return _printing_instance
	def __init__(self):
		self.level = 0
		self.is_new_line = True
		self.unit = ' > '
		self.style = '| '
		self.silent = False
	
	def inc_indent(self):
		self.level += 1
	def dec_indent(self):
		self.level = max(0, self.level-1)
	
	def process_addr(self, terms):

		# return '.'.join(terms)
		addr = []
		
		skip = False
		for term in terms[::-1]:
			if term == '':
				skip = True
				addr.append('')
			elif not skip:
				addr.append(term)
			else:
				skip = False
		
		addr = '.'.join(addr[::-1])
		return addr
	
	def log_record(self, raw, end='\n', silent=False):
		indent = self.level * self.unit
		style = self.style
		prefix = style + indent
		
		msg = raw.replace('\n', '\n' + prefix)
		if not self.is_new_line:
			prefix = ''
		msg = f'{prefix}{msg}{end}'
		if not (silent or self.silent):
			print(msg, end='')
			self.is_new_line = (len(msg) == 0 and self.is_new_line) or msg[-1] == '\n'
		return msg
		

class ConfigType(hp.Transactionable):
	'''
	The abstract super class of config objects.
	
	The most important methods:
		- ``push()`` - set a parameter in the config
		- ``pull()`` - get a parameter in the config
		- ``sub()`` - get a sub branch of this config
		- ``seq()`` - iterate through all contents
		- ``update()`` - update a config with a different config
		- ``export()`` - save the config object as a yaml file
	
	Another important property of the config object is that it acts as a tree where each node can hold parameters.
	If a parameter cannot be found at one node, it will search up the tree for the parameter.
	
	Config objects also allow for "deep" gets/sets, which means you can get and set parameters not just in
	the current node, but any number of nodes deeper in the tree by passing a list/tuple of keys
	or keys separated by ".".
	
	Note: that all parameters should be valid identifiers (strings with no white space that don't start with a number).
	
	'''

	def __init__(self, *args, _parent_obj_for_defaults=None, **kwargs):
		self.__dict__['_parent_obj_for_defaults'] = _parent_obj_for_defaults
		self.__dict__['_records_keeper_instance'] = Config_Printing()
		self.__dict__['_silent_config_flag'] = False
		self.__dict__['_prefix_used_for_records'] = []
		self.__dict__['_prefix_branch_used_for_records'] = []
		super().__init__(*args, **kwargs)

	def set_silent(self, silent=True):
		self._records_keeper_instance.silent = silent
		# self._silent_config_flag = silent

	def get_silent(self):
		return self._records_keeper_instance.silent

	def silence(self, setting=True):
		return _Silent_Config(self, setting=setting)

	def __getitem__(self, item):

		if isinstance(item, str) and '.' in item:
			item = item.split('.')

		if isinstance(item, (list, tuple)):
			if len(item) == 1:
				item = item[0]
			else:
				return self._single_get(item[0])[item[1:]]
		return self._single_get(item)

	def __setitem__(self, key, value):
		if isinstance(key, str) and '.' in key:
			key = key.split('.')

		if isinstance(key, (list, tuple)):
			if len(key) == 1:
				return self.__setitem__(key[0], value)
			got = self.__getitem__(key[0])
			if isinstance(got, list):
				idx = int(key[1])
				if len(key) == 2:
					return got.__setitem__(idx, value)
				got = got[idx]
				key = key[1:]
			return got.__setitem__(key[1:], value)

		return super().__setitem__(key, configurize(value))

	def __contains__(self, item):
		'''Check if ``item`` is in this config, item can be "deep" (multiple steps'''
		if '.' in item:
			item = item.split('.')

		if isinstance(item, (tuple, list)):
			if len(item) == 1:
				item = item[0]
			else:
				return item[0] in self and item[1:] in self[item[0]]

		return self.contains_nodefault(item) \
			or (not super().__contains__(item)
				and self._parent_obj_for_defaults is not None
				and item[0] != '_'
			    and item in self._parent_obj_for_defaults)

	@staticmethod
	def parse_argv(arg):
		try:
			return json.loads(arg)
		except:
			pass
			# prt.error(f'Json decoding failed for: {arg}')
		return arg

	def _single_get(self, item):

		if not self.contains_nodefault(item) \
				and self._parent_obj_for_defaults is not None \
				and item[0] != '_':
			return self._parent_obj_for_defaults[item]

		return self.get_nodefault(item)

	def get_nodefault(self, item):
		'''Get ``item`` without defaulting up the tree if not found.'''
		val = super().__getitem__(item)
		if val == '__x__':
			raise KeyError(item)
		return val

	def contains_nodefault(self, item):
		'''Check if ``item`` is contained in this config object without defaulting up the tree if ``item`` is not found'''
		if super().__contains__(item):
			return super().__getitem__(item) != '__x__'
		return False

	def sub(self, item):
		
		val = self.get_nodefault(item)
		
		if isinstance(item, (list, tuple)):
			item = '.'.join(item)
		
		if isinstance(val, ConfigType):
			val._prefix_used_for_records.append(item)
		
		return val

	def _record_action(self, action, suffix=None, val=None, silent=False, obj=None,
	                   defaulted=False, byparent=False, bychild=False, pushed=False):

		terms = self._prefix_used_for_records.copy()
		if suffix is not None and len(suffix):
			terms.append(suffix)
			
		name = self._records_keeper_instance.process_addr(terms) if len(terms) else '.'
		
		if pushed:
			name = f'[Pushed] {name}'

		if action == 'alias':
			return self._records_keeper_instance.log_record(f'{name} --> ', end='',
			                                                silent=(silent or self.get_silent()))
		
		origins = ['']
		# if byparent:
		# 	origins.append('(by parent)')
		if defaulted:
			origins.append('(by default)')
		# if bychild:
		# 	origins.append('(by child)')
		origins = ' '.join(origins)
			
		if action in {'creating', 'reusing'}:
			
			assert val is not None, 'no info provided'
			
			cmpn_type = val.pull('_type', silent=True)
			mods = val.pull('_mod', None, silent=True)
			
			mod_info = ''
			if mods is not None:
				if not isinstance(mods, (list, tuple)):
					mods = mods,
				
				mod_info = ' (mods=[{}])'.format(', '.join(m for m in mods)) if len(mods) > 1 \
					else f' (mod={mods[0]})'
			
			end = ''
			if action == 'reusing':
				assert obj is not None, 'no object provided'
				end = f': id={id(obj)}'
			
			head = '' if suffix is None else f' {name}'
			out = self._records_keeper_instance.log_record(f'{action.upper()}{head} '
			                                               f'(type={cmpn_type}){mod_info}{origins}{end}',
			                       silent=silent)
			if action == 'creating':
				self._records_keeper_instance.inc_indent()
			return out
		
		if action in {'pull-dict', 'pull-list'}:
			
			assert val is not None, 'no obj provided'
			
			obj_type = action.split('-')[-1]
			
			out = self._records_keeper_instance.log_record(f'{name} [{obj_type} with {len(val)} item/s]',
			                                               silent=silent)
			self._records_keeper_instance.inc_indent()
			return out
		
		if action in {'created', 'pulled-dict', 'pulled-list'}:
			assert obj is not None, 'no object provided'
			self._records_keeper_instance.dec_indent()
			return ''
			return self._records_keeper_instance.log_record(f'=> id={id(obj)}',
			                                                silent=silent)

		pval = None if val is None else repr(val)
		
		if action == 'entry': # when pulling dict/list
			assert suffix is not None, 'no suffix provided'
			return self._records_keeper_instance.log_record(f'({suffix}): ', end='',
			                                                silent=(silent or self.get_silent()))
		
		if action == 'pulled':
			head = '' if suffix is None else f'{name}: '
			return self._records_keeper_instance.log_record(f'{head}{pval}{origins}',
			                                                silent=silent)
		
	def pull(self, item, *defaults, silent=False, ref=False, no_parent=False, as_iter=False):
		'''
		Top-level function to get parameters from the config object (including automatically creating components)

		:param item: name of the parameter to get
		:param defaults: defaults to check if ``item`` is not found
		:param silent: don't print message that this parameter was pulled
		:param ref: if the parameter is a component that has already been created, get a reference to the created
		component instead of creating a new instance
		:param no_parent: don't default to parent node if the ``item`` is not found
		:param as_iter: return an iterator over the selected value
		:return: value of the parameter (or default if ``item`` is not found)
		'''
		return self._pull(item, *defaults, silent=silent, ref=ref, no_parent=no_parent, as_iter=as_iter)

	def pull_self(self, name='', silent=False, ref=False, as_iter=False):
		return self._process_val(name, self, silent=silent, reuse=ref, is_self=True, as_iter=as_iter)

	def _pull(self, item, *defaults, silent=False, ref=False, no_parent=False, as_iter=False,
	         _byparent=False, _bychild=False, _defaulted=False):
		
		# TODO: change defaults to be a keyword argument providing *1* default, and have item*s* instead,
		#  which are the keys to be checked in order

		if '.' in item:
			item = item.split('.')

		line = []
		if isinstance(item, (list, tuple)):
			line = item[1:]
			item = item[0]

		defaulted = item not in self
		if no_parent and not self.contains_nodefault(item):
			defaulted = True
		byparent = False
		if defaulted:
			if len(defaults) == 0:
				raise MissingConfigError(item)
			val, *defaults = defaults
		else:
			byparent = not self.contains_nodefault(item)
			val = self[item]

		if not defaulted and len(line): # child pull
			val._prefix_used_for_records.append(item)
			out = val._pull(line, *defaults, silent=silent, ref=ref, no_parent=no_parent, as_iter=as_iter,
			               _byparent=_byparent, _bychild=True,
			               _defaulted=_defaulted)
			val._prefix_used_for_records.pop()
			
			val = out
			
		elif byparent: # parent pull
			parent = self.__dict__['_parent_obj_for_defaults']
			old = parent._prefix_used_for_records
			parent._prefix_used_for_records = self._prefix_used_for_records
			parent._prefix_used_for_records.append('')
			# parent._prefix_used_for_records.append('.')
			# self._prefix_used_for_records.clear()
			
			val = parent._pull(item, *line, silent=silent, ref=ref, no_parent=no_parent, as_iter=as_iter,
			                                                     _byparent=True)
			
			parent._prefix_used_for_records.pop()
			self._prefix_used_for_records = parent._prefix_used_for_records
			parent._prefix_used_for_records = old
			
		else: # pull from me
			head = self._prefix_used_for_records.copy()
			
			val = self._process_val(item, val, *defaults, silent=silent, defaulted=defaulted or _defaulted,
			                        as_iter=as_iter, byparent=byparent or _byparent, bychild=_bychild, reuse=ref, )
			
			self._prefix_used_for_records = head

			if type(val) in {list, set}: # TODO: a little heavy handed
				val = tuple(val)

		return val

	def _process_val(self, item, val, *defaults, silent=False,
	                 reuse=False, is_self=False, as_iter=False, **record_flags):
		'''This is used by ``pull()`` to process the recovered value and print the correct message if ``not silent``'''
		
		if as_iter and isinstance(val, ConfigType):
			self._record_action('creating', suffix=item, val=val, silent=silent, **record_flags)
			
			itr = _Config_Iter(val, val)
			
			self._record_action('created', suffix=item, val=val, obj=itr, silent=silent, **record_flags)
			
			return itr
		
		if isinstance(val, dict):
			if '_type' in val:
				
				# val.push('__origin_key', item, silent=True)
				
				if reuse and '__obj' in val:
					# print('WARNING: would usually reuse {} now, but instead creating a new one!!')
					cmpn = val['__obj']
					self._record_action('reusing', suffix=item, val=val, obj=cmpn, silent=silent, **record_flags)
				else:

					self._record_action('creating', suffix=item, val=val, silent=silent, **record_flags)
					
					head = self._prefix_used_for_records
					self._prefix_used_for_records = []
					
					with self.silence(silent or self.get_silent()):
						cmpn = create_component(val)
					
					self._prefix_used_for_records = head
					
					if self.in_transaction():
						if len(item) and not is_self:
							self[item]['__obj'] = cmpn
						else:
							self['__obj'] = cmpn
					
					self._record_action('created', suffix=item, val=val, obj=cmpn, silent=silent, **record_flags)
					
					val = cmpn

			else:
				
				self._record_action('pull-dict', suffix=item, val=val, silent=silent, **record_flags)
				terms = {}
				for k, v in val.items():  # WARNING: pulls all entries in dict
					self._record_action('entry', silent=silent, suffix=k)
					terms[k] = self._process_val(None, v, reuse=reuse, silent=silent)
				self._record_action('pulled-dict', suffix=item, val=val, obj=terms, silent=silent, **record_flags)
				val = terms


		elif isinstance(val, list):
			
			self._record_action('pull-list', suffix=item, val=val, silent=silent, **record_flags)
			terms = []
			for i, v in enumerate(val):  # WARNING: pulls all entries in dict
				self._record_action('entry', silent=silent, suffix=str(i))
				terms.append(self._process_val(None, v, reuse=reuse, silent=silent))
			self._record_action('pulled-list', suffix=item, val=val, obj=terms, silent=silent, **record_flags)
			val = terms

		elif isinstance(val, str) and val[:2] == '<>':  # alias
			alias = val[2:]
			# assert not byparent, 'Using an alias from a parent is not supported: {} {}'.format(item, alias)

			self._record_action('alias', suffix=item, val=alias, silent=silent, **record_flags)
			# self._prefix_used_for_records.clear()
			
			head = self._prefix_used_for_records
			self._prefix_used_for_records = []
			val = self.pull(alias, *defaults, silent=silent)
			self._prefix_used_for_records = head

		else:
			self._record_action('pulled', suffix=item, val=val, silent=silent, **record_flags)

		return val
	
	def push(self, key, val, *_skip, silent=False, overwrite=True, no_parent=True, force_root=False):
		'''
		Set ``key`` with ``val`` in the config object, but pulls ``key`` first so that `val` is only set
		if it is not found or ``overwrite`` is set to ``True``. It will return the current value of ``key`` after
		possibly setting with ``val``.
		
		:param key: key to check/set (can be list or '.' separated string)
		:param val: data to possibly write into the config object
		:param _skip: soak up all other positional arguments to make sure the remaining are keyword only
		:param silent: Do not print messages
		:param overwrite: If key is already set, overwrite with (configurized) 'val'
		:param no_parent: Do not check parent object if not found in self
		:param force_root: Push key to the root config object
		:return: current val of key (updated if written)
		'''
		
		if '.' in key:
			key = key.split('.')

		line = []
		if isinstance(key, (list, tuple)):
			line = key[1:]
			key = key[0]
		
		exists = self.contains_nodefault(key)
		
		parent = self._parent_obj_for_defaults
		
		if parent is not None and force_root:
			return self.get_root().push((key, *line), val, silent=silent, overwrite=overwrite,
			                   no_parent=no_parent)
		elif no_parent:
			# assert not force_root, 'makes no sense'
			parent = None
		
		if exists and len(line): # push me
			child = self.get_nodefault(key)

			old = child._prefix_used_for_records
			child._prefix_used_for_records = self._prefix_used_for_records
			child._prefix_used_for_records.append(key)
			
			out = child.push(line, val, silent=silent, overwrite=overwrite, no_parent=True)
			
			child._prefix_used_for_records.pop()
			self._prefix_used_for_records = child._prefix_used_for_records
			child._prefix_used_for_records = old
			
			return out
		elif parent is not None and key in parent: # push parent

			old = parent._prefix_used_for_records
			parent._prefix_used_for_records = self._prefix_used_for_records
			parent._prefix_used_for_records.append('')
			
			out = parent.push((key, *line), val, silent=silent, overwrite=overwrite, no_parent=no_parent)
			
			parent._prefix_used_for_records.pop()
			self._prefix_used_for_records = parent._prefix_used_for_records
			parent._prefix_used_for_records = old
			
			return out
			
		elif len(line): # push child
			
			child = self.get_nodefault(key)
			old = child._prefix_used_for_records
			child._prefix_used_for_records = self._prefix_used_for_records
			child._prefix_used_for_records.append(key)
			
			out = child.push(line, val, silent=silent, overwrite=overwrite, no_parent=True)
			
			child._prefix_used_for_records.pop()
			self._prefix_used_for_records = child._prefix_used_for_records
			child._prefix_used_for_records = old
		
			return out
		
		if exists and not overwrite:
			return self.pull(key, silent=True)
		
		val = configurize(val)
		self[key] = val
		
		val = self._process_val(key, val, silent=silent, pushed=True)
		
		# TODO clean up _update_tree (maybe should be here)
		
		return val

	def is_root(self): # TODO: move to tree space
		'''Check if this config object has a parent for defaults'''
		return self.get_parent() is None

	def set_parent(self, parent):
		self._parent_obj_for_defaults = parent

	def get_parent(self):
		'''Get parent (returns None if this is the root)'''
		return self._parent_obj_for_defaults
	
	def get_root(self):
		'''Gets the root config object (returns ``self`` if ``self`` is the root)'''
		parent = self.get_parent()
		if parent is None:
			return self
		return parent.get_root()
	
	def export(self, path=None):
		'''Convert all data to a raw data (using dict/list) and save as yaml file to ``path`` if provided.
		Also returns data.'''

		data = yamlify(self)

		if path is not None:
			if os.path.isdir(path):
				path = os.path.join(path, 'config.yaml')
			with open(path, 'w') as f:
				yaml.dump(data, f)
			return path

		return data
	
	def purge_volatile(self):
		raise NotImplementedError
	
	def seq(self):
		return _Config_Iter(self, self)



class ConfigDict(ConfigType, hp.TreeSpace): # TODO: allow adding aliases
	'''
	Keys should all be valid python attributes (strings with no whitespace, and not starting with a number).

	NOTE: avoid setting keys that start with more than one underscore (especially '__obj')
	(unless you really know what you are doing)
	'''

	def purge_volatile(self):
		bad = []
		for k,v in self.items():
			if k.startswith('__'):
				bad.append(k)
			elif isinstance(v, ConfigType):
				v.purge_volatile()
				
		for k in bad:
			del self[k]

	def _missing_key(self, key):
		obj = super()._missing_key(key)
		obj.set_parent(self)
		return obj

	def update(self, other={}, parent_defaults=True):
		'''Merges ``self`` with ``other`` overwriting any parameters in ``self`` with those in ``other``'''
		# if not isinstance(other, ConfigDict):
		# 	# super().update(other)
		# 	other = configurize(other)
		for k, v in other.items():
			isconfig = isinstance(v, ConfigType)
			if self.contains_nodefault(k) and '_x_' == v: # reserved for deleting settings in parents
				del self[k]
				
			elif self.contains_nodefault(k) and isconfig and  \
					(isinstance(v, self[k].__class__) or isinstance(self[k], v.__class__)):
				self[k].update(v)

			elif k in _appendable_keys and v[0] == '+':
				# values of appendable keys can be appended instead of overwritten,
				# only when the new value starts with "+"
				vs = []
				if self.contains_nodefault(k):
					prev = self[k]
					if not isinstance(prev, list):
						prev = [prev]
					vs = prev
				vs.append(v[1:])
				self[k] = vs
				
			else:
				self[k] = v
			
			if parent_defaults and isconfig:
				v.set_parent(self)
				

	def __str__(self):
		return f'[{id(self)}]{super().__repr__()}'



class InvalidKeyError(Exception):
	'''Only raised when a key cannot be converted to an index for ``ConfigList``s'''
	pass

class ConfigList(ConfigType, hp.tlist):

	def purge_volatile(self):
		bad = []
		for k, v in self.items():
			if k.startswith('__'):
				bad.append(k)
			elif isinstance(v, ConfigType):
				v.purge_volatile()
		
		for k in bad:
			del self[k]

	def _str_to_int(self, item):
		'''Convert the input items to indices of the list'''
		if isinstance(item, int):
			return item

		if item[0] == '_':
			item = item[1:]

		try:
			return int(item)
		except TypeError:
			pass

		raise InvalidKeyError(f'failed to convert {item} to an index')
		
	def update(self, other=[], parent_defaults=True):
		'''Overwrite ``self`` with the provided list ``other``'''
		for i, x in enumerate(other):
			isconfig = isinstance(x, ConfigType)
			if len(self) == i:
				self.append(x)
			elif isconfig and (isinstance(x, self[i].__class__) or isinstance(self[i], x.__class__)):
				self[i].update(x)
			else:
				self[i] = x
			if parent_defaults and isconfig:
				x.set_parent(self)
	
	def _single_get(self, item):

		if isinstance(item, slice):
			return self.get_nodefault(item)

		try:
			idx = self._str_to_int(item)
		except InvalidKeyError:
			idx = None

		if idx is not None and self.contains_nodefault(idx):
			return self.get_nodefault(idx)

		if self._parent_obj_for_defaults is not None and item[0] != '_':
			return self._parent_obj_for_defaults[item]

		return self.get_nodefault(item)

	def push(self, first, *rest, overwrite=True, **kwargs):
		'''
		
		:param first: if no additional args are provided in `rest`, then this is used as the value and the key
		is the end of the list, otherwise this is used as key and the first element in `rest` is the value
		:param rest: optional second argument to specify the key, rather than defaulting to the end of the list
		:param kwargs: same keyword args as for the ConfigDict
		:return: same as for ConfigDict
		'''

		if len(rest):
			val, *rest = rest
			return super().push(first, val, *rest, overwrite=overwrite, **kwargs)
		
		val = first
		key = len(self)
		self.append(None)
		return super().push(key, val, *rest, overwrite=True, **kwargs) # note that *rest will have no effect
		
	def contains_nodefault(self, item):
		idx = self._str_to_int(item)
		return -len(self) <= idx < len(self)

	def append(self, item, parent_defaults=True):
		super().append(item)
		if parent_defaults and isinstance(item, ConfigType):
			item.set_parent(self)
		
		# self._update_tree(parent_defaults=parent_defaults)  # TODO: make sure manipulating lists works and updates parents

	def extend(self, item, parent_defaults=True):
		super().extend(item)
		
		if parent_defaults:
			for x in item:
				if isinstance(x, ConfigType):
					x.set_parent(self)

@Component('iter')
class _Config_Iter:
	'''Iterate through a list of parameters, processing each item only when it is iterated over (with ``next()``)'''

	def __init__(self, origin, elements=None): # skips _elements, _type
		self._idx = 0
		# self._name = config._ident
		# assert '_elements' in config, 'No elements found'
		if elements is None:
			elements = origin._elements
		self._elms = elements
		
		self._keys = list(self._elms.keys()) if isinstance(self._elms, dict) else None
		self._prefix = origin._prefix_used_for_records.copy()
		# self._origin = config

	def __len__(self):
		return len(self._elms) - self._idx

	def _next_idx(self):
		
		if self._keys is None:
			return self._idx
		
		while self._idx < len(self._elms):
			idx = self._keys[self._idx]
			
			if self.contains_nodefault(idx) \
					and idx not in {'_elements', '_mod', '_type', '__obj'} \
					and self._elms[idx] is not '__x__':
				return idx
			self._idx += 1
		
		raise StopIteration
		

	def __next__(self):

		if len(self._elms) == self._idx:
			raise StopIteration
		
		idx = self._next_idx()

		backup = self._elms._prefix_used_for_records
		self._elms._prefix_used_for_records = self._prefix

		obj = self._elms.pull(idx)
		
		self._elms._prefix_used_for_records = backup
		
		self._idx += 1
		if self._keys is None:
			return obj
		return idx, obj

	def __iter__(self):
		return self


_config_type = ConfigType
_config_dict = ConfigDict
_config_list = ConfigList

def process_raw_argv(arg):
	return _config_type.parse_argv(arg)


