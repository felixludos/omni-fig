
import sys, os
import inspect
from collections import namedtuple
import importlib.util

from .errors import MissingConfigError
from .loading import get_current_project
from .util import autofill_args

from omnibelt import Registry, Entry_Registry, get_printer, get_global_setting

prt = get_printer(__name__)


# region Scripts

class _Script_Registry(Entry_Registry, components=['fn', 'use_config', 'description', 'project']):
	pass
_script_registry = _Script_Registry()

def register_script(name, fn, use_config=False, description=None):
	prt.debug(f'Registering script {name}')
	if name in _script_registry:
		prt.warning(f'A script with name {name} has already been registered, now overwriting')
	
	project = get_current_project()
	_script_registry.new(name, fn=fn, use_config=use_config, description=description, project=project)
	
	if project is not None:
		project.new_script(name)
	
def get_script(name):
	return _script_registry.get(name, None)
	
def view_script_registry():
	return _script_registry.copy()

def Script(name, use_config=True, description=None):
	def _reg_script(fn):
		nonlocal name, use_config
		register_script(name, fn, use_config=use_config, description=description)
		return fn
	
	return _reg_script

def AutoScript(name, description=None):
	return Script(name, use_config=False, description=description)

# endregion

# region Components

class _Component_Registry(Entry_Registry, components=['create_fn', 'project']):
	pass
_component_registry = _Component_Registry()

def register_component(name, create_fn):
	'''
	create_fn takes a single input - a Config object
	The config object is guaranteed to have at least one entry with key "_type" and the value is the same as
	the registered name of the component.

	:param name: str (should be unique to this component)
	:param create_fn: callable accepting one arg (a Config object) (these should usually be classes)
	'''
	# assert name not in _reserved_names, '{} is reserved'.format(name)
	prt.debug(f'Registering component {name}')
	if name in _component_registry:
		prt.warning(f'A component with name {name} has already been registered, now overwriting')
	
	project = get_current_project()
	_component_registry.new(name, create_fn=create_fn, project=project)

	if project is not None:
		project.new_component(name)
	
	
def view_component_registry():
	return _component_registry.copy()


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


def AutoComponent(name=None, aliases=None):
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
			
			cls = type('Auto_{}'.format(cmp.__name__), (cmp,), {})
			
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

# endregion

# region Modifier

_appendable_keys = {'_mod'} # mods can be appended when updating (instead of overwriting)
# def register_appendable_key(key): # At that point, they might as well manipulate _appendable_keys directly
# 	_appendable_keys.add(key)

class _Modifier_Registry(Entry_Registry, components=['fn', 'expects_config', 'project']):
	pass
_mod_registry = _Modifier_Registry()

def register_modifier(name, mod_fn, expects_config=False):
	'''
	Takes as input the "create_fn" of some component and a Config object.

	NOTE: modifier names may not start with "+", as that is used to signify that the mod should be
	appended when merging configs

	:param name: str (should be unique to this component, may not start with "+")
	:param mod_fn: callable accepting one arg (the "create_fn" of a registered component)
	(these should usually be classes)
	'''
	# assert name not in _reserved_names, '{} is reserved'.format(name)
	prt.debug(f'Registering modifier {name}')
	if name in _mod_registry:
		prt.warning(f'A modifier with name {name} has already been registered, now overwriting')
	
	project = get_current_project()
	_mod_registry.new(name, fn=mod_fn, expects_config=expects_config, project=project)
	
	if project is not None:
		project.new_modifier(name)
	
def view_modifier_registry():
	return _mod_registry.copy()

def Modifier(name=None, expects_config=False):
	'''
	Decorator to register a modifier

	NOTE: modifiers are usually not types/classes, but functions

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

	(eg. see `Cropped` in .datasets.transforms)

	Note: in a way, this converts components to modifiers (but think before using). This turns the modified
	component into a child class of this modifier and its previous type.

	In short, Modifiers are used for wrapping of components, AutoModifiers are used for subclassing components

	:param name: if not provided, will use the __name__ attribute.
	:return: decorator to decorate a function
	'''

	def _auto_mod(mod_type):
		nonlocal name
		def _the_mod(cmpn_type):
			# awesome python feature -> dynamic type declaration!
			return type('{}_{}'.format(mod_type.__name__, cmpn_type.__name__), (mod_type, cmpn_type), {})
		Modifier(name=name)(_the_mod)
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
	A specific kind of Modifier that modifies the component after it is created
	
	expects a callable with input (component, config)
	
	:param name: name to register
	'''
	
	def _reg_modification(mod):
		nonlocal name
		Modifier(name)(_make_post_mod(mod))
		return mod
	
	return _reg_modification

# endregion


def create_component(info):
	'''
	Creates the component specified in info (checks component registry using info.pull('_type'),
	and modifier registry for info.pull('_mod'))

	_mod can be a list, inwhich case they will be applied in the given order, eg:

	let mods = [A, B, C]

	component <- C(B(A(component)))

	NOTE: generally, start with more specific modifications, and become more general

	:param info: should be a Config object with attribute "_type" (and optionally "_mod")
	:return: component(info)
	'''

	name = info.pull('_type', silent=True)

	assert name in _component_registry, 'Unknown component type (have you registered it?): {}'.format(name)

	component = _component_registry[name].create_fn

	try:
		mod_names = info.pull('_mod', silent=True)
	except MissingConfigError:
		mod_names = None

	if mod_names is not None:

		if not isinstance(mod_names, (list, tuple)):
			mod_names = mod_names,

		for mod_name in mod_names: # WARNING: apply modifications in reverse order
			if mod_name[0] == '+': # filter out initial + if found
				mod_name = mod_name[1:]
			mod = _mod_registry[mod_name]
			component = mod.fn(component, info) if mod.expects_config else mod.fn(component)

	return component(info)



