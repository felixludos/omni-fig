from typing import List, Dict, Tuple, Optional, Union, Any, Hashable, Sequence, Callable, Generator, Type, Iterable, \
	Iterator, NamedTuple, ContextManager
import abc
import inspect
from collections import OrderedDict
from omnibelt import get_printer, unspecified_argument, extract_function_signature, JSONABLE, Primitive
from omnibelt.nodes import AutoTreeNode, AutoTreeSparseNode, AutoTreeDenseNode, AutoAddressNode, AddressNode

from ..abstract import AbstractConfig, AbstractProject, AbstractCreator, AbstractConfigurable
from .creator import DefaultCreator
from .search import ConfigSearchBase, SimpleTrace, SimpleSearch
from .reporter import ConfigReporter, ConfigReporterBase

prt = get_printer(__name__)


class _ConfigNode(AbstractConfig, AutoTreeNode):
	# def __init__(self, *args, project: Optional[AbstractProject] = None, **kwargs):
	# 	super().__init__(*args, **kwargs)
	# 	self._project = project
	# 	# self.readonly = readonly

	@property
	def root(self) -> '_ConfigNode':
		parent = self.parent
		if parent is None:
			return self
		return parent.root


	# @property
	# def project(self):
	# 	return self.root._project
	# @project.setter
	# def project(self, value):
	# 	self.root._project = value
	#
	# @property
	# @abc.abstractmethod
	# def silent(self):
	# 	raise NotImplementedError
	# @silent.setter
	# @abc.abstractmethod
	# def silent(self, value):
	# 	raise NotImplementedError

	# @property
	# def readonly(self):
	# 	return self.root._readonly
	# @readonly.setter
	# def readonly(self, value):
	# 	self.root._readonly = value

	# class ReadOnlyError(Exception): pass


	# def push(self, addr: str, value: Any, overwrite: bool = True, silent: Optional[bool] = None) -> bool:
	# 	if self.readonly:
	# 		raise self.ReadOnlyError('Cannot push to read-only node')
	# 	try:
	# 		existing = self.get(addr)
	# 	except self.MissingKey:
	# 		existing = None
	#
	# 	if existing is None or overwrite:
	# 		self.set(addr, value)
	# 		return True
	# 	return False


	# LazyIterator = None
	# def as_iterator(self, *queries, product: bool = False, include_key: bool = False, silent: Optional[bool] = None,
	#                 **kwargs) -> Iterator[Union['ConfigNode', Tuple['ConfigNode', str]]]:
	# 	if len(queries):
	# 		return self.peeks(*queries, silent=silent).as_iterator(product=product, include_key=include_key,
	# 		                                                       silent=silent, **kwargs)
	# 	return self.LazyIterator(self, product=product, include_key=include_key, silent=silent, **kwargs)



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


class ConfigNode(_ConfigNode):
	DummyNode: 'ConfigNode' = None
	Settings = OrderedDict

	class Search(SimpleSearch):
		def sub_search(self, origin, queries):
			out = self.__class__(origin=origin, queries=queries, default=origin.empty_default,
			                      parent_search=self)
			out.query_chain = out.queries
			return out
		
		def __init__(self, origin: 'ConfigNode', queries: Optional[Sequence[str]], default: Any,
		             parent_search: Optional['ConfigNode.Search'] = None, **kwargs):
			super().__init__(origin=origin, queries=queries, default=default, **kwargs)
			self.force_create = False
			self.parent_search = parent_search

		confidential_prefix = '_'

		def _resolve_query(self, src: 'ConfigNode', query: Optional[str] = unspecified_argument) -> 'ConfigNode':
			if query is unspecified_argument:
				try:
					query = next(self.remaining_queries)
				except StopIteration:
					raise self.SearchFailed(*self.query_chain)
			if query is None:
				self.query_node = src
				return src

			try:
				result = src.get(query)
			except src.MissingKey:
				if src.settings.get('ask_parents', True) and not query.startswith(self.confidential_prefix):
					parent = src.parent
					if parent is not None:
						try:
							result = self._resolve_query(parent, query)
						except parent.MissingKey:
							pass
						else:
							self.query_chain[-1] = f'.{self.query_chain[-1]}'
							self.query_node = result
							return result
				self.query_chain.append(query)
				return self._resolve_query(src)
			else:
				self.query_chain.append(query)
				self.query_node = result
				return result

		def _find_node(self) -> 'ConfigNode':
			if self.queries is None or not len(self.queries):
				result = self.origin
				self.query_node = result
			else:
				self.remaining_queries = iter(self.queries)
				result = self._resolve_query(self.origin)
			self.result_node = self.process_node(result)
			return self.result_node
		
		def find_node(self, silent: Optional[bool] = None) -> 'ConfigNode':
			try:
				result = self._find_node()
			except self.SearchFailed:
				if self.default is self.origin.empty_default:
					raise
				result = self.origin.DummyNode(payload=self.default, parent=self.origin)
			result._trace = self
			return result

		def find_product(self, silent: Optional[bool] = None) -> Any:
			try:
				node = self._find_node()
			except self.SearchFailed:
				if self.default is self.origin.empty_default:
					raise
				old = self.origin._trace
				self.origin._trace = self
				self.origin.reporter.report_default(self.origin, self.default, silent=silent)
				self.origin._trace = old
				result = self.default
			else:
				old = node._trace
				node._trace = self
				result = node._create(silent=silent) if self.force_create \
					else node._process(silent=silent)
				node._trace = old
			return result

		force_create_prefix = '<!>' # force create (overwrite product if it exists)
		reference_prefix = '<>' # get reference to product (create if no product)
		origin_reference_prefix = '<o>' # get reference to product (create if no product) from origin
		missing_key_payload = '__x__' # payload for key that doesn't really exist

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
					elif payload == self.missing_key_payload:
						out = self._resolve_query(self.query_node)
						return self.process_node(out)
			return node


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
			# if silent is None:
			# 	silent = self.silent
			if not silent:
				return super().log(*msg, **kwargs)

		def get_key(self, trace: 'ConfigNode.Search') -> str:
			queries = trace.query_chain

			if trace.parent_search is not None:
			# if len(search.parent_search):
				queries = queries.copy()
				queries[0] = f'({queries[0]})'  # if getattr(search.parent_search[0]

			if len(queries) > self.max_num_aliases:
				key = self.transfer.join([queries[0], '...', queries[-1]])
			else:
				key = self.transfer.join(queries)
			return key

		def _stylize(self, node: 'ConfigNode', line: str) -> str:
			trace = node.trace
			if trace is not None:
				node = trace.origin
			indent = self._node_depth(node) * self.indent
			return f'{self.flair}{indent}{line}'

		def _format_component(self, key: str, component_type: str, modifiers: Sequence[str],
		                      creator_type: Optional[str]) -> str:
			mods = modifiers
			mod_info = ''
			if len(mods):
				mod_info = f' (mods=[{", ".join(map(repr,mods))}])' if len(mods) > 1 else f' (mod={mods[0]!r})'
			if creator_type is not None:
				mod_info = f'{mod_info} (creator={creator_type!r})'
			key = '' if key is None else f'{key} '
			return f'{key}type={component_type!r}{mod_info}'

		def _format_value(self, value: Any) -> str:
			return repr(value)

		def report_node(self, node: 'ConfigNode', *, silent: bool = None) -> Optional[str]:
			pass

		def report_product(self, node: 'ConfigNode', *, silent: bool = None) -> Optional[str]:
			pass

		def report_default(self, node: 'ConfigNode', default: Any, *, silent: bool = None) -> Optional[str]:
			trace = node.trace
			key = self.get_key(trace)

			line = f'{key}{self.colon}{self._format_value(default)} (by default)'
			return self.log(self._stylize(node, line), silent=silent)

		def report_iterator(self, node: 'ConfigNode', product: bool = False, include_key: bool = False,
		                    silent: bool = None) -> Optional[str]:
			trace = node.trace
			key = self.get_key(trace)
			N = len(node)
			size = f' [{N} element{"s" if N == 0 or N > 1 else ""}]'
			return self.log(self._stylize(node, f'ITERATOR {key}{size}'), silent=silent)

		def reuse_product(self, node: 'ConfigNode', product: Any, *, component_type: str = None,
		                  modifiers: Optional[Sequence[str]] = None, creator_type: str = None,
		                  silent: bool = None) -> Optional[str]:
			trace = node.trace
			key = self.get_key(trace)
			line = f'REUSING {self._format_component(key, component_type, modifiers, creator_type)}'
			return self.log(self._stylize(node, line), silent=silent)

		def create_primitive(self, node: 'ConfigNode', value: Primitive = unspecified_argument, *,
		                     silent: bool = None) -> Optional[str]:
			trace = node.trace
			key = self.get_key(trace)

			if value is unspecified_argument:
				value = node.payload
			line = f'{key}{self.colon}{self._format_value(value)}'
			return self.log(self._stylize(node, line), silent=silent)

		def create_container(self, node: 'ConfigNode', *, silent: bool = None) -> Optional[str]:
			trace = node.trace
			key = self.get_key(trace)
			N = len(node)

			t, x = ('dict', 'item') if isinstance(node, trace.origin.SparseNode) else ('list', 'element')
			x = f'{x}s' if N != 1 else x
			line = f'{key} [{t} with {N} {x}]'
			return self.log(self._stylize(node, line), silent=silent)

		def create_component(self, node: 'ConfigNode', *, component_type: str = None,
		                     modifiers: Optional[Sequence[str]] = None, creator_type: str = None,
		                     silent: bool = None) -> Optional[str]:
			trace = node.trace
			key = self.get_key(trace)
			line = f'CREATING {self._format_component(key, component_type, modifiers, creator_type)}'
			return self.log(self._stylize(node, line), silent=silent)

	
	class DefaultCreator(AbstractCreator):
		_config_component_key = '_type'
		_config_modifier_key = '_mod'
		_config_creator_key = '_creator'
		
		@classmethod
		def replace(cls, creator: 'ConfigNode.DefaultCreator', component_type: Optional[str] = None,
		            modifiers: Optional[Sequence[str]] = None,
		            project: Optional[AbstractProject] = unspecified_argument,
		            component_entry=unspecified_argument, silent=unspecified_argument, **kwargs):
			if component_type is None:
				component_type = creator.component_type
			if modifiers is None:
				modifiers = creator.modifiers
			if project is unspecified_argument:
				project = creator.project
			if component_entry is unspecified_argument:
				component_entry = creator.component_entry
			if silent is unspecified_argument:
				silent = creator.silent
			return super().replace(creator, component_type=component_type, modifiers=modifiers, project=project,
			                       component_entry=component_entry, silent=silent, **kwargs)
		
		def __init__(self, config: AbstractConfig, *, component_type: str = unspecified_argument,
		             modifiers: Optional[Sequence[str]] = None, project: Optional[AbstractProject] = None,
		             component_entry: Optional = unspecified_argument, silent: Optional[bool] = None, **kwargs):
			if component_type is unspecified_argument:
				component_type = config.pull(self._config_component_key, None, silent=True) \
					if isinstance(config, config.SparseNode) else None
			if component_type is not None and modifiers is None:
				modifiers = config.pull(self._config_modifier_key, None, silent=True)
				if modifiers is None:
					modifiers = []
				elif isinstance(modifiers, dict):
					modifiers = [mod for mod, _ in sorted(modifiers.items(), key=lambda x: (x[1], x[0]))]
				elif isinstance(modifiers, str):
					modifiers = [modifiers]
				elif isinstance(modifiers, (list, tuple)):
					modifiers = list(modifiers)
				else:
					raise ValueError(f'Invalid modifier: {modifiers!r}')
			if project is None:
				project = config.project
			super().__init__(config, **kwargs)
			if project is None:
				prt.warning('No project specified for creator')
			self.silent = silent
			self.project = project
			self.component_type = component_type
			self.modifiers = modifiers
			self.component_entry = component_entry
		
		def validate(self, config) -> 'DefaultCreator':
			if self.component_type is None:
				return
			if self.component_entry is unspecified_argument:
				self.component_entry = self.project.find_artifact('component', self.component_type)
			creator = config.pull(self._config_creator_key, self.component_entry.creator, silent=True)
			if creator is not None:
				entry = self.project.find_artifact('creator', creator)
				if type(self) != entry.cls:
					return entry.cls.replace(self, config).validate(config)
		
		# def _fix_args_and_kwargs(self, config, fn, args, kwargs, *, silent: Optional[bool] = None):
		# 	def default_fn(key, default=inspect.Parameter.empty):
		# 		if default is inspect.Parameter.empty:
		# 			default = unspecified_argument
		# 		return config.pull(key, default, silent=silent)
		#
		# 	return extract_function_signature(fn, args, kwargs, default_fn=default_fn)
		
		def _create_component(self, config: 'ConfigNode', args: Tuple, kwargs: Dict[str, Any],
		                      silent: bool = None) -> Any:
			config.reporter.create_component(config, component_type=self.component_type, modifiers=self.modifiers,
			                                 creator_type=self._creator_name, silent=silent)

			cls = self.component_entry.cls
			assert isinstance(cls, type), f'This creator can only be used for components that are classes: {cls!r}'
			
			mods = [self.project.find_artifact('modifier', mod).cls for mod in self.modifiers]
			if len(mods):
				bases = (*reversed(mods), cls)
				cls = type('_'.join(base.__name__ for base in bases), bases, {})
			
			if issubclass(cls, AbstractConfigurable):
				obj = cls.init_from_config(config, args, kwargs, silent=silent)
			else:
				settings = config.settings
				old_silent = settings.get('silent', None)
				settings['silent'] = silent
				obj = cls(config, *args, **kwargs)
				if old_silent is not None:
					settings['silent'] = old_silent
				# fixed_args, fixed_kwargs = self._fix_args_and_kwargs(config, cls.__init__, args, kwargs, silent=silent)
				# obj = cls(*fixed_args, **fixed_kwargs)

			config._trace = None
			return obj
		
		def _create_container(self, config: 'ConfigNode', silent: Optional[bool] = None) -> Any:
			config.reporter.create_container(config, silent=silent)
			trace = config.trace

			if isinstance(config, config.SparseNode):
				product = {}
				for key, child in config.children():
					old = child._trace
					child._trace = None if trace is None else trace.sub_search(config, [key])
					product[key] = child._process(silent=silent)
					child._trace = old
			
			elif isinstance(config, config.DenseNode):
				product = []
				for key, child in config.children():
					old = child._trace
					child._trace = None if trace is None else trace.sub_search(config, [key])
					product.append(child._process(silent=silent))
					child._trace = old
					
			else:
				raise NotImplementedError(f'Unknown container type: {type(config)}')

			config._trace = None
			return product
		
		def _create_primitive(self, config: 'ConfigNode', silent: Optional[bool] = None) -> Any:
			payload = config.payload
			config.reporter.create_primitive(config, value=payload, silent=silent)
			config._trace = None
			return payload
		
		# @staticmethod
		# def _force_create(config: 'ConfigNode') -> bool:
		# 	trace = config.trace
		# 	if trace is None or trace.force_create is None:
		# 		return config.settings.get('force_create', False)
		# 	return trace.force_create
		
		def create(self, config: 'ConfigNode', *args: Any, **kwargs: Any) -> Any:
			return self.create_product(config, args=args, kwargs=kwargs)
		
		def create_product(self, config: 'ConfigNode', args: Optional[Tuple] = None,
		           kwargs: Optional[Dict[str,Any]] = None, *, silent: Optional[bool] = None) -> Any:
			if args is None:
				args = ()
			if kwargs is None:
				kwargs = {}
			if silent is None:
				silent = self.silent
			
			transfer = self.validate(config)
			if transfer is not None:
				return transfer.create_product(config, args=args, kwargs=kwargs)
			
			if self.component_type is None:
				if config.has_payload:
					value = self._create_primitive(config, silent=silent)
				else:
					value = self._create_container(config, silent=silent)
			else:
				value = self._create_component(config, args=args, kwargs=kwargs, silent=silent)
			return value
			

	def search(self, *queries: str, default: Optional[Any] = AbstractConfig.empty_default, **kwargs) -> Search:
		return self.Search(origin=self, queries=queries, default=default, **kwargs)

	def peeks(self, *queries: str, default: Optional[Any] = AbstractConfig.empty_default, silent: Optional[bool] = None,
	         **kwargs) -> 'ConfigNode':
		search = self.search(*queries, default=default, **kwargs)
		return search.find_node(silent=silent)

	def pulls(self, *queries: str, default: Optional[Any] = AbstractConfig.empty_default,
	          silent: Optional[bool] = None, **kwargs) -> Any:
		search = self.search(*queries, default=default, **kwargs)
		return search.find_product(silent=silent)

	def push(self, addr: str, value: Any, overwrite: bool = True, silent: Optional[bool] = None) -> bool:
		if self.settings.get('readonly', False):
			raise self.ReadOnlyError('Cannot push to read-only node')

		if not self.has(addr) or overwrite:
			self.set(addr, value)
			return True
		return False


	def peek_children(self, *, include_key: bool = False, silent: Optional[bool] = None):
		self.reporter.report_iterator(self, include_key=include_key, product=False, silent=silent)
		for key, _ in self.children(keys=True):
			child = self.search(key, silent=silent).find_node(silent=silent)
			yield (key, child) if include_key else child
	
	def pull_children(self, *, include_key: bool = False, force_create: Optional[bool] = False,
	                  silent: Optional[bool] = None):
		for key, child in self.peek_children(include_key=True, silent=silent):
			product = child.create() if force_create else child.process()
			yield (key, product) if include_key else product
		

	def push_pull(self, addr: str, value: Any, overwrite: bool = True, **kwargs) -> Any:
		self.push(addr, value, overwrite=overwrite)
		return self.pull(addr, **kwargs)

	def peek_process(self, query, default: Optional[Any] = AbstractConfig.empty_default, *args, **kwargs):
		node = self.peek(query, default=default)
		out = node.process(*args, **kwargs)
		return out

	def __init__(self, *args, reporter: Optional[Reporter] = None, settings: Optional[Settings] = None,
	             project: Optional[AbstractProject] = None, **kwargs):
		super().__init__(*args, **kwargs)
		self._project = project
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
	def trace(self) -> Optional[Search]:
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

	class ReadOnlyError(Exception): pass

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
	            silent: Optional[bool] = None, **kwargs: Any) -> Any:
		# old = self._trace
		out = self.DefaultCreator(self, silent=silent,  **kwargs)\
			.create_product(self, args=component_args, kwargs=component_kwargs, silent=silent)
		# self._trace = old
		return out

	def _process(self, component_args: Optional[Tuple] = None, component_kwargs: Optional[Dict[str, Any]] = None,
	             silent: Optional[bool] = None, **kwargs: Any) -> Any:
		settings = self.settings
		force_create = settings.get('force_create', False)
		allow_create = settings.get('allow_create', True)
		assert not (force_create and not allow_create), f'Cannot force create without allowing create: {self}'
		if (allow_create and self._product is None) or force_create:
			self._product = self._create(component_args, component_kwargs, silent=silent, **kwargs)
		return self._product

	def create(self, *args: Any, **kwargs: Any) -> Any:
		# return self._create_component(*self._extract_component_info(), args=args, kwargs=kwargs)
		return self._create(args, kwargs, silent=self.settings.get('silent', None))
	
	def create_silent(self, *args: Any, **kwargs: Any) -> Any:
		return self._create(args, kwargs, silent=True)
	
	def process(self, *args: Any, **kwargs: Any) -> Any:
		return self._process(args, kwargs, silent=self.settings.get('silent', None))

	def process_silent(self, *args: Any, **kwargs: Any) -> Any:
		return self._process(args, kwargs, silent=True)

	@property
	def product_exists(self) -> bool:
		return self._product is not None

	def clear_product(self, recursive: bool = True) -> None:
		self._product = None
		if recursive:
			for _, child in self.children():
				child.clear_product(recursive=recursive)

	def __str__(self):
		return f'{self.__class__.__name__}[{len(self)} children]({", ".join(key for key, _ in self.children())})'

	def __repr__(self):
		return f'<{self.__class__.__name__} {len(self)} children>'

	def update(self, update: 'ConfigNode', *, clear_product: bool = True) -> 'ConfigNode':
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


	def silence(self, silent: bool = True) -> ContextManager:
		# return self.reporter.silence(silent)
		return self.context(silent=silent)


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
	ChildrenStructure = list
	def __init__(self, payload: Any, parent: ConfigNode, **kwargs):
		super().__init__(payload=payload, parent=parent, **kwargs)

	def _get(self, addr: Hashable):
		raise self.MissingKey(addr)

	def __repr__(self):
		return f'{self.__class__.__name__}({self.payload!r})'



class ConfigSparseNode(AutoTreeSparseNode, ConfigNode):
	_python_structure = dict


class ConfigDenseNode(AutoTreeDenseNode, ConfigNode):
	_python_structure = tuple


ConfigNode.DummyNode = ConfigDummyNode
ConfigNode.DefaultNode = ConfigSparseNode
ConfigNode.SparseNode = ConfigSparseNode
ConfigNode.DenseNode = ConfigDenseNode







