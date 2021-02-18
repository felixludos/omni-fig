import sys, os
import importlib
import importlib.util

from omnibelt import get_printer, Registry, Entry_Registry

prt = get_printer(__name__)

# region Source files

_loaded_files = {}
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
				sys.path.insert(1, os.path.dirname(apath))
				old = os.getcwd()
				os.chdir(os.path.dirname(apath))
				prt.debug(f'Loading {apath}')
				code_block = compile(open(apath).read(), apath, 'exec')
				globs = {'__file__':apath}
				exec(code_block, globs)
				_loaded_files[apath] = globs
				
				del sys.path[1]
				os.chdir(old)

def include_package(*packages):
	'''
	Imports packages based on their names
	
	:param packages: list of package names to be imported
	:return: None
	'''
	for pkg in packages:
		importlib.import_module(pkg)

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