

# class ConfigReporterBase:
	# def __init__(self, silent=False, **kwargs):
	# 	super().__init__(**kwargs)
	# 	self._silent = silent
	#
	# @property
	# def silent(self):
	# 	return self._silent
	# @silent.setter
	# def silent(self, value):
	# 	self._silent = value

class AbstractReporter:
	pass



class ConfigReporter(AbstractReporter):
	def __init__(self, indent=' > ', flair='| ', transfer=' --> ', colon=': ',
	             prefix_fmt='{prefix}', suffix_fmt=' (by {suffix!l})', max_num_aliases=3, **kwargs):
		super().__init__(**kwargs)
		self.indent = indent
		self.flair = flair
		self.transfer = transfer
		self.colon = colon
		self.prefix_fmt = prefix_fmt
		self.suffix_fmt = suffix_fmt
		self.max_num_aliases = max_num_aliases

	def log(self, *msg, silent=None, **kwargs) -> str:
		if silent is None:
			silent = self.silent
		if not silent:
			return super().log(msg, **kwargs)

	@classmethod
	def _node_depth(cls, node, _fuel=100):
		if _fuel <= 0:
			raise RuntimeError('Depth exceeded 100 (there is probably an infinite loop in the config tree)')
		if node.parent is None:
			return 0
		return cls._node_depth(node.parent, _fuel=_fuel - 1) + 1

	def _extract_prefix(self, search):
		prefix = getattr(search, 'action', None)
		if prefix is None:
			if search.action == 'component':
				prefix = 'creating'.upper()
			elif search.action == 'storage':
				prefix = 'reusing'.upper()
			elif search.action == 'iterator':
				prefix = 'iterator'.upper()
		if prefix is not None:
			return self.prefix_fmt.format(prefix=prefix)

	def _extract_suffix(self, search):
		suffix = getattr(search, 'source', None)
		if suffix is not None:
			return self.suffix_fmt.format(suffix=suffix)

	def component_creation(self, node, key, cmpn, mods, silent=None):
		if silent is None:
			silent = self.silent
		mod_info = ''
		if len(mods):
			mod_info = f' (mods=[{", ".join(mods)}])' if len(mods) > 1 else f' (mod={mods[0]})'
		key = '' if key is None else key + ' '
		indent = max(0, self._node_depth(node) - 1) * self.indent
		return self.log(f'{self.flair}{indent}CREATING {key}type={cmpn}{mod_info}', silent=silent)

	def get_key(self, search: 'ConfigNode.Search') -> str:

		queries = search.query_chain

		if len(search.parent_search):
			queries = queries.copy()
			queries[0] = f'({queries[0]})'  # if getattr(search.parent_search[0]

		if len(queries) > self.max_num_aliases:
			key = self.transfer.join([queries[0], '...', queries[-1]])
		else:
			key = self.transfer.join(queries)
		return key

	def _present_payload(self, search):
		key = self.get_key(search)

		if search.action == 'primitive':
			value = repr(search.result_node)
			return f'{key}{self.colon}{value}'

		elif search.action == 'no-payload' or search.action == 'iterator':  # list or dict
			node = search.result_node
			N = len(node)

			t, x = ('list', 'element') if isinstance(node, search.origin.SparseNode) else ('dict', 'item')
			x = x + 's' if N != 1 else x
			# return f'{key} has {N} {x}:'
			return f'{key} [{t} with {N} {x}]'

		# elif search.action == 'component':
		# 	return self._present_component(key, search)

		# elif search.action == 'storage':
		# 	return self._present_component(key, search)

		raise ValueError(f'Unknown action: {search.action!r}')

	def search_report(self, search):
		indent = self._node_depth(search.origin) * self.indent

		prefix = self._extract_prefix(search)
		result = self._present_payload(search)
		suffix = self._extract_suffix(search)

		line = f'{self.flair}{indent}{prefix}{result}{suffix}'
		return self.log(line, silent=search.silent)

	class Silencer:
		def __init__(self, reporter, silent=True):
			self.reporter = reporter
			self.silent = reporter.silent
			reporter.silent = silent

		def __enter__(self):
			return self

		def __exit__(self, exc_type, exc_val, exc_tb):
			self.reporter.silent = self.silent

	def silence(self, silent=True):
		return self.Silencer(self, silent=silent)





