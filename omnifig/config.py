
import sys, os
from pathlib import Path
from copy import deepcopy, copy
import humpack as hp
from collections import defaultdict, OrderedDict

from omnibelt import save_yaml, load_yaml, get_printer

from .util import primitives, global_settings, configurize, pythonize, ConfigurizeFailed
from .errors import PythonizeError, MissingParameterError, UnknownActionError, InvalidKeyError

prt = get_printer(__name__)

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
			_printing_instance.src = None
		
		return _printing_instance
	def __repr__(self):
		return f'ConfigPrinting[{hex(id(self))}]'
	def __str__(self):
		return f'ConfigPrinting'
	
	# def set_src(self, src):
	# 	self.src = src
	
	def inc_indent(self):
		self.level += 1
	def dec_indent(self):
		self.level = max(0, self.level-1)
	
	def process_addr(self, *terms):

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
		src = '' if self.src is None else f'({self.src}) '
		prefix = style + src + indent
		
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

	def __init__(self, parent=None, printer=None,
	             prefix=None, safe_mode=False, project=None,
	             data=None):
		'''
		Generally it should not be necessary to create a ConfigType manually, instead use ``get_config()``.
		
		:param parent: parent config used for defaults
		:param printer: printer object to handle printing messages
		:param prefix: initial prefix used for printing
		:param project: project this config responds to
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
		
		self.__dict__['_project'] = None
		
		self.set_parent(parent)
		# self._set_silent(silent)

		if project is not None:
			self.set_project(project)

		super().__init__()
		
		if data is not None:
			self.update(data)

	def __deepcopy__(self, memodict={}):
		raise NotImplementedError

	def __copy__(self):
		raise NotImplementedError

	def copy(self):
		'''shallow copy of the config object'''
		return copy(self)

	def pythonize(self):
		return pythonize(self)

	@classmethod
	def convert(cls, data, recurse):
		'''used by configurize to turn a nested python object into a config object'''
		return cls(data=[recurse(x) for x in data])
		
	def sub(self, item):
		'''
		Used to get a subbranch of the overall config
		:param item: address of the branch to return
		:return: config object at the address
		'''
		
		# TODO: replace with a pull(raw=True)
		
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
	                   defaulted=False, pushed=False, _entry=False, _raw=False):
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
			if mods is not None and len(mods):
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
			out = printer.log_record(f'{action.upper()}{head} (type={cmpn_type}){mod_info}{origins}{end}',
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
			# return printer.log_record(f'=> id={hex(id(obj))}', silent=silent)

		pval = None if val is None else (f'[{type(val)}]' if _raw else repr(val))
		
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
		
	def pull(self, item, *defaults, silent=False, ref=False, no_parent=False, as_iter=False, raw=False):
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
		return self._pull(item, *defaults, silent=silent, ref=ref, no_parent=no_parent, as_iter=as_iter,
		                  _origin=self, _raw=raw)

	def pull_self(self, name=None, silent=False, as_iter=False, raw=False, ref=False):
		'''
		Process self as a value being pulled.
		
		:param name: Name given to self for printed message
		:param silent: suppress printing message
		:param as_iter: Return self as an iterator (has same effect as calling ``seq()``)
		:return: the processed value of self
		'''
		self._reset_prefix()
		return self._process_val(name, self, silent=silent, reuse=ref, is_self=True, as_iter=as_iter,
		                         _origin=self, _raw=raw)

	def _pull(self, item, *defaults, silent=False, ref=False, no_parent=False, as_iter=False,
	          _defaulted=False, _origin=None, _raw=False):
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
		:param _raw: return unprocessed value
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
			try:
				if '__origin_key' in self: # cousins
					origin = self['__origin_key']
					if origin is not None:
						parent = self.get_parent()
						if parent is not None:
							grandparent = parent.get_parent()
							if grandparent is not None:
								return grandparent._pull((origin, item), silent=silent, _defaulted=defaulted or _defaulted,
							                        as_iter=as_iter, ref=ref, _origin=_origin, _raw=_raw)
			except MissingParameterError:
				pass
			
			if len(defaults) == 0:
				raise MissingParameterError(item)
			val, *defaults = defaults
			line = []
		else:
			val = self[item]

		if len(line) and not isinstance(val, ConfigType):
			defaulted = True
			if len(defaults) == 0:
				raise MissingParameterError(item)
			val, *defaults = defaults

		if defaulted and _origin is not None: # try again with new value

			_origin._reset_prefix()
			
			val = _origin._process_val(item, val, *defaults, silent=silent, defaulted=defaulted or _defaulted,
			                        as_iter=as_iter, reuse=ref, _origin=_origin, _raw=_raw)

		elif len(line): # child pull
			if not isinstance(val, ConfigType):
				prt.warning(f'Pulling through a non-config object: {val}')
			
			val._set_prefix(self.get_prefix() + [item])
			out = val._pull(line, *defaults, silent=silent, ref=ref, no_parent=no_parent, as_iter=as_iter,
			               _defaulted=_defaulted, _origin=_origin, _raw=_raw)
			
			val = out
			
		elif byparent and not item.startswith('_'): # parent pull
			parent = self.get_parent()

			parent._set_prefix(self.get_prefix() + [''])
			val = parent._pull((item, *line), *defaults, silent=silent, ref=ref, no_parent=no_parent, as_iter=as_iter,
			                   _origin=_origin, _raw=_raw)
			
		else: # process val from me/defaults
			val = self._process_val(item, val, *defaults, silent=silent, defaulted=defaulted or _defaulted,
			                        as_iter=as_iter, reuse=ref, _origin=_origin, _raw=_raw)
			
			if type(val) in {list, set}: # TODO: a little heavy handed
				val = tuple(val)

		return val

	def _process_val(self, item, val, *defaults, silent=False,
	                 reuse=False, is_self=False, as_iter=False, _origin=None, _raw=False,
	                 **record_flags):
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

			if obj_type == 'list' or '_type' not in val or not val.pull('_type', silent=True).startswith('iter'):

				self._record_action(f'iter-{obj_type}', suffix=item, val=val, silent=silent, **record_flags)

				if _raw:
					return val

				itr = ConfigIter(val, val)

				return itr
		
		if isinstance(val, ConfigDict) and not _raw:
			
			val.push('__origin_key', item, silent=True)
			typ = val._pull('_type', None, silent=True)
			if typ is not None:
				
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
						cmpn = self.get_project().create_component(val)

					if not self.in_safe_mode() or self.in_transaction():
						if item is not None and len(item) and not is_self:
							val['__obj'] = cmpn
						else:
							self['__obj'] = cmpn
					
					val._set_prefix(hidden)
					val._store_prefix()
					
					self._record_action('created', suffix=item, val=val, obj=cmpn, silent=silent, **record_flags)
					
				val = cmpn

			else:
				
				val.push('__origin_key', '_x_', silent=True)
				
				self._record_action('pull-dict', suffix=item, val=val, silent=silent, **record_flags)
				terms = {}
				for k, v in val.items():  # WARNING: pulls all entries in dict
					k = str(k)
					self._record_action('entry', silent=silent, suffix=k)
					terms[k] = val._process_val(k, v, reuse=reuse, silent=silent, _origin=_origin, _entry=True)
				self._record_action('pulled-dict', suffix=item, val=val, obj=terms, silent=silent, **record_flags)
				val = terms


		elif isinstance(val, ConfigList) and not _raw:
			
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
			
			val = self._pull(alias, *defaults, silent=silent, _origin=_origin, as_iter=as_iter)
			
		elif isinstance(val, str) and val.startswith('<o>'): # origin alias (returns to origin to find alias)
			alias = val[3:]
			
			self._record_action('origin-alias', suffix=item, val=alias, silent=silent, **record_flags)
			
			_origin._reset_prefix()
			val = _origin._pull(alias, *defaults, silent=silent, _origin=_origin, as_iter=as_iter)

		elif isinstance(val, str) and val.startswith('<!>'): # copy alias (only for local aliases)
			alias = val[3:]

			self._record_action('copy-alias', suffix=item, val=alias, silent=silent, **record_flags)

			val = self._pull(alias, *defaults, silent=silent, _origin=_origin, as_iter=as_iter, _raw=True)

			# self[item] = deepcopy(val)
			val = deepcopy(val)
			self[item] = val

			return self._process_val(item, val, silent=silent, _origin=_origin, as_iter=as_iter, _raw=_raw)


		else:
			self._record_action('pulled', suffix=item, val=val, silent=silent, _raw=_raw, **record_flags)

		return val
	
	def push(self, key, val, *_skip, silent=False, overwrite=True, no_parent=True, force_root=False, process=True):
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
		return self._push(key, val, silent=silent, overwrite=overwrite, no_parent=no_parent,
		                  force_root=force_root, process=process)
	
	def _push(self, key, val, silent=False, overwrite=True, no_parent=True, force_root=False,
	          process=True, _origin=None):
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
			                   no_parent=no_parent, process=process)
		elif no_parent:
			parent = None
		
		if exists and len(line): # push me
			child = self.get_nodefault(key)
			
			child._set_prefix(self.get_prefix() + [key])
			
			out = child._push(line, val, silent=silent, overwrite=overwrite, no_parent=True, process=process)
			
			return out
		elif parent is not None and key in parent: # push parent

			parent._set_prefix(self.get_prefix() + [''])
			
			out = parent._push((key, *line), val, silent=silent, overwrite=overwrite,
			                   no_parent=no_parent, process=process)
			
			return out
			
		elif len(line): # push child
			
			child = self.get_nodefault(key)
			
			child._set_prefix(self.get_prefix() + [key])
			
			out = child._push(line, val, silent=silent, overwrite=overwrite, no_parent=True, process=process)
		
			return out
		
		if exists and not overwrite:
			return self._pull(key, silent=True)
		
		if isinstance(val, str) and val == '_x_':
			if exists:
				self._record_action('removing', suffix=key, val=val, silent=silent)
				del self[key]
			return
		
		val = configurize(val)
		
		self[key] = val
		# val = self[key]
		
		if process:
			val = self._process_val(key, val, silent=silent, pushed=True)
		
		return val

	def export(self, path=None):
		'''
		Convert all data to raw data (using dict/list) and save as yaml file to ``path`` if provided.
		Also returns yamlified data.
		
		:param path: path to save data in this config (data is not saved to disk if not provided)
		:return: raw "yamlified" data
		'''

		data = pythonize(self)

		if path is not None:
			path = Path(path)
			if path.is_dir():
				path = path / 'config.yaml'
			save_yaml(data, path)
			return path

		return data
	
	def seq(self):
		'''
		Returns an iterator over the contents of this config object where elements are lazily
		processed during iteration (see ``ConfigIter`` for details).
		
		:return: iterator over all arguments in self
		'''
		return ConfigIter(self, self)

	def replace_vals(self, replacements):
		raise NotImplementedError

	# region Silencing
	
	def set_silent(self, silent=True):
		'''Sets whether pushes and pulls on this config object should be printed out to stdout'''
		self.__dict__['_printer'].silent = silent
	
	def silence(self, silent=True):
		self.set_silent(silent)
	
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
			self.config.set_silent(self.setting)
			return self.config
		
		def __exit__(self, exc_type, exc_val, exc_tb):
			self.config.set_silent(self.prev)
	
	def silenced(self, setting=True):
		'''Returns a context manager to silence this config object'''
		return ConfigType._Silent_Config(self, setting=setting)
	
	# endregion
	
	# region Parents
	
	def is_root(self):  # TODO: move to tree space
		'''Check if this config object has a parent for defaults'''
		return self.get_parent() is None
	
	def set_parent(self, parent):
		'''Sets the parent config object to be checked when a parameter is not found in `self`'''
		self.__dict__['_parent'] = parent
	
	def get_parent(self):
		'''Get parent (returns None if this is the root)'''
		return self.__dict__['_parent']
	
	def set_process_id(self, name=None):
		'''Set the unique ID to include when printing out pulls from this object'''
		self._get_printer().src = name
	
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
	
	def set_project(self, project):
		self.get_root().__dict__['_project'] = project
	
	def get_project(self):
		return self.get_root().__dict__['_project']
	
	def set_safe_mode(self, safe_mode):
		if self.is_root():
			self.__dict__['_safe_mode'] = safe_mode
		else:
			self.get_root().set_safe_mode(safe_mode)
	
	def in_safe_mode(self):
		if self.is_root():
			return self.__dict__['_safe_mode']
		return self.get_root().in_safe_mode()
	
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
		# return repr(self)
		return f'<{type(self).__name__}>'
	
	# endregion
	
	# region Get/Set/Contains
	
	def __setitem__(self, key, value):
		if isinstance(key, str) and '.' in key:
			key = key.split('.')
		
		if isinstance(key, (list, tuple)):
			if len(key) == 1:
				return self.__setitem__(key[0], value)
			child = self.get_nodefault(*key)
			assert isinstance(child, ConfigType)
			return child.__setitem__(key[1:], value)
		
		value = configurize(value)
		
		if isinstance(value, ConfigType):
			value.set_parent(self)
			# value.set_project(self.get_project())
		return self._single_set(key, value)
	
	def __getitem__(self, item, *future):
		
		if isinstance(item, str) and '.' in item:
			item = item.split('.')
		
		if isinstance(item, (list, tuple)):
			if len(item) == 1:
				item = item[0]
			else:
				return self.__getitem__(*item)[item[1:]]
		
		parent = self.get_parent()
		
		if not self.contains_nodefault(item) \
				and parent is not None \
				and item[0] != '_':
			return parent[item]
		
		return self._single_get(item, *future)
	
	def get_nodefault(self, item, *future):
		'''Get ``item`` without defaulting up the tree if not found.'''
		
		if isinstance(item, str) and '.' in item:
			item = item.split('.')
		
		if isinstance(item, (list, tuple)):
			if len(item) == 1:
				item = item[0]
			else:
				return self.get_nodefault(*item)[item[1:]]
		
		return self._single_get(item, *future)
	
	def _single_set(self, key, val):
		return super().__setitem__(key, val)
	
	def _single_get(self, item, *context):
		try:
			val = super().__getitem__(item)
			if val is EmptyElement and len(context):
				raise KeyError(item)
		except KeyError:
			return self._missing_key(item, *context)
		
		return val
	
	def _missing_key(self, key, *context):
		
		cls = ConfigDict
		
		if len(context):
			nxt = context[0]
			try:
				int(nxt)
			except ValueError:
				pass
			else:
				cls = ConfigList
		
		obj = cls(parent=self)
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

	def __deepcopy__(self, memodict={}):
		new = self.__class__(data={k:deepcopy(v) for k,v in self.items() if not k.startswith('__')})
		new.__dict__.update(self.__dict__)
		return new

	def __copy__(self):
		new = self.__class__(data={k:v for k,v in self.items()})
		new.__dict__.update(self.__dict__)
		return new

	def copy(self):
		return copy(self)

	def replace_vals(self, replacements):
		for k,v in self.items():
			if isinstance(v, primitives) and v in replacements:
				self[k] = replacements[v]
			elif isinstance(v, ConfigType):
				v.replace_vals(replacements)

	@classmethod
	def convert(cls, data, recurse):
		return cls(data={k: recurse(v) for k, v in data.items()})
	
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
		return repr(self)
		return '{{' + ', '.join(f'{k}' for k in self) + '}}'


class EmptyElement:
	pass

class ConfigList(ConfigType, hp.tlist):
	'''
	List like node in the config.
	'''



	def __init__(self, *args, empty_fill_value=EmptyElement, **kwargs):
		super().__init__(*args, **kwargs)
		self._empty_fill_value = empty_fill_value

	def __deepcopy__(self, memodict={}):
		new = self.__class__(data=[deepcopy(x) for x in self])
		new.__dict__.update(self.__dict__)
		return new

	def __copy__(self):
		new = self.__class__(data=[x for x in self])
		new.__dict__.update(self.__dict__)
		return new

	def __repr__(self):
		info = '[[' + ', '.join(f'{k}' for k in self) + ']]'
		return f'[{hex(id(self))}]{info}'

	def __str__(self):
		return '[[' + ', '.join(f'{k}' for k in self) + ']]'

	def replace_vals(self, replacements):
		for i, x in enumerate(self):
			if isinstance(x, primitives) and x in replacements:
				self[i] = replacements[x]
			elif isinstance(x, ConfigType):
				x.replace_vals(replacements)


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
			elif x is not EmptyElement:
				self[i] = x
	

	def _single_set(self, key, val):
		if key == '_':  # append to end of the list
			key = len(self)
		key = self._str_to_int(key)
		if key >= len(self):
			self.extend([self._empty_fill_value] * (key - len(self) + 1))
		return super()._single_set(key, val)
	
	def _single_get(self, item, *context):
		
		if isinstance(item, slice):
			return super(ConfigType, self).__getitem__(item)
		
		if item == '_':  # append to end of the list
			item = len(self)
		
		item = self._str_to_int(item)
		
		if item >= len(self):
			self.extend([self._empty_fill_value] * (item - len(self) + 1))
			
		return super()._single_get(item, *context)

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
			# item.set_project(self.get_project())
		
	def extend(self, item):
		super().extend(item)
		
		for x in item:
			if isinstance(x, ConfigType):
				x.set_parent(self)
				# x.set_project(self.get_project())


class ConfigIter:
	'''
	Iterate through a list of parameters, processing each item lazily,
	ie. only when it is iterated over (with ``next()``)
	'''
	
	def __init__(self, origin, elements=None, auto_pull=True, include_key=None, reversed=False):
		'''
		Can be used as a component or created manually (by providing the ``elements`` argument explicitly)

		For dicts, this will behave like ``.items()``, ie. for each entry in the dict it will return
		a tuple of the key and value.

		:param origin: config object where the iterator info is
		:param elements: manually provided elements to iterate over (uses contents of "_elements" in ``origin`` if not provided)
		'''
		# self._name = config._ident
		# assert '_elements' in config, 'No elements found'
		if elements is None:
			elements = origin['_elements']
		self._elms = elements
		
		self._keys = [k for k in self._elms.keys()
		              if k not in {'_elements', '_mod', '_type', '__obj', '__origin_key'}
		              and self._elms[k] != '__x__'] \
			if isinstance(self._elms, dict) else None
		self._include_key = include_key if include_key is not None else self._keys is not None
		self._prefix = origin.get_prefix().copy()
		
		self._reversed = False
		self._idx = 0
		self.set_reversed(reversed)
		self.set_auto_pull(auto_pull)
	
	def __len__(self):
		'''Returns the remaining length of this iterator instance'''
		return len(self._elms if self._keys is None else self._keys) - self._idx
	
	def _next_idx(self):
		'''Find the next index or key'''
		
		if self._keys is None:
			if 0 > self._idx >= len(self._elms):
				raise StopIteration
			return str(self._idx)
			# if not self._elms.contains_nodefault(self._idx):
			# 	raise StopIteration
			# return str(self._idx)
		
		while 0 <= self._idx < len(self._elms):
			idx = self._keys[self._idx]
			
			if self._elms.contains_nodefault(idx):
				return idx
			self._idx += (-1)**self._reversed
		
		raise StopIteration
	
	def view(self):
		'''Returns the next object without processing the item, may throw a StopIteration exception'''
		idx = self._next_idx()
		obj = self._elms.pull(idx, raw=True, silent=True)
		# obj = self._elms[idx]
		if isinstance(obj, ConfigType):
			obj.push('_iter_key', idx, silent=True)
			
		if isinstance(obj, global_settings['config_type']):
			obj = self._elms.sub(idx)
		return (idx, obj) if self._include_key else obj

	def step(self):
		obj = self.view()
		self._idx += (-1)**self._reversed
		return obj

	def set_auto_pull(self, auto=True):
		self._auto_pull = auto

	def set_reversed(self, reversed=True):
		self._reversed = reversed
		if reversed:
			self._idx = len(self)-1

	def has_next(self):
		return (self._reversed and self._idx >= 0) or (not self._reversed and self._idx < len(self._elms))
 
	def __next__(self):
		
		if not self.has_next():
			raise StopIteration

		obj = self.step()
		key, val = obj if self._include_key else (None,obj)
		if isinstance(val, global_settings['config_type']):
			val = val.pull_self(raw=not self._auto_pull, silent=not self._auto_pull)
		return (key,val) if self._include_key else val
	
	def __iter__(self):
		return self

nones = {'None', 'none', '_none', '_None', 'null', 'nil', }
def configurize_nones(s, recurse):
	'''Turns strings into None, if they match the expected patterns'''
	if s in nones:
		return None
	raise ConfigurizeFailed

global_settings.update({
	'config_type': ConfigType,
	'config_converters': OrderedDict([
		(str, configurize_nones),
		(dict, (False, ConfigDict.convert)),
		(OrderedDict, (False, ConfigDict.convert)),
		(list, ConfigList.convert),
		# (tuple, ConfigList.convert),
		(set, ConfigList.convert),
	]),
})


