from typing import Union, Any, Type, Optional, Iterator, Sequence, ContextManager, NamedTuple, List
from tabulate import tabulate
from omnibelt import colorize

from ..abstract import AbstractConfig, AbstractCustomArtifact
from .. import get_current_project, get_profile

from .base import Behavior



class Help(Behavior, name='help', code='h', priority=99, num_args=0, description='Display this help message'):
	'''
	When activated, this behavior prints the help message for the current project (and then exits the program).
	'''

	@staticmethod
	def _format_script_entry(entry: NamedTuple, verbose: bool = False) -> List[str]:
		ident = entry.name
		desc = getattr(entry, 'description', '')

		proj = getattr(entry, 'project', None)

		item = getattr(entry, 'cls', None)
		if item is None:
			item = getattr(entry, 'fn', None)
		if isinstance(item, AbstractCustomArtifact):
			item = item.get_wrapped()

		name = colorize(getattr(item, '__name__', ''), 'blue')
		mod = getattr(item, '__module__', None)
		if len(name) and mod is not None:
			name = f'{mod}.{name}'

		owner = getattr(proj, 'name', '')

		row = [
			colorize(ident, color='green'),
			name if verbose else mod,

			desc,
		]
		if verbose:
			row.insert(2, owner)
		return row

	_script_title = '''
This will run the script: {script} {script_info}
	
{doc}

You can additionally specify the following: [<configs>...] [-<meta>] [--<args>]'''

	@classmethod
	def format_selected_script(cls, config: AbstractConfig, entry: Optional[NamedTuple], verbose: bool = False) -> str:
		if entry is not None:

			terms = cls._format_script_entry(entry, verbose=True)
			ident, name, owner, desc = terms

			item = getattr(entry, 'cls', None)
			if item is None:
				item = getattr(entry, 'fn', None)
			if isinstance(item, AbstractCustomArtifact):
				item = item.get_wrapped()

			info = {'script': ident}

			if item.__doc__ is not None:
				doc = item.__doc__
				doc = [line if line.startswith('\t') else f'\t{line}' for line in doc.splitlines()]
				doc = '\n'.join(doc)
			elif desc is not None:
				doc = '\t' + desc
			else:
				doc = '-- no description or documentation found --'
			info['doc'] = doc

			if name is not None:
				info['script_info'] = f' ({name})'

			return {'header': cls._script_title.format(**info)}


			pass


	@classmethod
	def format_scripts(cls, config: AbstractConfig, entries: Iterator[NamedTuple], verbose: bool = False) -> str:
		rows = [cls._format_script_entry(s, verbose=verbose) for s in entries]

		if not len(rows):
			return '-- No scripts registered --'

		cols = ['code', 'name' if verbose else 'module', 'description']
		if verbose:
			cols.insert(2, 'project')

		return tabulate(rows, headers=cols, tablefmt='simple')  # tablefmt="plain"


	@staticmethod
	def _format_behavior_entry(entry: NamedTuple, verbose: bool = False) -> List[str]:
		ident = entry.name
		desc = getattr(entry, 'description', '')

		item = getattr(entry, 'cls', None)
		if item is None:
			item = getattr(entry, 'fn', None)
		if isinstance(item, AbstractCustomArtifact):
			item = item.get_wrapped()

		name = colorize(getattr(item, '__name__', ''), 'blue')
		mod = getattr(item, '__module__', None)
		if len(name) and mod is not None:
			name = f'{mod}.{name}'

		# if name.startswith('omnifig.'):
		# 	name = ''

		code = colorize(getattr(item, 'code', ''), 'green')
		if len(code):
			code = f'-{code}'

		row = [
			code,
			ident,

			desc,
		]
		if verbose:
			row.insert(2, name)
		return row


	@classmethod
	def format_behaviors(cls, config: AbstractConfig, entries: Iterator[NamedTuple], verbose: bool = False) -> str:
		rows = [cls._format_behavior_entry(entry, verbose=verbose) for entry in entries]

		cols = ['code', 'name', 'description']
		if verbose:
			cols.insert(2, 'class')
		table = tabulate(rows, headers=cols, tablefmt='simple')  # tablefmt="plain"
		return table


	@staticmethod
	def format_configs(config: AbstractConfig, entries: Iterator[NamedTuple], verbose: bool = False) -> str:
		names = [f'{e.name}' for e in entries]
		terms = [f'Config{"" if len(names) == 1 else "s"} ({len(names)}){":" if len(names) else ""}', ', '.join(sorted(names))]
		return ' '.join(terms)

	_blank_title = '''
Usage: fig [-<meta>] <script> [<configs>...] [--<args>]

+--------+
| script |
+--------+
Specify a registered script name to run

{scripts}'''

	_msg_template = '''{header}

+------+
| meta |
+------+
Optional meta behaviors to modify the execution (must be specified separately e.g. "-a -b")

{behaviors}

+---------+
| configs |
+---------+
Specify any registered configs to compose and use for the script

{configs}

+------+
| args |
+------+
Any additional arguments specified manually
as key-value pairs (either as "--key value" or "--key=value")

Current project: {project}'''


	@classmethod
	def pre_run(cls, meta: AbstractConfig, config: AbstractConfig) -> None:
		'''
		When activated, this rule prints the help message for the current project (and then exits the program).

		Args:
			meta: The meta config object (used to check if the rule is activated with the ``quiet`` key)
			config: The config object to be modified

		Returns:
			``None``

		Raises:
			:exc:`TerminationFlag`: if the rule is activated, to prevent the script from running

		'''

		with config.silence():
			verbose = config.pull('verbose', False)
			name = meta.pull('script_name', None)
			# num = meta.pull('show_args', 6)

		profile = get_profile()
		project = get_current_project()


		msg_info = {
			'project': project.name,
			'behaviors': cls.format_behaviors(config, profile.iterate_behaviors(), verbose=verbose),
			'configs': cls.format_configs(config, project.xray('config', as_list=True), verbose=verbose),
		}

		if name is not None:
			entry = project.find_script(name, None)
			if entry is not None:
				script_info = cls.format_selected_script(config, entry, verbose=verbose)
				if script_info is not None:
					msg_info.update(script_info)
			# else:
			# 	raise ValueError(f'Could not find script: {name}')

		if 'header' not in msg_info:

			scripts = cls.format_scripts(config, project.xray('script', as_list=True), verbose=verbose)

			msg_info['header'] = cls._blank_title.format(scripts=scripts)


		print(cls._msg_template.format(**msg_info))

		raise cls.TerminationFlag

		metas = [(f'-{r.code}', r.name, '-' if r.description is None else r.description)
		         for r in project.behaviors() if r.code is not None][:num]

		minfo = tabulate(metas, headers=['Code', 'Name', 'Description'], )  # tablefmt="plain"

		# TODO: use xray for prettier printing


		scripts = project.xray('script', as_list=True)

		snum = meta.pull('max_scripts', 8, silent=True)
		if snum is not None and len(scripts) > snum:
			scripts = scripts[:snum]




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
