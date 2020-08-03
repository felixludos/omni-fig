import sys, os
import importlib
import importlib.util

from omnibelt import get_printer, Registry, Entry_Registry


prt = get_printer(__name__)

# region Source files

_loaded_files = {}
_load_counter = 0
def include_files(*paths):
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
	for pkg in packages:
		importlib.import_module(pkg)

# endregion


# region config

class _Config_Registry(Entry_Registry, components=['path', 'project']):
	pass
_config_registry = _Config_Registry()


def register_config(name, path, project=None):
	assert os.path.isfile(path), 'Cant find config file: {}'.format(path)
	
	prt.debug(f'Registering config {name}')
	if name in _config_registry:
		prt.warning(f'A config with name {name} has already been registered, now overwriting')
	
	_config_registry.new(name, path=path, project=project)
	
	if project is not None:
		project.new_config(name)


def register_config_dir(path, recursive=False, prefix=None, joiner='/', project=None):
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
	for path in paths:
		if os.path.isdir(path):
			register_config_dir(path, recursive=True, project=project)
		elif os.path.isfile(path):
			fname = os.path.basename(path)
			parts = fname.split('.')
			if len(parts) > 1 and parts[-1] in {'yml', 'yaml'}:
				register_config(parts[0], path, project=project)

def view_config_registry(): # TODO: clean this up - return view not copy of the full registry
	return _config_registry.copy()


def find_config_path(name):
	if os.path.isfile(name):
		return name

	reg = _config_registry

	if name in reg:
		return reg[name].path
	elif os.path.isfile(name):
		return name
	# elif 'FOUNDATION_SAVE_DIR' in os.environ:
	#
	# 	run_dir = name if os.path.isdir(name) else os.path.join(os.environ['FOUNDATION_SAVE_DIR'], name)
	# 	path = os.path.join(run_dir, 'config.yml')
	#
	# 	if os.path.isfile(path):
	# 		return path

	# path = os.path.join(os.environ['FOUNDATION_SAVE_DIR'], name)
	# run_dir = os.path.dirname(path)
	#
	# path = os.path.join(run_dir, 'config.yml') # run dir
	#
	# name = path

	raise Exception(f'Unknown config: {name}')


# endregion

# region project types

_ptype_registry = Registry()


def register_project_type(name, cls):
	'''
	Project types allow users to customize the behavior of project objects

	:param name: identifier of this project type
	:param cls: project type class
	:return:
	'''

	_ptype_registry.new(name, cls)


def get_project_type(name):
	if name not in _ptype_registry:
		prt.error(f'Project type: {name} not found')
	return _ptype_registry.get(name, None)


# def Project_Type(name, auto_assoc=True):
# 	def _reg_ptype(cls):
# 		nonlocal name, auto_assoc
# 		register_project_type(name, cls, auto_assoc=auto_assoc)
# 		return cls
# 	return _reg_ptype

def view_project_types():
	return _ptype_registry.copy()


# def view_project_assocs():
# 	return _ptype_assocs.copy()
#
#
# def get_project_assoc(name):
# 	return _ptype_assocs.get(name, None)

# endregion