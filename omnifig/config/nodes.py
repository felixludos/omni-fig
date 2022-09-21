from typing import List, Dict, Tuple, Optional, Union, Any, Hashable, Sequence, Callable, Generator, Type, Iterable, \
	Iterator, Self, NamedTuple
from omnibelt import get_printer, unspecified_argument, extract_function_signature, JSONABLE
from inspect import Parameter
from omnibelt.nodes import AutoTreeNode, AutoTreeSparseNode, AutoTreeDenseNode, AutoAddressNode, AddressNode

from ..abstract import AbstractConfig, AbstractProject, AbstractCreator, AbstractConfigurable
from .search import ConfigSearch
from .reporter import ConfigReporter

prt = get_printer(__name__)


class _ConfigNode(AbstractConfig, AutoTreeNode):
	def __init__(self, *args, readonly: bool = False, project: Optional[AbstractProject] = None, **kwargs):
		super().__init__(*args, **kwargs)
		self._project = project
		self._readonly = readonly

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
	def silent(self):
		raise NotImplementedError
	@silent.setter
	def silent(self, value):
		raise NotImplementedError


# class Editable(_ConfigNode):
# 	def __init__(self, *args, **kwargs):
# 		super().__init__(*args, **kwargs)
# 		self._readonly = readonly

	@property
	def readonly(self):
		return self.root._readonly
	@readonly.setter
	def readonly(self, value):
		self.root._readonly = value

	class ReadOnlyError(Exception):
		pass

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



class SimpleConfigNode(_ConfigNode):
	Search = ConfigSearch
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

	def peeks(self, *queries, default: Optional[Any] = unspecified_argument, silent: Optional[bool] = None,
	         **kwargs) -> 'SimpleConfigNode':
		return self.search(*queries, default=default, **kwargs).find_node()

	def pull(self, query: str, default: Optional[Any] = unspecified_argument, *, silent: Optional[bool] = None,
	         **kwargs) -> Any:
		return self.pulls(query, default=default, silent=silent, **kwargs)

	def pulls(self, *queries: str, default: Optional[Any] = unspecified_argument, silent: Optional[bool] = None,
	          **kwargs) -> Any:
		return self.search(*queries, default=default, silent=silent, **kwargs).evaluate()

	def push_pull(self, addr: str, value: Any, overwrite: bool = True, **kwargs) -> Any:
		self.push(addr, value, overwrite=overwrite)
		return self.pull(addr, **kwargs)

	def create(self, config, args=None, kwargs=None) -> Any:
		raise NotImplementedError



class ConfigNode(_ConfigNode):
	Reporter = ConfigReporter

	class DefaultCreator(AbstractCreator):
		_config_component_key = '_type'
		_config_modifier_key = '_mod'
		_config_creator_key = '_creator'

		@classmethod
		def replace(cls, creator: 'ConfigNode.DefaultCreator', component_type=None, modifiers=None,
		            project=unspecified_argument, component_entry=unspecified_argument, search=unspecified_argument,
		            **kwargs):
			if component_type is None:
				component_type = creator.component_type
			if modifiers is None:
				modifiers = creator.modifiers
			if project is unspecified_argument:
				project = creator.project
			if component_entry is unspecified_argument:
				component_entry = creator.component_entry
			if search is unspecified_argument:
				search = creator.search
			return super().replace(creator, component_type=component_type, modifiers=modifiers, search=search,
			                       project=project, component_entry=component_entry, **kwargs)

		def __init__(self, config: AbstractConfig, *, component_type: str = None,
		             modifiers: Optional[Sequence[str]] = None, project: Optional[AbstractProject] = None,
		             component_entry: Optional = None, search: Optional = None, **kwargs):
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
			self.project = project
			self.component_type = component_type
			self.modifiers = modifiers
			self.component_entry = component_entry
			self.search = search

		def validate(self, config) -> Union[Self, 'DefaultCreator']:
			if self.component_entry is None:
				self.component_entry = self.project.find_component(self.component_type)
			creator = config.pull(self._config_creator_key, self.component_entry.creator, silent=True)
			if creator is not None:
				entry = self.project.find_creator(creator)
				if type(self) != entry.cls:
					return entry.cls.replace(self, config).validate(config)
			return self

		def _create_component(self, config, args=(), kwargs=None, *, silent=None) -> None:
			pass

		def create(self, config, args=(), kwargs=None, *, silent=None) -> Any:
			if kwargs is None:
				kwargs = {}

			if self.component_type is None:
				raise NotImplementedError


			if self.component_entry is None:
				self.component_entry = self.project.find_component(self.component_type)
			cls = self.component_entry.cls
			assert isinstance(cls, type), f'This creator can only be used for components that are classes: {cls!r}'

			mods = [self.project.find_modifier(mod).cls for mod in self.modifiers]
			if len(mods):
				bases = (*reversed(mods), cls)
				cls = type('_'.join(base.__name__ for base in bases), bases, {})

			if issubclass(cls, AbstractConfigurable):
				return cls.init_from_config(config, args, kwargs, silent=silent)
			fixed_args, fixed_kwargs = self._fix_args_and_kwargs(cls.__init__, args, kwargs, silent=silent)
			return cls(*fixed_args, **fixed_kwargs)

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

	def __init__(self, *args, reporter: Optional[Reporter] = None, **kwargs):
		if reporter is None:
			reporter = self.Reporter()
		super().__init__(*args, **kwargs)
		self.reporter = reporter
		self._product = None
		self._settings = None
		if self.settings is None:
			self.root.settings = {}

	class DummyNode: # output of peek if default is not unspecified_argument but node does not exist
		raise NotImplementedError

	@property
	def settings(self): # global settings for config object,
		# including: ask_parent, prefer_product, product_only, silent, readonly, etc.
		if self._settings is None:
			return self.root._settings
		return self._settings
	@settings.setter
	def settings(self, value):
		self._settings = value
		
	def using(self, **settings):
		raise NotImplementedError # TODO: context manager to temporarily change settings
		

	def _create(self, component_args=(), component_kwargs=None, **kwargs):
		return self.DefaultCreator(self, **kwargs).validate(self)\
			.create(self, args=component_args, kwargs=component_kwargs)

	def create(self, *args, **kwargs):
		# return self._create_component(*self._extract_component_info(), args=args, kwargs=kwargs)
		return self._create(args, kwargs)
	
	def clear_product(self, recursive=True):
		self._product = None
		if recursive:
			for child in self.children():
				child.clear_product(recursive=recursive)
	
	@property
	def product(self):
		if self._product is None:
			self._product = self.create()
		return self._product

	@property
	def product_exists(self):
		return self._product is not None

	def __repr__(self):
		return f'<{self.__class__.__name__} {len(self)} children>'

	def update(self, update: 'ConfigNode'):
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

	@property
	def silent(self):
		return self.reporter.silent
	@silent.setter
	def silent(self, value):
		self.reporter.silent = value

	def set(self, addr: str, value: Any, reporter=None, **kwargs) -> 'ConfigNode':
		# if editor is None:
		# 	editor = self.editor
		if reporter is None:
			reporter = self.reporter
		node, key = self._evaluate_address(addr, auto_create=True)
		return super(AddressNode, node).set(key, value, reporter=reporter, **kwargs)



class ConfigSparseNode(AutoTreeSparseNode, ConfigNode): pass


class ConfigDenseNode(AutoTreeDenseNode, ConfigNode): pass


ConfigNode.DefaultNode = ConfigSparseNode
ConfigNode.SparseNode = ConfigSparseNode
ConfigNode.DenseNode = ConfigDenseNode







