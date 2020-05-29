
import sys
import inspect

from .registry import view_script_registry, autofill_args
from .config import parse_config

_help_msg = '''fig <script> [args...]
Please specify a script (and optionally args), registered scripts:
{}'''
_help_cmds = {'-h', '--help'}

_error_msg = '''Error script {} is not registered.
Please specify a script (and optionally args), registered scripts:
{}'''

def main(script_name, *argv):
	return _main_script((script_name, *argv))

def _main_script(argv=None):
	if argv is None:
		argv = sys.argv[1:]
	
	scripts = view_script_registry()
	script_names = ', '.join(scripts.keys())
	
	if len(argv) == 0 or (len(argv) == 1 and argv[0] in _help_cmds):
		print(_help_msg.format(script_names))
		return 0
	elif argv[0] not in scripts:
		print(_error_msg.format(argv[0], script_names))
		return 1
	
	name, *argv = argv
	fn, use_config = scripts[name]
	
	if len(argv) == 1 and argv[0] in _help_cmds:
		print(f'Help message for script: {name}')
		
		doc = fn.__doc__
		
		if doc is None and not use_config:
			doc = str(inspect.signature(fn))
			doc = f'Arguments {doc}'
		
		print(doc)
		return 0
	
	A = parse_config(argv=argv)
	
	if use_config:
		out = fn(A)
	else:
		out = autofill_args(fn, A)
	
	if out is None:
		return 0
	return out


