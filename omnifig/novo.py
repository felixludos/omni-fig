from typing import List, Dict, Tuple, Optional, Union, Any, Hashable, Sequence, Callable, Generator, Type, Iterable, Iterator
from collections import OrderedDict
from omnibelt import unspecified_argument, Singleton, extract_function_signature
from inspect import Parameter
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


class Configurable:
	_my_config = None

	@property
	def my_config(self):
		return self._my_config

	@classmethod
	def init_from_spec(cls, spec, args: Tuple, kwargs: Dict[str, Any], silent: Optional[bool] = None):
		# obj = cls.__new__(*args, **kwargs)
		# obj._my_config = spec
		# obj.__init__(*args, **kwargs)
		# return obj
		# return cls(*args, **kwargs)
		cls._my_config = spec
		with spec.silence(silent):
			obj = cls(*args, **kwargs)
		del cls._my_config
		obj._my_config = spec
		return obj


primitive = (int, float, str, bool, type(None))
Primitive = Union[primitive]

import io
import yaml
from pathlib import Path
from omnibelt import Path_Registry

class ConfigManager:

	_config_path_delimiter = '/'

	def __init__(self, project):
		self.registry = Path_Registry()
		self.project = project

	def register(self, name: str, path: Path, **kwargs):
		self.registry.new(name, path, **kwargs)

	def auto_register_directory(self, root: Path, exts=('yaml', 'yml')):
		for ext in exts:
			for path in root.glob(f'**/*.{ext}'):
				terms = path.relative_to(root).parts[:-1]
				name = path.stem
				ident = self._config_path_delimiter.join(terms + (name,))
				self.register(ident, path)


	def _parse_raw_arg(self, arg):
		return yaml.safe_load(io.StringIO(arg))
		# try:
		# 	if isinstance(mode, str):
		# 		if mode == 'yaml':
		# 			return yaml.safe_load(io.StringIO(arg))
		# 		elif mode == 'python':
		# 			return eval(arg, {}, {})
		# 		else:
		# 			pass
		# 	else:
		# 		return mode(arg)
		# except:
		# 	pass
		# return arg

	def parse_argv(self, argv):




		pass


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


		def component_creation(self, node, key, cmpn, mods, silent=None):
			if silent is None:
				silent = self.silent
			mod_info = f' (mods=[{", ".join(mods)}])' if len(mods) > 1 else f' (mod={mods[0]})'
			key = '' if key is None else key + ' '
			indent = self._node_depth(node) * self.indent
			return self.log(f'{self.flair}{indent}CREATING {key}type={cmpn}{mod_info}', silent=silent)


		def get_key(self, search: 'ConfigNode.Search') -> str:

			queries = search.query_chain

			if len(search.parent_search):
				queries = queries.copy()
				queries[0] = f'({queries[0]})' #if getattr(search.parent_search[0]

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

			elif search.action == 'no-payload' or search.action == 'iterator': # list or dict
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
			return self.log(line)


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
			
			
	class Search(SimpleConfigNode.Search):
		def __init__(self, origin, queries, default=unspecified_argument,
		             ask_parent=True, lazy_iterator=None, parent_search=(), **kwargs):
			super().__init__(origin=origin, queries=queries, default=default, **kwargs)
			# self.init_origin = origin
			self.query_chain = []
			self._ask_parent = ask_parent
			self.lazy_iterator = lazy_iterator
			self.parent_search = parent_search

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
				payload = node.payload
				self.action = 'primitive'
				return payload
			
			# complex object - either component or list/dict
			try:
				cmpn, mods = node._extract_component_info()
			except node.NoComponentFound:
				# check for iterator
				if self.lazy_iterator is not None:
					self.action = 'iterator'
					node.reporter.search_report(self)
					return self.lazy_iterator(node)

				self.action = 'no-payload'

				# list or dict
				if isinstance(node, node.SparseNode):
					self.product_type = 'dict'
					product = OrderedDict()
					for key, child in node.children():
						product[key] = self.sub_search(node, key)

				elif isinstance(node, node.DenseNode):
					self.product_type = 'list'
					product = []
					for key, child in node.children():
						product.append(self.sub_search(node, key))

				else:
					raise TypeError(f'Unknown node type: {node!r}')

				return product
			else:
				# create component
				return node._create_component(cmpn, mods, record_key=node.reporter.get_key(self))


		def silence(self, silent=True):
			return self.reporter.silence(silent)


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

	def __init__(self, *args, project=None, reporter=None, **kwargs):
		if reporter is None:
			reporter = self.Reporter()
		super().__init__(*args, **kwargs)
		self.reporter = reporter
		self._project = project

	_component_type_key = '_type'
	_component_mod_key = '_mod'

	class UnknownComponentType(ValueError): pass

	class NoComponentFound(ValueError):pass
	def _extract_component_info(self) -> Tuple[str, Sequence[str]]:
		cmpn = self.pull(self._component_type_key, None, silent=True)
		if cmpn is None:
			raise self.NoComponentFound

		mods = self.pull(self._component_mod_key, None, silent=True)
		if mods is None:
			mods = []
		elif isinstance(mods, dict):
			mods = [mod for mod, _ in sorted(mods.items(), key=lambda x: (x[1], x[0]))]
		elif isinstance(mods, str):
			mods = [mods]
		else:
			raise ValueError(f'Invalid modifier: {mods!r}')
		return cmpn, mods

	def _fix_args_and_kwargs(self, fn, args, kwargs, *, silent=None):
		def default_fn(key, default=Parameter.empty):
			if default is Parameter.empty:
				default = unspecified_argument
			return self.pull(key, default, silent=silent)
		return extract_function_signature(fn, args, kwargs, default_fn=default_fn)
		if len(args) == 1 and isinstance(args[0], dict):
			kwargs = args[0]
			args = ()
		return args, kwargs

	def _create_component(self, component_type: str, mod_types: Sequence[str],
	                      args: Tuple = (), kwargs: Dict[str, Any] = None, *,
	                      record_key: Optional[str] = None, silent: Optional[bool] = None):
		if kwargs is None:
			kwargs = {}

		self.reporter.component_creation(self, record_key, component_type, mod_types, silent=silent)

		project = self.project
		cmpn = project.find_component(component_type)
		mods = [project.find_modifier(mod) for mod in mod_types]

		cls = cmpn
		if len(mods):
			bases = (*reversed(mods), cmpn)
			cls = type('_'.join(base.__name__ for base in bases), bases, {})

		if issubclass(cls, Configurable):
			return cls.init_from_spec(self, args, kwargs, silent=silent)
		fixed_args, fixed_kwargs = self._fix_args_and_kwargs(cls.__init__, args, kwargs, silent=silent)
		return cls(*fixed_args, **fixed_kwargs)

	def create(self, *args, **kwargs):
		return self._create_component(*self._extract_component_info(), args=args, kwargs=kwargs)


	@property
	def project(self):
		if self._project is None:
			if not self.has_parent:
				raise ValueError('No project found')
			return self.parent.project
		return self._project

	@property
	def silent(self):
		return self.reporter.silent
	@silent.setter
	def silent(self, value):
		self.reporter.silent = value

	# @property
	# def readonly(self):
	# 	return self.editor.readonly
	# @readonly.setter
	# def readonly(self, value):
	# 	self.editor.readonly = value


	def set(self, addr: str, value: Any, reporter=None, **kwargs) -> 'ConfigNode':
		# if editor is None:
		# 	editor = self.editor
		if reporter is None:
			reporter = self.reporter
		node, key = self._evaluate_address(addr)
		return super(AddressNode, node).set(key, value, reporter=reporter, **kwargs)



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


from .organization import Project

class NovoProject(Project, name='novo'):
	ConfigManager = ConfigManager

	def __init__(self, profile=None, **kwargs):
		super().__init__(**kwargs)
		self.config_manager = ConfigManager(self)

	pass






