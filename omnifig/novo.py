from typing import List, Dict, Tuple, Optional, Union, Any, Hashable, Sequence, Callable, Generator, Type, Iterable, Iterator
from omnibelt import unspecified_argument, Singleton
from omnibelt.nodes import AutoTreeNode, AutoTreeSparseNode, AutoTreeDenseNode,  AutoAddressNode, AddressNode


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
			self.result_node = None
			self.final_query = None

		class SearchFailed(KeyError):
			def __init__(self, queries):
				super().__init__(', '.join(queries))

		def _resolve_queries(self, src, queries):
			if not len(queries):
				return None, src
			for query in queries:
				if query is None:
					return None, src
				try:
					return query, src.get(query)
				except src.MissingKey:
					pass
			raise self.SearchFailed(queries)

		def find_node(self):
			try:
				self.final_query, self.result_node = self._resolve_queries(self.origin, self.queries)
			except self.SearchFailed:
				if self.default is unspecified_argument:
					raise
			return self.result_node

		def evaluate(self):
			self.find_node()
			self.product = self.package(self.result_node)
			return self.product

		def package(self, node):
			if node is None:
				return self.default
			return self.result_node.payload

	def __init__(self, *args, readonly=False, **kwargs):
		super().__init__(*args, **kwargs)
		self._readonly = readonly

	@property
	def root(self):
		parent = self.parent
		if parent is None:
			return self
		return parent.root

	@property
	def readonly(self):
		return self._readonly
	@readonly.setter
	def readonly(self, value):
		self._readonly = value

	class ReadOnlyError(Exception): pass

	def search(self, *queries, default: Optional[Any] = unspecified_argument, **kwargs):
		return self.Search(origin=self, queries=queries, default=default, **kwargs)


	def peek(self, *queries, default: Optional[Any] = unspecified_argument, **kwargs) -> 'SimpleConfigNode':
		return self.search(*queries, default=default, **kwargs).find_node()

	def pull(self, query: str, default: Optional[Any] = unspecified_argument, **kwargs) -> Any:
		return self.pulls(query, default=default, **kwargs)

	def pulls(self, *queries: str, default: Optional[Any] = unspecified_argument, **kwargs) -> Any:
		return self.search(*queries, default=default, **kwargs).evaluate()

	def push(self, addr: str, value: Any, overwrite: bool = True, silent: Optional[bool] = None) -> bool:
		if self.readonly:
			raise self.ReadOnlyError('Cannot push to read-only node')
		try:
			existing = self.get(addr)
		except self.MissingKey:
			existing = None

		if existing is None or overwrite:
			self.set(addr, value)
			return True
		return False


	def push_pull(self, addr: str, value: Any, overwrite: bool = True, **kwargs) -> Any:
		self.push(addr, value, overwrite=overwrite)
		return self.pull(addr, **kwargs)



primitive = (int, float, str, bool, type(None))
Primitive = Union[primitive]


class ConfigNode(SimpleConfigNode):
	class Reporter(ConfigReporter):
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


		def _present_component(self, key, search):
			cmpn_type = search.component_type
			mod_types = search.mod_types
			mod_info = f' (mods=[{", ".join(mod_types)}])' if len(mod_types) > 1 else f' (mod={mod_types[0]})'
			return f'{key} type={cmpn_type}{mod_info}'


		def _present_payload(self, search):
			if len(search.query_chain) > self.max_num_aliases:
				key = self.transfer.join([search.query_chain[0], '...', search.query_chain[-1]])
			else:
				key = self.transfer.join(search.query_chain)
			
			if search.action == 'primitive':
				value = repr(search.result_node)
				return f'{key}{self.colon}{value}'

			elif search.action == 'no-payload' or search.action == 'iterator': # list or dict
				node = search.result_node
				N = len(node)
				
				t, x = ('list', 'element') if isinstance(node, search.origin.SparseNode) else ('dict', 'item')
				x = x + 's' if N != 1 else x
				# return f'{key} has {N} {x}:'
				return f'{key} [{t} with {N} {x}]'
				
			elif search.action == 'component':
				return self._present_component(key, search)

			elif search.action == 'storage':
				return self._present_component(key, search)

			raise ValueError(f'Unknown action: {search.action!r}')


		def search_report(self, search):
			indent = self._node_depth(search.origin) * self.indent

			prefix = self._extract_prefix(search)
			result = self._present_payload(search)
			suffix = self._extract_suffix(search)

			line = f'{self.flair}{indent}{prefix}{result}{suffix}'
			return self.log(line)
			
			
	class Search(SimpleConfigNode.Search):
		def __init__(self, origin, queries, default=unspecified_argument,
		             ask_parent=True, lazy_iterator=None, parent_search=(), **kwargs):
			super().__init__(origin=origin, queries=queries, default=default, **kwargs)
			# self.init_origin = origin
			self.query_chain = []
			self._ask_parent = ask_parent
			self.lazy_iterator = lazy_iterator
			self.parent_search = parent_search

		# class SearchFailed(KeyError):
		# 	def __init__(self, queries):
		# 		super().__init__(', '.join(queries))

		_confidential_prefix = '_'

		def _resolve_query(self, src, query, *remainder):
			try:
				result = src.get(query)
			except src.MissingKey:
				if self._ask_parent and not query.startswith(self._confidential_prefix):
					parent = src.parent
					if parent is not None:
						try:
							result = self._resolve_query(parent, query)
						except parent.MissingKey:
							pass
						else:
							self.query_chain.append(f'.{query}')
							return result
				if len(remainder):
					self.query_chain.append(query)
					return self._resolve_query(src, *remainder)
				raise
			else:
				self.query_chain.append(query)
				return result
			
		def find_node(self):
			if self.queries is None or not len(self.queries):
				node = self.origin
			else:
				node = self._resolve_query(self.origin, *self.queries)
				# try:
				# 	node = self._resolve_query(self.origin, *self.queries)
				# except self.origin.MissingKey:
				# 	raise self.SearchFailed(self.queries)
			
			self.query_node = node
			self.result_node = self.process_node(node)
			return self.result_node
		

		# _weak_storage_prefix = '<?>'
		# _strong_storage_prefix = '<!>'
		reference_prefix = '<>'
		origin_reference_prefix = '<o>'
		
		def process_node(self, node: 'ConfigNode'): # follows references
			if node.has_payload:
				payload = node.payload
				if isinstance(payload, str):
					if payload.startswith(self.reference_prefix):
						ref = payload[len(self.reference_prefix):]
						out = self._resolve_query(node, ref)
						return self.process_node(out)
					elif payload.startswith(self.origin_reference_prefix):
						ref = payload[len(self.origin_reference_prefix):]
						out = self._resolve_query(self.origin, ref)
						return self.process_node(out)
			return node
		
		def package_payload(self, node: 'ConfigNode'): # creates components
			
			if node.has_payload:
				return node.payload
			
			# complex object - either component or list/dict
			
			typ = node.pull('_type', None, silent=True)
			if typ is None:
				# check for iterator
				if self.lazy_iterator is not None:
					return self.lazy_iterator(node)
				
				# list or dict
				if isinstance(node, node.SparseNode):
					product = {}
					
					for key, child in node.children():
						product[key] = self.sub_search(node, key)
					
				elif isinstance(node, node.DenseNode):
					product = []
					
					for key, child in node.children():
						product.append(self.sub_search(node, key))
					
				else:
					raise TypeError(f'Unknown node type: {node!r}')
				
			# create component
			
			
			
			
			pass

		def sub_search(self, node, key):
			return self.__class__(node, (key,), parent_search=(*self.parent_search, self)).evaluate()

		def evaluate(self):
			try:
				node = self.find_node()
			except self.SearchFailed:
				if self.default is not unspecified_argument:
					return self.default
				raise
			else:
				self.product = self.package_payload(node)
				return self.product
		
		_ask_parent = True
		_volatile_prefix = '__'

		def package(self, node):
			if node is None:
				return self.default
			
			if node.has_payload:
				payload = node.payload
				
				if isinstance(payload, primitive):
					if isinstance(payload, str) and payload.startswith(self.reference_prefix):
						ref = payload[len(self.reference_prefix):]
						
				
				else:
					return payload
				
				return payload
			
			
			
			return self.result_node.payload


		# def _search_path(self, query, path=()):
		# 	if query in self.origin:
		# 		return path + (query,)
		# 	for key, value in self.origin.items():
		# 		if isinstance(value, SimpleConfigNode):
		# 			try:
		# 				return value._search_path(query, path=path + (key,))
		# 			except self.QueryFailed:
		# 				pass
		# 	raise self.QueryFailed(query)
		#
		#
		# def evaluate(self, silent=None):
		# 	for query in queries:
		# 		try:
		# 			path = self._search_path(query, path=())
		# 		except self.QueryFailed:
		# 			path = None
		# 		else:
		# 			path = self._clean_up_search_path(path)
		# 			break
		#
		# 	return self.package(path, default=default, silent=silent)


	class Editor:
		def __init__(self, readonly=False, **kwargs):
			super().__init__(**kwargs)
			self._readonly = readonly
		
		@property
		def readonly(self):
			return self._readonly
		@readonly.setter
		def readonly(self, value):
			self._readonly = value
		

	def __init__(self, *args, reporter=None, editor=None, **kwargs):
		if reporter is None:
			reporter = self.Reporter()
		if editor is None:
			editor = self.Editor()
		super().__init__(*args, **kwargs)
		del self._readonly
		self.reporter = reporter
		self.editor = editor

	@property
	def silent(self):
		return self.reporter.silent
	@silent.setter
	def silent(self, value):
		self.reporter.silent = value

	@property
	def readonly(self):
		return self.editor.readonly
	@readonly.setter
	def readonly(self, value):
		self.editor.readonly = value


	def set(self, addr: str, value: Any, editor=None, reporter=None, **kwargs) -> 'ConfigNode':
		if editor is None:
			editor = self.editor
		if reporter is None:
			reporter = self.reporter
		node, key = self._evaluate_address(addr)
		return super(AddressNode, node).set(key, value, editor=editor, reporter=reporter, **kwargs)



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













