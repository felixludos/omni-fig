import sys, os
import importlib
import importlib.util

from omnibelt import get_printer, Registry, Entry_Registry

from .errors import ConfigNotFoundError

prt = get_printer(__name__)

# region Source files

_loaded_files = {}
_load_counter = 0
def include_files(*paths):
	'''
	Executes all provided paths to python files that have not already been run.
	
	:param paths: paths to python files to be executed (if not already)
	:return: None
	'''
	global _load_counter
	
	for path in paths:
		if os.path.isfile(path):
			apath = os.path.abspath(path)
			if apath not in _loaded_files:
				prt.debug(f'Loading {apath}')
				spec = importlib.util.spec_from_file_location(f"load{_load_counter}", apath)
				mod = importlib.util.module_from_spec(spec)
				spec.loader.exec_module(mod)
				# mod.MyClass()
				_loaded_files[apath] = mod
				_load_counter += 1

def include_package(*packages):
	'''
	Imports packages based on their names
	
	:param packages: list of package names to be imported
	:return: None
	'''
	for pkg in packages:
		importlib.import_module(pkg)

# endregion


# region config

class _Config_Registry(Entry_Registry, components=['path', 'project']):
	pass
_config_registry = _Config_Registry()


def register_config(name, path, project=None):
	'''
	Registers a single config yaml file
	
	:param name: name to associate with this config
	:param path: absolute path to config
	:param project: project associated with this config
	:return: None
	'''
	assert os.path.isfile(path), 'Cant find config file: {}'.format(path)
	
	prt.debug(f'Registering config {name}')
	if name in _config_registry:
		prt.warning(f'A config with name {name} has already been registered, now overwriting')
	
	_config_registry.new(name, path=path, project=project)
	
	if project is not None:
		project.new_config(name)


def register_config_dir(path, recursive=False, prefix=None, joiner='/', project=None):
	'''
	Registers all yaml files found in the given directory (possibly recursively)
	
	When recusively checking all directories inside, the internal folder hierarchy is preserved
	in the name of the config registered, so for example if the given ``path`` points to a
	directory that contains a directory ``a`` and two files ``f1.yaml`` and ``f2.yaml``:
	
	Contents of ``path`` and corresponding registered names:
	
		- ``f1.yaml`` => ``f1``
		- ``f2.yaml`` => ``f2``
		- ``a/f3.yaml`` => ``a/f3``
		- ``a/b/f4.yaml`` => ``a/b/f3``
	
	If a ``prefix`` is provided, it is appended to the beginning of the registered names
	
	:param path: path to root directory to search through
	:param recursive: search recursively through sub-directories for more config yaml files
	:param prefix: prefix for names of configs found herein
	:param joiner: string to merge directories when recursively searching (default ``/``)
	:param project: project object to associate with all configs registered here
	:return: None
	'''
	assert os.path.isdir(path)
	for fname in os.listdir(path):
		parts = fname.split('.')
		candidate = os.path.join(path, fname)
		if os.path.isfile(candidate) and len(parts) > 1 and parts[-1] in {'yml', 'yaml'}:
			name = parts[0]
			if prefix is not None:
				name = joiner.join([prefix, name])
			register_config(name, os.path.join(path, fname), project=project)
		elif recursive and os.path.isdir(candidate):
			newprefix = fname if prefix is None else joiner.join([prefix, fname])
			register_config_dir(candidate, recursive=recursive, prefix=newprefix, joiner=joiner, project=project)

def include_configs(*paths, project=None):
	'''
	Convenience function which can be given paths to directories or individual files,
	all of which will be registered (recursively)
	
	:param paths: paths to yaml config files or directories to be registered
	:param project: project to associate with all configs registered here
	:return: None
	'''
	for path in paths:
		if os.path.isdir(path):
			register_config_dir(path, recursive=True, project=project)
		elif os.path.isfile(path):
			fname = os.path.basename(path)
			parts = fname.split('.')
			if len(parts) > 1 and parts[-1] in {'yml', 'yaml'}:
				register_config(parts[0], path, project=project)

def view_config_registry(): # TODO: clean this up - return view not copy of the full registry
	'''Return a copy of the full config registry'''
	return _config_registry.copy()


def find_config_path(name):
	'''
	Given a name or path, find the associated config file
	by checking the registry in possible
	
	:param name: path or name of config to find
	:return: full absolute path of config (raising :class:`ConfigNotFoundError` if nothing is found)
	'''
	if os.path.isfile(name):
		return name

	reg = _config_registry

	if name in reg:
		return reg[name].path
	elif os.path.isfile(name):
		return name
	raise ConfigNotFoundError(name)


# endregion

# region project types

_ptype_registry = Registry()


def register_project_type(name, cls):
	'''
	Project types allow users to customize the behavior of project objects

	:param name: identifier of this project type
	:param cls: project type class
	:return: None
	'''

	_ptype_registry.new(name, cls)


def get_project_type(name):
	'''Gets the project type associated with that name, otherwise returns None'''
	if name not in _ptype_registry:
		prt.error(f'Project type: {name} not found')
	return _ptype_registry.get(name, None)


def view_project_types():
	'''Returns a copy of the full project type registry'''
	return _ptype_registry.copy()

# endregion