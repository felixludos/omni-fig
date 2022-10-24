from typing import Dict, Any, Optional
import sys
from tabulate import tabulate
from omnibelt import get_printer

from ..abstract import AbstractConfig
from .. import meta_rule, create_config, get_current_project
from ..registration import Meta_Rule


prt = get_printer(__name__)


# @meta_rule(name='help', code='h', priority=99, num_args=0, description='Display this help message')
class Help_Rule(Meta_Rule, name='help', code='h', priority=99, num_args=0, description='Display this help message'):
	_default_help_msg = '''
Usage: fig [-<meta>] {script} [<configs>...] [--<args>]

{scripts}

+------+
| meta |
+------+
Optional meta arguments (usually specified with a single letter)
{metas}

+---------+
| configs |
+---------+
Specify any registered configs to merge

{configs}

+------+
| args |
+------+
Any additional arguments specified manually
as key-value pairs (keys with "--")

Current project: {project}
'''
	
	_default_script_info = '''+--------+
| script |
+--------+
Specify a registered script name to run
{available}'''

	_script_sel = '''Script: {script}
{doc}'''

	@classmethod
	def run(cls, config: AbstractConfig, meta: AbstractConfig) -> Optional[AbstractConfig]:

		show_help = meta.pull('help', False, silent=True)

		if not show_help:
			return

		name = meta.pull('script_name', None, silent=True)
		num = meta.pull('show_args', 4, silent=True)

		project = get_current_project()
		project.activate()

		metas = [(f'-{r.code}', r.name, '-' if r.description is None else r.description)
		         for r in project.iterate_meta_rules() if r.code is not None][:num]

		minfo = tabulate(metas, headers=['Code', 'Name', 'Description'], )  # tablefmt="plain"

		scripts = [(s.name, '-' if s.description is None else s.description)
		           for s in project.iterate_artifacts('script') if not s.hidden]  # [:num]

		configs = [c.name for c in project.iterate_artifacts('config')]

		end = ''
		if len(configs) > num:
			end = f' ... [{len(configs)} items]'

		cinfo = ', '.join(configs)
		cinfo = f'Registered configs: {cinfo}{end}'

		if name is None:
			name = '<script>'

			if len(scripts) == 0:
				sinfo = '\n  - No scripts registered -'
			else:
				sinfo = tabulate(scripts, headers=['Name', 'Description'], )  # tablefmt="plain"

			sinfo = cls._default_script_info.format(available=sinfo)

		else:

			info = project.find_artifact('script', name)
			doc = info.fn.__doc__

			if doc is None or len(doc) == 0:
				doc = '[no docstring]\n'

			sinfo = cls._script_sel.format(script=name, doc=doc)
		
		project_name = project.name
		print(cls._default_help_msg.format(script=name, scripts=sinfo, metas=minfo, configs=cinfo,
		                                   project=project_name))

		raise cls.TerminationFlag


#
# @Meta_Rule('help', priority=99, code='h', description='Display this help message')
# def help_message(meta, config):
# 	'''
# 	When activated, this rule prints out help message for the ``fig`` command, which includes
# 	a list of all registered scripts, meta rules, and configs that have been loaded.
#
# 	:param meta: meta config object
# 	:param config: config object
# 	:return: [system exit, with code 0]
# 	'''
#
# 	show_help = meta.pull('help', False, silent=True)
#
# 	if not show_help:
# 		return config
#
# 	name = meta.pull('script_name', None, silent=True)
# 	num = meta.pull('show_args', 4, silent=True)
#
# 	metas = [(f'-{r.code}', r.name, '-' if r.description is None else r.description)
# 	         for r in view_meta_rules() if r.code is not None][:num]
#
# 	minfo = tabulate(metas, headers=['Code', 'Name', 'Description'], ) # tablefmt="plain"
#
# 	scripts = [(s.name, '-' if s.description is None else s.description)
# 	           for s in view_scripts().values() if not s.name.startswith('_')]#[:num]
#
# 	configs = [c.name for c in view_configs().values()]
#
# 	end = ''
# 	if len(configs) > num:
# 		end = f' ... [{len(configs)} items]'
#
# 	cinfo = ', '.join(configs)
# 	cinfo = f'Registered configs: {cinfo}{end}'
#
# 	if name is None:
# 		name = '<script>'
#
# 		if len(scripts) == 0:
# 			sinfo = '\n  - No scripts registered -'
# 		else:
# 			sinfo = tabulate(scripts, headers=['Name', 'Description'],) #tablefmt="plain"
#
# 		sinfo = _default_script_info.format(available=sinfo)
#
# 	else:
#
# 		info = find_script(name)
# 		doc = info.fn.__doc__
#
# 		if doc is None or len(doc) == 0:
# 			doc = '[no docstring]\n'
#
# 		sinfo = _script_sel.format(script=name, doc=doc)
#
# 	print(_default_help_msg.format(script=name, scripts=sinfo, metas=minfo, configs=cinfo))
#
# 	sys.exit(0)

