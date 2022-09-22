from typing import List, Dict, Tuple, Optional, Union, Any, Hashable, Sequence, Callable, Generator, Type, Iterable, \
	Iterator, NamedTuple
import inspect
from omnibelt import get_printer, unspecified_argument, extract_function_signature

from ..abstract import AbstractCreator, AbstractConfig, AbstractProject, AbstractConfigurable

prt = get_printer(__name__)



class DefaultCreator(AbstractCreator):
	_config_component_key = '_type'
	_config_modifier_key = '_mod'
	_config_creator_key = '_creator'

	@classmethod
	def replace(cls, creator: 'DefaultCreator', component_type=None, modifiers=None,
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

	def validate(self, config) -> 'DefaultCreator':
		if self.component_entry is None:
			self.component_entry = self.project.find_artifact('component', self.component_type)
		creator = config.pull(self._config_creator_key, self.component_entry.creator, silent=True)
		if creator is not None:
			entry = self.project.find_artifact('creator', creator)
			if type(self) != entry.cls:
				return entry.cls.replace(self, config).validate(config)
		return self

	def _create_component(self, config, args=None, kwargs=None, *, silent=None) -> None:
		pass

	def create(self, config, args=None, kwargs=None, *, silent=None) -> Any:
		if args is None:
			args = ()
		if kwargs is None:
			kwargs = {}

		self = self.validate(config)

		if self.component_type is None:
			raise NotImplementedError

		if self.component_entry is None:
			self.component_entry = self.project.find_artifact('component', self.component_type)
		cls = self.component_entry.cls
		assert isinstance(cls, type), f'This creator can only be used for components that are classes: {cls!r}'

		mods = [self.project.find_artifact('modifier', mod).cls for mod in self.modifiers]
		if len(mods):
			bases = (*reversed(mods), cls)
			cls = type('_'.join(base.__name__ for base in bases), bases, {})

		if issubclass(cls, AbstractConfigurable):
			return cls.init_from_config(config, args, kwargs, silent=silent)
		fixed_args, fixed_kwargs = self._fix_args_and_kwargs(cls.__init__, args, kwargs, silent=silent)
		return cls(*fixed_args, **fixed_kwargs)

	def _fix_args_and_kwargs(self, fn, args, kwargs, *, silent=None):
		def default_fn(key, default=inspect.Parameter.empty):
			if default is inspect.Parameter.empty:
				default = unspecified_argument
			return self.pull(key, default, silent=silent)

		return extract_function_signature(fn, args, kwargs, default_fn=default_fn)
		if len(args) == 1 and isinstance(args[0], dict):
			kwargs = args[0]
			args = ()
		return args, kwargs
