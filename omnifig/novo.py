from typing import List, Dict, Tuple, Optional, Union, Any, Hashable, Sequence, Callable, Generator, Type, Iterable, Iterator
from omnibelt import unspecified_argument, Singleton
from omnibelt.nodes import AutoTreeNode, AutoTreeSparseNode, AutoTreeDenseNode


class ConfigReporter:
	def __init__(self, silent=False, **kwargs):
		super().__init__(**kwargs)
		self._silent = silent

	@property
	def silent(self):
		return self._silent
	@silent.setter
	def silent(self, value):
		self._silent = value

	@staticmethod
	def log(*msg, end='\n', sep=' ') -> None:
		msg = sep.join(str(m) for m in msg) + end
		print(msg, end='')
		return msg


class SimpleConfigNode(AutoTreeNode):

	class Search:
		def __init__(self, origin, queries, default=unspecified_argument, **kwargs):
			super().__init__(**kwargs)
			self.origin = origin
			self.queries = queries
			self.default = default
			self.result = None

		class SearchFailed(KeyError):
			def __init__(self, queries):
				super().__init__(', '.join(queries))

		def _resolve_queries(self):
			if not len(self.queries):
				return None, self.origin
			for query in self.queries:
				if query is None:
					return None, self.origin
				try:
					return query, self.origin.get(query)
				except self.origin.MissingKey:
					pass
			raise self.SearchFailed(self.queries)

		def evaluate_node(self):
			try:
				self.query, self.result = self._resolve_queries()
			except self.SearchFailed:
				if self.default is unspecified_argument:
					raise
				self.result = self.default
			return self.result

		def evaluate(self):
			return self.package(self.evaluate_node())

		def package(self, node):
			return node.payload


	def pull(self, *queries: str, default=unspecified_argument, **kwargs):
		search = self.Search(origin=self, queries=queries, default=default, **kwargs)
		return search.evaluate()


	def push(self, addr: str, value: Any, overwrite: bool = True, silent: Optional[bool] = None) -> bool:
		# if self.read_only:
		# 	raise self.ReadOnlyError('Cannot push to read-only node')
		try:
			existing = self.get(addr)
		except self.MissingKey:
			existing = None

		if existing is None or overwrite:
			self.set(addr, value)
			return True
		return False


	def peek(self, *queries, default=unspecified_argument, **kwargs) -> 'SimpleConfigNode':
		search = self.Search(self, queries, default, **kwargs)
		return search.evaluate_node()


	def push_pull(self, addr: str, value: Any, overwrite: bool = True, **kwargs) -> Any:
		self.push(addr, value, overwrite=overwrite)
		return self.pull(addr, **kwargs)



primitive = (int, float, str, bool, type(None))
Primitive = Union[primitive]


class ConfigNode(SimpleConfigNode):
	class Reporter(ConfigReporter, Singleton):
		def __init__(self, indent=' > ', flair='| ', transfer=' -> ', colon=': ',
		             prefix_fmt='{prefix}', suffix_fmt=' (by {suffix!l})', **kwargs):
			super().__init__(**kwargs)
			self.indent = indent
			self.flair = flair
			self.transfer = transfer
			self.colon = colon
			self.prefix_fmt = prefix_fmt
			self.suffix_fmt = suffix_fmt


		def log(self, *msg, silent=None, **kwargs):
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
			return cls._node_depth(node.parent, _fuel=_fuel-1) + 1

		def _extract_prefix(self, search):
			prefix = getattr(search, 'action', None)
			if prefix is not None:
				return self.prefix_fmt.format(prefix=prefix)

		def _extract_suffix(self, search):
			suffix = getattr(search, 'source', None)
			if suffix is not None:
				return self.suffix_fmt.format(suffix=suffix)

		def _extract_product(self, search):
			pass

		def _present_payload(self, search):

			if search.action == 'primitive':
				key = self.transfer.join(search.query_chain)
				value = self._extract_value(search)

				return f'{key}{self.colon}{value}'

			elif search.action == 'no-payload': # list or dict
				pass

			elif search.action == 'component':
				pass


		def search_report(self, search):
			indent = self._node_depth(search.origin) * self.indent

			result = self._present_payload(search)
			prefix = self._extract_prefix(search)
			suffix = self._extract_suffix(search)

			line = f'{self.flair}{indent}{prefix}{result}{suffix}'
			return self.log(line)
			

	class Search:
		def __init__(self, origin, queries, default=unspecified_argument, **kwargs):
			super().__init__(origin=origin, queries=queries, default=default, **kwargs)
			self.query_chain = []
			self.product = None



		def _resolve_query(self, node, query):
			return node.get(query)

		def _search_path(self, query, path=()):

			if query in self.origin:
				return path + (query,)
			for key, value in self.origin.items():
				if isinstance(value, SimpleConfigNode):
					try:
						return value._search_path(query, path=path + (key,))
					except self.QueryFailed:
						pass
			raise self.QueryFailed(query)


		def evaluate(self, silent=None):
			for query in queries:
				try:
					path = self._search_path(query, path=())
				except self.QueryFailed:
					path = None
				else:
					path = self._clean_up_search_path(path)
					break

			return self.package(path, default=default, silent=silent)


	class Editor:
		def __init__(self, node):
			self.node = node

		def __enter__(self):
			return self.node

		def __exit__(self, exc_type, exc_val, exc_tb):
			pass

	def __init__(self, *args, reporter=None, **kwargs):
		if reporter is None:
			reporter = self.Reporter()
		super().__init__(*args, **kwargs)
		self.reporter = reporter

	@property
	def silent(self):
		return self.reporter.silent
	@silent.setter
	def silent(self, value):
		self.reporter.silent = value

	@property
	def readonly(self):
		return self._readonly
	@readonly.setter
	def readonly(self, value):
		self._readonly = value

	pass

class AskParentNode(SimpleConfigNode):
	_ask_parent = True
	_confidential_prefix = '_'


class VolatileNode(SimpleConfigNode):
	_volatile_prefix = '__'


class StorageNodes(VolatileNode):
	_weak_storage_prefix = '<?>'
	_strong_storage_prefix = '<!>'
	# created components are stored under __obj and can be access with prefix
	# (where weak creates component when missing)
	pass



class ReferenceNode(SimpleConfigNode):
	reference_prefix = '<>'
	origin_reference_prefix = '<o>'

	def package(self, value):
		if value is None:
			return None
		return self.ref.package(value)




class ConfigSparseNode(AutoTreeSparseNode, ConfigNode): pass
class ConfigDenseNode(AutoTreeDenseNode, ConfigNode): pass
ConfigNode.DefaultNode = AutoTreeSparseNode
ConfigNode.SparseNode = AutoTreeSparseNode
ConfigNode.DenseNode = AutoTreeDenseNode













