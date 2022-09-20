



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
			self._idx += (-1 )* *self._reversed

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
		self._idx += (-1 )* *self._reversed
		return obj

	def set_auto_pull(self, auto=True):
		self._auto_pull = auto

	def set_reversed(self, reversed=True):
		self._reversed = reversed
		if reversed:
			self._idx = len(self ) -1

	def has_next(self):
		return (self._reversed and self._idx >= 0) or (not self._reversed and self._idx < len(self._elms))

	def __next__(self):

		if not self.has_next():
			raise StopIteration

		obj = self.step()
		key, val = obj if self._include_key else (None ,obj)
		if isinstance(val, global_settings['config_type']):
			val = val.pull_self(raw=not self._auto_pull, silent=not self._auto_pull)
		return (key ,val) if self._include_key else val

	def __iter__(self):
		return self










