from typing import List, Dict, Tuple, Optional, Union, Any, Sequence, Type, Iterator, NamedTuple, ContextManager
from pathlib import Path
from contextlib import nullcontext
from copy import deepcopy
import yaml
from collections import OrderedDict
from omnibelt import unspecified_argument, Primitive, primitive, Modifiable
from omnibelt.nodes import AutoTreeNode, AutoTreeSparseNode, AutoTreeDenseNode

from .. import __logger__ as prt
from ..abstract import AbstractConfig, AbstractProject, AbstractCreator, AbstractConfigurable, AbstractConfigManager, \
	AbstractCustomArtifact, AbstractCertifiable

from .abstract import AbstractSearch, AbstractReporter



class ConfigNode(AutoTreeNode, AbstractConfig):
	'''
	The main config node class. This class is used to represent the config tree
	and is the main interface for interacting with the config.
	'''

	Settings = OrderedDict

	@classmethod
	def from_raw(cls, raw: Any, *, parent: Optional['ConfigNode'] = unspecified_argument,
	             parent_key: Optional[str] = None, **kwargs) -> 'ConfigNode':
		'''
		Converts the given raw data into a config node.
		This will recursively convert all nested data into config nodes.

		Args:
			raw: python data to convert (may be a primitive or a dict/list-like object)
			parent: the parent node (if any) of the node to be created
			parent_key: the key of the node to be created (if any) in the parent node
			**kwargs: additional arguments to pass to the constructor

		Returns:
			The created config node

		'''
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
		'''
		Used to traverse the config tree and find the node corresponding to the given set of queries.
		'''

		confidential_prefix = '_' # keys with this prefix do not default to parent nodes

		force_create_prefix = '<!>' # force create of delegate
		delegation_prefix = '<>' # delegate from current node
		delegation_origin_prefix = '<o>' # delegate from origin node of the query
		missing_key_payload = '__x__' # payload for a node that should be treated as missing

		class _sub_search:
			'''
			Context manager to keep track of the previous search object when the search is nested
			(e.g. when the product is a container such as a list or dict).
			'''
			past = None

			def __init__(self, current: AbstractSearch):
				self._old = self.past
				self.current = current
				self.__class__.past = current

			def __enter__(self):
				pass

			def __exit__(self, exc_type, exc_val, exc_tb):
				self.__class__.past = self._old


		def sub_search(self) -> 'ContextManager':
			'''Returns a context manager that allows new searches to reference back to this search'''
			return self._sub_search(self)


		def __init__(self, origin: 'ConfigNode', queries: Optional[Sequence[str]], default: Any,
		             parent_search: Optional['ConfigNode.Search'] = unspecified_argument, **kwargs):
			'''
			Evaluates the given queries and default values to find the node (or consequent product) in the config tree.

			Args:
				origin: the node from which to start the search
				queries: keys to search for (in order) in the config tree
				default: if the search fails, this value is returned
				parent_search: if the search is nested, this is the search that was used to find the parent node
				**kwargs: additional arguments to pass to the constructor (not used)
			'''
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


		def _resolve_query(self, src: 'ConfigNode', query: str, *remaining: str,
		                   chain: Optional[List[str]] = None) -> Tuple[Optional['ConfigNode'], Tuple, List[str]]:
			'''
			Traverses the config tree from the given source node to find the node corresponding to the given query,
			thereby appending the query to the query chain.

			Note that when a query is not found directly in the src node (i.e. the query is not a key in the src node).
			If that fails and the current node has a parent, and the query does not begin with "_" the query is
			passed to the parent node as is. If that also fails and the "allow_cousins" setting is on,
			the parent_key is prepended to the query and passed to the grandparent node (if one exists).

			This process relies on two flags in the settings of the config: "ask_parent" (default: True)
			and "allow_cousins" (default: False).

			Args:
				src: the current node in the traversal
				query: the target key to search for
				*remaining: alternative queries to search for (if the current query fails)
				chain: chain of queries that have been traversed so far (e.g. due to delegations or missing keys)

			Returns:
				A tuple of the node when resolving all given queries in order (or None if no node was found),
				any remaining unused queries, and the updated query chain

			'''
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
			'''
			Traverses the config tree from the origin node to find the node corresponding to the queries
			(given in __init__). If no queries are provided, the origin node is returned.

			Before returning the node, the node is processed with the "process_node"
			(which should check follow delegations as needed). The output of "process_node" is stored as "result_node",
			while the original result of resolving the queries without processing is stored as "query_node".
			Lastly, any unused queries are stored as "unused_queries", while the query chain thus far is "query_chain".

			Returns:
				The processed node corresponding to the queries

			Raises:
				SearchFailed: if the node could not be found

			'''
			if self.queries is None or not len(self.queries):
				result = self.origin
			else:
				result, self.unused_queries, self.query_chain = self._resolve_query(self.origin, *self.queries)
			self.query_node = result
			self.result_node = self.process_node(result)
			return self.result_node


		def find_node(self, silent: Optional[bool] = None) -> 'ConfigNode':
			'''
			Traverses the config tree from the origin node to find the node corresponding to the queries
			(given in __init__). If no queries are provided, the origin node is returned.

			This method should be used when the end result of the search should be the node (not a product).

			Returns:
				The node corresponding to the queries with the current search as the trace (for reporting)

			Raises:
				SearchFailed: if the node could not be found and no default was provided

			'''
			if silent is None:
				silent = self.origin.silent
			try:
				result = self._find_node()
			except self.SearchFailed:
				if self.default is self.origin._empty_default:
					raise
				return self.default
			result._trace = self
			self.origin.reporter.report_node(result, silent=silent)
			return result


		def find_product(self, silent: Optional[bool] = None) -> Any:
			'''
			Traverses the config tree from the origin node to find the node corresponding to the queries and then
			produces the product of that node (using the "process" or "create" method of the node).

			This method should be used when the end result of the search should be the product
			(i.e. value contained by the node).

			If all the queries failed, the default is returned (if provided) and reported using the origin's reporter.

			Args:
				silent: propagate the silent flag the reporter or node processing

			Returns:
				Result of resolving the queries, which is either the product of the node
				or the default value if no node was found

			Raises:
				SearchFailed: if the node could not be found and no default was provided

			'''
			if silent is None:
				silent = self.origin.silent
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


		def process_node(self, node: 'ConfigNode') -> 'ConfigNode':  # resolves delegations
			'''
			Processes the node by checking for delegations (and then resolving those)
			or any other special search features (such as making sure this node is still valid).

			A delegation is a node where the value is itself interpretted as a query to a different node
			(e.g. using the prefix "<>"). There are a few specific prefixes that can be used for different types of
			delegations:
				
				- ``<>``: delegate to a new node starting the search from the current node
				
				- ``<o>``: delegate to a new node starting the search from the origin node
				
				- ``<!>``: delegate to a new node for which the product is always newly created
					(rather than reused if it already exists)

			If the current node delegates, the unused queries and query chain may be updated through
			the ``_resolve_query()`` method.

			If the value of a node is "__x__", the node is considered to be missing
			(i.e. it effectively doesn't exist).

			Args:
				node: the result of resolving the queries thus far

			Returns:
				The node once all delegations and special features have been resolved

			Raises:
				SearchFailed: if the node is not valid or a delegation could not be resolved

			'''
			if node is None:
				raise self.SearchFailed(*self.query_chain)
			if self.origin.empty_value is node:
				return node
			if node.has_payload:
				payload = node.payload
				if isinstance(payload, str):
					if payload.startswith(self.delegation_prefix):
						ref = payload[len(self.delegation_prefix):]
						result, self.unused_queries, self.query_chain \
							= self._resolve_query(node, ref, *self.unused_queries, chain=self.query_chain)
						return self.process_node(result)
					elif payload.startswith(self.delegation_origin_prefix):
						ref = payload[len(self.delegation_origin_prefix):]
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
		'''Formats and prints the results of a search over the config tree.'''
		def __init__(self, indent: str = ' > ', flair: str = '| ', alias_fmt: str = ' --> ', colon:str = ': ',
		             max_num_aliases: int = 3, **kwargs):
			'''
			Specifies the format in which the search results are printed to the console.

			Args:
				indent: for each depth, this string is prepended to the line
				flair: prepended to every line this reporter prints (to distinguish it from other output)
				alias_fmt: used to indicate that a query was replaced by another (e.g. due to delegation or missing)
				colon: separates the key from the value
				max_num_aliases: the maximum number of aliases to print before truncating the list
				**kwargs: passed to the parent class (unused)
			'''
			super().__init__(**kwargs)
			self.indent = indent
			self.flair = flair
			self.alias_fmt = alias_fmt
			self.colon = colon
			self.max_num_aliases = max_num_aliases


		@classmethod
		def _node_depth(cls, node: 'ConfigNode', _fuel: int = 1000) -> int:
			'''
			Returns the depth of the node in the config tree for indents.

			Args:
				node: the node to check
				_fuel: used to prevent infinite recursion

			Returns:
				The depth of the node in the config tree

			Raises:
				RecursionError: if the node is too deep in the tree
			'''
			if _fuel <= 0:
				raise RecursionError('Depth exceeded 1000 (there is probably an infinite loop in the config tree)')
			if node.parent is None:
				return 0
			return cls._node_depth(node.parent, _fuel=_fuel - 1) + 1


		@staticmethod
		def log(*msg: str, end: str = '\n', sep: str = ' ', silent: Optional[bool] = None) -> str:
			'''
			Prints the message to the console (similar to :code:`print`).

			Args:
				*msg: terms to join and print
				end: ending character (default is newline)
				sep: character to join terms (default is space)
				silent: if True, the message is not printed (but still returned)

			Returns:
				The message that was printed

			'''
			msg = sep.join(str(m) for m in msg) + end
			if not silent:
				print(msg, end='')
			return msg


		def get_key(self, trace: 'ConfigNode.Search') -> str:
			'''
			Formats the key of the node (taking parents into account).

			Args:
				trace: the search context (used to get the node)

			Returns:
				The formatted key (including aliases and parents)

			'''
			if trace is None:
				return '.'
			queries = trace.query_chain

			if trace.parent_search is not None:
			# if len(search.parent_search):
				queries = queries.copy()
				queries[0] = f'({queries[0]})'  # if getattr(search.parent_search[0]

			if len(queries) > self.max_num_aliases:
				key = self.alias_fmt.join([queries[0], '...', queries[-1]])
			else:
				key = self.alias_fmt.join(queries)
			return key.replace('_', '-')


		def _stylize(self, node: 'ConfigNode', line: str) -> str:
			'''
			Stylizes the line based on the search origin's depth and the reporter's flair.

			Args:
				node: result of the search
				line: information to print

			Returns:
				The stylized line (including flair and indents)

			'''
			trace = node.trace
			if trace is not None:
				node = trace.origin
			indent = self._node_depth(node) * self.indent
			return f'{self.flair}{indent}{line}'


		def _format_component(self, key: str, component_type: str, modifiers: Sequence[str],
		                      creator_type: Optional[str]) -> str:
			'''
			Formats the component information (type, modifiers, creator) when it is created.

			Args:
				key: of the node that contains the component (i.e. result of :code:`get_key`)
				component_type: registered type of the component
				modifiers: registered modifiers of the component
				creator_type: registered type of the creator (defaults to None)

			Returns:
				The formatted component information

			'''
			mods = modifiers
			mod_info = ''
			if len(mods):
				mod_info = f' (mods=[{", ".join(map(repr,mods))}])' if len(mods) > 1 else f' (mod={mods[0]!r})'
			if creator_type is not None:
				mod_info = f'{mod_info} (creator={creator_type!r})'
			key = '' if key is None else f'{key} '
			return f'{key}type={component_type!r}{mod_info}'


		def _format_value(self, value: Any) -> str:
			'''
			Formats the value of the node (e.g. when the product is a python primitive).

			Args:
				value: payload of the node

			Returns:
				The formatted value (using :code:`repr`)

			'''
			return repr(value)


		def report_node(self, node: 'ConfigNode', *, silent: bool = None) -> Optional[str]:
			'''
			Reports when a node was found and prints it to the console. By default, no message is printed.

			Args:
				node: result of the search
				silent: if True, the message is not printed (but still returned)

			Returns:
				None

			'''
			pass


		def report_default(self, node: 'ConfigNode', default: Any, *, silent: bool = None) -> Optional[str]:
			'''
			Reports when a default value was used and prints it to the console.

			Args:
				node: result of the search
				default: value that was used instead
				silent: if True, the message is not printed (but still returned)

			Returns:
				Message that was printed

			'''
			trace = node.trace
			key = self.get_key(trace)

			line = f'{key}{self.colon}{self._format_value(default)} (by default)'
			return self.log(self._stylize(node, line), silent=silent)


		def report_empty(self, node: 'ConfigNode', *, silent: bool = None) -> Optional[str]:
			'''
			Reports when a node was found, but it was empty and prints it to the console.

			Args:
				node: result of the search
				silent: if True, the message is not printed (but still returned)

			Returns:
				Message that was printed

			'''
			trace = node.trace
			key = self.get_key(trace)

			line = f'{key}{self.colon}<is empty>'
			return self.log(self._stylize(node, line), silent=silent)


		def report_iterator(self, node: 'ConfigNode', product: Optional[bool] = False, *,
		                    silent: Optional[bool] = None) -> Optional[str]:
			'''
			Reports when a node was found and returned as an iterator and prints it to the console.

			Args:
				node: result of the search
				product: if True, the iterator returns the products of the nodes (defaults to False)
				silent: if True, the message is not printed (but still returned)

			Returns:
				Message that was printed

			'''
			trace = node.trace
			key = self.get_key(trace)
			N = len(node)
			size = f' [{N} element{"s" if N == 0 or N > 1 else ""}]'
			return self.log(self._stylize(node, f'ITERATOR {key}{size}'), silent=silent)


		def reuse_product(self, node: 'ConfigNode', product: Any, *, silent: bool = None) -> Optional[str]:
			'''
			Reports when a node was found and its product was reused and prints it to the console.

			Args:
				node: result of the search
				product: the product that was reused
				silent: if True, the message is not printed (but still returned)

			Returns:
				Message that was printed

			'''
			trace = node.trace
			key = self.get_key(trace)

			reusing = '' if isinstance(product, primitive) else ' (reuse)'
			line = f'{key}{self.colon}{self._format_value(product)}{reusing}'
			return self.log(self._stylize(node, line), silent=silent)

			line = f'REUSING {self._format_component(key, component_type, modifiers, creator_type)}'
			return self.log(self._stylize(node, line), silent=silent)


		def create_primitive(self, node: 'ConfigNode', value: Primitive = unspecified_argument, *,
		                     silent: bool = None) -> Optional[str]:
			'''
			Reports when a product was created that was a primitive and prints it to the console.

			Args:
				node: result of the search
				value: of the product
				silent: if True, the message is not printed (but still returned)

			Returns:
				Message that was printed

			'''
			trace = node.trace
			key = self.get_key(trace)

			if value is unspecified_argument:
				value = node.payload
			line = f'{key}{self.colon}{self._format_value(value)}'
			return self.log(self._stylize(node, line), silent=silent)


		def create_container(self, node: 'ConfigNode', *, silent: bool = None) -> Optional[str]:
			'''
			Reports when a product was created that was a container and prints it to the console.

			Args:
				node: result of the search
				silent: if True, the message is not printed (but still returned)

			Returns:
				Message that was printed

			'''
			trace = node.trace
			if trace is not None:
				key = self.get_key(trace)
				N = len(node)

				t, x = ('dict', 'item') if isinstance(node, trace.origin.SparseNode) else ('list', 'element')
				x = f'{x}s' if N != 1 else x
				line = f'{key} [{t} with {N} {x}]'
				return self.log(self._stylize(node, line), silent=silent)


		def create_component(self, node: 'ConfigNode', *, component_type: str = None,
		                     modifiers: Optional[Sequence[str]] = None, creator_type: str = None,
		                     silent: bool = None) -> Optional[str]:
			'''
			Reports when a product was created that was a component and prints it to the console.

			Args:
				node: result of the search
				component_type: registered name of the component
				modifiers: registered names of the modifiers
				creator_type: registered name of the creator (defaults to None)
				silent: if True, the message is not printed (but still returned)

			Returns:
				Message that was printed

			'''
			trace = node.trace
			key = self.get_key(trace)
			line = f'CREATING {self._format_component(key, component_type, modifiers, creator_type)}'
			return self.log(self._stylize(node, line), silent=silent)


	class CycleError(RuntimeError):
		'''Raised when a cycle is detected in the config tree.'''
		def __init__(self, config):
			super().__init__(f'Cycle detected for {config.my_address()}')
			self.config = config


	class DefaultCreator(AbstractCreator):
		'''
		Manages the creation of products of config nodes. Generally, there are three types of products:
			- primitives (int, float, str, bool, None)
			- containers (list, dict)
			- components (objects, must be registered, and may optionally be modified)

		The default creator is responsible for creating the products, but you can also create
		your own creators (e.g. subclassses) and then specify them when registering components
		(to make those the defaults) or in the config directly.
		Alternatively, you can force a specific creator to be used by changing the config setting "creator".

		Note, that it is generally up to the creator to call the config reporter to report the creation of products.

		'''
		_config_component_key = '_type'
		_config_modifier_key = '_mod'
		_config_creator_key = '_creator'

		_creation_context = None
		
		@classmethod
		def replace(cls, creator: 'ConfigNode.DefaultCreator', config, *, component_type: Optional[str] = None,
		            modifiers: Optional[Sequence[str]] = None,
		            project: Optional[AbstractProject] = unspecified_argument,
		            component_entry=unspecified_argument, silent=unspecified_argument, **kwargs) -> AbstractCreator:
			'''
			Extracts information from the given creator to replace it.
			Used primarily in :meth:`DefaultCreator.validate`.
			'''
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
			'''
			A default creator is instantiated each time a product of a config node is created.

			Args:
				config: node for which the product is being created
				component_type: if not specified, the type is extracted from the config node with the key "_type"
				modifiers: if not specified, the modifiers are extracted from the config node with the key "_mod"
				project: the owning project, if not specified, the same project as the config is used
				component_entry: if the component entry has already been found, it can be passed here
				silent: if True, suppresses the reporter from printing messages
				**kwargs: additional arguments (unused)
			'''
			if component_type is unspecified_argument:
				component_type = config.pull(self._config_component_key, None, silent=True) \
					if isinstance(config, config.SparseNode) else None
			if component_type is not None and modifiers is None:
				modifiers = config.pull(self._config_modifier_key, None, silent=True)
				if modifiers is None:
					modifiers = []
				elif isinstance(modifiers, dict):
					if len(modifiers):
						key = next(iter(modifiers))
						modifiers = [mod for _, mod in sorted(modifiers.items(), key=lambda x: int(x[0]))] \
							if key.isdigit() \
							else [mod for mod, _ in sorted(modifiers.items(), key=lambda x: (int(x[1]), x[0]))]
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


		def validate(self, config: 'AbstractConfig') -> AbstractCreator:
			'''
			Validates the creator. If the creator is invalid, a new one is created and returned
			based on what is specified in the config or component_entry.

			If a different creator is specified, the current one is replaced with :meth:`DefaultCreator.replace`.
			Otherwise, the creator is returned unchanged.

			Args:
				config: node for which the product is being created

			Returns:
				Validated creator

			'''
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
		def _modify_component(component: NamedTuple, modifiers: Optional[Tuple] = ()) -> Type:
			'''
			Modifies the component by applying the given modifiers.

			By default, this will create a subclass of all the modifiers and the original component.

			Args:
				component: entry of the component
				modifiers: entries of the modifiers to apply

			Returns:
				Modified component type

			'''
			cls = component.cls
			if isinstance(cls, AbstractCustomArtifact):
				cls = cls.top
				if len(modifiers) > 0:
					raise ValueError(f'Cannot apply modifiers to custom artifacts: {component.name!r}')
				return cls
			mods = [mod.cls for mod in modifiers]
			if issubclass(cls, Modifiable):
				return cls.inject_mods(*reversed(mods))
			# default subclass
			if len(mods):
				bases = (*mods, cls)
				cls = type('_'.join(base.__name__ for base in bases), bases, {})
			return cls


		def _create_component(self, config: 'ConfigNode', args: Tuple, kwargs: Dict[str, Any],
		                      silent: bool = None) -> Any:
			'''
			Creates the component. First finds the component and modifier entries,
			and propagates the silent flag when the component is initialized.

			Note that if the component is a subclass of :class:`AbstractCertifiable`, then after the component
			is fully instantiated and initialized, ``__certify__`` is called with the config
			to certify the component.

			Args:
				config: node for which the product is being created
				args: any manual positional arguments to pass to the component constructor
				kwargs: any manual keyword arguments to pass to the component constructor
				silent: if True, suppresses the reporter from printing messages

			Returns:

			'''
			config.reporter.create_component(config, component_type=self.component_type, modifiers=self.modifiers,
			                                 creator_type=self._creator_name, silent=silent)
			cls = self._modify_component(self.component_entry,
			                             [self.project.find_artifact('modifier', mod) for mod in self.modifiers])

			if isinstance(cls, type) and issubclass(cls, AbstractConfigurable):
				obj = cls.init_from_config(config, args, kwargs, silent=silent)
			else:
				settings = config.settings
				old_silent = settings.get('silent', None)
				settings['silent'] = silent
				obj = cls(config, *args, **kwargs)
				if old_silent is not None:
					settings['silent'] = old_silent

			if isinstance(obj, AbstractCertifiable):
				obj = obj.__certify__(config)

			config._trace = None
			return obj


		def _create_container(self, config: 'ConfigNode', silent: Optional[bool] = None) -> Any:
			'''
			Creates the container, such as a :class:`dict` or :class:`list` based on the config tree structure.

			Depending on what type of node is used, the container will either be a :class:`dict` or :class:`list`.

			All the children of the config node are created using :meth:`ConfigNode.pull`. For this purpose,
			if the current creation is the result of a search, the children are pulled using
			a :meth:`AbstractSearch.sub_search`.

			Args:
				config: node for which the product is being created
				silent: if True, suppresses the reporter from printing messages

			Returns:
				Container with the processed children

			Raises:
				:exc:`NotImplementedError`: if the config node is not recognized


			'''
			config.reporter.create_container(config, silent=silent)
			trace = config.trace

			context = nullcontext() if trace is None else trace.sub_search()

			with context:
				if isinstance(config, config.SparseNode):
					product = {}
					for key, child in config.named_children():
						product[key] = config.pull(key, silent=silent)

				elif isinstance(config, config.DenseNode):
					product = []
					for key, child in config.named_children():
						product.append(config.pull(key, silent=silent))
				else:
					raise NotImplementedError(f'Unknown container type: {type(config)}')

			config._trace = None
			return product


		def _create_primitive(self, config: 'ConfigNode', silent: Optional[bool] = None) -> Any:
			'''
			Creates the primitive, such as a :class:`str` or :class:`int` based on the payload of the config node.

			Args:
				config: node for which the product is being created
				silent: if True, suppresses the reporter from printing messages

			Returns:
				Primitive value contained in the config node

			'''
			payload = config.payload
			config.reporter.create_primitive(config, value=payload, silent=silent)
			config._trace = None
			return payload


		def _setup_context(self, config: 'ConfigNode') -> None:
			'''
			This prepares the creator for creating the node to avoid getting stuck in
			an infinite loop of creating products if there are some cycles in the config tree.

			Args:
				config: node for which the product is being created

			Returns:
				None

			'''
			table = ConfigNode.DefaultCreator._creation_context
			if table is None:
				ConfigNode.DefaultCreator._creation_context = {config: True}
			else:
				if config in table:
					raise config.CycleError(config)
				table[config] = False


		def _end_context(self, config: 'ConfigNode', product: Any) -> None:
			'''
			This cleans up the creator after creating the product.

			Args:
				config: node for which the product is being created
				product: that was created

			Returns:
				None

			'''
			reset = ConfigNode.DefaultCreator._creation_context.get(config, None)
			if reset:
				ConfigNode.DefaultCreator._creation_context = None
			elif reset is not None:
				del ConfigNode.DefaultCreator._creation_context[config]


		def create_product(self, config: 'ConfigNode', args: Optional[Tuple] = None,
		           kwargs: Optional[Dict[str,Any]] = None, *, silent: Optional[bool] = None) -> Any:
			'''
			Top level method for creating the product from the config node which is called by the config node.

			Args:
				config: node for which the product is being created
				args: manual positional arguments to be passed to the component constructor
				kwargs: manual keyword arguments to be passed to the component constructor
				silent: if True, suppresses the reporter from printing messages

			Returns:
				Product created from the config node

			'''
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
		'''
		Creates a search object that can be used to resolve the given queries to find the corresponding node.

		Note that this method is usually not called directly, but rather through the top level methods such as
		:meth:`ConfigNode.pull` or :meth:`ConfigNode.peek`.

		Args:
			*queries: list of queries to be resolved
			default: if all the queries fail, this value will be returned
			**kwargs: additional keyword arguments to be passed to the search object constructor

		Returns:
			Search object that can be used to traverse the config tree

		'''
		return self.Search(origin=self, queries=queries, default=default, **kwargs)


	def peeks(self, *queries: str, default: Optional[Any] = AbstractConfig._empty_default,
	          silent: Optional[bool] = None) -> 'ConfigNode':
		'''
		Searches in the config based on the given queries and returns the resulting node.

		If multiple queries are given, the first one that resolves to a node will be returned.
		If all the queries fail, the default value will be returned (if given),
		otherwise a :exc:`Search.SearchFailed` will be raised.

		Args:
			*queries: list of queries to be resolved
			default: value to be returned if all the queries fail
			silent: if True, suppresses the reporter from printing messages

		Returns:
			Config node that corresponds to the first query that resolves to a node

		Raises:
			Search.SearchFailed: if all the queries fail and no default value is given

		'''
		return self.search(*queries, default=default).find_node(silent=silent)


	def pulls(self, *queries: str, default: Optional[Any] = AbstractConfig._empty_default,
	          silent: Optional[bool] = None, **kwargs) -> Any:
		'''
		Searches in the config based on the given queries and returns the product of the resulting node.
		The product is the value that node contains, which can be a primitive, a container, or a component.
		If the product is a container or component, it will be created if it has not been created yet.

		If multiple queries are given, the first one that resolves to a node is used
		If all the queries fail, the default value will be returned (if given),
		otherwise a :exc:`Search.SearchFailed` will be raised.

		Args:
			*queries: list of queries to be resolved
			default: value to be returned if all the queries fail
			silent: if True, suppresses the reporter from printing messages

		Returns:
			Product of the config node corresponding to the first query that doesn't fail

		Raises:
			Search.SearchFailed: if all the queries fail and no default value is given

		'''
		return self.search(*queries, default=default, **kwargs).find_product(silent=silent)


	def push(self, addr: str, value: Any, overwrite: bool = True, silent: Optional[bool] = None) -> bool:
		'''
		Inserts a new node into the config tree.

		Args:
			addr: of the new node (i.e. the key or index)
			value: of the new node
			overwrite: if True, overwrites the existing node if there is one
			silent: if True, suppresses the reporter from printing messages

		Returns:
			True if the node was inserted, False if it was not inserted

		Raises:
			ReadonlyError: if the config is readonly

		'''
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
		'''Number of children of the node.'''
		return len(list(self._child_keys()))


	def _child_keys(self) -> Iterator[str]:
		'''Returns the keys of the children of the node.'''
		for key, child in self.named_children():
			if child is not self.empty_value and not child.has_payload or child.payload not in {'__x__', '_x_'}:
				yield key


	def peek_children(self, *, silent: Optional[bool] = None) -> Iterator['ConfigNode']:
		'''
		Returns an iterator over the child nodes of ``self``.

		The iterator skips invalid children (such as empty values or ``__x__``).

		Args:
			silent: if True, suppresses the reporter from printing messages

		Returns:
			Iterator over the children of ``self``

		'''
		for key, child in self.peek_named_children(silent=silent):
			yield child


	def peek_named_children(self, *, silent: Optional[bool] = None) -> Iterator[Tuple[str, 'ConfigNode']]:
		'''
		Returns an iterator over the child nodes of ``self``, including their keys.

		The iterator skips invalid children (such as empty values or ``__x__``).

		Args:
			silent: if True, suppresses the reporter from printing messages

		Returns:
			Iterator producing tuples in the form of (key, child_node)

		'''
		self.reporter.report_iterator(self, product=False, silent=silent)
		for key in self._child_keys():
			child = self.search(key).find_node(silent=silent)
			yield key, child


	def pull_children(self, *, force_create: Optional[bool] = False, silent: Optional[bool] = None) -> Iterator[Any]:
		'''
		Returns an iterator over the products of the child nodes of ``self``.

		The iterator skips invalid children (such as empty values or ``__x__``).

		Args:
			force_create: if True, will always create new products instead of reuse existing ones
			silent: if True, suppresses the reporter from printing messages

		Returns:
			Iterator over the products of the children of the node

		'''
		for key, product in self.pull_named_children(force_create=force_create, silent=silent):
			yield product


	def pull_named_children(self, *, force_create: Optional[bool] = False, silent: Optional[bool] = None) \
			-> Iterator[Tuple[str, Any]]:
		'''
		Returns an iterator over the products of the child nodes of ``self``, including their keys.

		The iterator skips invalid children (such as empty values or ``__x__``).

		Args:
			force_create: if True, will always create new products instead of reuse existing ones
			silent: if True, suppresses the reporter from printing messages

		Returns:
			Iterator over the products of the children of the node

		'''
		for key, child in self.peek_named_children(silent=silent):
			product = child.create() if force_create else child.process()
			yield key, product
		

	def peek_process(self, query, default: Optional[Any] = AbstractConfig._empty_default,
	                 *args: Any, **kwargs: Any) -> Any:
		'''
		Convenience method which composes :meth:`peek` and :meth:`process`, to only process a node if it exists,
		and otherwise return the given default value.

		Args:
			query: of the node to be processed
			default: value to be returned if the node doesn't exist
			*args: positional arguments to be passed to :meth:`process` (e.g. to the constructor of the component)
			**kwargs: keyword arguments to be passed to :meth:`process` (e.g. to the constructor of the component)

		Returns:
			Product of the node corresponding to the query, or the default value if the node doesn't exist

		Raises:
			Search.SearchFailed: if the query fails and no default value is given

		'''
		try:
			node = self.peek(query)
		except self.Search.SearchFailed:
			if default is self._empty_default:
				raise
			return default
		else:
			out = node.process(*args, **kwargs)
			return out


	def peeks_process(self, *queries, default: Optional[Any] = AbstractConfig._empty_default,
	                  **kwargs: Any) -> Any:
		'''
		Convenience method which composes :meth:`peeks` and :meth:`process`, to only process a node if it exists,
		and otherwise return the given default value.

		Note that since this method allows for multiple queries, no positional arguments can be passed to the
		:meth:`process` method, and neither can the keyword argument ``default``.

		Args:
			*queries: of the nodes to be processed
			default: value to be returned if the node doesn't exist
			**kwargs: keyword arguments to be passed to :meth:`process` (e.g. to the constructor of the component)

		Returns:
			Product of the node corresponding to the query, or the default value if the node doesn't exist

		Raises:
			Search.SearchFailed: if the query fails and no default value is given

		'''
		try:
			node = self.peeks(*queries)
		except self.Search.SearchFailed:
			if default is self._empty_default:
				raise
			return default
		else:
			out = node.process(**kwargs)
			return out


	def peek_create(self, query, default: Optional[Any] = AbstractConfig._empty_default,
	                *args: Any, **kwargs: Any) -> Any:
		'''
		Convenience method which composes :meth:`peek` and :meth:`create`,
		to only create the product if the node exists, and otherwise return the given default value.

		Args:
			query: of the node for which the product should be created
			default: value to be returned if the node doesn't exist
			*args: positional arguments to be passed to :meth:`create` (e.g. to the constructor of the component)
			**kwargs: keyword arguments to be passed to :meth:`create` (e.g. to the constructor of the component)

		Returns:
			Product of the node corresponding to the query, or the default value if the node doesn't exist

		Raises:
			Search.SearchFailed: if the query fails and no default value is given

		'''
		try:
			node = self.peek(query)
		except self.Search.SearchFailed:
			if default is self._empty_default:
				raise
			return default
		else:
			out = node.create(*args, **kwargs)
			return out


	def peeks_create(self, *queries, default: Optional[Any] = AbstractConfig._empty_default,
	                  **kwargs: Any) -> Any:
		'''
		Convenience method which composes :meth:`peeks` and :meth:`create`, to only create the product if the node
		exists, and otherwise return the given default value.

		Note that since this method allows for multiple queries, no positional arguments can be passed to the
		:meth:`create` method, and neither can the keyword argument ``default``.

		Args:
			*queries: of the nodes to be processed
			default: value to be returned if the node doesn't exist
			**kwargs: keyword arguments to be passed to :meth:`create` (e.g. to the constructor of the component)

		Returns:
			Product of the node corresponding to the query, or the default value if the node doesn't exist

		Raises:
			Search.SearchFailed: if the query fails and no default value is given

		'''
		try:
			node = self.peeks(*queries)
		except self.Search.SearchFailed:
			if default is self._empty_default:
				raise
			return default
		else:
			out = node.process(**kwargs)
			return out


	def __init__(self, *args, reporter: Optional[Reporter] = None, settings: Optional[Settings] = None,
	             project: Optional[AbstractProject] = None, manager: Optional[AbstractConfigManager] = None,
	             **kwargs):
		'''
		Initializes a new config node. Most of the arguments passed to this constructor should usually be ``None``
		so that this node refers to the values of the root config node.

		Args:
			*args: unused positional arguments passed to the constructor of the super class
			reporter: used for reporting when data is accessed, defers to the root node
			settings: used to determine the behavior of searching and producing products, defers to the root node
			project: associated with this config, defers to the root node
			manager: associated with this config, defers to the root node
			**kwargs: unused keyword arguments passed to the constructor of the super class
		'''
		super().__init__(*args, **kwargs)
		self._project = project
		self._trace = None
		self._product = None
		self._cro = None
		self._bases = None
		self._manager = manager
		self._reporter = reporter
		self._settings = settings
		if self.reporter is None:
			self.reporter = self.Reporter()
		if self.settings is None:
			self.settings = self.Settings()
	
	
	def __deepcopy__(self, memodict={}):
		'''Deep copy of the node (and all subnodes). Does not include the parent node.'''
		new = self.from_raw(self.to_python())
		new._settings = deepcopy(self._settings)
		new._manager = self._manager
		new._project = self._project
		new._trace = self._trace
		new._product = self._product
		new._cro = self._cro
		new._bases = self._bases
		return new
	
	
	def __eq__(self, other):
		'''Compares this config node to another object.'''
		return type(self) == type(other) \
		       and id(self.root) == id(other.root) \
		       and self.my_address() == other.my_address()


	def __hash__(self):
		'''Returns a hash value for this config node.'''
		return hash(self.my_address())


	def export(self, name: Union[str, Path], *, root: Optional[Union[str, Path]] = None,
			   fmt: Optional[str] = None) -> Optional[Path]:
		'''
		Exports the given config to the given path (in yaml format).

		Args:
			config: object to export
			name: of file name or path to export to (without extension)
			root: directory to export to (if not provided, the current working directory is used)
			fmt: format to export to (if not provided, the extension of the file name is used, and defaults to yaml)

		Returns:
			The path to which the config was exported

		'''
		return self.manager.export(self, name, root=root, fmt=fmt)


	@property
	def project(self):
		'''Returns the project associated with this config tree.'''
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
	def cro(self) -> Tuple[str, ...]:
		'''
		Returns the list of all config files that were composed to produce this config tree.
		Analogous to the method resolution order (``mro``) for classes.
		'''
		if self._cro is None:
			if self.parent is None:
				return ()
			return self.parent.cro
		return self._cro


	@property
	def bases(self) -> Tuple[str, ...]:
		'''
		Returns the list of config files that were explicitly mentioned to produce this config tree.
		Analogous to ``__bases__`` for classes.
		'''
		if self._bases is None:
			if self.parent is None:
				return ()
			return self.parent.bases
		return self._bases


	@property
	def manager(self):
		'''Returns the manager associated with this config tree.'''
		if self._manager is None:
			parent = self.parent
			if parent is not None:
				return parent.manager
		return self._manager
	@manager.setter
	def manager(self, manager: AbstractConfigManager):
		parent = self.parent
		if parent is None:
			self._manager = manager
		else:
			parent.manager = manager


	@property
	def trace(self) -> Optional[Search]:
		'''
		Returns the current search trace associated this config node
		(generally only used by creators and reporters).
		'''
		return self._trace


	@property
	def reporter(self) -> Reporter:
		'''Returns the reporter associated with this config tree.'''
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
	def settings(self) -> Settings:
		'''Returns the (global) settings associated with this config tree.'''
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
		'''Returns whether this config node is in silent mode.'''
		return self.settings.get('silent', False)
	@silent.setter
	def silent(self, value: bool):
		'''Sets whether this config node is in silent mode.'''
		self.settings['silent'] = value


	class ReadOnlyError(Exception):
		'''Raised when a read-only config node is attempted to be modified.'''
		pass


	class ConfigContext:
		'''
		Context manager for temporarily modifying the (global) settings of a config tree.
		'''
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
		'''Returns a context manager for temporarily modifying the (global) settings of this config tree.'''
		return self.ConfigContext(self, settings)
		

	def _create(self, component_args: Optional[Tuple] = None, component_kwargs: Optional[Dict[str,Any]] = None,
	            silent: Optional[bool] = None, creator: Optional[str] = unspecified_argument, **kwargs: Any) -> Any:
		'''
		Creates the product of this config node (which may be a primitive, a container such as a list or dict,
		or a component).

		Args:
			component_args: positional arguments to pass to the product constructor
			component_kwargs: keyword arguments to pass to the product constructor
			silent: if True, suppresses the reporter from printing any messages
			creator: the creator to use to create the product (if unspecified, the "creator" setting is checked,
			or the default creator is used)
			**kwargs: additional keyword arguments to pass to the creator for it's own initialization

		Returns:
			The newly created product of this config node.

		'''
		if creator is unspecified_argument:
			creator = self.settings.get('creator')
		creator = self.DefaultCreator if creator is None else self.project.find_artifact('creator', creator).cls
		out = creator(self, silent=silent, project=self.project,  **kwargs)\
			.create_product(self, args=component_args, kwargs=component_kwargs, silent=silent)
		return out


	def _process(self, component_args: Optional[Tuple] = None, component_kwargs: Optional[Dict[str, Any]] = None,
	             silent: Optional[bool] = None, **kwargs: Any) -> Any:
		'''
		Returns the product of this config node. If the product of the node has already been created, that is returned,
		otherwise the product is created using :meth:`_create`.

		Args:
			component_args: positional arguments to pass to the product constructor (if the product is created)
			component_kwargs: keyword arguments to pass to the product constructor (if the product is created)
			silent: if True, suppresses the reporter from printing any messages (if the product is created)
			**kwargs: additional keyword arguments to pass to the creator for it's own initialization
			(if the product is created)

		Returns:
			The product of this config node.

		'''
		settings = self.settings
		force_create = settings.get('force_create', False)
		allow_create = settings.get('allow_create', True)
		assert not (force_create and not allow_create), f'Cannot force create without allowing create: {self}'
		if (allow_create and self._product is None) or force_create:
			self._product = self._create(component_args, component_kwargs, silent=silent, **kwargs)
		else:
			self.reporter.reuse_product(self, self._product, silent=silent)
		return self._product


	def create(self, *args: Any, **kwargs: Any) -> Any:
		'''
		Creates a new value based on the contents of self.

		Args:
			*args: Manual arguments to pass to the value constructor.
			**kwargs: Manual keyword arguments to pass to the value constructor.

		Returns:
			The newly created value.

		'''
		return self._create(args, kwargs, silent=self.settings.get('silent', None))


	def create_silent(self, *args: Any, **kwargs: Any) -> Any:
		'''Convenience method for creating a value in silent mode.'''
		return self._create(args, kwargs, silent=True)


	def process(self, *args: Any, **kwargs: Any) -> Any:
		'''
		Processes the config object using the contents of self.

		If a value for this config object has already been created, it is returned instead of creating a new one.

		Args:
			*args: Manual arguments to pass to the value constructor. (ignored if a value has already been created)
			**kwargs: Manual keyword arguments to pass to the value constructor.
			(ignored if a value has already been created)

		Returns:
			The processed value.

		'''
		return self._process(args, kwargs, silent=self.settings.get('silent', None))


	def process_silent(self, *args: Any, **kwargs: Any) -> Any:
		'''Convenience method for processing a value in silent mode.'''
		return self._process(args, kwargs, silent=True)


	@property
	def product_exists(self) -> bool:
		'''Returns True if the product of this config node has already been created.'''
		return self._product is not None


	def clear_product(self, recursive: bool = True) -> None:
		'''
		Removes the product of this config node (if it exists), and optionally removes the products of all child nodes.

		Args:
			recursive: if True, the products of all child nodes are also removed

		'''
		self._product = None
		if recursive:
			for _, child in self.named_children():
				child.clear_product(recursive=recursive)

	def to_yaml(self, stream=None, default_flow_style=None, sort_keys=True, **kwargs: Any) -> None:
		'''
		Dumps the contents of this config node in YAML format to the specified stream.

		Args:
			stream: destination stream
			default_flow_style: YAML formatting option (see PyYAML documentation)
			sort_keys: YAML formatting option (if True, keys are sorted alphabetically)
			**kwargs: additional keyword arguments to pass to PyYAML's dump function

		Returns:
			None

		'''
		return yaml.dump(self.to_python(), stream, default_flow_style=default_flow_style, sort_keys=sort_keys,
		                 **kwargs)


	def __str__(self):
		'''Returns a string representation of the contents of this config node.'''
		return f'<{self.payload!r}>' if self.is_leaf else self.to_yaml()


	def __repr__(self):
		'''Returns a string representation of this config node.'''
		return f'<{self.__class__.__name__} {len(self)} children>'


	def update(self, update: 'ConfigNode', *, clear_product: bool = True) -> 'ConfigNode':
		'''
		Updates the contents of this config node with the contents of another config node.

		Args:
			update: the config node to update from
			clear_product: if True, all references to the products of ``self`` and ``update`` are removed

		Returns:
			The updated config node, ``self``

		'''
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
		'''
		Recursively validates the contents of this config node.

		Including removing any children with the value ``_x_`` (marked for removal).
		'''
		bad = []
		for key, child in self.named_children():
			if child.has_payload and child.payload == self._delete_value:
				bad.append(key)
			else:
				child.validate()
		for key in bad:
			self.remove(key)

	def silence(self, silent: bool = True) -> ContextManager:
		'''Convenience method for temporarily setting the silent flag of this config node.'''
		return self.context(silent=silent)

	def print(self, *terms: Any, force: bool = False, sep: str = ' ', end: str = '\n', **kwargs):
		'''Convenience method for printing iff (`force` or not self.silent)'''
		if force or not self.silent:
			print(*terms, sep=sep, end=end, **kwargs)



class ConfigSparseNode(AutoTreeSparseNode, ConfigNode):
	'''A config node that treats its children as being in a dict.'''
	_python_structure = dict

	def _get(self, addr: str):
		try:
			return super()._get(addr)
		except self._MissingKey:
			try:
				return super()._get(addr.replace('-', '_'))
			except self._MissingKey:
				pass
			raise

	def _set(self, addr: str, node):
		return super()._set(addr, node)

	def _remove(self, addr: str):
		if addr in self._children:
			del self._children[addr]

	def _has(self, addr: str):
		return addr in self._children or addr.replace('-', '_') in self._children





class ConfigDenseNode(AutoTreeDenseNode, ConfigNode):
	'''A config node that treats its children as being in a list.'''
	_python_structure = list



ConfigNode.DefaultNode = ConfigSparseNode
ConfigNode.SparseNode = ConfigSparseNode
ConfigNode.DenseNode = ConfigDenseNode







