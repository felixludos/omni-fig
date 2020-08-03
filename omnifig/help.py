
import sys, os
from tabulate import tabulate

from .external import view_config_registry
from .registry import get_script, view_script_registry
from .rules import Meta_Rule, view_meta_rules


_default_help_msg = '''
Usage: fig [-<meta>] {script} [<configs>...] [--<args>]

{scripts}
meta: Optional meta arguments (usually specified with a single letter)
{metas}
configs: Specify any registered configs to merge
{configs}
args: Any additional arguments specified manually
as key-value pairs (keys with "--")
'''

_default_script_info = '''script: Specify a registered script name to run
{available}'''

_script_sel = '''Script: {script}
{doc}'''


@Meta_Rule('help', priority=99, code='h', description='Display this help message')
def help_message(meta, config):
	
	name = meta.pull('script_name', None, silent=True)
	num = meta.pull('show_args', 4, silent=True)
	
	metas = [(f'-{r.code}', r.name, '-' if r.description is None else r.description)
	         for r in view_meta_rules() if r.code is not None][:num]
	
	minfo = tabulate(metas, headers=['Code', 'Name', 'Description'], ) + '\n' # tablefmt="plain"
	
	scripts = [(s.name, '-' if s.description is None else s.description)
	           for s in view_script_registry().values()]#[:num]
	
	configs = [c.name for c in view_config_registry().values()]
	
	end = ''
	if len(configs) > num:
		end = f' ... [{len(configs)} items]'
	
	cinfo = ', '.join(configs)
	cinfo = f'Registered configs: {cinfo}{end}\n'
	
	if name is None:
		name = '<script>'
		
		sinfo = _default_script_info.format(available=
		                    tabulate(scripts, headers=['Name', 'Description'],)) + '\n' #tablefmt="plain"
		
	
	else:
		
		info = get_script(name)
		doc = info.fn.__doc__
	
		if doc is None or len(doc) == 0:
			doc = '[no docstring]\n'
	
		sinfo = _script_sel.format(script=name, doc=doc)
		
	print(_default_help_msg.format(script=name, scripts=sinfo, metas=minfo, configs=cinfo))
	
	sys.exit(0)

