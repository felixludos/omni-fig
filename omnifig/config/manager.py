from typing import List, Dict, Tuple, Optional, Union, Any, Hashable, Sequence, Callable, Generator, Type, Iterable, \
	Iterator, NamedTuple
from pathlib import Path
import io
import yaml
import toml
from collections import OrderedDict
from c3linearize import linearize
from omnibelt import Path_Registry, load_yaml, JSONABLE, unspecified_argument, load_json
from omnibelt.nodes import LocalNode

from ..abstract import AbstractConfig, AbstractProject, AbstractConfigManager
from .nodes import ConfigNode


_PathEntry = NamedTuple('_PathEntry', [('name', str), ('path', Path)])

class ConfigManager(AbstractConfigManager):
	_config_path_delimiter = '/'
	_config_exts = ('yaml', 'yml', 'json', 'tml', 'toml')
	_config_nones = {'None', 'none', '_none', '_None', 'null', 'nil', }

	ConfigNode = ConfigNode

	Config_Registry = Path_Registry

	def __init__(self, project: AbstractProject):
		self.registry = Path_Registry()
		self.project = project

	def iterate_configs(self) -> Iterator[NamedTuple]:
		return self.registry.values()

	def register_config(self, name: str, path: Union[str, Path], **kwargs) -> NamedTuple:
		return self.registry.new(name, path, **kwargs)

	def register_config_dir(self, root: Union[str, Path], recursive=True, prefix=None, delimiter=None) \
			-> List[NamedTuple]:
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

		:param path: path to root directory to search through
		:param recursive: search recursively through sub-directories for more config yaml files
		:param prefix: prefix for names of configs found herein
		:param joiner: string to merge directories when recursively searching (default ``/``)
		:return: None
		'''
		if delimiter is None:
			delimiter = self._config_path_delimiter
		if prefix is None:
			prefix = ''
		root = Path(root)
		entries = []
		for ext in self._config_exts:
			for path in root.glob(f'**/*.{ext}' if recursive else f'*.{ext}'):
				terms = path.relative_to(root).parts[:-1]
				name = path.stem
				ident = prefix + delimiter.join(terms + (name,))
				entries.append(self.register_config(ident, path))
		return entries

	def _parse_raw_arg(self, arg: str) -> JSONABLE:
		val = yaml.safe_load(io.StringIO(arg))
		if isinstance(val, str) and val in self._config_nones:
			return None
		return val

	# try:
	# 	if isinstance(mode, str):
	# 		if mode == 'yaml':
	# 			return yaml.safe_load(io.StringIO(arg))
	# 		elif mode == 'python':
	# 			return eval(arg, {}, {})
	# 		else:
	# 			pass
	# 	else:
	# 		return mode(arg)
	# except:
	# 	pass
	# return arg

	class AmbiguousRuleError(Exception):
		pass

	class UnknownMetaError(ValueError):
		pass

	def parse_argv(self, argv: Sequence[str], script_name: Optional[str] = unspecified_argument) -> AbstractConfig:
		waiting_key = None
		waiting_meta = 0

		remaining = list(reversed(argv))
		
		meta = {}
		while len(remaining):
			term = remaining.pop()

			if waiting_meta > 0:
				val = self._parse_raw_arg(term)
				if waiting_key in meta and isinstance(meta[waiting_key], list):
					meta[waiting_key].append(val)
				else:
					meta[waiting_key] = val
				waiting_meta -= 1
				if waiting_meta == 0:
					waiting_key = None

			elif term.startswith('-') and not term.startswith('--'):
				text = term[1:]
				while len(text) > 0:
					for rule in self.project.iterate_meta_rules():
						name = rule.name
						code = rule.code
						if code is not None and text.startswith(code):
							text = text[len(code):]
							num = rule.num_args
							if num:
								if len(text):
									raise self.AmbiguousRuleError(code, text)
								waiting_key = name
								waiting_meta = num
								if num > 1:
									meta[waiting_key] = []
							else:
								meta[name] = True
						if not len(text):
							break
					else:
						raise self.UnknownMetaError(text)

			elif script_name is not unspecified_argument:
				remaining.append(term)
				break

			elif term != '_' and script_name is unspecified_argument:
				script_name = term
				
			else:
				break

		if script_name not in {None, unspecified_argument}:
			meta['script_name'] = script_name

		configs = []
		while len(remaining):
			term = remaining.pop()
			
			if term.startswith('--'):
				remaining.append(term)
				break
			else:
				configs.append(term)

		waiting_arg_key = None
		data = {}
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

		if '_meta' in data:
			data['_meta'].update(meta)
		else:
			data['_meta'] = meta

		return self.create_config(configs, data)

	def find_config_path(self, name: str) -> Path:
		# if name not in self.registry:
		# 	raise ValueError(f'Unknown config: {name}')
		return self.find_config_entry(name).path

	class ConfigNotRegistered(KeyError): pass

	def find_config_entry(self, name: str) -> AbstractConfig:
		try:
			return self.registry.find(name)
		except self.registry.NotFoundError:
			pass
		raise self.ConfigNotRegistered(name)

	_config_parents_key = '_src'

	@classmethod
	def _find_config_parents(cls, path: Optional[Path], raw: Dict[str, Any]) -> List[str]:
		src = raw.get(cls._config_parents_key, [])
		if isinstance(src, str):
			src = [src]
		assert isinstance(src, list), f'Invalid parents: {src}'
		return src

	def _merge_raw_configs(self, raws: List[JSONABLE]) -> AbstractConfig:
		singles = [self.configurize(raw) for raw in raws]

		if not len(singles):
			return self.ConfigNode.from_raw({})

		merged = singles.pop()
		while len(singles):
			update = singles.pop()
			merged.update(update)

		return merged

	# def _unify_config_node(self, node):
	# 	for child in node.children():
	# 		child.parent = node
	# 		child.reporter = node.reporter
	# 		self._unify_config_node(child)

	def _process_full_config(self, config):
		# self._unify_config_node(config)
		pass

	def _load_raw_config(self, path: Path) -> JSONABLE:
		return load_yaml(path, ordered=True)

	def create_config(self, configs: Optional[Sequence[str]] = None, data: Optional[JSONABLE] = None, *,
	                  project: Optional[AbstractProject] = unspecified_argument) -> AbstractConfig:
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
		# data[self._config_parents_key] = list(configs)
		while len(todo):
			name = todo.pop()
			path = self.find_config_path(name)
			if path not in raws:
				if not path.exists():
					raise FileNotFoundError(path)
				used_paths[name] = path
				raws[path] = self._load_raw_config(path)
				ancestry_names[path] = name
				parent_table[path] = self._find_config_parents(path, raws[path])
				todo.extend(parent_table[path])

		if len(used_paths) != len(todo):
			graph = {key: [used_paths[name] for name in srcs] for key, srcs in parent_table.items()}
			order = linearize(graph, heads=[None], order=True)[None]
			ancestry = [ancestry_names[p] for p in order[1:]]
			order = [data] + [raws[p] for p in order[1:]]
			# order = list(reversed(order))
		else:
			order = [data]
			ancestry = []

		# if ancestry_key is not None:
		# 	ancestors = [raw.get(ancestry_key, None) for raw in order[1:]]

		merged = self._merge_raw_configs(order)

		merged._composition = tuple(ancestry)
		merged._sources = tuple(configs)

		if project is not None:
			merged.project = project
		merged.settings = merged.pull('_meta.settings', {}, silent=True)

		merged.validate()
		return merged
	
	def load_raw_config(self, path: Union[str, Path]) -> JSONABLE:
		if path.suffix in ('.yaml', '.yml'):
			return load_yaml(path, ordered=True)
		elif path.suffix == '.json':
			return load_json(path)
		elif path.suffix in ('.toml', '.tml'):
			return toml.load(path, _dict=OrderedDict)
		raise ValueError(f'Unknown config file type: {path}')

	def _configurize(self, raw: JSONABLE, parent: Optional[ConfigNode] = None, **kwargs) -> AbstractConfig:
		return self.ConfigNode.from_raw(raw, parent=parent, **kwargs)
		# if isinstance(raw, LocalNode):
		# 	raw.parent = parent
		# 	return raw
		# if isinstance(raw, dict):
		# 	node = self.ConfigNode.SparseNode(parent=parent, **kwargs)
		# 	for key, value in raw.items():
		# 		if key in node:
		# 			node.get(key).update(self._configurize(value, parent=node, **kwargs))
		# 		else:
		# 			node.set(key, self._configurize(value, parent=node, **kwargs), **kwargs)
		# elif isinstance(raw, (tuple, list)):
		# 	node = self.ConfigNode.DenseNode(parent=parent, **kwargs)
		# 	for idx, value in enumerate(raw):
		# 		idx = str(idx)
		# 		node.set(idx, self._configurize(value, parent=node, **kwargs), **kwargs)
		# else:
		# 	node = self.ConfigNode.DefaultNode(payload=raw, parent=parent, **kwargs)
		# return node
		
	def configurize(self, raw: JSONABLE):
		return self._configurize(raw)
	
	def merge_configs(self, *configs: AbstractConfig) -> AbstractConfig:
		merged = self.create_config()
		
		todo = list(configs)
		while len(todo):
			self.update_config(merged, todo.pop())
		return merged
	
	@staticmethod
	def update_config(base: AbstractConfig, update: AbstractConfig, *, clear_product=True) -> AbstractConfig:
		return base.update(update)
		






















