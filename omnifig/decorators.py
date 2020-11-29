
from .top import register_script, register_component, register_modifier
from .util import autofill_args

def Script(name, description=None, use_config=True):
	'''
	Decorator to register a script

	:param name: name of script
	:param description: a short description of what the script does
	:param use_config: :code:`True` if the config should be passed as only arg when calling the script function, otherise it will automatically pull all arguments in the script function signature
	:return: decorator function expecting a callable
	'''
	def _reg_script(fn):
		nonlocal name, use_config
		register_script(name, fn, use_config=use_config, description=description)
		return fn
	
	return _reg_script

def AutoScript(name, description=None):
	'''
	Convienence decorator to register scripts that automatically extract
	relevant arguments from the config object

	:param name: name of the script
	:param description: a short description of what the script does
	:return: decorator function expecting a callable that does not expect the config as argument (otherwise use :func:`Script`)
	'''
	return Script(name, use_config=False, description=description)


def Component(name=None):
	'''
	Decorator to register a component

	NOTE: components should usually be types/classes to allow modifications

	:param name: if not provided, will use the __name__ attribute.
	:return: decorator function
	'''
	
	def _cmp(cmp):
		nonlocal name
		if name is None:
			name = cmp.__name__
		register_component(name, cmp)
		return cmp
	
	return _cmp


def AutoComponent(name=None, aliases=None, auto_name=True):
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
	
	def _auto_cmp(cmp):
		nonlocal name, aliases
		
		if type(cmp) == type:  # to allow AutoModifiers
			
			cls = type(f'Auto_{cmp.__name__}' if auto_name else cmp.__name__, (cmp,), {})
			
			def cmp_init(self, info):
				args, kwargs = autofill_args(cmp, info, aliases=aliases, run=False)
				super(cls, self).__init__(*args, **kwargs)
			
			cls.__init__ = cmp_init
			
			_create = cls
		
		else:
			def _create(config):
				nonlocal cmp, aliases
				return autofill_args(cmp, config, aliases)
		
		Component(name)(_create)
		
		return cmp
	
	return _auto_cmp


def Modifier(name=None, expects_config=False):
	'''
	Decorator to register a modifier

	NOTE: a :class:`Modifier` is usually not a type/class, but rather a function
	(except :class:`AutoModifiers`, see below)

	:param name: if not provided, will use the __name__ attribute.
	:param expects_config: True iff this modifier expects to be given the config as second arg
	:return: decorator function
	'''
	
	def _mod(mod):
		nonlocal name, expects_config
		if name is None:
			name = mod.__name__
		register_modifier(name, mod, expects_config=expects_config)
		return mod
	
	return _mod


def AutoModifier(name=None):
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
	
	def _auto_mod(mod_type):
		nonlocal name
		
		def _the_mod(cmpn_type):
			# awesome python feature -> dynamic type declaration!
			return type('{}_{}'.format(mod_type.__name__, cmpn_type.__name__), (mod_type, cmpn_type), {})
		
		Modifier(name=mod_type.__name__ if name is None else name)(_the_mod)
		return mod_type
	
	return _auto_mod


def _make_post_mod(mod):
	def _make_cmpn(cmpn):
		def _make_mod(info):
			return mod(cmpn(info), info)
		
		return _make_mod
	
	return _make_cmpn


def Modification(name=None):
	'''
	A kind of Modifier that modifies the component after it is created,
	and then returns the modified component

	expects a callable with input (component, config)

	Modifications should almost always be applied after all other modifiers,
	so they should appear at the end of _mod list

	:param name: name to register
	:return: a decorator expecting the modification function
	'''
	
	def _reg_modification(mod):
		nonlocal name
		Modifier(name)(_make_post_mod(mod))
		return mod
	
	return _reg_modification


