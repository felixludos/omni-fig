from typing import List, Dict, Tuple, Optional, Union, Any, Hashable, Sequence, Callable, Generator, Type, Iterable, \
	Iterator, Self, NamedTuple, ContextManager
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
	def as_iterator(self, *queries, product: bool = False, include_key: bool = False, silent: Optional[bool] = None,
	                **kwargs) -> Iterator[Union['ConfigNode', Tuple['ConfigNode', str]]]:
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


class ConfigNode(_ConfigNode):
	DummyNode: 'ConfigNode' = None
	Settings = OrderedDict

	class Search(SimpleSearch):
		def sub_search(self, origin, queries):
			return self.__class__(origin=origin, queries=queries, default=origin.empty_default, parent_search=self)
		
		def __init__(self, origin: 'ConfigNode', queries: Optional[Sequence[str]], default: Any,
		             parent_search: Optional['ConfigNode.Search'] = None, **kwargs):
			super().__init__(origin=origin, queries=queries, default=default, **kwargs)
			self.remaining_queries = iter([] if queries is None else queries)
			self.force_create = False
			self.ask_parents = origin.settings.get('ask_parents', True)
			self.parent_search = parent_search

		confidential_prefix = '_'

		def _resolve_query(self, src: 'ConfigNode', query: str) -> 'ConfigNode':
			try:
				result = src.get(query)
			except src.MissingKey:
				if self.ask_parents and not query.startswith(self.confidential_prefix):
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
			self.result_node._trace = self
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

		def get_key(self, trace: 'ConfigNode.Search') -> str:
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

		def _format_component(self, key: str, component_type: str, modifiers: Sequence[str],
		                      creator_type: Optional[str]) -> str:
			mods = modifiers
			mod_info = ''
			if len(mods):
				mod_info = f' (mods=[{", ".join(mods)}])' if len(mods) > 1 else f' (mod={mods[0]})'
			if creator_type is not None:
				mod_info = f'{mod_info} (creator={creator_type})'
			key = '' if key is None else f'{key} '
			return f'{key}type={component_type}{mod_info}'

		def report_node(self, node: 'ConfigNode', *, silent: bool = None) -> Optional[str]:
			pass

		def report_default(self, node: 'ConfigNode', default: Any, *, silent: bool = None) -> Optional[str]:
			raise NotImplementedError

		def reuse_product(self, node: 'ConfigNode', product: Any, *, component_type: str = None,
		                  modifiers: Optional[Sequence[str]] = None, creator_type: str = None,
		                  silent: bool = None) -> Optional[str]:
			trace = node.trace
			key = self.get_key(trace)
			line = f'REUSING {self._format_component(key, component_type, modifiers, creator_type)}'
			return self.log(self._stylize(node, line), silent=silent)

		def report_iterator(self, node: 'ConfigNode', product: bool = False, include_key: bool = False,
		                    silent: bool = None) -> Optional[str]:
			raise NotImplementedError

		def create_primitive(self, node: 'ConfigNode', value: Primitive = unspecified_argument, *,
		                     silent: bool = None) -> Optional[str]:
			trace = node.trace
			key = self.get_key(trace)

			if value is unspecified_argument:
				value = repr(node.payload)
			line = f'{key}{self.colon}{value}'
			return self.log(self._stylize(node, line), silent=silent)

		def create_container(self, node: 'ConfigNode', *, silent: bool = None) -> Optional[str]:
			trace = node.trace
			key = self.get_key(trace)
			N = len(node)

			# if value is unspecified_argument:
			# 	t, x = ('list', 'element') if isinstance(node, trace.origin.SparseNode) else ('dict', 'item')
			# else:
			# 	t, x = ('list', 'element') if isinstance(value, list) else ('dict', 'item')
			t, x = ('list', 'element') if isinstance(node, trace.origin.SparseNode) else ('dict', 'item')
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
		
		def __init__(self, config: AbstractConfig, *, component_type: str = None,
		             modifiers: Optional[Sequence[str]] = None, project: Optional[AbstractProject] = None,
		             component_entry: Optional = None, silent: Optional[bool] = None, **kwargs):
			if component_type is None:
				component_type = config.pull(self._config_component_key, None, silent=True)
			if modifiers is None:
				modifiers = config.pull(self._config_modifier_key, None, silent=True)
				if modifiers is None:
					modifiers = []
				elif isinstance(modifiers, dict):
					modifiers = [mod for mod, _ in sorted(modifiers.items(), key=lambda x: (x[1], x[0]))]
				elif isinstance(modifiers, str):
					modifiers = [modifiers]
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
		
		def validate(self, config) -> Union[Self, 'DefaultCreator']:
			if self.component_entry is None:
				self.component_entry = self.project.find_artifact('component', self.component_type)
			creator = config.pull(self._config_creator_key, self.component_entry.creator, silent=True)
			if creator is not None:
				entry = self.project.find_artifact('creator', creator)
				if type(self) != entry.cls:
					return entry.cls.replace(self, config).validate(config)
		
		def _fix_args_and_kwargs(self, config, fn, args, kwargs, *, silent: Optional[bool] = None):
			def default_fn(key, default=inspect.Parameter.empty):
				if default is inspect.Parameter.empty:
					default = unspecified_argument
				return config.pull(key, default, silent=silent)
			
			return extract_function_signature(fn, args, kwargs, default_fn=default_fn)
		
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
				return cls.init_from_config(config, args, kwargs, silent=silent)
			fixed_args, fixed_kwargs = self._fix_args_and_kwargs(config, cls.__init__, args, kwargs, silent=silent)
			return cls(*fixed_args, **fixed_kwargs)
		
		def _create_container(self, config: 'ConfigNode', silent: Optional[bool] = None) -> Any:
			config.reporter.create_container(config, silent=silent)

			trace = config.trace
			if isinstance(config, config.SparseNode):
				product = {}
				for key, child in config.children():
					child._trace = None if trace is None else trace.sub_search(config, key)
					product[key] = child.product
					child._trace = None
			
			elif isinstance(config, config.DenseNode):
				product = []
				for key, child in config.children():
					child._trace = None if trace is None else trace.sub_search(config, key)
					product.append(child.product)
					child._trace = None
					
			else:
				raise NotImplementedError(f'Unknown container type: {type(config)}')
		
			return product
		
		def _create_primitive(self, config: 'ConfigNode', silent: Optional[bool] = None) -> Any:
			payload = config.payload
			config.reporter.create_primitive(config, value=payload, silent=silent)
			return payload
		
		@staticmethod
		def _force_create(config: 'ConfigNode') -> bool:
			trace = config.trace
			if trace is None or trace.force_create is None:
				return config.settings.get('force_create', False)
			return trace.force_create
		
		def create(self, config: 'ConfigNode', args: Optional[Tuple] = None,
		           kwargs: Optional[Dict[str,Any]] = None, *, silent: Optional[bool] = None) -> Any:
			if args is None:
				args = ()
			if kwargs is None:
				kwargs = {}
			if silent is None:
				silent = self.silent
			
			transfer = self.validate(config)
			if transfer is not None:
				return transfer.create(config, args=args, kwargs=kwargs)
			
			force_create = self._force_create(config)
			if config.product_exists and not force_create:
				product = config._product
				if isinstance(product, Primitive):
					config.reporter.create_primitive(config, value=product, silent=silent)
				else:
					config.reporter.reuse_product(config, product, component_type=self.component_type,
					                              modifiers=self.modifiers, creator_type=self._creator_name,
					                              silent=silent)
				return product
			
			if self.component_entry is None:
				if config.has_payload:
					value = self._create_primitive(config, silent=silent)
				else:
					value = self._create_container(config, silent=silent)
			else:
				value = self._create_component(config, args=args, kwargs=kwargs, silent=silent)
			
			if not force_create:
				config._product = value
			return value
			

	def search(self, *queries: str, default: Optional[Any] = unspecified_argument, **kwargs) -> Search:
		return self.Search(origin=self, queries=queries, default=default, **kwargs)

	def peeks(self, *queries: str, default: Optional[Any] = unspecified_argument, silent: Optional[bool] = None,
	         **kwargs) -> 'ConfigNode':
		search = self.search(*queries, default=default, **kwargs)
		node = search.find_node()
		node.reporter.report_node(node)
		return node

	def pulls(self, *queries: str, default: Optional[Any] = unspecified_argument, *,
	          silent: Optional[bool] = None) -> Any:
		search = self.search(*queries, default=default)
		node = search.find_node()
		out = node.create()
		return out

	def push(self, addr: str, value: Any, overwrite: bool = True, silent: Optional[bool] = None) -> bool:
		if self.settings.get('readonly', False):
			raise self.ReadOnlyError('Cannot push to read-only node')
		try:
			existing = self.get(addr)
		except self.MissingKey:
			existing = None

		if existing is None or overwrite:
			self.set(addr, value)
			return True
		return False


	class LazyIterator:
		def __init__(self):
			raise NotImplementedError
		
	
	def peek_children(self, *, include_key: bool = False, silent: Optional[bool] = None):
		raise NotImplementedError
	
	def pull_children(self, *, include_key: bool = False, silent: Optional[bool] = None):
		raise NotImplementedError
		

	def push_pull(self, addr: str, value: Any, overwrite: bool = True, **kwargs) -> Any:
		self.push(addr, value, overwrite=overwrite)
		return self.pull(addr, **kwargs)


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
		out = self.DefaultCreator(self, silent=silent,  **kwargs).create(self, args=component_args,
		                                                                 kwargs=component_kwargs)
		self._trace = None
		return out

	def create(self, *args: Any, **kwargs: Any) -> Any:
		# return self._create_component(*self._extract_component_info(), args=args, kwargs=kwargs)
		return self._create(args, kwargs)
	
	def create_silent(self, *args: Any, **kwargs: Any) -> Any:
		return self._create(args, kwargs, silent=True)
	
	def get_product(self, *args: Any, **kwargs: Any) -> Any:
		settings = self.settings
		force_create = settings.get('force_create', False)
		allow_create = settings.get('allow_create', True)
		assert not (force_create and not allow_create), f'Cannot force create without allowing create: {self}'
		if (allow_create and self._product is None) or force_create:
			self._product = self._create(args, kwargs)
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

	def update(self, update: 'ConfigNode', *, clear_product: bool = True) -> Self:
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







