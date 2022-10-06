import sys, os
import importlib
import importlib.util

from omnibelt import get_printer

prt = get_printer(__name__)


LIB_PATH = os.path.dirname(__file__)


# region Source Files

_loaded_files = {}
def include_files(*paths: str):
	'''
	Executes all provided paths to python files that have not already been run.

	Args:
		paths: paths to python files to be executed (if not already)

	Returns:
		:code:`None`

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



def include_package(*packages: str):
	'''
	Imports packages based on their names

	Args:
		packages: list of package names to be imported

	Returns:
		:code:`None`

	'''
	for pkg in packages:
		importlib.import_module(pkg)


# endregion




