from typing import List, Dict, Optional, Union, Any, Sequence, Iterator, NamedTuple
import os
from pathlib import Path
import io
import yaml
from collections import OrderedDict
from omnibelt import Path_Registry, JSONABLE, unspecified_argument, export, load_export, linearize, CycleDetectedError

from ..abstract import AbstractConfig, AbstractProject, AbstractConfigManager
from .nodes import ConfigNode



class ConfigManager(AbstractConfigManager):
	_config_path_delimiter = '/'
	_config_exts = ('yaml', 'yml', 'json', 'tml', 'toml')
	_config_nones = {'None', 'none', '_none', '_None', 'null', 'nil', }
	_config_parent_key = '_base'

	ConfigNode = ConfigNode


	class Config_Registry(Path_Registry, components=['project']):
		'''Registry for config files.'''
		pass


	def __init__(self, project: AbstractProject):
		self.registry = self.Config_Registry()
		self.project = project


	def export(self, config: ConfigNode, name: Union[str, Path], *, root: Optional[Path] = None,
			   fmt: Optional[str] = None) -> Path:
		'''
		Exports the given config to the given path (in yaml format).

		Args:
			config: object to export
			name: of file to export to
			root: directory to export to (if not provided, the current working directory is used)
			fmt: format to export to (if not provided, the extension of the file name is used, and defaults to yaml)

		Returns:
			The path to which the config was exported

		'''
		return export(config, path=name, root=root, fmt=fmt)


	def iterate_configs(self) -> Iterator[NamedTuple]:
		'''
		Iterates over all registered config file entries.

		Returns:
			An iterator over all registered config file entries.

		'''
		yield from self.registry.values()


	def register_config(self, name: Union[str, Path], path: Union[str, Path] = None, **kwargs) -> NamedTuple:
		'''
		Registers a config file with the given name.

		Note:
			It is generally not recommended to register configs manually, but rather to use the ``register_config_dir``
			method to register all configs in a directory at once.

		Args:
			name: to register the config under
			path: of the config file (if not provided, the provided name is assumed to be a path)
			**kwargs: Other arguments to pass to the ``Config_Registry.register`` method

		Returns:
			The entry of the config file that was registered

		'''
		if path is None:
			path = name
			name = None
		if name is None:
			name = Path(path).stem
		return self.registry.new(name, path, **kwargs)


	def register_config_dir(self, root: Union[str, Path], *, recursive: Optional[bool] = True,
	                        prefix: Optional[str] = None, delimiter: Optional[str] = None) -> List[NamedTuple]:
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

		Args:
			root: root directory to search through
			recursive: search recursively through subdirectories for more config yaml files
			prefix: prefix for names of configs found herein
			delimiter: string to merge directories when recursively searching (default ``/``)

		Returns:
			A list of all config entries that were registered.

		'''
		if delimiter is None:
			delimiter = self._config_path_delimiter
		if prefix is None:
			prefix = ''
		root = Path(root)
		entries = []
		for ext in self._config_exts:
			for path in sorted(root.glob(f'**/*.{ext}' if recursive else f'*.{ext}')):
				terms = path.relative_to(root).parts[:-1]
				name = path.stem
				ident = prefix + delimiter.join(terms + (name,))
				entries.append(self.register_config(ident, path, project=self.project))
		return entries

	def _parse_raw_arg(self, arg: str) -> JSONABLE:
		val = yaml.safe_load(io.StringIO(arg))
		if isinstance(val, str) and val in self._config_nones:
			return None
		return val


	class UnknownBehaviorError(ValueError):
		'''While parsing command-line arguments, a meta config was referenced that was not registered'''
		def __init__(self, term):
			super().__init__(f'{term!r} was not recognized (and consequently removed) by any registered Behaviors.')


	def parse_argv(self, argv: Sequence[str], script_name: Optional[str] = unspecified_argument) -> AbstractConfig:
		'''
		Parses command-line arguments and returns a config object that contains the parsed arguments.

		Args:
			argv: raw command-line arguments
			script_name: if not provided, the script name is inferred from ``argv``

		Returns:
			A config object containing the parsed arguments

		Raises:
			UnknownBehaviorError: if an unknown behavior config is encountered
			ValueError: if an argument is invalid

		'''

		meta = {}
		argv = list(argv)

		for behavior in self.project.behaviors():
			out = behavior.parse_argv(meta, argv, script_name=script_name)
			if out is not None:
				argv = out

		configs = []
		data = {}

		remaining = list(reversed(argv))
		if len(remaining):
			# parse script (if provided)
			term = remaining.pop()
			if term.startswith('-') and not term.startswith('--'):
				raise self.UnknownBehaviorError(term)
			elif term.startswith('--'):
				remaining.append(term)
			elif script_name is not unspecified_argument:
				remaining.append(term)
			elif term != '_' and script_name is unspecified_argument:
				script_name = term
			if script_name not in {None, unspecified_argument}:
				meta['script_name'] = script_name

			# parse remaining (keyword) arguments
			while len(remaining):
				term = remaining.pop()

				if term.startswith('--'):
					remaining.append(term)
					break
				else:
					configs.append(term)

			waiting_arg_key = None
			while len(remaining):
				term = remaining.pop()

				if term.startswith('--'):
					if waiting_arg_key is not None:
						data[waiting_arg_key] = True

					key, *other = term[2:].split('=', 1)
					if len(other) and len(other[0]):
						if len(other) > 1:
							raise ValueError(f'Invalid argument {term} (avoid using "=" in argument names)')
						data[key] = self._parse_raw_arg(other[0])
					else:
						waiting_arg_key = key

				elif waiting_arg_key is not None:
					data[waiting_arg_key] = self._parse_raw_arg(term)
					waiting_arg_key = None

				else:
					raise ValueError(f'Unexpected argument: {term}')

			if waiting_arg_key is not None:
				data[waiting_arg_key] = True

		# configurize parsed data (including meta)
		config = self.create_config(configs, data)
		meta = self.create_config(None, meta)
		meta_base = config.push_peek('_meta', {}, silent=True, overwrite=False)
		meta_base.update(meta)
		return config


	def find_local_config_entry(self, name: str, default: Optional[Any] = unspecified_argument) -> NamedTuple:
		'''
		Finds the entry for a config by name.

		Args:
			name: used to register the config
			default: Default value to return if the artifact is not found.

		Returns:
			The entry for the config

		Raises:
			ConfigNotFoundError: if the config is not registered

		'''
		try:
			return self.registry.find(name)
		except self.registry.NotFoundError:
			pass
		if default is not unspecified_argument:
			return default
		raise self.ConfigNotRegistered(name)


	def find_project_config_entry(self, name: str, default: Optional[Any] = unspecified_argument) -> NamedTuple:
		'''
		Finds the entry for a config by name. Including checking the nonlocal projects.

		Args:
			name: of the config file used to register the config
			default: Default value to return if the artifact is not found.

		Returns:
			The entry for the config

		Raises:
			ConfigNotFoundError: if the config is not registered

		'''
		return self.project.find_artifact('config', name, default=default)


	def find_config_path(self, name: str, default: Optional[Any] = unspecified_argument) -> Path:
		'''
		Finds the path to a config file by name. Including checking the nonlocal projects.

		Args:
			name: of the config file used to register the config
			default: Default value to return if the artifact is not found.

		Returns:
			The path to the config file

		Raises:
			ConfigNotFoundError: if the config is not registered

		'''
		if isinstance(name, Path) and name.is_file():
			return name
		elif os.path.isfile(name):
			return Path(name)
		try:
			return self.find_project_config_entry(name).path
		except self.ConfigNotRegistered:
			if default is unspecified_argument:
				raise
			return default


	@classmethod
	def _find_config_parents(cls, path: Optional[Path], raw: Dict[str, Any]) -> List[str]:
		'''
		Finds the base configs of a config file.

		By default, the ``path`` is not used, and instead ``raw`` is checked for a ``_base`` key.

		Args:
			path: of the config file
			raw: loaded data of the config file

		Returns:
			Names of the base configs of the config file (in order)

		'''
		src = []
		if raw is None:
			return src
		if cls._config_parent_key is not None:
			base = raw.get(cls._config_parent_key, [])
			if isinstance(base, str):
				base = [base]
			src.extend(base)
		assert isinstance(src, list), f'Invalid parents: {src}'
		return src


	def _merge_raw_configs(self, raws: List[JSONABLE]) -> AbstractConfig:
		'''
		Merges a list of raw configs into a single config object.

		Args:
			raws: list of raw configs (in order)

		Returns:
			The merged config

		'''
		singles = [self.configurize(raw) for raw in raws]

		if not len(singles):
			return self.ConfigNode.from_raw({})

		merged = singles.pop()
		while len(singles):
			update = singles.pop()
			merged.update(update)

		return merged


	def load_raw_config(self, path: Union[str, Path]) -> JSONABLE:
		'''
		Loads raw data of a config file (formats: JSON, YAML, TOML).

		Args:
			path: to the config file

		Returns:
			The raw data of the config file

		Raises:
			ValueError: if the config file is not a valid format

		'''
		if path.suffix.endswith('.yml') or path.suffix.endswith('.yaml'):
			# return load_yaml(path, ordered=True)
			return load_export(path=path, fmt='yaml', ordered=True)
		elif path.suffix == '.json':
			# return load_json(path)
			return load_export(path=path, fmt='json')
		elif path.suffix in ('.toml', '.tml'):
			# return toml.load(path, _dict=OrderedDict)
			return load_export(path=path, fmt='toml', _dict=OrderedDict)
		raise ValueError(f'Unknown config file type: {path}')


	class ConfigCycleError(ValueError):
		'''
		Indicates that a cycle in the config bases was detected.
		'''
		def __init__(self, bad: List[str]):
			super().__init__(f'Config cycle detected within: {", ".join(bad)}')


	def create_config(self, configs: Optional[Sequence[Union[str, Path]]] = None, data: Optional[JSONABLE] = None, *,
	                  project: Optional[AbstractProject] = unspecified_argument) -> AbstractConfig:
		'''
		Creates a config object from a list of configs and raw data.

		Args:
			configs: names of registered configs or paths to config files to load
			data: raw data to merge into the config (e.g. from command line arguments)
			project: to associate the resulting config with

		Returns:
			The config object

		Raises:
			ConfigNotFoundError: if a requested config is not registered

		'''
		if configs is None:
			configs = []
		if data is None:
			data = {}
		if project is unspecified_argument:
			project = self.project
		assert len(self._find_config_parents(None, data)) == 0, 'Passed in args cannot have a parents key'

		ancestry_names = {}
		parent_table = {None: configs}
		raws = {None: data}
		used_paths = {}

		todo = list(configs)
		while len(todo):
			name = todo.pop()
			path = self.find_config_path(name)
			if path not in raws:
				if not path.exists():
					raise FileNotFoundError(path)
				used_paths[name] = path
				raws[path] = self.load_raw_config(path)
				if raws[path] is None:
					raws[path] = {}
				ancestry_names[path] = name
				parent_table[path] = self._find_config_parents(path, raws[path])
				todo.extend(parent_table[path])

		if len(used_paths) != len(todo):
			graph = {key: [used_paths[name] for name in srcs] for key, srcs in parent_table.items()}

			try:
				order = linearize(graph)[None]
			except CycleDetectedError as c:
				bad = c.remaining
				del bad[None]
				used_names = {path: name for name, path in used_paths.items()}
				bad = [used_names[path] for path in bad]
				raise self.ConfigCycleError(sorted(bad))

			ancestry = [ancestry_names[p] for p in order[1:]]
			order = [data] + [raws[p] for p in order[1:]]
		else:
			order = [data]
			ancestry = []

		merged = self._merge_raw_configs(order)

		merged._cro = tuple(map(str,ancestry))
		merged._bases = tuple(map(str,configs))

		if project is not None:
			merged.project = project
		merged.settings = merged.pull('_meta.settings', {}, silent=True)

		merged.validate()
		merged.manager = self
		return merged


	def configurize(self, raw: JSONABLE, **kwargs: Any) -> AbstractConfig:
		'''
		Converts raw data into a config object (using the config class of this manager ``ConfigNode``).

		Args:
			raw: python data structure to convert (e.g. from a JSON or YAML file)
			**kwargs: additional arguments to pass to the config class constructor

		Returns:
			The config object

		'''
		return self.ConfigNode.from_raw(raw, **kwargs)


	def merge_configs(self, *configs: AbstractConfig) -> AbstractConfig:
		'''
		Given a list of config objects, merges them into a single config object in the given order.

		Args:
			*configs: objects to merge

		Returns:
			The merged config object

		'''
		merged = self.create_config()
		
		todo = list(configs)
		while len(todo):
			self.update_config(merged, todo.pop())
		return merged


	@staticmethod
	def update_config(base: AbstractConfig, update: AbstractConfig) -> AbstractConfig:
		'''
		Updates a config object with the contents of another config object.

		Args:
			base: config object to update
			update: config object to merge into the base

		Returns:
			The updated config object

		'''
		return base.update(update)
		







