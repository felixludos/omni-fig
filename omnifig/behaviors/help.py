from typing import Optional, Iterator, NamedTuple, List
import sys
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
		'''Formats a script entry for printing help message.'''
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
Usage: {usage}
	
This will run the script: {script} {script_info}
	
{doc}

You can additionally specify the following:'''


	@classmethod
	def format_selected_script(cls, config: AbstractConfig, entry: Optional[NamedTuple], verbose: bool = False) -> str:
		'''Formats the help message about the selected script.'''
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
				info['script_info'] = f'(found in {name})'

			info['usage'] = cls._format_usage(entry.name)

			return {'header': cls._script_title.format(**info)}


	@classmethod
	def format_scripts(cls, config: AbstractConfig, entries: Iterator[NamedTuple], verbose: bool = False) -> str:
		'''Formats the help message about the available scripts.'''
		rows = [cls._format_script_entry(s, verbose=verbose) for s in entries]

		if not len(rows):
			return '  -- No scripts registered --'

		cols = ['code', 'name' if verbose else 'module', 'description']
		if verbose:
			cols.insert(2, 'project')

		return tabulate(rows, headers=cols, tablefmt='simple')


	@staticmethod
	def _format_behavior_entry(entry: NamedTuple, verbose: bool = False) -> List[str]:
		'''Formats a behavior entry for printing help message.'''
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
		'''Formats the help message about the available behaviors.'''
		rows = [cls._format_behavior_entry(entry, verbose=verbose) for entry in entries]

		if len(rows) == 0:
			return '  -- No configs registered --'

		cols = ['code', 'name', 'description']
		if verbose:
			cols.insert(2, 'class')
		table = tabulate(rows, headers=cols, tablefmt='simple')
		return table


	@staticmethod
	def format_configs(config: AbstractConfig, entries: Iterator[NamedTuple], verbose: bool = False) -> str:
		'''Formats the help message about the available configs.'''
		names = [f'{e.name}' for e in entries]
		terms = [f'Config{"" if len(names) == 1 else "s"} ({len(names)}){":" if len(names) else ""}',
		         ', '.join(sorted(names))]
		if len(names) == 0:
			terms.clear()
			terms.append('  -- No configs registered --')

		return ' '.join(terms)


	_blank_title = '''
Usage: {usage}

+--------+
| script |
+--------+
Specify a registered script name to run

{scripts}'''


	_msg_template = '''{header}

+------+
| meta |
+------+
Optional meta behaviors to modify the execution 
(must be specified separately e.g. "-a -b")

{behaviors}

+---------+
| configs |
+---------+
Specify any registered config files or paths to YAML files 
to compose and pass to the script

{configs}

+------+
| args |
+------+
Any additional arguments specified manually
as key-value pairs (either as "--key value" or "--key=value")

Current project: {project}'''

	_default_usage = 'fig [-<meta>] <script> [<configs>...] [--<args>]'


	@classmethod
	def _format_usage(cls, name: Optional[str] = None):
		raw = sys.argv

		terms = ['fig' if len(raw) == 0 or raw[0].endswith('fig') else f'python {raw[0]}']

		if name in raw:
			terms.append(name)

		terms.append(
			'[-<meta>] <script> [<configs>...] [--<args>]' if name is None else '[-<meta>] [<configs>...] [--<args>]'
		)

		return colorize(' '.join(terms), 'magenta')


	@classmethod
	def pre_run(cls, meta: AbstractConfig, config: AbstractConfig) -> None:
		'''
		When activated, this behavior prints the help message for the current project (and then exits the program).

		Args:
			meta: The meta config object (used to check if the behavior is activated with the ``quiet`` key)
			config: The config object to be modified

		Returns:
			``None``

		Raises:
			:exc:`TerminationFlag`: if the rule is activated, to prevent the script from running

		'''

		with config.silence():
			verbose = config.pull('verbose', False)
			name = meta.pull('script_name', None)

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

		if 'header' not in msg_info:

			scripts = cls.format_scripts(config, project.xray('script', as_list=True), verbose=verbose)

			msg_info['header'] = cls._blank_title.format(scripts=scripts, usage=cls._format_usage(name))


		print(cls._msg_template.format(**msg_info))

		raise cls.TerminationFlag
