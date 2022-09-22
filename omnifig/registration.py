from typing import List, Dict, Tuple, Optional, Union, Any, Hashable, Sequence, Callable, Generator, Type, Iterable, \
	Iterator, NewType
from inspect import Parameter
from omnibelt import extract_function_signature, get_printer
# from .top import register_script, register_component, register_modifier, register_creator
# from .config import Config
# from .novo_root import get_current_project, ProjectBase, GeneralProject, Profile
# from .util import autofill_args

from .abstract import AbstractScript, AbstractCreator, AbstractComponent, AbstractModifier, \
	AbstractConfig, AbstractProject
from .organization import GeneralProject, Profile
from .top import get_current_project, get_profile

prt = get_printer(__name__)

Product = Any
RawCallableItem = Callable[[Any], Product]
ConfigCallableItem = Callable[[AbstractConfig], Product]
ModifierCallableItem = Callable[[ConfigCallableItem], ConfigCallableItem]


class _Registration_Decorator:
	'''Base class for all registration decorators'''
	def __init__(self, name: Optional[str] = None, **kwargs):
		'''
		:param name: name of item to be registered (defaults to its __name__)
		:param kwargs: additional keyword arguments to pass to :func:`register_script()`
		'''
		self.name = name
		self.kwargs = kwargs
		self.item = None

	def __call__(self, item: RawCallableItem) -> RawCallableItem:
		if self.name is None:
			self.name = item.__name__
		self.item = item
		self.register(self.name, item, **self.kwargs)
		return item

	@staticmethod
	def register(name: str, item: ConfigCallableItem, **kwargs) -> None:
		raise NotImplementedError


class _Project_Registration_Decorator(_Registration_Decorator):
	'''Registration decorator which registers the item with the current project'''

	@classmethod
	def register(cls, name: str, item: ConfigCallableItem, project: Optional[AbstractProject] = None,
	             **kwargs) -> None:
		if project is None:
			project = get_current_project()
		cls.register_project(project, name, item, **kwargs)

	@staticmethod
	def register_project(self, project: AbstractProject, name: str, item: ConfigCallableItem, **kwargs) -> None:
		raise NotImplementedError



class script(_Project_Registration_Decorator):
	'''Decorator to register a script'''
	def __init__(self, name: Optional[str] = None, description: Optional[str] = None, *,
	             hidden: bool = None) -> None:
		'''
		:param name: name of item to be registered (defaults to its __name__)
		:param description: a short description of what the script does (defaults to first line of its docstring)
		:param hidden: if True, the script will not be listed in the help menu
		'''
		super().__init__(name=name, description=description, hidden=hidden)

	@staticmethod
	def register_project(project: AbstractProject, name: str, item: ConfigCallableItem,
	                     description: Optional[str] = None, hidden: Optional[bool] = None, **kwargs) -> None:
		if description is None and item.__doc__ is not None:
			description = item.__doc__.split('\n')[0]
		if hidden is None:
			hidden = name.startswith('_')
		if not isinstance(project, GeneralProject):
			prt.error(f'Cannot register script {name} for project {project} (not a "general" project)')
		project.register_script(name, item, description=description, hidden=hidden, **kwargs)



# class Script(AbstractScript):
# 	def __init_subclass__(cls, script_name: str = None, description: Optional[str] = None, **kwargs):
# 		super().__init_subclass__(**kwargs)
# 		if script_name is not None:
# 			script(script_name, description=description)(cls)



class creator(_Project_Registration_Decorator):
	def __init__(self, name: Optional[str] = None):
		'''
		:param name: name of item to be registered (defaults to its __name__)
		'''
		super().__init__(name=name)

	@staticmethod
	def register_project(project: AbstractProject, name: str, item: ConfigCallableItem, **kwargs) -> None:
		if not isinstance(project, Profile.Project):
			prt.error(f'Cannot register creator {name} for project {project} (not a "default" project)')
		item._creator_name = name
		project.register_creator(name, item, **kwargs)



# class Creator(AbstractCreator):
# 	_creator_name = None
# 	def __init_subclass__(cls, creator_name: str = None, **kwargs):
# 		super().__init_subclass__(**kwargs)
# 		if creator_name is not None:
# 			creator(creator_name)(cls)



class component(_Project_Registration_Decorator):
	'''Decorator to register a component (expected to be a type)'''
	def __init__(self, name: Optional[str] = None, creator: Optional[Union[str, AbstractCreator]] = None):
		'''
		:param name: name of item to be registered (defaults to its __name__)
		'''
		super().__init__(name=name, creator=creator)

	@staticmethod
	def register_project(project: AbstractProject, name: str, item: ConfigCallableItem,
	                     creator: Optional[Union[str, AbstractCreator]] = None, **kwargs) -> None:
		if not isinstance(project, Profile.Project):
			prt.error(f'Cannot register component {name} for project {project} (not a "default" project)')
		project.register_component(name, item, creator=creator, **kwargs)



# class Component(AbstractComponent):
# 	def __init_subclass__(cls, component_name: str = None, creator: Optional[str] = None, **kwargs):
# 		super().__init_subclass__(**kwargs)
# 		if component_name is not None:
# 			component(component_name, creator=creator)(cls)



class modifier(_Project_Registration_Decorator):
	'''Decorator to register a modifier (expected be a type)

	Modifiers are "runtime mixins" for components. When specifying a component to be modified with the `_mod` key
	in the config, a new type is dynamically created which is a child of all the specified modifiers as well as
	the original component.
	'''
	def __init__(self, name: Optional[str] = None):
		'''
		:param name: name of item to be registered (defaults to its __name__)
		'''
		super().__init__(name=name)

	@staticmethod
	def register_project(project: AbstractProject, name: str, item: ConfigCallableItem, **kwargs) -> None:
		if not isinstance(project, Profile.Project):
			prt.error(f'Cannot register modifier {name} for project {project} (not a "default" project)')
		project.register_modifier(name, item, **kwargs)



# class Modifier(AbstractModifier):
# 	def __init_subclass__(cls, modifier_name: str = None, **kwargs):
# 		super().__init_subclass__(**kwargs)
# 		if modifier_name is not None:
# 			component(modifier_name)(cls)



class _AutofillMixin(_Registration_Decorator):
	'''Mixin for decorators that autofill arguments from config'''

	def __init__(self, name: Optional[str] = None,
	             aliases: Optional[Dict[str,Union[str,Sequence[str]]]] = None, **kwargs):
		'''
		:param name: name of item to be registered (defaults to its __name__)
		:param aliases: alternative names for arguments (can have multiple aliases per argument)
		:param kwargs: additional keyword arguments to pass to :func:`register_script()`
		'''
		if aliases is None:
			aliases = {}
		super().__init__(name=name, **kwargs)
		self.aliases = aliases

	def autofill(self, config: AbstractConfig) -> Tuple[List[Any], Dict[str, Any]]:
		def default_fn(key, default):
			if default is Parameter.empty:
				default = config.empty_default
			aliases = self.aliases.get(key, ())
			if isinstance(aliases, str):
				aliases = (aliases,)
			return config.pulls(key, *aliases, default=default)
		return extract_function_signature(self.item, default_fn=default_fn)

	def top(self, config: AbstractConfig) -> Product:
		args, kwargs = self.autofill(config)
		return self.item(*args, **kwargs)

	def register(self, name: str, item: RawCallableItem, **kwargs):
		super().register(name, self.top, **kwargs)



class autoscript(_AutofillMixin, script):
	'''Convienence decorator to register scripts where the arguments are automatically extracted from the config'''
	def __init__(self, name: Optional[str] = None, description: Optional[str] = None,
	             aliases: Optional[Dict[str, Union[str, Sequence[str]]]] = None, **kwargs):
		'''
		:param name: name of item to be registered (defaults to its __name__)
		:param description: description: a short description of what the script does
		:param aliases: alternative names for arguments (can have multiple aliases per argument)
		'''
		super().__init__(name, description=description, aliases=aliases, **kwargs)



# class AutoScript(AbstractScript):
# 	def __init_subclass__(cls, script_name: str = None, description: Optional[str] = None,
# 	                      aliases: Optional[Dict[str, Union[str, Sequence[str]]]] = None, **kwargs):
# 		super().__init_subclass__(**kwargs)
# 		if script_name is not None:
# 			autoscript(script_name, description=description, aliases=aliases)(cls)



class meta_rule(_Registration_Decorator):
	'''Decorator to register a modifier (expected be a type)

	Modifiers are "runtime mixins" for components. When specifying a component to be modified with the `_mod` key
	in the config, a new type is dynamically created which is a child of all the specified modifiers as well as
	the original component.
	'''
	def __init__(self, name: str, code: str, description: Optional[str] = None,
	             priority: Optional[int] = 0, num_args: Optional[int] = 0, **kwargs):
		'''
		:param name: name of item to be registered (defaults to its __name__)
		'''
		super().__init__(name=name, code=code, description=description, priority=priority, num_args=num_args, **kwargs)

	@staticmethod
	def register(name: str, func: Callable, *, code: str, description: Optional[str] = None,
	                       priority: Optional[int] = 0, num_args: Optional[int] = 0) -> None:
		get_profile().register_meta_rule(name, func, code=code, description=description,
		                                 priority=priority, num_args=num_args)




# class Meta_Rule(AbstractMetaRule):
# 	def __init_subclass__(cls, code=None, name=None, priority=0, num_args=0, description=None, **kwargs):
# 		super().__init_subclass__(**kwargs)
# 		if code is not None and name is None:
# 			prt.warning(f'No name for {Meta_Rule.__name__} {cls.__name__} provided, will default to {cls.__name__!r}')
# 			name = cls.__name__
# 		if code is None and name is not None:
# 			prt.error(f'No code for {Meta_Rule.__name__} {name!r} provided, '
# 			          f'cannot register a {Meta_Rule.__name__} without a code')
# 		if code is not None and name is not None:
# 			get_profile().register_meta_rule(name, cls, code=code, priority=priority, num_args=num_args, description=description)
#
# 	def __call__(self, config: AbstractConfig, meta: AbstractConfig):
# 		pass






# class AutoComponent(_AutofillMixin, Component): # TODO: add note on Configurable type to automatically fill in args
# 	'''
# 	Instead of directly passing the config to an AutoComponent, the necessary args are auto filled and passed in.
# 	This means AutoComponents are somewhat limited in that they cannot modify the config object and they cannot be
# 	modified with AutoModifiers.
#
# 	Note: AutoComponents are usually components that are created with functions (rather than classes) since they can't
# 	be automodified. When registering classes as components, you should probably use `Component` instead, and pull
# 	from the config directly.
# 	'''
# 	def __init__(self, name: Optional[str] = None, aliases: Optional[Dict[str, Union[str, Sequence[str]]]] = None):
# 		'''
# 		:param name: name of item to be registered (defaults to its __name__)
# 		:param aliases: alternative names for arguments (can have multiple aliases per argument)
# 		'''
# 		super().__init__(name=name, aliases=aliases)
#
# 	@property
# 	def top(self) -> ConfigCallableItem:
# 		return type(f'Auto_{self.item.__name__}', (self._Autofill_Component_Mixin, self.item),
# 		            {'_autofill_aliases': self.aliases})
# TODO: instead of AutoComponent chain @Component and @autofill_with_config



class autofill_with_config:  # TODO: generally not recommended for types, use Configurable instead
	'''Decorator that automatically extracts arguments of a function or type with values from the config object'''

	def __init__(self, aliases=None, rename_fmt='Auto_{name}'):
		if aliases is None:
			aliases = {}
		self.aliases = aliases
		self.rename_fmt = rename_fmt
		self.fn = None

	class _Autofill_Init:
		_autofill_aliases = None

		def _autofill_init(self, config: AbstractConfig, kwargs: Dict[str, Any]) -> Tuple[List[Any], Dict[str, Any]]:
			def default_fn(key, default):
				if default is Parameter.empty:
					default = config.empty_default
				if self._autofill_aliases is None:
					aliases = ()
				else:
					aliases = self._autofill_aliases.get(key, ())
					if isinstance(aliases, str):
						aliases = (aliases,)
				return config.pulls(key, *aliases, default=default)

			return extract_function_signature(super().__init__, kwargs=kwargs, default_fn=default_fn)

		def __init__(self, config: AbstractConfig, **kwargs):
			args, kwargs = self._autofill_init(config, **kwargs)
			super().__init__(*args, **kwargs)

	def autofill(self, config: AbstractConfig, args: Optional[Tuple] = None,
	             kwargs: Optional[Dict[str, Any]] = None) -> Tuple[List[Any], Dict[str, Any]]:
		def default_fn(key, default):
			if default is Parameter.empty:
				default = config.empty_default
			aliases = self.aliases.get(key, ())
			if isinstance(aliases, str):
				aliases = (aliases,)
			return config.pulls(key, *aliases, default=default)

		return extract_function_signature(self.fn, args=args, kwargs=kwargs, default_fn=default_fn)

	def top(self, config: AbstractConfig, *args, **kwargs) -> Product:
		fixed_args, fixed_kwargs = self.autofill(config, args=args, kwargs=kwargs)
		return self.fn(*fixed_args, **fixed_kwargs)

	def __call__(self, func: RawCallableItem) -> ConfigCallableItem:
		if isinstance(func, type):
			assert not isinstance(func, self._Autofill_Init), \
				'Cannot apply autofill decorator to a class that already has it'
			return type(self.rename_fmt.format(name=func.__name__), (self._Autofill_Init, func),
			            {'_autofill_aliases': self.aliases})
		self.fn = func
		return self.top






# class Modification: # TODO: old version of modifier
# 	'''
# 	Decorator to register a modifier
#
# 	NOTE: a :class:`Modifier` is usually not a type/class, but rather a function
# 	(except :class:`AutoModifiers`, see below)
#
# 	The modifier signature is expected to be: (component_type) -> component_type
# 	'''
#
#
# class ConfigModifier(Modifier):
# 	pass
#
#
# class AutoModifier(Modifier):
# 	'''
# 	Can be used to automatically register modifiers that combine types
#
# 	To keep component creation as clean as possible, modifier types should allow arguments to their __init__
# 	(other than the Config object) and only call pull on arguments not provided, that way child classes of
# 	the modifier types can specify defaults for the modifications without calling pull() multiple times
# 	on the same arg.
#
# 	Note: in a way, this converts components to modifiers (but think before using). This turns the modified
# 	component into a child class of this modifier and its previous type.
#
# 	In short, Modifiers are used for wrapping of components, AutoModifiers are used for subclassing components
#
# 	:param name: if not provided, will use the __name__ attribute.
# 	:return: decorator to decorate a class
# 	'''
# 	def create_modified_component(self, component):
# 		self.product = component if issubclass(component, self.mod_cls) \
# 			else type('{}_{}'.format(self.mod_cls.__name__, component.__name__), (self.mod_cls, component), {})
# 		return self.product
#
#
# 	def __call__(self, cls):
# 		if self.name is None:
# 			self.name = cls.__name__
# 		self.mod_cls = cls
# 		super().__call__(self.create_modified_component)
# 		return cls
#
#
#
# class Modification(Modifier):
# 	'''
# 	A kind of Modifier that modifies the component after it is created,
# 	and then returns the modified component
#
# 	expects a callable with input (component, config)
#
# 	Modifications should almost always be applied after all other modifiers,
# 	so they should appear at the end of _mod list
#
# 	:param name: name to register
# 	:return: a decorator expecting the modification function
# 	'''
#
# 	def top(self, component):
# 		self.component_fn = component
# 		return self.create_and_modify
#
#
# 	def create_and_modify(self, config):
# 		component = self.component_fn(config)
# 		return self.fn(component, config)
#
#
# 	def __call__(self, fn):
# 		if self.name is None:
# 			self.name = fn.__name__
# 		self.fn = fn
# 		super().__call__(self.top)
# 		return fn



