from typing import List, Dict, Tuple, Optional, Union, Any, Hashable, Sequence, Callable, Generator, Type, Iterable, \
	Iterator, NewType
from inspect import Parameter
from omnibelt import extract_function_signature, duplicate_class
from .top import register_script, register_component, register_modifier, register_creator
from .config import Config
# from .util import autofill_args

Product = NewType('Product', Any)
RawCallableItem = Callable[[...], Product]
ConfigCallableItem = Callable[[Config], Product]
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

	def register(self, name: str, item: ConfigCallableItem, **kwargs) -> None:
		raise NotImplementedError



class Script(_Registration_Decorator):
	'''Decorator to register a script'''

	def __init__(self, name: Optional[str] = None, description: Optional[str] = None):
		'''
		:param name: name of item to be registered (defaults to its __name__)
		:param description: a short description of what the script does
		'''
		super().__init__(name=name, description=description)

	def register(self, name: str, item: ConfigCallableItem, **kwargs) -> None:
		register_script(name, item, **self.kwargs)



class Creator(_Registration_Decorator):
	def __init__(self, name: Optional[str] = None):
		'''
		:param name: name of item to be registered (defaults to its __name__)
		'''
		super().__init__(name=name)

	def register(self, name: str, item: ConfigCallableItem, **kwargs) -> None:
		register_creator(name, item, **kwargs)



class Component(_Registration_Decorator):
	'''Decorator to register a component (expected to be a type)'''

	def __init__(self, name: Optional[str] = None, creator: Optional[Union[str, Creator]] = None):
		'''
		:param name: name of item to be registered (defaults to its __name__)
		'''
		super().__init__(name=name, creator=creator)

	def register(self, name: str, item: ConfigCallableItem, **kwargs) -> None:
		register_component(name, item, **kwargs)



class Modifier(_Registration_Decorator):
	'''Decorator to register a modifier (expected be a type)

	Modifiers are used as dynamic mixins for components. They are specified using the `_mod` key in the config.
	'''
	def __init__(self, name: Optional[str] = None):
		'''
		:param name: name of item to be registered (defaults to its __name__)
		'''
		super().__init__(name=name)

	def register(self, name: str, item: ConfigCallableItem, **kwargs) -> None:
		register_modifier(name, item, **kwargs)




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

	def autofill(self, config: Config) -> Tuple[List[Any], Dict[str, Any]]:
		def default_fn(key, default):
			if default is Parameter.empty:
				default = config.empty_default
			aliases = self.aliases.get(key, ())
			if isinstance(aliases, str):
				aliases = (aliases,)
			return config.pulls(key, *aliases, default=default)
		return extract_function_signature(self.item, default_fn=default_fn)

	def top(self, config: Config) -> Product:
		args, kwargs = self.autofill(config)
		return self.item(*args, **kwargs)

	def register(self, name: str, item: RawCallableItem, **kwargs):
		super().register(name, self.top, **kwargs)


class AutoScript(_AutofillMixin, Script):
	'''Convienence decorator to register scripts where the arguments are automatically extracted from the config'''
	def __init__(self, name: Optional[str] = None, description: Optional[str] = None,
	             aliases: Optional[Dict[str, Union[str, Sequence[str]]]] = None, **kwargs):
		'''
		:param name: name of item to be registered (defaults to its __name__)
		:param description: description: a short description of what the script does
		:param aliases: alternative names for arguments (can have multiple aliases per argument)
		'''
		super().__init__(name, description=description, aliases=aliases, **kwargs)




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

		def _autofill_init(self, config: Config, kwargs: Dict[str, Any]) -> Tuple[List[Any], Dict[str, Any]]:
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

		def __init__(self, config: Config, **kwargs):
			args, kwargs = self._autofill_init(config, **kwargs)
			super().__init__(*args, **kwargs)

	def autofill(self, config: Config, args: Optional[Tuple[...]] = None, kwargs: Optional[Dict[str, Any]] = None) \
			-> Tuple[List[Any], Dict[str, Any]]:
		def default_fn(key, default):
			if default is Parameter.empty:
				default = config.empty_default
			aliases = self.aliases.get(key, ())
			if isinstance(aliases, str):
				aliases = (aliases,)
			return config.pulls(key, *aliases, default=default)

		return extract_function_signature(self.fn, args=args, kwargs=kwargs, default_fn=default_fn)

	def top(self, config: Config, *args, **kwargs) -> Product:
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



