from typing import List, Dict, Tuple, Optional, Union, Any, Sequence, Callable, Type
from inspect import Parameter
from omnibelt import extract_function_signature

from .abstract import AbstractCreator, AbstractConfig, AbstractProject, AbstractCustomArtifact
from .top import get_current_project



class _Registration_Decorator:
	'''Base class for all registration decorators'''
	def __init__(self, name: Optional[str] = None, **kwargs: Any):
		'''

		Args:
			name: name of item to be registered (defaults to its __name__)
			**kwargs: additional keyword arguments to pass to :func:`register_script()`
		'''
		self.name = name
		self.kwargs = kwargs
		self.item = None


	def __call__(self, item: Callable) -> Callable:
		'''Decorator call that registers the item. Leaves the decorated item unchanged.'''
		if self.name is None:
			self.name = item.__name__
		self.item = item
		self.register(self.name, item, **self.kwargs)
		return item


	@staticmethod
	def register(name: str, item: Callable[[AbstractConfig], Any], **kwargs) -> None:
		'''Must be implemented by subclasses to register the item'''
		raise NotImplementedError



class _Project_Registration_Decorator(_Registration_Decorator):
	'''Registration decorator which registers the item with the current project'''


	@classmethod
	def register(cls, name: str, item: Callable[[AbstractConfig], Any], project: Optional[AbstractProject] = None,
	             **kwargs) -> None:
		'''Registers the item with the current project using :func:`get_current_project()`.'''
		if project is None:
			project = get_current_project()
		cls.register_project(project, name, item, **kwargs)


	@staticmethod
	def register_project(project: AbstractProject, name: str, item: Callable[[AbstractConfig], Any],
	                     **kwargs) -> None:
		'''Must be implemented by subclasses to register the item with the current project'''
		raise NotImplementedError



class script(_Project_Registration_Decorator):
	'''
	Decorator to register a script.

	Scripts are callable objects (usually functions) with only one input argument (the config object) and can be called
	from the command line using the :code:`fig` command.
	'''

	def __init__(self, name: Optional[str] = None, description: Optional[str] = None, *,
	             hidden: bool = None) -> None:
		'''

		Args:
			name: name of item to be registered (defaults to its __name__)
			description: a short description of what the script does (defaults to first line of its docstring)
			hidden: if True, the script will not be listed in the help menu
		'''
		super().__init__(name=name, description=description, hidden=hidden)


	@staticmethod
	def register_project(project: AbstractProject, name: str, item: Callable[[AbstractConfig], Any],
	                     description: Optional[str] = None, hidden: Optional[bool] = None, **kwargs) -> None:
		if description is None and item.__doc__ is not None:
			description = item.__doc__.split('\n')[0]
		if hidden is None:
			hidden = name.startswith('_')
		project.register_artifact('script', name, item, description=description, hidden=hidden, **kwargs)



class creator(_Project_Registration_Decorator):
	'''
	Decorator to register a creator.

	Creators are generally subclasses of :class:`AbstractCreator` and are used to create objects from the config.

	Usually, the default creator is sufficient, but this decorator can be used to register a custom creator.
	'''

	def __init__(self, name: Optional[str] = None, description: Optional[str] = None):
		'''

		Args:
			name: name of item to be registered (defaults to its __name__)
			description: a short description of what the script does (defaults to first line of its docstring)
		'''
		super().__init__(name=name, description=description)


	@staticmethod
	def register_project(project: AbstractProject, name: str, item: Callable[[AbstractConfig], Any],
	                     description: Optional[str] = None, **kwargs) -> None:
		item._creator_name = name
		project.register_artifact('creator', name, item, description=description, **kwargs)



class component(_Project_Registration_Decorator):
	'''
	Decorator to register a component.

	Components are (usually) classes, and can be automatically be instantiated from the config object
	(using the ``_type`` key).

	There are generally two different ways to use components. Both use a creator (see :class:`AbstractCreator`):
		1. If the component is a subclass of :class:`Configurable`,
			arguments in __init__ can be automatically be filled in with the config object.
		2. Otherwise, the component will be instantiated (by default) with the following signature:
			:code:`config, *args, **kwargs`, where :code:`config` is the config object,
			while :code:`*args` and :code:`**kwargs` are arguments manually passed to the creator.
			This is the signature expected for :func:`init_from_config()` if the component
			is a subclass of :class:`AbstractConfigurable` and :func:`__init__` otherwise.
	'''

	def __init__(self, name: Optional[str] = None, description: Optional[str] = None, creator: Optional[str] = None):
		'''
		Decorator to register a component.

		Args:
			name: name of item to be registered (defaults to its __name__)
			description: a short description of what the script does (defaults to first line of its docstring)
			creator: name of the creator that should be used to create this component (generally not recommended)
		'''
		super().__init__(name=name, creator=creator, description=description)


	@staticmethod
	def register_project(project: AbstractProject, name: str, item: Callable[[AbstractConfig], Any],
	                     description: Optional[str] = None, creator: Optional[Union[str, AbstractCreator]] = None,
	                     **kwargs) -> None:
		if description is None and item.__doc__ is not None:
			description = item.__doc__.split('\n')[0]
		project.register_artifact('component', name, item, description=description, creator=creator, **kwargs)



class modifier(_Project_Registration_Decorator):
	'''
	Decorator to register a modifier.

	Modifiers are "runtime mixins" for components and must be classes. When specifying a component to be modified
	with the ``_mod`` key in the config, a new type is dynamically created for which the bases are all the specified
	modifiers followed by the original component.
	'''

	def __init__(self, name: Optional[str] = None, description: Optional[str] = None):
		'''
		Decorator to register a modifier.

		Args:
			name: name of item to be registered (defaults to its __name__)
			description: a short description of what the script does (defaults to first line of its docstring)
		'''
		super().__init__(name=name, description=description)


	@staticmethod
	def register_project(project: AbstractProject, name: str, item: Callable[[AbstractConfig], Any],
	                     description: Optional[str] = None, **kwargs) -> None:
		if description is None and item.__doc__ is not None:
			description = item.__doc__.split('\n')[0]
		project.register_artifact('modifier', name, item, description=description, **kwargs)



class _AutofillMixin(_Registration_Decorator, AbstractCustomArtifact):
	'''Mixin for decorators that autofill arguments from config'''

	def __init__(self, name: Optional[str] = None,
	             aliases: Optional[Dict[str,Union[str,Sequence[str]]]] = None, **kwargs):
		'''
		Shared constructor for decorators that autofill arguments from config.

		Args:
			name: name of item to be registered (defaults to its __name__)
			aliases: alternative names for arguments (can have multiple aliases per argument)
			**kwargs: additional keyword arguments to pass to :func:`register_script()`
		'''
		if aliases is None:
			aliases = {}
		super().__init__(name=name, **kwargs)
		self.aliases = aliases


	def get_wrapped(self) -> Union[Callable, Type]:
		return self.item


	def autofill(self, config: AbstractConfig, args: Optional[Tuple] = None, kwargs: Optional[Dict[str, Any]] = None) \
			-> Tuple[List[Any], Dict[str, Any]]:
		'''
		Autofill arguments needed for the original item (which was decorated) from config.

		Args:
			config: Config object to autofill from
			args: Manually specified arguments
			kwargs: Manually specified keyword arguments

		Returns:
			Arguments to pass to the original item
		'''
		def default_fn(key, default):
			if default is Parameter.empty:
				default = config._empty_default
			aliases = self.aliases.get(key, ())
			if isinstance(aliases, str):
				aliases = (aliases,)
			return config.pulls(key, *aliases, default=default)
		return extract_function_signature(self.item, args=args, kwargs=kwargs, default_fn=default_fn)


	def top(self, config: AbstractConfig, *args: Any, **kwargs: Any) -> Any:
		'''
		Replacement item to be registered, which first autofills arguments
		from the config and then calls the original item.

		Args:
			config: Config object to autofill from
			*args: Manually specified arguments
			**kwargs: Manually specified keyword arguments

		Returns:
			Result of calling the original item
		'''
		fixed_args, fixed_kwargs = self.autofill(config, args=args, kwargs=kwargs)
		return self.item(*fixed_args, **fixed_kwargs)


	def register(self, name: str, item: Callable[[Any], Any], **kwargs):
		super().register(name, self, **kwargs)



class autoscript(_AutofillMixin, script):
	'''
	Convienence decorator to register scripts where the arguments of the script signature
	are automatically extracted from the config before running the script.

	Note:
		This is generally only recommended for simple, short scripts (since it severely limits the usage of the
		config object by the script).
	'''

	def __init__(self, name: Optional[str] = None, description: Optional[str] = None,
	             aliases: Optional[Dict[str, Union[str, Sequence[str]]]] = None, **kwargs):
		'''
		Decorator to register a script (where arguments are extracted from the config automatically).

		Args:
			name: name of item to be registered (defaults to its __name__)
			description: a short description of what the script does (defaults to first line of its docstring)
			aliases: alternative names for arguments (can have multiple aliases per argument)
		'''
		super().__init__(name, description=description, aliases=aliases, **kwargs)



class autocomponent(_AutofillMixin, component):
	'''
	Convienence decorator to register components where the arguments of the component function
	are automatically extracted from the config

	Note:
		This is generally only recommended for simple components that are functions (rather than classes),
		since class components should simply subclass :class:`Configurable` for effectively the same behavior.
	'''

	def __init__(self, name: Optional[str] = None, description: Optional[str] = None,
	             aliases: Optional[Dict[str, Union[str, Sequence[str]]]] = None,
	             creator: Optional[Union[str, AbstractCreator]] = None):
		'''
		Decorator to register a component (where arguments are extracted from the config automatically).

		Args:
			name: name of item to be registered (defaults to its __name__)
			description: a short description of what the script does (defaults to first line of its docstring)
			aliases: alternative names for arguments (can have multiple aliases per argument)
			creator: name of the creator that should be used to create this component
		'''
		super().__init__(name=name, creator=creator, description=description, aliases=aliases)
	


