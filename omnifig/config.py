
import sys, os
import humpack as hp
import yaml, json
from collections import defaultdict
from c3linearize import linearize

from .util import primitives
from .errors import YamlifyError, ParsingError, NoConfigFound, MissingConfigError
from .preload import find_config_path
from .registry import create_component, _appendable_keys

nones = {'None', 'none', '_none', '_None', 'null', 'nil', }


def configurize(data):
	if isinstance(data, dict):
		return ConfigDict({k: configurize(v) for k, v in data.items()})
	if isinstance(data, list):
		return ConfigList(configurize(x) for x in data)
		ls = []
		cfg = False
		for x in data:
			x = configurize(x)
			cfg = cfg or isinstance(x, _ConfigType)
		return ConfigList(ls) if cfg else util.tlist(ls)
	if isinstance(data, str) and data in nones:
		return None
	return data


def yamlify(data):
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
	# path = find_config_path(path)
	with open(path, 'r') as f:
		data = yaml.safe_load(f)
	
	if data is None:
		data = {}
	
	if process:
		return configurize(data)
	return data


def load_single_config(data, process=True, parents=None):  # data can either be an existing config or a path to a config
	
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
			parents[ppath] = load_single_config(ppath, parents=parents)
	
	return data


# def _check_for_load(config, parent_defaults=True):
#
# 	if 'load' in config:
# 		lparents = {}
# 		load = load_single_config(config.load, parents=lparents)
# 		assert len(lparents) == 0, 'Loaded configs are not allowed to have parents.'
# 		load.update(config, parent_defaults=parent_defaults)
# 		config = load
#
# 	return config

def merge_configs(configs, parent_defaults=True):
	'''
	configs should be ordered from oldest to newest (ie. parents first, children last)
	also configs can contain "load"
	'''
	
	if not len(configs):
		return ConfigDict()
	
	child = configs.pop()
	merged = merge_configs(configs, parent_defaults=parent_defaults)
	
	# load = child.load if 'load' in child else None
	merged.update(child)
	
	return merged


def get_config(path=None, parent_defaults=True, include_load_history=False):  # Top level function
	
	if path is None:
		return ConfigDict()
	
	parents = {}
	
	root = load_single_config(path, parents=parents)
	
	pnames = []
	if len(parents):  # topo sort parents
		
		root_id = 'root'
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
	
	load = None
	for part in order:
		if 'load' in part:
			assert load is None, 'Only one load config is allowed in a config'
			load = part.load
	
	order.insert(0, get_config(load, parent_defaults=parent_defaults, include_load_history=include_load_history))
	
	root = merge_configs(order,
	                     parent_defaults=parent_defaults)  # update to connect parents and children in tree and remove reversed - see Config.update
	
	if include_load_history:
		root._history = pnames
		if load is not None:
			root._loaded = load
		if 'load' in root:
			del root.load
	
	return root




def parse_config(argv=None, parent_defaults=True, include_load_history=False):
	# WARNING: 'argv' should not be equivalent to sys.argv here (no script name in element 0)
	
	if argv is None:
		argv = sys.argv[1:]
	
	# argv = argv[1:]
	
	root = ConfigDict()  # from argv
	
	parents = []
	for term in argv:
		if len(term) >= 2 and term[:2] == '--':
			break
		else:
			# assert term in _config_registry or os.path.isfile(term), 'invalid config name/path: {}'.format(term)
			parents.append(term)
	root.parents = parents
	
	argv = argv[len(parents):]
	
	if len(argv):
		
		terms = iter(argv)
		
		term = next(terms)
		if term[:2] != '--':
			raise ParsingError(term)
		done = False
		while not done:
			keys = term[2:].split('.')
			values = []
			try:
				val = next(terms)
				while val[:2] != '--':
					try:
						values.append(configurize(json.loads(val)))
					except json.JSONDecodeError:
						print('Json failed to parse: {}'.format(repr(val)))
						values.append(val)
					val = next(terms)
				term = val
			except StopIteration:
				done = True
			
			if len(values) == 0:
				values = [True]
			if len(values) == 1:
				values = values[0]
			root[keys] = values
	
	root = get_config(root, parent_defaults=parent_defaults, include_load_history=include_load_history)
	
	return root


# _reserved_names.update({'_x_'})


def _add_default_parent(C):
	for k, child in C.items():
		if isinstance(child, ConfigDict):
			child._parent_obj_for_defaults = C
			_add_default_parent(child)
		elif isinstance(child, (tuple, list, set)):
			for c in child:
				if isinstance(c, ConfigDict):
					c._parent_obj_for_defaults = C
					_add_default_parent(c)


def _clean_up_reserved(C):
	bad = []
	for k, v in C.items():
		if v == '_x_':  # maybe include other _reserved_names
			bad.append(k)
		elif isinstance(v, ConfigDict):
			_clean_up_reserved(v)
	for k in bad:
		del C[k]


# TODO: find a way to avoid this ... probably not easy
_print_waiting = False
_print_indent = 0


def _print_with_indent(s):
	return s if _print_waiting else ''.join(['  ' * _print_indent, s])


class _ConfigType(hp.Transactionable):

	def __init__(self, *args, _parent_obj_for_defaults=None, **kwargs):
		self.__dict__['_parent_obj_for_defaults'] = _parent_obj_for_defaults
		super().__init__(*args, **kwargs)

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
		if '.' in item:
			item = item.split('.')

		if isinstance(item, (tuple, list)):
			if len(item) == 1:
				item = item[0]
			else:

				# got = self._single_get(item[0])
				#
				# if len(item) >= 2 and isinstance(got, list):
				# 	idx = int(item[1])
				# 	got = got[idx]
				# 	if len(item) == 2:
				# 		return got
				# 	item = item[1:]
				# return got[item[1:]]

				return item[0] in self and item[1:] in self[item[0]]

		return self.contains_nodefault(item) \
			or (not super().__contains__(item)
				and self._parent_obj_for_defaults is not None
				and item[0] != '_'
			    and item in self._parent_obj_for_defaults)

	def _single_get(self, item):

		if not self.contains_nodefault(item) \
				and self._parent_obj_for_defaults is not None \
				and item[0] != '_':
			return self._parent_obj_for_defaults[item]

		return self.get_nodefault(item)

	def get_nodefault(self, item):
		val = super().__getitem__(item)
		if val == '__x__':
			raise KeyError(item)
		return val

	def contains_nodefault(self, item):
		# if isinstance(item, (tuple, list)):
		# 	if len(item) == 1:
		# 		item = item[0]
		# 	else:
		# 		return item[0] in self and item[1:] in self
		if super().__contains__(item):
			return super().__getitem__(item) != '__x__'
		return False


	def pull(self, item, *defaults, silent=False, ref=False, no_parent=False,
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
			val = val.pull(line, *defaults, silent=silent, ref=ref, no_parent=no_parent,
			               _byparent=_byparent, _bychild=True,
			               _defaulted=_defaulted)
		elif byparent: # parent pull
			val = self.__dict__['_parent_obj_for_defaults'].pull(item, silent=silent, ref=ref, no_parent=no_parent,
			                                                     _byparent=True)
		else: # pull from me
			val = self._process_val(item, val, *defaults, silent=silent, defaulted=defaulted or _defaulted,
			                        byparent=byparent or _byparent, bychild=_bychild, reuse=ref, )

			if type(val) in {list, set}: # TODO: a little heavy handed
				val = tuple(val)

		return val


	def _process_val(self, item, val, *defaults, silent=False, reuse=False, defaulted=False, byparent=False, bychild=False):
		global _print_indent, _print_waiting

		# TODO: add option to return an "iterator" of the value (both list and dict)

		if isinstance(val, dict):

			if '_type' in val:

				# WARNING: using pull will automatically create registered sub components

				# no longer an issue
				# assert not byparent, 'Pulling a sub-component from a parent is not supported (yet): {}'.format(item)

				assert not (reuse and defaulted)


				# TODO: should probably be deprecated - just register a "list" component separately
				if val['_type'] == 'list':
					if not silent:
						_print_indent += 1
						print(_print_with_indent('{} (type={}): '.format(item, val['_type'])))
					terms = []
					for i, v in enumerate(val._elements): # WARNING: elements must be listed with '_elements' key
						terms.append(self._process_val('[{}]'.format(i), v, reuse=reuse, silent=silent))
					val = tuple(terms)
					if not silent:
						_print_indent -= 1

				elif val['_type'] == 'iter':
					elms = val['_elements']
					if not silent:
						print(_print_with_indent('{} (type={}) with {} elements'.format(item, val['_type'], len(elms))))
					val = _Config_Iter(self, item, elms)

				elif val['_type'] == 'config': # get the actual config (raw, no view)

					if not silent:
						print(_print_with_indent('{} (type={}) containing: {}'.format(item, 'config',
						                                                              ', '.join(val.keys()))))

				else: # create component

					type_name = val['_type']
					if type_name[:2] == '<>':
						type_name = val.pull('_type', silent=True)
					mod_info = ''
					if '_mod' in val:
						mods = val['_mod']
						if not isinstance(mods, (list, tuple)):
							mods = mods,

						mod_info = ' (mods=[{}])'.format(', '.join(m for m in mods)) if len(mods) > 1 \
							else ' (mod={})'.format(mods[0])

					cmpn = None
					if self.in_transaction() and '__obj' in val and reuse:
						print('WARNING: would usually reuse {} now, but instead creating a new one!!')
						cmpn = val['__obj']

					creation_note = 'Creating ' if cmpn is None else 'Reusing '

					if not silent:
						print(_print_with_indent('{}{} (type={}){}{}'.format(creation_note, item, type_name, mod_info,
						                                                     ' (in parent)' if byparent else '')))

					if cmpn is None:
						_print_indent += 1
						cmpn = create_component(val)
						_print_indent -= 1

					if self.in_transaction():
						self[item]['__obj'] = cmpn
					# else:
					# 	print('WARNING: this Config is NOT currently in a transaction, so all subcomponents will be created '
					# 	      'again everytime they are pulled')

					val = cmpn

			else: # convert config to dict (by pulling all entries) and return full dict
				if not silent:
					_print_indent += 1
					print(_print_with_indent('{} (type={}): '.format(item, 'dict')))
				terms = {}
				for k, v in val.items():  # WARNING: pulls all entries in dict
					terms[k] = self._process_val('({})'.format(k), v, reuse=reuse, silent=silent)
				val = terms
				if not silent:
					_print_indent -= 1

		elif isinstance(val, list):
			if not silent:
				_print_indent += 1
				print(_print_with_indent('{} (type={}): '.format(item, 'list')))
			terms = []
			for i, v in enumerate(val):  # WARNING: elements must be listed with '_elements' key
				terms.append(self._process_val('[{}]'.format(i), v, reuse=reuse, silent=silent))
			val = terms
			if not silent:
				_print_indent -= 1


		elif isinstance(val, str) and val[:2] == '<>':  # alias
			alias = val[2:]
			# assert not byparent, 'Using an alias from a parent is not supported: {} {}'.format(item, alias)

			if not silent:
				print(_print_with_indent('{} --> '.format(item)), end='')
				_print_waiting = True
			val = self.pull(alias, *defaults, silent=silent)
			if not silent:
				_print_waiting = False

		elif not silent:
			print(_print_with_indent('{}: {}{}{}'.format(item, val, ' (by default)' if defaulted
					else (' (in parent)' if byparent else ''), ' (by child)' if bychild else '')))

		return val
	
	def push(self, key, val, *_skip, silent=False, overwrite=True, no_parent=False, force_root=False):
		'''
		
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
		if no_parent:
			assert not force_root, 'makes no sense'
			parent = None
		
		if parent is not None and force_root:
			return parent.push((key, *line), val, silent=silent, overwrite=overwrite,
			                   no_parent=no_parent, force_root=True)
		elif exists and len(line): # push me
			return self[key].push(line, val, silent=silent, overwrite=overwrite, no_parent=True)
		elif parent is not None and key in parent: # push parent
			return parent.push((key, *line), val, silent=silent, overwrite=overwrite, no_parent=no_parent)
		elif len(line): # push child
			return self[key].push(line, val, silent=silent, overwrite=overwrite, no_parent=True)
		
		if exists and not overwrite:
			return self.pull(key, silent=silent)
		
		val = configurize(val)
		self[key] = val
		
		val = self._process_val(f'[Pushed] {key}:', val, silent=silent)
		
		# TODO clean up _update_tree (maybe should be here)
		
		return val

	def is_root(self):
		return self.get_parent() is None

	def get_parent(self):
		return self._parent_obj_for_defaults
	
	def get_root(self):
		parent = self.get_parent()
		if parent is None:
			return self
		return parent.get_root()
	
	def export(self, path=None):

		data = yamlify(self)

		if path is not None:
			if os.path.isdir(path):
				path = os.path.join(path, 'config.yaml')
			with open(path, 'w') as f:
				yaml.dump(data, f)
			return path

		return data

	def _update_tree(self, parent_defaults=True):
		_clean_up_reserved(self)

		if parent_defaults:
			_add_default_parent(self)



class ConfigDict(_ConfigType, hp.TreeSpace): # TODO: allow adding aliases
	'''
	Features:

	Keys:
	'_{}' = protected - not visible to children
	({1}, {2}, ...) = [{1}][{2}]...
	'{1}.{2}' = ['{1}']['{2}']
	'{1}.{2}' = ['{1}'][{2}] (where {2} is an int and self['{1}'] is a list)
	if {} not found: first check parent (if exists) otherwise create self[{}] = Config(parent=self)

	Values:
	'<>{}' = alias to key '{}'
	'_x_' = (only when merging) remove this key locally, if exists
	'__x__' = dont default this key and behaves as though it doesnt exist (except on iteration)
	(for values of "appendable" keys)
	"+{}" = '{}' gets appended to preexisting value if if it exists
		(otherwise, the "+" is removed and the value is turned into a list with itself as the only element)

	Also, this is Transactionable, so when creating subcomponents, the same instance is returned when pulling the same
	sub component again.

	NOTE: avoid setting '__obj' keys (unless you really know what you are doing)

	'''

	def update(self, other={}, parent_defaults=True):
		if not isinstance(other, ConfigDict):
			# super().update(other)
			other = configurize(other)
		for k, v in other.items():
			if self.contains_nodefault(k) and '_x_' == v: # reserved for deleting settings in parents
				del self[k]
			elif self.contains_nodefault(k) and isinstance(v, ConfigDict) and isinstance(self[k], ConfigDict):
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

		self._update_tree(parent_defaults=parent_defaults)

	def __str__(self):
		return super().__repr__()



class InvalidKeyError(Exception):
	pass

class ConfigList(_ConfigType, hp.tlist):

	# def pull_iter(self):
	# 	return _Config_Iter(self, '', self)

	def _str_to_int(self, item):
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
		for i, x in enumerate(other):
			if len(self) == i:
				self.append(x)
			else:
				self[i] = x


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

	def push(self, first, *rest, **kwargs):
		'''
		
		:param first: if no additional args are provided in `rest`, then this is used as the value and the key
		is the end of the list, otherwise this is used as key and the first element in `rest` is the value
		:param rest: optional second argument to specify the key, rather than defaulting to the end of the list
		:param kwargs: same keyword args as for the ConfigDict
		:return: same as for ConfigDict
		'''

		if len(rest):
			val, *rest = rest
			return super().push(first, val, *rest, **kwargs)
		
		val = first
		key = len(self)
		self.append(None)
		return super().push(key, val, *rest, **kwargs) # note that *rest will have no effect
		
	def contains_nodefault(self, item):
		idx = self._str_to_int(item)
		return 0 <= idx < len(self)

	def append(self, item, parent_defaults=True):
		super().append(item)
		# self._update_tree(parent_defaults=parent_defaults)  # TODO: make sure this makes sense

	def extend(self, item, parent_defaults=True):
		super().extend(item)
		# self._update_tree(parent_defaults=parent_defaults)


class _Config_Iter(object): # TODO: generalize to dict as well (maybe iterating through full items)

	def __init__(self, config, name, elms):
		self._idx = 0
		self._name = name
		self._elms = elms
		self._origin = config

	def __len__(self):
		return len(self._elms)

	def remaining(self):
		return len(self._elms) - self._idx

	def current(self):
		return self._elms[self._idx] if self._idx < len(self._elms) else None

	def __next__(self):

		if len(self._elms) == self._idx:
			raise StopIteration

		obj = self._origin._process_val(f'{self._name}[{self._idx}]', self.current())
		self._idx += 1
		return obj

	def __iter__(self):
		return self


