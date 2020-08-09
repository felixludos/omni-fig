
import sys, os
import humpack as hp
import yaml, json
from collections import defaultdict, OrderedDict
from c3linearize import linearize

from omnibelt import load_yaml, get_printer

from .util import primitives
from .errors import YamlifyError, ParsingError, NoConfigFound, MissingConfigError, UnknownActionError
from .external import find_config_path
from .registry import create_component, _appendable_keys, Component

nones = {'None', 'none', '_none', '_None', 'null', 'nil', }

prt = get_printer(__name__)

def configurize(data):
	'''
	Transform data container to use config objects (ConfigDict/ConfigList)
	
	:param data: dict/list data
	:return: deep copy of data using ConfigDict/ConfigList
	'''
	if isinstance(data, ConfigType):
		return data
	if isinstance(data, dict):
		return ConfigDict(data={k: configurize(v) for k, v in data.items()})
	if isinstance(data, (list, set)):
		return ConfigList(data=[configurize(x) for x in data])
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
		for parent in data['parents']:  # prep new parents
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
		
	if waiting_key is not None:
		terms[waiting_key] = True
		
	root.update(configurize(terms))
	
	if len(reg) == 0:
		return root

	parents = {}
	
	root['parents'] = ConfigList(data=reg)
	root = process_single_config(root, parents=parents)

	pnames = []
	if len(parents):  # topo sort parents
		
		root_id = ' root'
		src = defaultdict(list)
		
		names = {find_config_path(p): p for p in root['parents']} if 'parents' in root else {}
		src[root_id] = list(names.keys())
		
		for n, data in parents.items():
			connections = {find_config_path(p): p for p in data['parents']} if 'parents' in data else {}
			names.update(connections)
			src[n] = list(connections.keys())
		
		order = linearize(src, heads=[root_id], order=True)[root_id]
		
		pnames = [names[p] for p in order[1:]]
		order = [root] + [parents[p] for p in order[1:]]
		
		# for analysis, record the history of all loaded parents

		order = list(reversed(order))
		
		# for p in order:
		# 	if 'parents' in p:
		# 		for prt in p.parents:
		# 			if len(pnames) == 0 or prt not in pnames:
		# 				pnames.append(prt)
		# pnames = list(reversed(pnames))
	
	else:  # TODO: clean up
		order = [root]
	
	root = merge_configs(order,
	                     parent_defaults=parent_defaults)  # update to connect parents and children in tree and remove reversed - see Config.update
	
	if include_load_history:
		root['_history'] = pnames
	
	return root


class _Silent_Config:
	def __init__(self, config, setting):
		self.config = config
		self.setting = setting
		self.prev = config._get_silent()
	
	def __enter__(self):
		self.config._set_silent(self.setting)
		return self.config
	
	def __exit__(self, exc_type, exc_val, exc_tb):
		self.config._set_silent(self.prev)

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
	
	def __repr__(self):
		return f'ConfigPrinting[{id(self)}]'
	def __str__(self):
		return f'ConfigPrinting'
	
	def inc_indent(self):
		self.level += 1
	def dec_indent(self):
		self.level = max(0, self.level-1)
	
	def process_addr(self, *terms):

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
		
		if not len(addr):
			return '.'
		
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
# class ConfigType(object):
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
	
	Note: that all parameters must not contain "." and should generally be valid identifiers
	(strings with no white space that don't start with a number).
	
	'''

	def __init__(self, parent=None, silent=False, printer=None, prefix=None, data=None):
		
		
		if printer is None:
			printer = Config_Printing()
		self.__dict__['_printer'] = printer
		
		if prefix is None:
			prefix = []
		self.__dict__['_prefix'] = prefix
		self.__dict__['_hidden_prefix'] = prefix.copy()
		
		self.set_parent(parent)
		self._set_silent(silent)

		super().__init__()
		
		if data is not None:
			self.update(data)
		
	# region Silencing
	
	def _set_silent(self, silent=True):
		self.__dict__['_printer'].silent = silent
		# self._silent_config_flag = silent

	def _get_silent(self):
		return self.__dict__['_printer'].silent

	def silenced(self, setting=True):
		return _Silent_Config(self, setting=setting)

	# endregion

	# region Parents
	
	def is_root(self):  # TODO: move to tree space
		'''Check if this config object has a parent for defaults'''
		return self.get_parent() is None
	
	def set_parent(self, parent):
		self.__dict__['_parent'] = parent
	
	def get_parent(self):
		'''Get parent (returns None if this is the root)'''
		return self.__dict__['_parent']
	
	def get_root(self):
		'''Gets the root config object (returns ``self`` if ``self`` is the root)'''
		parent = self.get_parent()
		if parent is None:
			return self
		return parent.get_root()
	
	# endregion
	
	# region Addressing
	
	def _get_printer(self):
		return self.__dict__['_printer']
	
	def get_prefix(self):
		return self._prefix
	
	def _send_prefix(self, obj=None, new=None):
		
		if new is not None:
			self._append_prefix(new)
		
		if obj is not None:
			obj._swap_prefix(self._prefix)
			
	def _receive_prefix(self, obj=None, pop=False):
		
		if obj is not None:
			self._swap_prefix(obj._prefix)
			
		if pop:
			self._pop_prefix()
		
	def _swap_prefix(self, prefix=None):
		if prefix is None:
			prefix = self._hidden_prefix.copy()
		self._prefix = prefix
		return prefix
		
	def _store_prefix(self):
		self._hidden_prefix = self._prefix.copy()
		
	def _append_prefix(self, item):
		self._prefix.append(item)
	def _pop_prefix(self):
		self._prefix.pop()
		
	
	# endregion
	
	# region Misc
	
	@staticmethod
	def parse_argv(arg):
		try:
			return json.loads(arg)
		except:
			pass
			# prt.error(f'Json decoding failed for: {arg}')
		return arg
	
	def purge_volatile(self):
		raise NotImplementedError
	
	# endregion
	
	# region Get/Set/Contains
	
	def __setitem__(self, key, value):
		if isinstance(key, str) and '.' in key:
			key = key.split('.')

		if isinstance(key, (list, tuple)):
			if len(key) == 1:
				return self.__setitem__(key[0], value)
			child = self.__getitem__(key[0])
			assert isinstance(child, ConfigType)
			return child.__setitem__(key[1:], value)
			# if isinstance(child, ConfigType):
			# 	return child.__setitem__(key[1:], value)
			# if not isinstance(child, ConfigType):
			# 	prt.warning(f'Trying to set {key[1:]} in {child}')
			# return child.__setitem__(key[1:], value)

		value = configurize(value)

		if isinstance(value, ConfigType):
			value.set_parent(self)
		return super().__setitem__(key, value)

	
	def __getattr__(self, item):
		return super().__getattribute__(item)
	
	def __setattr__(self, key, value):
		return super().__setattr__(key, value)
	
	def __getitem__(self, item):

		if isinstance(item, str) and '.' in item:
			item = item.split('.')

		if isinstance(item, (list, tuple)):
			if len(item) == 1:
				item = item[0]
			else:
				return self.__getitem__(item[0])[item[1:]]

		parent = self.get_parent()

		if  not self.contains_nodefault(item) \
				and parent is not None \
				and item[0] != '_':
			return parent[item]

		return self._single_get(item)

	def get_nodefault(self, item):
		'''Get ``item`` without defaulting up the tree if not found.'''

		if isinstance(item, str) and '.' in item:
			item = item.split('.')

		if isinstance(item, (list, tuple)):
			if len(item) == 1:
				item = item[0]
			else:
				return self.get_nodefault(item[0])[item[1:]]

		return self._single_get(item)

	def _single_get(self, item):
		try:
			val = super().__getitem__(item)
		except KeyError:
			return self._missing_key(item)

		# if val == '__x__':
		# 	raise MissingConfigError(item)
		return val

	def _missing_key(self, key):
		obj = self.__class__(parent=self)
		self.__setitem__(key, obj)
		return obj


	def __contains__(self, item):
		'''Check if ``item`` is in this config, item can be "deep" (multiple steps'''
		if isinstance(item, str) and '.' in item:
			item = item.split('.')

		if isinstance(item, (tuple, list)):
			if len(item) == 1:
				item = item[0]
			else:
				return item[0] in self and item[1:] in self[item[0]]

		parent = self.get_parent()

		return self.contains_nodefault(item) \
			or (not super().__contains__(item)
				and parent is not None
				and item[0] != '_'
			    and item in parent)

	def contains_nodefault(self, item):
		'''Check if ``item`` is contained in this config object without defaulting up the tree if ``item`` is not found'''

		if isinstance(item, str) and '.' in item:
			item = item.split('.')

		if isinstance(item, (tuple, list)):
			if len(item) == 1:
				item = item[0]
			else:
				return self.contains_nodefault(item[0]) and self[item[0]].contains_nodefault(item[1:])

		if super().__contains__(item):
			return self.get_nodefault(item) is not '__x__'
		return False

	# endregion
	
	
	def sub(self, item):
		
		val = self.get_nodefault(item)
		
		if isinstance(item, (list, tuple)):
			item = '.'.join(item)
		
		if isinstance(val, ConfigType):
			self._swap_prefix()
			val._send_prefix(self)
			val._append_prefix(item)
			val._store_prefix()
		
		return val


	def _record_action(self, action, suffix=None, val=None, silent=False, obj=None,
	                   defaulted=False, pushed=False):

		printer = self._get_printer()

		if action == 'defaulted':
			return ''
		
		name = printer.process_addr(*self.get_prefix(), suffix)
		
		if pushed:
			name = '[Pushed] ' + name

		if 'alias' in action:
			return printer.log_record(f'{name} --> ', end='', silent=silent)
		
		origins = ' (by default)' if defaulted else ''
		
		if action == 'removing':
			obj_type = action.split('-')[-1]
			return printer.log_record(f'REMOVING {name}', silent=silent)
		
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
				end = f': id={hex(id(obj))}'
			
			head = '' if suffix is None else f' {name}'
			out = printer.log_record(f'{action.upper()}{head} '
			                                               f'(type={cmpn_type}){mod_info}{origins}{end}',
			                       silent=silent)
			if action == 'creating':
				printer.inc_indent()
			return out
		
		if action in {'iter-dict', 'iter-list'}:
			obj_type = action.split('-')[-1]
			
			head = '' if suffix is None else f'{name} [{obj_type} with {len(val)} item/s]'
			return printer.log_record(f'ITERATOR {head}{origins}', silent=silent)
		
		if action in {'pull-dict', 'pull-list'}:
			
			assert val is not None, 'no obj provided'
			
			obj_type = action.split('-')[-1]
			
			out = printer.log_record(f'{name} [{obj_type} with {len(val)} item/s]', silent=silent)
			printer.inc_indent()
			return out
		
		if action in {'created', 'pulled-dict', 'pulled-list'}:
			assert obj is not None, 'no object provided'
			printer.dec_indent()
			return ''
			return printer.log_record(f'=> id={hex(id(obj))}', silent=silent)

		pval = None if val is None else repr(val)
		
		if action == 'entry': # when pulling dict/list
			assert suffix is not None, 'no suffix provided'
			return printer.log_record(f'({suffix}): ', end='',
			                          silent=(silent or self._get_silent()))
		
		if action == 'pulled':
			head = '' if suffix is None else f'{name}: '
			return printer.log_record(f'{head}{pval}{origins}', silent=silent)
		
		raise UnknownActionError(action)
		
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
		self._swap_prefix()
		return self._pull(item, *defaults, silent=silent, ref=ref, no_parent=no_parent, as_iter=as_iter, _origin=self)

	def pull_self(self, name='', silent=False, ref=False, as_iter=False):
		self._swap_prefix()
		return self._process_val(name, self, silent=silent, reuse=ref, is_self=True, as_iter=as_iter, _origin=self)

	def _pull(self, item, *defaults, silent=False, ref=False, no_parent=False, as_iter=False,
	          _defaulted=False, _origin=None):
		
		# TODO: change defaults to be a keyword argument providing *1* default, and have item*s* instead,
		#  which are the keys to be checked in order

		if '.' in item:
			item = item.split('.')

		line = []
		if isinstance(item, (list, tuple)):
			line = item[1:]
			item = item[0]

		defaulted = item not in self
		byparent = not self.contains_nodefault(item)
		if no_parent and byparent:
			defaulted = True
		if defaulted:
			if len(defaults) == 0:
				raise MissingConfigError(item)
			val, *defaults = defaults
		else:
			val = self[item]

		if len(line) and not isinstance(val, ConfigType):
			defaulted = True
			if len(defaults) == 0:
				raise MissingConfigError(item)
			val, *defaults = defaults

		if defaulted: # try again with new value

			_origin._swap_prefix()
			
			val = _origin._process_val(item, val, *defaults, silent=silent, defaulted=defaulted or _defaulted,
			                        as_iter=as_iter, reuse=ref, _origin=_origin)

		elif len(line): # child pull
			if not isinstance(val, ConfigType):
				prt.warning(f'Pulling through a non-config object: {val}')
			
			self._send_prefix(val, item)
			out = val._pull(line, *defaults, silent=silent, ref=ref, no_parent=no_parent, as_iter=as_iter,
			               _defaulted=_defaulted, _origin=_origin)
			
			val = out
			
		elif byparent: # parent pull
			parent = self.get_parent()

			self._send_prefix(parent, '')
			val = parent._pull((item, *line), *defaults, silent=silent, ref=ref, no_parent=no_parent, as_iter=as_iter,
			                   _origin=_origin)
			
		else: # process val from me/defaults
			val = self._process_val(item, val, *defaults, silent=silent, defaulted=defaulted or _defaulted,
			                        as_iter=as_iter, reuse=ref, _origin=_origin)
			
			if type(val) in {list, set}: # TODO: a little heavy handed
				val = tuple(val)

		return val

	def _process_val(self, item, val, *defaults, silent=False,
	                 reuse=False, is_self=False, as_iter=False, _origin=None, **record_flags):
		'''This is used by ``pull()`` to process the recovered value and print the correct message if ``not silent``'''
		
		if as_iter and isinstance(val, ConfigType):
			
			obj_type = 'list' if isinstance(val, list) else 'dict'
			
			self._record_action(f'iter-{obj_type}', suffix=item, val=val, silent=silent, **record_flags)
			
			itr = _Config_Iter(val, val)
			
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
					
					self._swap_prefix()
					
					with self.silenced(silent or self._get_silent()):
						cmpn = create_component(val)
					
					# self._swap_prefix()
					
					# if self.in_transaction(): # TODO: make transactionable again
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
					terms[k] = val._process_val('', v, reuse=reuse, silent=silent, _origin=_origin)
				self._record_action('pulled-dict', suffix=item, val=val, obj=terms, silent=silent, **record_flags)
				val = terms


		elif isinstance(val, list):
			
			self._record_action('pull-list', suffix=item, val=val, silent=silent, **record_flags)
			terms = []
			for i, v in enumerate(val):  # WARNING: pulls all entries in list
				self._record_action('entry', silent=silent, suffix=str(i))
				terms.append(val._process_val('', v, reuse=reuse, silent=silent, _origin=_origin))
			self._record_action('pulled-list', suffix=item, val=val, obj=terms, silent=silent, **record_flags)
			val = terms

		elif isinstance(val, str) and val.startswith('<>'):  # local alias (looks for alias locally)
			alias = val[2:]
			
			self._record_action('local-alias', suffix=item, val=alias, silent=silent, **record_flags)
			
			# self._send_prefix(_origin)
			# val = _origin._pull(alias, *defaults, silent=silent, _origin=_origin)
		
			val = self._pull(alias, *defaults, silent=silent, _origin=_origin)
			# self._receive_prefix(_origin)
			
		elif isinstance(val, str) and val.startswith('<o>'): # origin alias (returns to origin to find alias)
			alias = val[3:]
			
			self._record_action('origin-alias', suffix=item, val=alias, silent=silent, **record_flags)
			
			_origin._swap_prefix()
			val = _origin._pull(alias, *defaults, silent=silent, _origin=_origin)
			
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
		self._swap_prefix()
		return self._push(key, val, silent=silent, overwrite=overwrite, no_parent=no_parent, force_root=force_root)
	
	def _push(self, key, val, silent=False, overwrite=True, no_parent=True, force_root=False, _origin=None):
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
		
		parent = self.get_parent()
		
		if parent is not None and force_root:
			return self.get_root().push((key, *line), val, silent=silent, overwrite=overwrite,
			                   no_parent=no_parent)
		elif no_parent:
			parent = None
		
		if exists and len(line): # push me
			child = self.get_nodefault(key)

			self._send_prefix(child, key)

			out = child.push(line, val, silent=silent, overwrite=overwrite, no_parent=True)
			
			return out
		elif parent is not None and key in parent: # push parent

			self._send_prefix(parent, '')
			
			out = parent.push((key, *line), val, silent=silent, overwrite=overwrite, no_parent=no_parent)
			
			return out
			
		elif len(line): # push child
			
			child = self.get_nodefault(key)
			
			self._send_prefix(child, key)
			
			out = child.push(line, val, silent=silent, overwrite=overwrite, no_parent=True)
		
			return out
		
		if exists and not overwrite:
			return self._pull(key, silent=True)
		
		if exists and isinstance(val, str) and val == '_x_':
			self._record_action('removing', suffix=key, val=val, silent=silent)
			del self[key]
			return
		
		val = configurize(val)
		# val = self.__setitem__(key, val)
		
		self[key] = val
		# val = self[key]
		
		val = self._process_val(key, val, silent=silent, pushed=True)
		
		return val

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
	
	def seq(self):
		return _Config_Iter(self, self)



class ConfigDict(ConfigType, hp.tdict):
# class ConfigDict(ConfigType, OrderedDict):
	
	'''
	Keys should all be valid python attributes (strings with no whitespace, and not starting with a number).

	NOTE: avoid setting keys that start with more than one underscore (especially '__obj')
	(unless you really know what you are doing)
	'''
	
	# def purge_volatile(self):
	# 	bad = []
	# 	for k, v in self.items():
	# 		if k.startswith('__'):
	# 			bad.append(k)
	# 		elif isinstance(v, ConfigType):
	# 			v.purge_volatile()
	#
	# 	for k in bad:
	# 		del self[k]
	
	def update(self, other):
		# '''Merges ``self`` with ``other`` overwriting any parameters in ``self`` with those in ``other``'''
		# return super().update(other)
		
		# other = configurize(other)
		# if not isinstance(other, ConfigDict):
		# 	print(type(self), type(other))
		# 	raise TypeError(self, other)
		
		assert isinstance(other, dict), f'invalid: {type(other)}'
		
		for k, v in other.items():
			isconfig = isinstance(v, ConfigType)
			exists = self.contains_nodefault(k)
			if exists and '_x_' == v:  # reserved for deleting settings in parents
				del self[k]
			
			elif exists and isconfig and \
					(isinstance(v, self[k].__class__)
					 or isinstance(self[k], v.__class__)):
				self[k].update(v)
				
			else:
				self[k] = v
	
	def __str__(self):
		return '[{}]{}{}{}'.format(id(self), '{{', ', '.join(f'{k}' for k in self), '}}')
	
	# def __str__(self):
	# 	return f'[{id(self)}]{super().__repr__()}'


class InvalidKeyError(Exception):
	'''Only raised when a key cannot be converted to an index for ``ConfigList``s'''
	pass

class ConfigList(ConfigType, hp.tlist):
# class ConfigList(ConfigType, list):

	def __init__(self, *args, empty_fill_value=None, **kwargs):
		super().__init__(*args, **kwargs)
		self._empty_fill_value = empty_fill_value

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

		try:
			# if item[0] == '_':
			# 	item = item[1:]
			
			return int(item)
		except (TypeError, ValueError):
			pass

		raise InvalidKeyError(f'failed to convert {item} to an index')
		
	def update(self, other):
		'''Overwrite ``self`` with the provided list ``other``'''
		for i, x in enumerate(other):
			isconfig = isinstance(x, ConfigType)
			if len(self) == i:
				self.append(x)
			elif isconfig and (isinstance(x, self[i].__class__) or isinstance(self[i], x.__class__)):
				self[i].update(x)
			else:
				self[i] = x
	
	def _single_get(self, item):
		try:
			idx = self._str_to_int(item)
		except InvalidKeyError:
			idx = None
		
		return super()._single_get(item if idx is None else idx)

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
		
	def __setitem__(self, key, value):

		if key == '_': # append to end of the list
			return self.__setitem__(len(self), value)

		idx = self._str_to_int(key)
		
		if idx >= len(self):
			self.extend([self._empty_fill_value]*(idx-len(self)+1))
		return super().__setitem__(idx, value)
		
		
	def contains_nodefault(self, item):
		
		try:
			idx = self._str_to_int(item)
		except InvalidKeyError:
			return isinstance(item, slice)
		
		N = len(self)
		return -N <= idx < N
		
	def append(self, item):
		super().append(item)
		if isinstance(item, ConfigType):
			item.set_parent(self)
		
		# self._update_tree(parent_defaults=parent_defaults)  # TODO: make sure manipulating lists works and updates parents

	def extend(self, item):
		super().extend(item)
		
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
		
		self._keys = [k for k in self._elms.keys()
		              if k not in {'_elements', '_mod', '_type', '__obj'}
					  and self._elms[k] != '__x__'] \
			if isinstance(self._elms, dict) else None
		self._prefix = origin.get_prefix().copy()
		# self._origin = config

	def __len__(self):
		return len(self._elms if self._keys is None else self._keys) - self._idx

	def _next_idx(self):
		
		if self._keys is None:
			return self._idx
		
		while self._idx < len(self._elms):
			idx = self._keys[self._idx]
			
			if self._elms.contains_nodefault(idx):
				return idx
			self._idx += 1
		
		raise StopIteration
		

	def __next__(self):

		if len(self._elms) == self._idx:
			raise StopIteration
		
		idx = self._next_idx()

		self._elms._prefix = self._prefix
		
		obj = self._elms._pull(str(idx))
		
		self._idx += 1
		if self._keys is None:
			return obj
		return idx, obj

	def __iter__(self):
		return self



#
# class ConfigArgDict(ConfigType, hp.TreeSpace):  # TODO: allow adding aliases
# 	'''
# 	Keys should all be valid python attributes (strings with no whitespace, and not starting with a number).
#
# 	NOTE: avoid setting keys that start with more than one underscore (especially '__obj')
# 	(unless you really know what you are doing)
# 	'''
#
# 	def purge_volatile(self):
# 		bad = []
# 		for k, v in self.items():
# 			if k.startswith('__'):
# 				bad.append(k)
# 			elif isinstance(v, ConfigType):
# 				v.purge_volatile()
#
# 		for k in bad:
# 			del self[k]
#
# 	def _missing_key(self, key):
# 		obj = super()._missing_key(key)
# 		obj.set_parent(self)
# 		return obj
#
# 	def update(self, other={}, parent_defaults=True):
# 		'''Merges ``self`` with ``other`` overwriting any parameters in ``self`` with those in ``other``'''
# 		# if not isinstance(other, ConfigDict):
# 		# 	# super().update(other)
# 		# 	other = configurize(other)
# 		for k, v in other.items():
# 			isconfig = isinstance(v, ConfigType)
# 			if self.contains_nodefault(k) and '_x_' == v:  # reserved for deleting settings in parents
# 				del self[k]
#
# 			elif self.contains_nodefault(k) and isconfig and \
# 					(isinstance(v, self[k].__class__) or isinstance(self[k], v.__class__)):
# 				self[k].update(v)
#
# 			# elif isinstance(v, str) and v.startswith('++') and self.contains_nodefault(k):
# 			# 	# values of appendable keys can be appended instead of overwritten,
# 			# 	# only when the new value starts with "+"
# 			# 	vs = []
# 			# 	if :
# 			# 		prev = self[k]
# 			# 		if not isinstance(prev, list):
# 			# 			prev = [prev]
# 			# 		vs = prev
# 			# 	vs.append(v[2:])
# 			# 	self[k] = vs
#
# 			else:
# 				self[k] = v
#
# 			if parent_defaults and isconfig:
# 				v.set_parent(self)
#
# 	def __str__(self):
# 		return f'[{id(self)}]{super().__repr__()}'


_config_type = ConfigType
_config_dict = ConfigDict
_config_list = ConfigList

def process_raw_argv(arg):
	return _config_type.parse_argv(arg)


