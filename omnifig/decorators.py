
from .top import register_script, register_component, register_modifier
from .util import autofill_args


class Script:
	'''
	Decorator to register a script

	:param name: name of script
	:param description: a short description of what the script does
	:param use_config: :code:`True` if the config should be passed as only arg when calling the script function, otherise it will automatically pull all arguments in the script function signature
	:return: decorator function expecting a callable
	'''
	def __init__(self, name, description=None, use_config=True):
		self.name = name
		self.description = description
		self.use_config = use_config
	
	
	def __call__(self, fn):
		register_script(self.name, fn, use_config=self.use_config, description=self.description)
		return fn
		
		

class AutofillMixin:
	def __init__(self, name=None, aliases=None, **kwargs):
		super().__init__(name=name, **kwargs)
		self.aliases = aliases


	def autofill(self, config):
		return autofill_args(self.fn, config, aliases=self.aliases, run=False)


	def top(self, config):
		'''
		Automatically fill in the arguments of the component function
		:param config: config object
		:return: the result of the component function
		'''
		args, kwargs = self.autofill(config)
		return self.fn(*args, **kwargs)


	def __call__(self, fn):
		if self.name is None:
			self.name = fn.__name__
		self.fn = fn
		super().__call__(self.top)
		return fn



class AutoScript(AutofillMixin, Script):
	'''
	Convienence decorator to register scripts that automatically extract
	relevant arguments from the config object

	:param name: name of the script
	:param description: a short description of what the script does
	:param aliases: optional aliases for arguments used when autofilling (should be a dict[name,list[aliases]])
	'''
	def __init__(self, name, description=None, aliases=None):
		super().__init__(name, description=description, aliases=aliases, use_config=False)



class Component:
	'''
	Decorator to register a component

	NOTE: components should usually be types/classes to allow modifications

	:param name: if not provided, will use the __name__ attribute.
	'''
	def __init__(self, name=None):
		self.name = name

	def __call__(self, fn):
		if self.name is None:
			self.name = fn.__name__
		register_component(self.name, fn)
		return fn



class AutoComponent(AutofillMixin, Component):
	'''
	Instead of directly passing the config to an AutoComponent, the necessary args are auto filled and passed in.
	This means AutoComponents are somewhat limited in that they cannot modify the config object and they cannot be
	modified with AutoModifiers.

	Note: AutoComponents are usually components that are created with functions (rather than classes) since they can't
	be automodified. When registering classes as components, you should probably use `Component` instead, and pull
	from the config directly.

	:param name: name to use when registering the auto component
	:param aliases: optional aliases for arguments used when autofilling (should be a dict[name,list[aliases]])
	:return: decorator function
	'''
	def __init__(self, name=None, aliases=None):
		super().__init__(name=name, aliases=aliases)



class Modifier:
	'''
	Decorator to register a modifier

	NOTE: a :class:`Modifier` is usually not a type/class, but rather a function
	(except :class:`AutoModifiers`, see below)

	:param name: if not provided, will use the __name__ attribute.
	:param expects_config: True iff this modifier expects to be given the config as second arg
	:return: decorator function
	'''
	def __init__(self, name=None, expects_config=False):
		self.name = name
		self.expects_config = expects_config


	def __call__(self, fn):
		if self.name is None:
			self.name = fn.__name__
		register_modifier(self.name, fn, expects_config=self.expects_config)
		return fn
	
	

class AutoModifier(Modifier):
	'''
	Can be used to automatically register modifiers that combine types

	To keep component creation as clean as possible, modifier types should allow arguments to their __init__
	(other than the Config object) and only call pull on arguments not provided, that way child classes of
	the modifier types can specify defaults for the modifications without calling pull() multiple times
	on the same arg.

	Note: in a way, this converts components to modifiers (but think before using). This turns the modified
	component into a child class of this modifier and its previous type.

	In short, Modifiers are used for wrapping of components, AutoModifiers are used for subclassing components

	:param name: if not provided, will use the __name__ attribute.
	:return: decorator to decorate a class
	'''
	def create_modified_component(self, component):
		self.product = component if issubclass(component, self.mod_cls) \
			else type('{}_{}'.format(self.mod_cls.__name__, component.__name__), (self.mod_cls, component), {})
		return self.product


	def __call__(self, cls):
		if self.name is None:
			self.name = cls.__name__
		self.mod_cls = cls
		super().__call__(self.create_modified_component)
		return cls



class Modification(Modifier):
	'''
	A kind of Modifier that modifies the component after it is created,
	and then returns the modified component

	expects a callable with input (component, config)

	Modifications should almost always be applied after all other modifiers,
	so they should appear at the end of _mod list

	:param name: name to register
	:return: a decorator expecting the modification function
	'''
	
	def top(self, component):
		self.component_fn = component
		return self.create_and_modify
	
	
	def create_and_modify(self, config):
		component = self.component_fn(config)
		return self.fn(component, config)


	def __call__(self, fn):
		if self.name is None:
			self.name = fn.__name__
		self.fn = fn
		super().__call__(self.top)
		return fn



