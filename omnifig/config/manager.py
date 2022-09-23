from typing import List, Dict, Tuple, Optional, Union, Any, Hashable, Sequence, Callable, Generator, Type, Iterable, \
	Iterator, NamedTuple
from pathlib import Path
import io
import yaml
from c3linearize import linearize
from omnibelt import Path_Registry, load_yaml, JSONABLE

from ..abstract import AbstractConfig, AbstractProject, AbstractConfigManager
from .nodes import ConfigNode


_PathEntry = NamedTuple('_PathEntry', [('name', str), ('path', Path)])

class ConfigManager(AbstractConfigManager):
	_config_path_delimiter = '/'
	_config_exts = ('yaml', 'yml')
	_config_nones = {'None', 'none', '_none', '_None', 'null', 'nil', }

	ConfigNode = ConfigNode

	Config_Registry = Path_Registry

	def __init__(self, project: AbstractProject):
		self.registry = Path_Registry()
		self.project = project

	def register_config(self, name: str, path: Union[str, Path], **kwargs) -> None:
		self.registry.new(name, path, **kwargs)

	def register_config_dir(self, root: Union[str, Path], recursive=True, prefix=None, delimiter=None) -> None:
		if delimiter is None:
			delimiter = self._config_path_delimiter
		if prefix is None:
			prefix = ''
		root = Path(root)
		for ext in self._config_exts:
			for path in root.glob(f'**/*.{ext}' if recursive else f'*.{ext}'):
				terms = path.relative_to(root).parts[:-1]
				name = path.stem
				ident = prefix + delimiter.join(terms + (name,))
				self.register_config(ident, path)

	def _parse_raw_arg(self, arg: str) -> JSONABLE:
		val = yaml.safe_load(io.StringIO(arg))
		if val in self._config_nones:
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

	def parse_argv(self, argv: Sequence[str], script_name: Optional[str] = None) -> AbstractConfig:
		meta = {}

		waiting_key = None
		waiting_meta = 0

		remaining = []
		for i, arg in enumerate(argv):

			if waiting_meta > 0:
				val = self._parse_raw_arg(arg)
				if waiting_key in meta and isinstance(meta[waiting_key], list):
					meta[waiting_key].append(val)
				else:
					meta[waiting_key] = val
				waiting_meta -= 1
				if waiting_meta == 0:
					waiting_key = None

			elif arg.startswith('-') and not arg.startswith('--'):
				text = arg[1:]
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

			elif arg == '_' or script_name is not None:
				remaining = argv[i + int(script_name is None):]
				break

			elif script_name is None:
				script_name = arg

		if script_name is not None:
			meta['script_name'] = script_name

		configs = []
		for i, term in enumerate(remaining):
			if term.startswith('--'):
				remaining = remaining[i:]
			else:
				configs.append(term)

		waiting_arg_key = None
		data = {}

		for arg in remaining:
			if arg.startswith('--'):
				if waiting_arg_key is not None:
					data[waiting_arg_key] = True

				key, *other = arg[2:].split('=', 1)
				if len(other) and len(other[0]):
					data[key] = self._parse_raw_arg(other[0])
				else:
					waiting_arg_key = key

			elif waiting_arg_key is not None:
				data[waiting_arg_key] = self._parse_raw_arg(arg)
				waiting_arg_key = None

			else:
				raise ValueError(f'Unexpected argument: {arg}')

		if waiting_arg_key is not None:
			data[waiting_arg_key] = True

		if '_meta' in data:
			data['_meta'].update(meta)
		else:
			data['_meta'] = meta

		# create config with remaining argv
		return self.create_config(configs, data)

	def find_config_path(self, name: str) -> Path:
		# if name not in self.registry:
		# 	raise ValueError(f'Unknown config: {name}')
		return self.registry.get_path(name)

	@staticmethod
	def _find_config_parents(raw: Dict[str, Any]) -> List[str]:
		return raw.get('parents', [])

	def _configurize(self, raw: JSONABLE) -> AbstractConfig:
		return self.ConfigNode.from_raw(raw)

	def _merge_raw_configs(self, raws: List[JSONABLE]) -> AbstractConfig:
		singles = [self._configurize(raw) for raw in raws]

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

	def create_config(self, configs: Optional[Sequence[str]] = None, data: Optional[JSONABLE] = None) -> AbstractConfig:
		if configs is None:
			configs = []
		if data is None:
			data = {}
		assert len(self._find_config_parents(data)) == 0, 'Passed in args cannot have a parents key'
		todo = list(configs)
		data['parents'] = list(configs)
		raws = {None: data}
		used_paths = {}
		while len(todo):
			name = todo.pop()
			path = self.find_config_path(name)
			if path not in raws:
				if not path.exists():
					raise FileNotFoundError(path)
				raws[path] = load_yaml(path)
				todo.extend(self._find_config_parents(raws[path]))
				used_paths[name] = path
		if len(used_paths) != len(todo):
			graph = {key: [used_paths[name] for name in self._find_config_parents(raw)] for key, raw in raws.items()}
			graph[None] = [used_paths[name] for name in data['parents']]
			order = linearize(graph, heads=[None], order=True)[None]
			order = [data] + [raws[p] for p in order[1:]]
			order = list(reversed(order))
		else:
			order = [data]

		merged = self._merge_raw_configs(order)

		merged.settings = merged.pull('_meta.settings', {}, silent=True)
		return merged
























