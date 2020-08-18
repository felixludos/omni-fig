
import sys, os
import humpack as hp
import io, yaml, json
from collections import defaultdict, OrderedDict
from c3linearize import linearize

from omnibelt import load_yaml, get_printer

from .util import primitives
from .errors import YamlifyError, MissingConfigError, UnknownActionError, InvalidKeyError
from .external import find_config_path
from .registry import create_component, _appendable_keys, Component

nones = {'None', 'none', '_none', '_None', 'null', 'nil', }

prt = get_printer(__name__)

def load_config_from_path(path, process=True):
	'''
	Load the yaml file and transform data to a config object
	
	Generally, ``get_config`` should be used instead of this method
	
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
	
	Generally, ``get_config`` should be used instead of this method
	
	:param data: config name or path or raw data (dict/list) or config object
	:param process: configurize loaded data
	:param parents: if None, no parents are loaded, otherwise it must be a dict where the keys are the absolute paths to the config (yaml) file and values are the loaded data
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
	
	This is an internal method used by ``get_config()`` and should generally not be called manually.
	'''
	
	if not len(configs):
		return ConfigDict()
	
	child = configs.pop()
	merged = merge_configs(configs, parent_defaults=parent_defaults)
	
	# load = child.load if 'load' in child else None
	merged.update(child)
	
	return merged


def get_config(*contents, **manual):  # Top level function
	'''
	Top level function for users. This is the best way to load/create a config object.

	All parent config (registered names or paths) that should be loaded
	must precede any manual entries, and will be loaded in reverse order (like python class inheritance).
	
	If the key ``_history_key`` is specified and not :code:`None`, a flattened list of all parents of
	this config is pushed to the given key.
	
	:param contents: registered configs or paths or manual entries (like in terminal)
	:param manual: specify parameters manually as key value pairs
	:return: config object
	'''
	root = ConfigDict()
	if len(contents) + len(manual) == 0:
		return root

	reg = []
	terms = {**manual}
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

	root['parents'] = ConfigList(data=reg + (list(root['parents']) if 'parents' in root else []))

	parents = {}
	
	root = process_single_config(root, parents=parents)

	pnames = []
	if len(parents):  # topo sort parents
		
		# TODO: maybe clean up?
		
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
	
	else:  # TODO: clean up
		order = [root]
	
	root = merge_configs(order,)
	
	include_history = root.pull('_history_key', None, silent=True)
	if include_history is not None:
		root.push(include_history, pnames, silent=True)
	
	root.push('parents', '_x_', silent=True)
	
	return root




_printing_instance = None
class Config_Printing:
	'''
	Internal class to manage the printing pulls/pushes of the config object. (eg. indent/line styles)
	'''
	def __new__(cls, *args, **kwargs): # singleton
		global _printing_instance
		if _printing_instance is None:
			_printing_instance = super().__new__(cls)
			
			_printing_instance.level = 0
			_printing_instance.is_new_line = True
			_printing_instance.unit = ' > '
			_printing_instance.style = '| '
			_printing_instance.silent = False
			
		return _printing_instance
	def __repr__(self):
		return f'ConfigPrinting[{hex(id(self))}]'
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
			elif term is None:
				pass
			elif not skip:
				addr.append(term)
			else:
				skip = False
		
		if not len(addr):
			return '.'
		
		addr = '.'.join(addr[::-1])
		return addr
	
	def log_record(self, raw, end='\n',
	               silent=False):
		indent = self.level * self.unit
		style = self.style
		prefix = style + indent
		
		msg = raw.replace('\n', '\n' + prefix)
		if not self.is_new_line:
			prefix = ''
		msg = f'{prefix}{msg}{end}'
		base = self.silent
		if not (silent or base):
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
	or keys separated by "." (hereafter called the "address" of the parameter).
	
	Note: that all parameters must not contain "." and should generally be valid python identifiers
	(strings with no white space that don't start with a number).
	
	'''

	def __init__(self, parent=None, silent=False, printer=None, prefix=None, safe_mode=False,
	             data=None):
		'''
		Generally it should not be necessary to create a ConfigType manually, instead use ``get_config()``.
		
		:param parent: parent config used for defaults
		:param silent: don't print ``pull``s and ``push``es
		:param printer: printer object to handle printing messages
		:param prefix: initial prefix used for printing
		:param safe_mode: don't save created component instances, unless during a transaction
		:param data: raw parameters to immediately add to this config
		'''
		
		if printer is None:
			printer = Config_Printing()
		self.__dict__['_printer'] = printer
		
		if prefix is None:
			prefix = []
		self.__dict__['_prefix'] = prefix
		self.__dict__['_hidden_prefix'] = prefix.copy()
		self.__dict__['_safe_mode'] = safe_mode
		
		self.set_parent(parent)
		# self._set_silent(silent)

		super().__init__()
		
		if data is not None:
			self.update(data)
		
	def sub(self, item):
		'''
		Used to get a subbranch of the overall config
		:param item: address of the branch to return
		:return: config object at the address
		'''
		
		val = self.get_nodefault(item)
		
		if isinstance(item, (list, tuple)):
			item = '.'.join(item)
		
		if isinstance(val, ConfigType):
			val._set_prefix(self.get_prefix() + [item])
			val._store_prefix()
		
		return val

	def update(self, other):
		'''
		Used to merge two config nodes (and their children) together
		
		This method must be implemented by child classes depending on how the contents of the node is stored
		
		:param other: config node to overwrite ``self`` with
		:return: None
		'''
		try:
			return super().update(other)
		except AttributeError:
			raise NotImplementedError

	def _record_action(self, action, suffix=None, val=None, silent=False, obj=None,
	                   defaulted=False, pushed=False, _entry=False):
		'''
		Internal function to manage printing out messages after various actions have been taken with this config.
		
		:param action: name of the action (see code for examples)
		:param suffix: suffix of the address (aka. last item in the address)
		:param val: contents at that address
		:param silent: suppress printing a message for this action
		:param obj: object created or used in this action (eg. a newly created component)
		:param defaulted: is a default value being used
		:param pushed: has this value just been pushed
		:param _entry: internal flag used for printing messages
		:return: formatted message corresponding to this action
		'''
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
			
			# head = '' if suffix is None else f' {name}'
			head = f' {name}'
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
			if _entry:
				head = ''
			return printer.log_record(f'{head}{pval}{origins}', silent=silent)
		
		raise UnknownActionError(action)
		
	def pull(self, item, *defaults, silent=False, ref=False, no_parent=False, as_iter=False):
		'''
		Top-level function to get parameters from the config object (including automatically creating components)

		:param item: address of the parameter to get
		:param defaults: default values to use if ``item`` is not found
		:param silent: suppress printing message that this parameter was pulled
		:param ref: if the parameter is a component that has already been created, get a reference to the created component instead of creating a new instance
		:param no_parent: don't default to a parent node if the ``item`` is not found here
		:param as_iter: return an iterator over the selected value (only works if the value is a dict/list)
		:return: processed value of the parameter (or default if ``item`` is not found, or raises a ``MissingConfigError`` if not found)
		'''
		self._reset_prefix()
		return self._pull(item, *defaults, silent=silent, ref=ref, no_parent=no_parent, as_iter=as_iter, _origin=self)

	def pull_self(self, name=None, silent=False, as_iter=False):
		'''
		Process self as a value being pulled.
		
		:param name: Name given to self for printed message
		:param silent: suppress printing message
		:param as_iter: Return self as an iterator (has same effect as calling ``seq()``)
		:return: the processed value of self
		'''
		self._reset_prefix()
		return self._process_val(name, self, silent=silent, reuse=False, is_self=True, as_iter=as_iter, _origin=self)

	def _pull(self, item, *defaults, silent=False, ref=False, no_parent=False, as_iter=False,
	          _defaulted=False, _origin=None):
		'''
		Internal pull method, should generally not be called manually (unless you know what you're doing)
		
		:param item: remaining address to find
		:param defaults: any default values that can be used if address is not found
		:param silent: suppress messages
		:param ref: return an instance of the value instead of creating a new instance, if one exists
		:param no_parent: do not check for the parameter in the parent
		:param as_iter: return the value as an iterator (only for dicts/lists)
		:param _defaulted: flag that this value was once a provided default (used for printing)
		:param _origin: reference to the original config node that was pulled (some pulls require returing to origin)
		:return: processed value found at ``item`` or a processed default value
		'''
		
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

			_origin._reset_prefix()
			
			val = _origin._process_val(item, val, *defaults, silent=silent, defaulted=defaulted or _defaulted,
			                        as_iter=as_iter, reuse=ref, _origin=_origin)

		elif len(line): # child pull
			if not isinstance(val, ConfigType):
				prt.warning(f'Pulling through a non-config object: {val}')
			
			val._set_prefix(self.get_prefix() + [item])
			out = val._pull(line, *defaults, silent=silent, ref=ref, no_parent=no_parent, as_iter=as_iter,
			               _defaulted=_defaulted, _origin=_origin)
			
			val = out
			
		elif byparent: # parent pull
			parent = self.get_parent()

			parent._set_prefix(self.get_prefix() + [''])
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
		'''
		This is used by ``pull()`` to process the recovered value and print the correct message if ``not silent``
		
		:param item: remaining address where this value was found
		:param val: value that was found given the original address
		:param defaults: any additional defaults to use if processing fails with ``val``
		:param silent: suppress messages
		:param reuse: if an instance is found (under ``__obj``) then that should be returned instead of creating a new one
		:param is_self: this config object should be returned after processing
		:param as_iter: return an iterator of ``val`` (only works if ``val`` is a list/dict)
		:param _origin: original config node where the pull or push request was intially called
		:param record_flags: additional flags used for printing.
		:return: processed value
		'''
		
		if as_iter and isinstance(val, ConfigType):
			
			obj_type = 'list' if isinstance(val, list) else 'dict'
			
			self._record_action(f'iter-{obj_type}', suffix=item, val=val, silent=silent, **record_flags)
			
			itr = Config_Iter(val, val)
			
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
					
					hidden = val._get_hidden_prefix()
					val.get_prefix().clear()
					val._store_prefix()
					
					past = self._get_silent()
					with self.silenced(silent or past):
						cmpn = create_component(val)
					
					if not self.in_safe_mode() or self.in_transaction():
						if item is not None and len(item) and not is_self:
							self[item]['__obj'] = cmpn
						else:
							self['__obj'] = cmpn
					
					val._set_prefix(hidden)
					val._store_prefix()
					
					self._record_action('created', suffix=item, val=val, obj=cmpn, silent=silent, **record_flags)
					
				val = cmpn

			else:
				
				self._record_action('pull-dict', suffix=item, val=val, silent=silent, **record_flags)
				terms = {}
				for k, v in val.items():  # WARNING: pulls all entries in dict
					self._record_action('entry', silent=silent, suffix=k)
					terms[k] = val._process_val(k, v, reuse=reuse, silent=silent, _origin=_origin, _entry=True)
				self._record_action('pulled-dict', suffix=item, val=val, obj=terms, silent=silent, **record_flags)
				val = terms


		elif isinstance(val, list):
			
			self._record_action('pull-list', suffix=item, val=val, silent=silent, **record_flags)
			terms = []
			for i, v in enumerate(val):  # WARNING: pulls all entries in list
				self._record_action('entry', silent=silent, suffix=str(i))
				terms.append(val._process_val(str(i), v, reuse=reuse, silent=silent, _origin=_origin, _entry=True))
			self._record_action('pulled-list', suffix=item, val=val, obj=terms, silent=silent, **record_flags)
			val = terms

		elif isinstance(val, str) and val.startswith('<>'):  # local alias (looks for alias locally)
			alias = val[2:]
			
			self._record_action('local-alias', suffix=item, val=alias, silent=silent, **record_flags)
			
			val = self._pull(alias, *defaults, silent=silent, _origin=_origin)
			
		elif isinstance(val, str) and val.startswith('<o>'): # origin alias (returns to origin to find alias)
			alias = val[3:]
			
			self._record_action('origin-alias', suffix=item, val=alias, silent=silent, **record_flags)
			
			_origin._reset_prefix()
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
		self._reset_prefix()
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
			
			child._set_prefix(self.get_prefix() + [key])
			
			out = child._push(line, val, silent=silent, overwrite=overwrite, no_parent=True)
			
			return out
		elif parent is not None and key in parent: # push parent

			parent._set_prefix(self.get_prefix() + [''])
			
			out = parent._push((key, *line), val, silent=silent, overwrite=overwrite, no_parent=no_parent)
			
			return out
			
		elif len(line): # push child
			
			child = self.get_nodefault(key)
			
			child._set_prefix(self.get_prefix() + [key])
			
			out = child._push(line, val, silent=silent, overwrite=overwrite, no_parent=True)
		
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
		'''
		Convert all data to raw data (using dict/list) and save as yaml file to ``path`` if provided.
		Also returns yamlified data.
		
		:param path: path to save data in this config (data is not saved to disk if not provided)
		:return: raw "yamlified" data
		'''

		data = yamlify(self)

		if path is not None:
			if os.path.isdir(path):
				path = os.path.join(path, 'config.yaml')
			with open(path, 'w') as f:
				yaml.dump(data, f)
			return path

		return data
	
	def seq(self):
		'''
		Returns an iterator over the contents of this config object where elements are lazily
		processed during iteration (see ``Config_Iter`` for details).
		
		:return: iterator over all arguments in self
		'''
		return Config_Iter(self, self)
	
	# region Silencing
	
	def _set_silent(self, silent=True):
		self.__dict__['_printer'].silent = silent
	
	# self._silent_config_flag = silent
	
	def _get_silent(self):
		return self.__dict__['_printer'].silent
	
	class _Silent_Config:
		'''Internal context manager to silence a config object'''
		
		def __init__(self, config, setting):
			self.config = config
			self.setting = setting
			self.prev = config._get_silent()
		
		def __enter__(self):
			self.config._set_silent(self.setting)
			return self.config
		
		def __exit__(self, exc_type, exc_val, exc_tb):
			self.config._set_silent(self.prev)
	
	def silenced(self, setting=True):
		return ConfigType._Silent_Config(self, setting=setting)
	
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
		return self.__dict__['_prefix']
	
	def _set_prefix(self, prefix):
		self.__dict__['_prefix'] = prefix
	
	def _reset_prefix(self):
		self._set_prefix(self._get_hidden_prefix())
	
	def _get_hidden_prefix(self):
		return self.__dict__['_hidden_prefix']
	
	def _store_prefix(self):
		self.__dict__['_hidden_prefix'] = self.get_prefix().copy()
	
	# endregion
	
	# region Misc
	
	def set_safe_mode(self, safe_mode):
		if self.is_root():
			self.__dict__['_safe_mode'] = safe_mode
		else:
			self.get_root().set_safe_mode(safe_mode)
	
	def in_safe_mode(self):
		if self.is_root():
			return self.__dict__['_safe_mode']
		return self.get_root().in_safe_mode()
	
	@staticmethod
	def parse_argv(arg):
		try:
			return yaml.safe_load(io.StringIO(arg))
		except:
			pass
		return arg
	
	def purge_volatile(self):
		'''
		Recursively remove any items where the key starts with "__"

		Must be implemented by the child class

		:return: None
		'''
		raise NotImplementedError
	
	def __repr__(self):
		return f'{type(self).__name__}[id={hex(id(self))}]'
	
	def __str__(self):
		return f'<{type(self).__name__}>'
	
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
		
		value = configurize(value)
		
		if isinstance(value, ConfigType):
			value.set_parent(self)
		return super().__setitem__(key, value)
	
	def __getitem__(self, item):
		
		if isinstance(item, str) and '.' in item:
			item = item.split('.')
		
		if isinstance(item, (list, tuple)):
			if len(item) == 1:
				item = item[0]
			else:
				return self.__getitem__(item[0])[item[1:]]
		
		parent = self.get_parent()
		
		if not self.contains_nodefault(item) \
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


class ConfigDict(ConfigType, hp.tdict):
	'''
	Dict like node in the config.
	
	Keys should all be valid python attributes (strings with no whitespace, and not starting with a number).

	NOTE: avoid setting keys that start with more than one underscore (especially '__obj')
	(unless you really know what you are doing)
	'''
	
	def update(self, other):
		'''
		Merge self with another dict-like object
		
		:param other: must be dict like
		:return: None
		'''
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
	
	def purge_volatile(self):
		'''
		Recursively remove any items where the key starts with "__"
		
		:return: None
		'''
		bad = []
		for k, v in self.items():
			if k.startswith('__'):
				bad.append(k)
			elif isinstance(v, ConfigType):
				v.purge_volatile()
		
		for k in bad:
			del self[k]
	
	def __repr__(self):
		info = '{{' + ', '.join(f'{k}' for k in self) + '}}'
		return f'[{hex(id(self))}]{info}'
	
	def __str__(self):
		return '{{' + ', '.join(f'{k}' for k in self) + '}}'




class ConfigList(ConfigType, hp.tlist):
	'''
	List like node in the config.
	'''

	def __init__(self, *args, empty_fill_value=None, **kwargs):
		super().__init__(*args, **kwargs)
		self._empty_fill_value = empty_fill_value

	def purge_volatile(self):
		'''
		Recursively remove any items where the key starts with "__"
		
		:return: None
		'''
		for x in self:
			if isinstance(x, ConfigType):
				x.purge_volatile()
		
	def _str_to_int(self, item):
		'''Convert the input items to indices of the list'''
		if isinstance(item, int):
			return item

		try:
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
		When pushing to a list, if you don't provide an index, the value is automatically pushed to the end of the list
		
		:param first: if no additional args are provided in `rest`, then this is used as the value and the key is the end of the list, otherwise this is used as key and the first element in `rest` is the value
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
		
	def extend(self, item):
		super().extend(item)
		
		for x in item:
			if isinstance(x, ConfigType):
				x.set_parent(self)

@Component('iter')
class Config_Iter:
	'''
	Iterate through a list of parameters, processing each item lazily,
	ie. only when it is iterated over (with ``next()``)
	'''

	def __init__(self, origin, elements=None):
		'''
		Can be used as a component or created manually (by providing the ``elements`` argument explicitly)
		
		For dicts, this will behave like ``.items()``, ie. for each entry in the dict it will return
		a tuple of the key and value.
		
		:param origin: config object where the iterator info is
		:param elements: manually provided elements to iterate over (uses contents of "_elements" in ``origin`` if not provided)
		'''
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

	def __len__(self):
		'''Returns the remaining length of this iterator instance'''
		return len(self._elms if self._keys is None else self._keys) - self._idx

	def _next_idx(self):
		'''Find the next index or key'''
		
		if self._keys is None:
			return str(self._idx)
		
		while self._idx < len(self._elms):
			idx = self._keys[self._idx]
			
			if self._elms.contains_nodefault(idx):
				return idx
			self._idx += 1
		
		raise StopIteration
		
	def view(self):
		'''Returns the next object without processing the item, may throw a StopIteration exception'''
		obj = self._elms[self._next_idx()]
		if isinstance(obj, ConfigType):
			return self._elms.sub(self._next_idx())
		return obj

	def __next__(self):

		if len(self._elms) == self._idx:
			raise StopIteration
		
		idx = self._next_idx()

		self._elms._prefix = self._prefix
		
		obj = self._elms._pull(idx)
		
		self._idx += 1
		if self._keys is None:
			return obj
		return idx, obj

	def __iter__(self):
		return self


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


def yamlify(data):  # TODO: allow adding yamlify rules for custom objects
	'''
	Transform data container into regular dicts/lists to export to yaml file

	:param data: Config object
	:return: deep copy of data using dict/list
	'''
	# if data is None:
	# 	return '_None'
	if data is None or isinstance(data, primitives):
		return data
	if isinstance(data, dict):
		return {k: yamlify(v) for k, v in data.items() if not k.startswith('__')}
	if isinstance(data, (list, tuple, set)):
		return [yamlify(x) for x in data]
	
	raise YamlifyError(data)


# _config_type = ConfigType
# _config_dict = ConfigDict
# _config_list = ConfigList

def process_raw_argv(arg):
	'''
	This is the preferred way to parse arguments for the config
	(especially arguments specified through the terminal)
	'''
	return ConfigType.parse_argv(arg)


