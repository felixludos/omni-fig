
# from omnibelt import monkey_patch

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
	def _reg_script_decorator(fn):
		nonlocal name, use_config
		register_script(name, fn, use_config=use_config, description=description)
		return fn
	# monkey_patch(_reg_script_decorator)
	
	return _reg_script_decorator

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
	
	def _register_cmp_decorator(cmp):
		nonlocal name
		if name is None:
			name = cmp.__name__
		register_component(name, cmp)
		return cmp
	# monkey_patch(_register_cmp_decorator)
	
	return _register_cmp_decorator


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
	
	def _auto_cmp_decorator(cmp):
		nonlocal name, aliases
		
		if type(cmp) == type:  # to allow AutoModifiers
			
			cls = type(f'Auto_{cmp.__name__}' if auto_name else cmp.__name__, (cmp,), {})
			# monkey_patch(cls)
			
			def _cmp_init_fn(self, info):
				args, kwargs = autofill_args(cmp, info, aliases=aliases, run=False)
				super(cls, self).__init__(*args, **kwargs)
			# monkey_patch(_cmp_init_fn)
			
			cls.__init__ = _cmp_init_fn
			
			_auto_create_fn = cls
		
		else:
			def _auto_create_fn(config):
				nonlocal cmp, aliases
				return autofill_args(cmp, config, aliases)
			
			# monkey_patch(_auto_create_fn)
		Component(name)(_auto_create_fn)
		
		return cmp
	
	# monkey_patch(_auto_cmp_decorator)
	
	return _auto_cmp_decorator


def Modifier(name=None, expects_config=False):
	'''
	Decorator to register a modifier

	NOTE: a :class:`Modifier` is usually not a type/class, but rather a function
	(except :class:`AutoModifiers`, see below)

	:param name: if not provided, will use the __name__ attribute.
	:param expects_config: True iff this modifier expects to be given the config as second arg
	:return: decorator function
	'''
	
	def _mod_decorator_fn(mod):
		nonlocal name, expects_config
		if name is None:
			name = mod.__name__
		register_modifier(name, mod, expects_config=expects_config)
		return mod
	# monkey_patch(_mod_decorator_fn)
	
	return _mod_decorator_fn


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
	
	def _auto_mod_decorator(mod_type):
		nonlocal name
		
		def _the_mod_creation_fn(cmpn_type):
			# awesome python feature -> dynamic type declaration!
			cls = cmpn_type if issubclass(cmpn_type, mod_type) \
				else type('{}_{}'.format(mod_type.__name__, cmpn_type.__name__), (mod_type, cmpn_type), {})
			# monkey_patch(cls)
			return cls
		# monkey_patch(_the_mod_creation_fn)
		
		Modifier(name=mod_type.__name__ if name is None else name)(_the_mod_creation_fn)
		return mod_type
	# monkey_patch(_auto_mod_decorator)
	
	return _auto_mod_decorator


def _make_post_mod(mod):
	def _make_cmpn_decorator(cmpn):
		def _modification_fn(info):
			return mod(cmpn(info), info)
		# monkey_patch(_modification_fn)
		return _modification_fn
	# monkey_patch(_make_cmpn_decorator)
	return _make_cmpn_decorator


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
	# monkey_patch(_reg_modification)
	
	return _reg_modification


