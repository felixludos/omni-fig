from typing import List, Dict, Tuple, Optional, Union, Any, Hashable, Sequence, Callable, Generator, Type, Iterable, \
	Iterator, Self, NamedTuple, ContextManager
import abc
from inspect import Parameter
from omnibelt import get_printer, unspecified_argument, extract_function_signature, JSONABLE, Primitive
from omnibelt.nodes import AutoTreeNode, AutoTreeSparseNode, AutoTreeDenseNode, AutoAddressNode, AddressNode

from ..abstract import AbstractConfig, AbstractProject, AbstractCreator, AbstractConfigurable
from .creator import DefaultCreator
from .search import ConfigSearchBase
from .reporter import ConfigReporter, ConfigReporterBase

prt = get_printer(__name__)


class _ConfigNode(AbstractConfig, AutoTreeNode):
	def __init__(self, *args, readonly: bool = False, project: Optional[AbstractProject] = None, **kwargs):
		super().__init__(*args, **kwargs)
		self.project = project
		self.readonly = readonly

	@property
	def root(self) -> '_ConfigNode':
		parent = self.parent
		if parent is None:
			return self
		return parent.root


	@property
	def project(self):
		return self.root._project
	@project.setter
	def project(self, value):
		self.root._project = value

	@property
	@abc.abstractmethod
	def silent(self):
		raise NotImplementedError
	@silent.setter
	@abc.abstractmethod
	def silent(self, value):
		raise NotImplementedError

	@property
	def readonly(self):
		return self.root._readonly
	@readonly.setter
	def readonly(self, value):
		self.root._readonly = value

	class ReadOnlyError(Exception): pass


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


	LazyIterator = None
	def as_iterator(self, *queries, product: bool = False, include_key: bool = False,
	                silent: Optional[bool] = None, **kwargs) -> Iterator:
		if len(queries):
			return self.peeks(*queries, silent=silent).as_iterator(product=product, include_key=include_key,
			                                                       silent=silent, **kwargs)
		return self.LazyIterator(self, product=product, include_key=include_key, silent=silent, **kwargs)



class SimpleConfigNode(_ConfigNode):
	Search = ConfigSearchBase
	def __init__(self, *args, silent=False, **kwargs):
		super().__init__(*args, **kwargs)
		self._silent = silent

	@property
	def silent(self):
		return self.root._silent
	@silent.setter
	def silent(self, value):
		self.root._silent = value


	def search(self, *queries, default: Optional[Any] = unspecified_argument, silent: Optional[bool] = None,
	           **kwargs) -> Search:
		return self.Search(origin=self, queries=queries, default=default, **kwargs)

	# def peek(self, query: str, default: Optional[Any] = _ConfigNode.empty_default, *,
	#          silent: Optional[bool] = False) -> 'SimpleConfigNode':
	# 	return self.peeks(query, default=default, silent=silent)
	#
	# def pull(self, query: str, default: Optional[Any] = unspecified_argument, *, silent: Optional[bool] = None,
	#          **kwargs) -> Any:
	# 	return self.pulls(query, default=default, silent=silent, **kwargs)

	def peeks(self, *queries, default: Optional[Any] = unspecified_argument, silent: Optional[bool] = None,
	         **kwargs) -> 'SimpleConfigNode':
		node = self.search(*queries, default=default, **kwargs).find_node()
		self._trace = None
		return node

	def pulls(self, *queries: str, default: Optional[Any] = unspecified_argument, silent: Optional[bool] = None,
	          **kwargs) -> Any:
		out = self.search(*queries, default=default, silent=silent, **kwargs).evaluate()
		self._trace = None
		return out

	def push_pull(self, addr: str, value: Any, overwrite: bool = True, **kwargs) -> Any:
		self.push(addr, value, overwrite=overwrite)
		return self.pull(addr, **kwargs)

	def create(self, config, args=None, kwargs=None) -> Any:
		raise NotImplementedError


from collections import OrderedDict


class ConfigNode(_ConfigNode):
	DummyNode: 'ConfigNode' = None
	DefaultCreator = DefaultCreator
	Settings = OrderedDict

	class Search(ConfigSearchBase):
		def __init__(self, origin: 'ConfigNode', queries: Optional[Sequence[str]],
		             default: Optional[Any] = unspecified_argument, ask_parent: bool = True, **kwargs):
			super().__init__(origin=origin, queries=queries, default=default, **kwargs)
			# self.init_origin = origin
			self.query_chain = []
			self._ask_parent = ask_parent
			self.remaining_queries = iter([] if queries is None else queries)
			self.force_create = False

		confidential_prefix = '_'

		def _resolve_query(self, src: 'ConfigNode', query: str) -> 'ConfigNode':
			try:
				result = src.get(query)
			except src.MissingKey:
				if self._ask_parent and not query.startswith(self.confidential_prefix):
					parent = src.parent
					if parent is not None:
						try:
							result = self._resolve_query(parent, query)
						except parent.MissingKey:
							pass
						else:
							self.query_chain.append(f'.{query}')
							return result
				self.query_chain.append(query)
				try:
					next_query = next(self.remaining_queries)
				except StopIteration:
					raise self.SearchFailed(f'No such key: {query!r}')
				else:
					return self._resolve_query(src, next_query)
			else:
				self.query_chain.append(query)
				return result

		def find_node(self) -> 'ConfigNode':
			try:
				query = next(self.remaining_queries)
			except StopIteration:
				result = self.origin
			else:
				result = self._resolve_query(self.origin, query)

			self.query_node = result
			self.result_node = self.process_node(result)
			return self.result_node

		force_create_prefix = '<!>' # force create (overwrite product if it exists)
		reference_prefix = '<>' # get reference to product (create if no product)
		origin_reference_prefix = '<o>' # get reference to product (create if no product) from origin

		def process_node(self, node: 'ConfigNode') -> 'ConfigNode':  # follows references
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
					elif payload.startswith(self.force_create_prefix):
						ref = payload[len(self.force_create_prefix):]
						out = self._resolve_query(node, ref)
						self.force_create = True
						return self.process_node(out)
			return node


	class Trace:
		@classmethod
		def from_search(cls, search: 'ConfigNode.Search', previous: Optional['ConfigNode.Trace'] = None)\
				-> 'ConfigNode.Trace':
			return cls(origin=search.origin, chain=search.chain, previous=previous)

		def __init__(self, *, origin: 'ConfigNode', chain: List[str],
		             previous: Optional['ConfigNode.Trace'] = None) -> None:
			self.origin = origin
			self.chain = chain
			self.previous = previous
			self.component_type = None
			self.modifiers = None
			self.creator_type = None

		@property
		def key(self) -> str:
			return self.origin.reporter.get_key(self)

		def __repr__(self) -> str:
			return f'<{self.__class__.__name__} {self.origin} {self.chain} {self.previous}>'


	class Reporter(ConfigReporterBase):
		def __init__(self, indent: str = ' > ', flair: str = '| ', transfer: str = ' --> ', colon:str = ': ',
		             prefix_fmt: str = '{prefix}', suffix_fmt: str = ' (by {suffix!l})',
		             max_num_aliases: int = 3, **kwargs):
			super().__init__(**kwargs)
			self.indent = indent
			self.flair = flair
			self.transfer = transfer
			self.colon = colon
			self.prefix_fmt = prefix_fmt
			self.suffix_fmt = suffix_fmt
			self.max_num_aliases = max_num_aliases

		@classmethod
		def _node_depth(cls, node: 'ConfigNode', _fuel: int = 100) -> int:
			if _fuel <= 0:
				raise RuntimeError('Depth exceeded 100 (there is probably an infinite loop in the config tree)')
			if node.parent is None:
				return 0
			return cls._node_depth(node.parent, _fuel=_fuel - 1) + 1

		def log(self, *msg, silent=None, **kwargs) -> str:
			if silent is None:
				silent = self.silent
			if not silent:
				return super().log(msg, **kwargs)

		def get_key(self, trace: 'ConfigNode.Trace') -> str:
			queries = trace.chain

			if trace.previous is not None:
			# if len(search.parent_search):
				queries = queries.copy()
				queries[0] = f'({queries[0]})'  # if getattr(search.parent_search[0]

			if len(queries) > self.max_num_aliases:
				key = self.transfer.join([queries[0], '...', queries[-1]])
			else:
				key = self.transfer.join(queries)
			return key

		def _stylize(self, node: 'ConfigNode', line: str) -> str:
			indent = max(0, self._node_depth(node) - 1) * self.indent
			return f'{self.flair}{indent}{line}'

		def report_node(self, node: 'ConfigNode', *, silent: bool = None) -> Optional[str]:
			pass

		def report_default(self, node: 'ConfigNode', default: Any, *, silent: bool = None) -> Optional[str]:
			raise NotImplementedError

		def create_primitive(self, node: 'ConfigNode', value: Primitive = unspecified_argument, *,
		                     silent: bool = None) -> Optional[str]:
			trace = node.trace
			key = self.get_key(trace)

			if value is unspecified_argument:
				value = repr(node.payload)
			line = f'{key}{self.colon}{value}'
			return self.log(self._stylize(node, line), silent=silent)

		def create_branch(self, node: 'ConfigNode', action: Optional[str] = None,
		                  value: Union[List, Dict] = unspecified_argument, *,
		                  silent: bool = None) -> Optional[str]:
			trace = node.trace
			key = self.get_key(trace)
			N = len(node)

			if action is not None:
				key = f'{action.upper()} {key}'

			if value is unspecified_argument:
				t, x = ('list', 'element') if isinstance(node, trace.origin.SparseNode) else ('dict', 'item')
			else:
				t, x = ('list', 'element') if isinstance(value, list) else ('dict', 'item')
			x = f'{x}s' if N != 1 else x
			line = f'{key} [{t} with {N} {x}]'
			return self.log(self._stylize(node, line), silent=silent)

		def create_component(self, node: 'ConfigNode', action: Optional[str] = 'creating', *,
		                     silent: bool = None) -> Optional[str]:
			trace = node.trace
			key = trace.key
			cmpn = trace.component_type
			mods = trace.modifiers
			creator = trace.creator_type

			mod_info = ''
			if len(mods):
				mod_info = f' (mods=[{", ".join(mods)}])' if len(mods) > 1 else f' (mod={mods[0]})'
			if creator is not None:
				mod_info = f'{mod_info} (creator={creator})'
			key = '' if key is None else f'{key} '
			line = f'{action.upper()} {key}type={cmpn}{mod_info}'
			return self.log(self._stylize(node, line), silent=silent)


	def __init__(self, *args, reporter: Optional[Reporter] = None, settings: Optional[Settings] = None, **kwargs):
		super().__init__(*args, **kwargs)
		self._trace = None
		self._product = None
		self._reporter = reporter
		self._settings = settings
		if self.reporter is None:
			self.reporter = self.Reporter()
		if self.settings is None:
			self.settings = self.Settings()

	@property
	def project(self):
		if self._project is None:
			parent = self.parent
			if parent is not None:
				return parent.project
		return self._project
	@project.setter
	def project(self, project: AbstractProject):
		parent = self.parent
		if parent is None:
			self._project = project
		else:
			parent.project = project

	@property
	def trace(self) -> Optional[Trace]:
		return self._trace

	@property
	def reporter(self) -> Reporter:
		if self._reporter is None:
			parent = self.parent
			if parent is not None:
				return parent.reporter
		return self._reporter
	@reporter.setter
	def reporter(self, reporter: Reporter):
		parent = self.parent
		if parent is None:
			self._reporter = reporter
		else:
			parent.reporter = reporter

	@property
	def settings(self) -> Settings: # global settings for config object,
		# including: ask_parent, prefer_product, product_only, silent, readonly, etc.
		if self._settings is None:
			parent = self.parent
			if parent is not None:
				return parent.settings
		return self._settings
	@settings.setter
	def settings(self, settings: Settings):
		parent = self.parent
		if parent is None:
			self._settings = settings
		else:
			parent.settings = settings

	@property
	def silent(self) -> bool:
		return self.settings.get('silent', False)
	@silent.setter
	def silent(self, value: bool):
		self.settings['silent'] = value

	@property
	def readonly(self) -> bool:
		return self.settings.get('readonly', False)
	@readonly.setter
	def readonly(self, value: bool):
		self.settings['readonly'] = value


	class ConfigContext:
		def __init__(self, config: 'ConfigNode', settings: Dict[str, bool]):
			self.config = config
			self.old_settings = None
			self.settings = settings

		def __enter__(self):
			settings = self.config.settings
			self.old_settings = settings.copy()
			settings.update(self.settings)

		def __exit__(self, exc_type, exc_val, exc_tb):
			settings = self.config.settings
			settings.clear()
			settings.update(self.old_settings)
	def context(self, **settings: bool) -> ContextManager:
		return self.ConfigContext(self, settings)
		

	def _create(self, component_args: Optional[Tuple] = None, component_kwargs: Optional[Dict[str,Any]] = None,
	            **kwargs: Any) -> Any:
		return self.DefaultCreator(self, **kwargs).create(self, args=component_args, kwargs=component_kwargs)

	def create(self, *args: Any, **kwargs: Any) -> Any:
		# return self._create_component(*self._extract_component_info(), args=args, kwargs=kwargs)
		return self._create(args, kwargs)

	@property
	def product(self) -> Any:
		if self._product is None:
			self._product = self.create()
		return self._product

	@property
	def product_exists(self) -> bool:
		return self._product is not None

	def clear_product(self, recursive: bool = True) -> None:
		self._product = None
		if recursive:
			for child in self.children():
				child.clear_product(recursive=recursive)


	def __repr__(self):
		return f'<{self.__class__.__name__} {len(self)} children>'

	def update(self, update: 'ConfigNode', clear_product: bool = True) -> Self:
		if clear_product:
			self.clear_product()
			update.clear_product()
		if update.has_payload:
			self.payload = update.payload
		elif self.has_payload:
			self.payload = unspecified_argument
		for key, child in update.children():
			child.reporter = self.reporter
			child.parent = self
			if key in self:
				self[key].update(child)
			else:
				self[key] = child
		return self


	def silence(self, silent=True) -> ContextManager:
		# return self.reporter.silence(silent)
		return self.context(silent=silent)


	# def set(self, addr: str, value: Any, reporter=None, **kwargs) -> 'ConfigNode':
	# 	# if editor is None:
	# 	# 	editor = self.editor
	# 	if reporter is None:
	# 		reporter = self.reporter
	# 	node, key = self._evaluate_address(addr, auto_create=True)
	# 	return super(AddressNode, node).set(key, value, reporter=reporter, **kwargs)



	# _ask_parent = True
	# _volatile_prefix = '__'

	# class Editor:
	# 	def __init__(self, readonly=False, **kwargs):
	# 		super().__init__(**kwargs)
	# 		self._readonly = readonly
	#
	# 	@property
	# 	def readonly(self):
	# 		return self._readonly
	# 	@readonly.setter
	# 	def readonly(self, value):
	# 		self._readonly = value
	#
	#
	# def __init__(self, *args, reporter=None, editor=None, **kwargs):
	# 	if reporter is None:
	# 		reporter = self.Reporter()
	# 	if editor is None:
	# 		editor = self.Editor()
	# 	super().__init__(*args, **kwargs)
	# 	del self._readonly
	# 	self.reporter = reporter
	# 	self.editor = editor



class ConfigDummyNode(ConfigNode): # output of peek if default is not unspecified_argument but node does not exist
	def __init__(self, payload: Any, parent: ConfigNode, **kwargs):
		super().__init__(payload=payload, parent=parent, **kwargs)



class ConfigSparseNode(AutoTreeSparseNode, ConfigNode): pass


class ConfigDenseNode(AutoTreeDenseNode, ConfigNode): pass


ConfigNode.DummyNode = ConfigDummyNode
ConfigNode.DefaultNode = ConfigSparseNode
ConfigNode.SparseNode = ConfigSparseNode
ConfigNode.DenseNode = ConfigDenseNode







