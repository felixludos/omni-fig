# import sys, os
# import importlib
# import importlib.util
# from pathlib import Path
#
# from omnibelt import get_printer, cwd, dict_harvester
#
# prt = get_printer('omnifig')
#
#
# LIB_PATH = os.path.dirname(__file__)
#
#
# # region Source Files
#
# _loaded_files = {}
# def include_files(*paths: str):
# 	'''
# 	Executes all provided paths to python files that have not already been run.
#
# 	Args:
# 		paths: paths to python files to be executed (if not already)
#
# 	Returns:
# 		:code:`None`
#
# 	'''
# 	global _load_counter
#
# 	# TODO: currently individual scripts are rerun separately for each project that references them. this should
# 	#  probably be a global setting
#
# 	for path in paths:
# 		if os.path.isfile(path):
# 			apath = os.path.abspath(path)
# 			if apath not in _loaded_files:
# 				sys.path.insert(1, os.path.dirname(apath))
# 				old = os.getcwd()
# 				os.chdir(os.path.dirname(apath))
# 				prt.debug(f'Loading {apath}')
# 				code_block = compile(open(apath).read(), apath, 'exec')
# 				globs = {'__file__':apath}
# 				exec(code_block, globs)
# 				# _loaded_files[apath] = globs
# 				del sys.path[1]
# 				os.chdir(old)
# 		else:
# 			prt.warning(f'Source file not found: {path}')
#
#
#
# def include_package(*packages: str, path=None):
# 	'''
# 	Imports packages based on their names
#
# 	Args:
# 		packages: list of package names to be imported
#
# 	Returns:
# 		:code:`None`
#
# 	'''
# 	old = None
# 	if path is not None:
# 		sys.path.insert(0, str(path))
# 		old = os.getcwd()
# 		os.chdir(str(path))
# 	for pkg in packages:
# 		# if pkg not in sys.modules:
# 		# 	prt.debug(f'Importing {pkg}')
# 		# 	importlib.import_module(pkg)
# 		# else:
# 		# 	prt.debug(f'Reloading {pkg}')
# 		# 	importlib.reload(sys.modules[pkg])
# 		importlib.import_module(pkg)
# 	if path is not None:
# 		del sys.path[0]
# 		os.chdir(old)
#
# # endregion
#
#
#
#
