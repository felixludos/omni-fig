from typing import List, Dict, Tuple, Optional, Union, Any, Hashable, Sequence, Callable, Generator, Type, Iterable, \
	Iterator, NamedTuple, ContextManager
import abc
import inspect
from contextlib import nullcontext
import yaml
from collections import OrderedDict
from omnibelt import Exportable, get_printer, unspecified_argument, extract_function_signature, \
	JSONABLE, Primitive, primitive, Modifiable
from omnibelt.nodes import AutoTreeNode, AutoTreeSparseNode, AutoTreeDenseNode, AutoAddressNode, AddressNode

from ..abstract import AbstractConfig, AbstractProject, AbstractCreator, AbstractConfigurable, AbstractConfigManager, \
	AbstractCustomArtifact, AbstractCertifiable
from .abstract import AbstractSearch, AbstractReporter

prt = get_printer(__name__)


class ConfigNode(AutoTreeNode, Exportable, AbstractConfig, extensions=['.fig.yml', '.fig.yaml']):
	# _DummyNode: 'ConfigNode' = None
	Settings = OrderedDict

	@classmethod
	def from_raw(cls, raw: Any, *, parent: Optional['ConfigNode'] = unspecified_argument,
	             parent_key: Optional[str] = None, **kwargs) -> 'ConfigNode':
		if isinstance(raw, ConfigNode):
			raw.parent = parent
			raw._parent_key = parent_key
			return raw
		if isinstance(raw, dict):
			node = cls.SparseNode(parent=parent, parent_key=parent_key, **kwargs)
			for key, value in raw.items():
				child = cls.from_raw(value, parent=node, parent_key=key, **kwargs)
				if key in node:
					node.get(key).update(child)
				else:
					node.set(key, child, **kwargs)
		elif isinstance(raw, (tuple, list)):
			node = cls.DenseNode(parent=parent, parent_key=parent_key, **kwargs)
			for idx, value in enumerate(raw):
				idx = str(idx)
				node.set(idx, cls.from_raw(value, parent=node, parent_key=idx, **kwargs), **kwargs)
		else:
			node = cls.DefaultNode(payload=raw, parent=parent, parent_key=parent_key, **kwargs)
		return node
	
	
	class Search(AbstractSearch):

		class _sub_search: # TODO: generalize to take in a config object (and then use its trace)
			past = None

			def __init__(self, current):
				self._old = self.past
				self.current = current
				self.__class__.past = current

			def __enter__(self):
				pass

			def __exit__(self, exc_type, exc_val, exc_tb):
				self.__class__.past = self._old

		def sub_search(self) -> 'AbstractSearch':
			return self._sub_search(self)

		# def sub_search(self, origin, queries):
		# 	out = self.__class__(origin=origin, queries=queries, default=origin._empty_default,
		# 	                     parent_search=self)
		# 	out.query_chain = out.queries
		# 	return out
		
		def __init__(self, origin: 'ConfigNode', queries: Optional[Sequence[str]], default: Any,
		             parent_search: Optional['ConfigNode.Search'] = unspecified_argument, **kwargs):
			if parent_search is unspecified_argument:
				parent_search = self._sub_search.past
			super().__init__(origin=origin, queries=queries, default=default, **kwargs)
			self.origin = origin
			self.queries = queries
			self.default = default
			self.query_chain = []
			self.result_node = None
			self.force_create = False
			self.parent_search = parent_search
			self.extra_queries = None

		confidential_prefix = '_'

		def _resolve_query(self, src: 'ConfigNode', query: str, *remaining: str,
		                   chain: Optional[List[str]] = None) -> Tuple[Optional['ConfigNode'], Tuple, List[str]]:
			if chain is None:
				chain = []
			if query is None:
				return src, remaining, chain

			try:
				result = src.get(query)
			except src._MissingKey:
				result = None

			if result is None:
				if src.settings.get('ask_parents', True) and not query.startswith(self.confidential_prefix):
					parent = src.parent
					if parent is not None:
						result, _, parent_chain = self._resolve_query(parent, query)
						if result is None:
							grandparent = parent.parent
							if grandparent is not None and src.settings.get('allow_cousins', False) \
									and src._parent_key is not None:
								cousin_query = f'{src._parent_key}.{query}'
								result, _, cousin_chain = self._resolve_query(grandparent, cousin_query)
								if result is not None:
									chain.append(f'..{cousin_chain[-1]}')
									return result, remaining, chain
						else:
							chain.append(f'.{parent_chain[-1]}')
							return result, remaining, chain
				if len(remaining):
					return self._resolve_query(src, *remaining, chain=chain)
			chain.append(query)
			return result, remaining, chain

		def _find_node(self) -> 'ConfigNode':
			if self.queries is None or not len(self.queries):
				result = self.origin
			else:
				result, self.unused_queries, self.query_chain = self._resolve_query(self.origin, *self.queries)
				if result is None:
					raise self.SearchFailed(*self.query_chain)
			self.query_node = result
			self.result_node = self.process_node(result)
			return self.result_node
		
		def find_node(self, silent: Optional[bool] = None) -> 'ConfigNode':
			try:
				result = self._find_node()
			except self.SearchFailed:
				if self.default is self.origin._empty_default:
					raise
				# result = self.origin._DummyNode(payload=self.default, parent=self.origin)
				return self.default
			result._trace = self
			return result

		def find_product(self, silent: Optional[bool] = None) -> Any:
			try:
				node = self._find_node()
			except self.SearchFailed:
				if self.default is self.origin._empty_default:
					raise
				old = self.origin._trace
				self.origin._trace = self
				self.origin.reporter.report_default(self.origin, self.default, silent=silent)
				self.origin._trace = old
				result = self.default
			else:
				if node is self.origin.empty_value:
					result = node # TODO: finish
					old = self.origin._trace
					self.origin._trace = self
					self.origin.reporter.report_empty(self.origin, silent=silent)
					self.origin._trace = old
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
			if self.origin.empty_value is node:
				# return self.origin._DummyNode(payload=node, parent=self.origin)
				return node
			if node.has_payload:
				payload = node.payload
				if isinstance(payload, str):
					if payload.startswith(self.reference_prefix):
						ref = payload[len(self.reference_prefix):]
						result, self.unused_queries, self.query_chain \
							= self._resolve_query(node, ref, *self.unused_queries, chain=self.query_chain)
						return self.process_node(result)
					elif payload.startswith(self.origin_reference_prefix):
						ref = payload[len(self.origin_reference_prefix):]
						result, self.unused_queries, self.query_chain \
							= self._resolve_query(self.origin, ref, *self.unused_queries, chain=self.query_chain)
						return self.process_node(result)
					elif payload.startswith(self.force_create_prefix):
						ref = payload[len(self.force_create_prefix):]
						result, self.unused_queries, self.query_chain \
							= self._resolve_query(node, ref, *self.unused_queries, chain=self.query_chain)
						self.force_create = True
						return self.process_node(result)
					elif payload == self.missing_key_payload:
						result, self.unused_queries, self.query_chain \
							= self._resolve_query(self.query_node, *self.unused_queries, chain=self.query_chain)
						return self.process_node(result)
			return node

	SearchFailed = Search.SearchFailed

	class Reporter(AbstractReporter):
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
		
		@staticmethod
		def log(*msg, end='\n', sep=' ', silent=None) -> str:
			if not silent:
				msg = sep.join(str(m) for m in msg) + end
				print(msg, end='')
				return msg
		
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

		def report_empty(self, node: 'ConfigNode', *, silent: bool = None) -> Optional[str]:
			trace = node.trace
			key = self.get_key(trace)

			line = f'{key}{self.colon}<is empty>'
			return self.log(self._stylize(node, line), silent=silent)

		def report_iterator(self, node: 'ConfigNode', product: bool = False, silent: bool = None) -> Optional[str]:
			trace = node.trace
			key = self.get_key(trace)
			N = len(node)
			size = f' [{N} element{"s" if N == 0 or N > 1 else ""}]'
			return self.log(self._stylize(node, f'ITERATOR {key}{size}'), silent=silent)

		def reuse_product(self, node: 'ConfigNode', product: Any, *, silent: bool = None) -> Optional[str]:
			trace = node.trace
			key = self.get_key(trace)

			reusing = '' if isinstance(product, primitive) else ' (reuse)'
			line = f'{key}{self.colon}{self._format_value(product)}{reusing}'
			return self.log(self._stylize(node, line), silent=silent)

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


	class CycleError(RuntimeError):
		def __init__(self, config):
			super().__init__(f'Cycle detected for {config.my_address()}')
			self.config = config


	class DefaultCreator(AbstractCreator):
		_config_component_key = '_type'
		_config_modifier_key = '_mod'
		_config_creator_key = '_creator'

		_creation_context = None
		
		@classmethod
		def replace(cls, creator: 'ConfigNode.DefaultCreator', config, *, component_type: Optional[str] = None,
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
			return super().replace(creator, config, component_type=component_type, modifiers=modifiers, project=project,
			                       component_entry=component_entry, silent=silent, **kwargs)
		
		def __init__(self, config: 'ConfigNode', *, component_type: Optional[str] = unspecified_argument,
		             modifiers: Optional[Sequence[str]] = None, project: Optional[AbstractProject] = None,
		             component_entry: Optional[NamedTuple] = unspecified_argument, silent: Optional[bool] = None,
		             **kwargs):
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

		@staticmethod
		def _modify_component(component, modifiers=()):
			cls = component.cls
			if isinstance(cls, AbstractCustomArtifact):
				cls = cls.top
				if len(modifiers) > 0:
					raise ValueError(f'Cannot apply modifiers to custom artifacts: {component.name!r}')
				return cls
			mods = [mod.cls for mod in modifiers]
			if issubclass(cls, Modifiable):
				return cls.inject_mods(*mods)
			# default subclass
			if len(mods):
				bases = (*reversed(mods), cls)
				cls = type('_'.join(base.__name__ for base in bases), bases, {})
			return cls

		def _create_component(self, config: 'ConfigNode', args: Tuple, kwargs: Dict[str, Any],
		                      silent: bool = None) -> Any:
			config.reporter.create_component(config, component_type=self.component_type, modifiers=self.modifiers,
			                                 creator_type=self._creator_name, silent=silent)
			cls = self._modify_component(self.component_entry,
			                             [self.project.find_artifact('modifier', mod) for mod in self.modifiers])
			# assert isinstance(cls, type), f'This creator can only be used for components that are classes: {cls!r}'

			if isinstance(cls, type) and issubclass(cls, AbstractConfigurable):
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

			if isinstance(obj, AbstractCertifiable):
				obj = obj.__certify__(config)

			config._trace = None
			return obj
		
		def _create_container(self, config: 'ConfigNode', silent: Optional[bool] = None) -> Any:
			config.reporter.create_container(config, silent=silent)
			trace = config.trace

			context = nullcontext() if trace is None else trace.sub_search()

			with context:
				if isinstance(config, config.SparseNode):
					product = {}
					for key, child in config.named_children():
						# old = child._trace
						# child._trace = None if trace is None else trace.sub_search(config, [key])
						product[key] = config.pull(key, silent=silent)
						# child._trace = old
					# product = config.SparseNode._python_structure(product)

				elif isinstance(config, config.DenseNode):
					product = []
					for key, child in config.named_children():
						# old = child._trace
						# child._trace = None if trace is None else trace.sub_search(config, [key])
						product.append(config.pull(key, silent=silent))
						# child._trace = old
					# product = config.DenseNode._python_structure(product)
				else:
					raise NotImplementedError(f'Unknown container type: {type(config)}')

			config._trace = None
			return product
		
		def _create_primitive(self, config: 'ConfigNode', silent: Optional[bool] = None) -> Any:
			payload = config.payload
			config.reporter.create_primitive(config, value=payload, silent=silent)
			config._trace = None
			return payload

		def _setup_context(self, config: 'ConfigNode') -> None:
			table = ConfigNode.DefaultCreator._creation_context
			if table is None:
				ConfigNode.DefaultCreator._creation_context = {config: True}
			else:
				if config in table:
					raise config.CycleError(config)
				table[config] = False

		def _end_context(self, config: 'ConfigNode', product: Any) -> None:
			reset = ConfigNode.DefaultCreator._creation_context.get(config, None)
			if reset:
				ConfigNode.DefaultCreator._creation_context = None
			elif reset is not None:
				del ConfigNode.DefaultCreator._creation_context[config]

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

			self._setup_context(config)

			if self.component_type is None:
				if config.has_payload:
					value = self._create_primitive(config, silent=silent)
				else:
					value = self._create_container(config, silent=silent)
			else:
				value = self._create_component(config, args=args, kwargs=kwargs, silent=silent)

			self._end_context(config, value)
			return value
			

	def search(self, *queries: str, default: Optional[Any] = AbstractConfig._empty_default, **kwargs) -> Search:
		return self.Search(origin=self, queries=queries, default=default, **kwargs)

	def peeks(self, *queries: str, default: Optional[Any] = AbstractConfig._empty_default, silent: Optional[bool] = None,
	          **kwargs) -> 'ConfigNode':
		search = self.search(*queries, default=default, **kwargs)
		return search.find_node(silent=silent)

	def pulls(self, *queries: str, default: Optional[Any] = AbstractConfig._empty_default,
	          silent: Optional[bool] = None, **kwargs) -> Any:
		search = self.search(*queries, default=default, **kwargs)
		return search.find_product(silent=silent)

	def push(self, addr: str, value: Any, overwrite: bool = True, silent: Optional[bool] = None) -> bool:
		if self.settings.get('readonly', False):
			raise self.ReadOnlyError('Cannot push to read-only node')

		if value == self._delete_value:
			self.remove(addr)
			return True

		if not self.has(addr) or overwrite:
			self.set(addr, value)
			return True
		return False

	def __len__(self):
		return len(list(self._child_keys()))
	
	def _child_keys(self) -> Iterator[str]:
		for key, child in self.named_children():
			if child is not self.empty_value and not child.has_payload or child.payload not in {'__x__', '_x_'}:
				yield key

	def peek_children(self, *, silent: Optional[bool] = None) -> Iterator['ConfigNode']:
		for key, child in self.peek_named_children(silent=silent):
			yield child

	def peek_named_children(self, *, silent: Optional[bool] = None) -> Iterator[Tuple[str, 'ConfigNode']]:
		self.reporter.report_iterator(self, product=False, silent=silent)
		for key in self._child_keys():
			child = self.search(key).find_node(silent=silent)
			yield key, child

	def pull_children(self, *, force_create: Optional[bool] = False, silent: Optional[bool] = None) -> Iterator[Any]:
		for key, product in self.pull_named_children(force_create=force_create, silent=silent):
			yield product

	def pull_named_children(self, *, force_create: Optional[bool] = False, silent: Optional[bool] = None) \
			-> Iterator[Tuple[str, Any]]:
		for key, child in self.peek_named_children(silent=silent):
			product = child.create() if force_create else child.process()
			yield key, product
		

	def peek_process(self, query, default: Optional[Any] = AbstractConfig._empty_default,
	                 *args: Any, **kwargs: Any) -> Any:
		try:
			node = self.peek(query)
		except self.Search.SearchFailed:
			if default is self._empty_default:
				raise
			return default
		else:
			out = node.process(*args, **kwargs)
			return out

	def peek_create(self, query, default: Optional[Any] = AbstractConfig._empty_default,
	                *args: Any, **kwargs: Any) -> Any:
		try:
			node = self.peek(query)
		except self.Search.SearchFailed:
			if default is self._empty_default:
				raise
			return default
		else:
			out = node.create(*args, **kwargs)
			return out

	def __init__(self, *args, reporter: Optional[Reporter] = None, settings: Optional[Settings] = None,
	             project: Optional[AbstractProject] = None, manager: Optional[AbstractConfigManager] = None,
	             **kwargs):
		super().__init__(*args, **kwargs)
		self._project = project
		self._trace = None
		self._product = None
		self._composition = None
		self._sources = None
		self._manager = manager
		self._reporter = reporter
		self._settings = settings
		if self.reporter is None:
			self.reporter = self.Reporter()
		if self.settings is None:
			self.settings = self.Settings()

	def __eq__(self, other):
		return type(self) == type(other) \
		       and id(self.root) == id(other.root) \
		       and self.my_address() == other.my_address()

	def __hash__(self):
		return hash(self.my_address())

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
	def composition(self) -> Tuple[str]:
		if self._composition is None:
			if self.parent is None:
				return ()
			return self.parent.composition
		return self._composition

	@property
	def sources(self) -> Tuple[str]:
		if self._sources is None:
			if self.parent is None:
				return ()
			return self.parent.sources
		return self._sources

	@property
	def manager(self):
		if self._manager is None:
			parent = self.parent
			if parent is not None:
				return parent.manager
		return self._manager
	
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
	            silent: Optional[bool] = None, creator: Optional[str] = unspecified_argument, **kwargs: Any) -> Any:
		if creator is unspecified_argument:
			creator = self.settings.get('creator')
		creator = self.DefaultCreator if creator is None else self.project.find_artifact('creator', creator).cls
		out = creator(self, silent=silent, project=self.project,  **kwargs)\
			.create_product(self, args=component_args, kwargs=component_kwargs, silent=silent)
		return out

	def _process(self, component_args: Optional[Tuple] = None, component_kwargs: Optional[Dict[str, Any]] = None,
	             silent: Optional[bool] = None, **kwargs: Any) -> Any:
		settings = self.settings
		force_create = settings.get('force_create', False)
		allow_create = settings.get('allow_create', True)
		assert not (force_create and not allow_create), f'Cannot force create without allowing create: {self}'
		if (allow_create and self._product is None) or force_create:
			self._product = self._create(component_args, component_kwargs, silent=silent, **kwargs)
		else:
			self.reporter.reuse_product(self, self._product)
		return self._product

	def create(self, *args: Any, **kwargs: Any) -> Any:
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
			for _, child in self.named_children():
				child.clear_product(recursive=recursive)

	def to_yaml(self, stream=None, default_flow_style=None, sort_keys=True, **kwargs: Any) -> None:
		return yaml.dump(self.to_python(), stream, default_flow_style=default_flow_style, sort_keys=sort_keys,
		                 **kwargs)

	def __str__(self):
		return self.to_yaml()

	def __repr__(self):
		return f'<{self.__class__.__name__} {len(self)} children>'

	def update(self, update: 'ConfigNode', *, clear_product: bool = True, **kwargs) -> 'ConfigNode':
		if clear_product:
			self.clear_product()
			update.clear_product()
		if update.has_payload:
			self.payload = update.payload
		elif self.has_payload:
			self.payload = unspecified_argument
		for key, child in update.named_children():
			child.parent = self
			if key in self:
				self[key].update(child)
			else:
				self[key] = child
		return self


	_delete_value = '_x_'
	def validate(self):
		for key, child in self.named_children():
			if child.has_payload and child.payload == self._delete_value:
				self.remove(key)
			else:
				child.validate()


	def silence(self, silent: bool = True) -> ContextManager:
		# return self.reporter.silence(silent)
		return self.context(silent=silent)



# class ConfigDummyNode(ConfigNode): # output of peek if default is not unspecified_argument but node does not exist
# 	_ChildrenStructure = list
# 	def __init__(self, payload: Optional[Any] = unspecified_argument,
# 	             parent: Optional[ConfigNode] = None, **kwargs):
# 		super().__init__(payload=payload, parent=parent, **kwargs)
#
# 	def _get(self, addr: Hashable):
# 		raise self._MissingKey(addr)
#
# 	def __repr__(self):
# 		return f'{self.__class__.__name__}({self.payload!r})'



class ConfigSparseNode(AutoTreeSparseNode, ConfigNode):
	_python_structure = dict


class ConfigDenseNode(AutoTreeDenseNode, ConfigNode):
	_python_structure = list


# ConfigNode._DummyNode = ConfigDummyNode
ConfigNode.DefaultNode = ConfigSparseNode
ConfigNode.SparseNode = ConfigSparseNode
ConfigNode.DenseNode = ConfigDenseNode







