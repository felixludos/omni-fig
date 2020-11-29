
import sys, os
from pathlib import Path
from collections import defaultdict, OrderedDict
from c3linearize import linearize

from omnibelt import get_printer, load_yaml

from .containers import Container
from .rules import view_meta_rules, meta_rule_fns
from .errors import UnknownArtifactError, artifact_errors, MissingModifierError, AmbiguousRuleError, \
	MissingConfigError, MissingArtifactError
from .registry import Script_Registry, Component_Registry, Modifier_Registry, Config_Registry
from .external import include_files, include_package
from .util import global_settings, configurize, parse_arg

prt = get_printer(__name__)

class Workspace(Container):
	
	def __init__(self, silent=False, **kwargs):
		super().__init__(**kwargs)
		self.silent = silent
		
		self.reset_registries()
	
	def _process(self, raw):
		
		self.config_paths = raw.get('configs', [])
		if isinstance(self.config_paths, str):
			self.config_paths = [self.config_paths]
		self.src_paths = raw.get('src', [])
		if isinstance(self.src_paths, str):
			self.src_paths = [self.src_paths]
		self.src_packages = raw.get('packages', [])
		if isinstance(self.src_packages, str):
			self.src_packages = [self.src_packages]
		
		super()._process(raw)
	
	def initialize(self):
		'''
		This loads the project, primarily by registering any specified config files,
		importing specified packages, and finally running any provided source files

		:return: None
		'''
		
		self.load_configs(self.config_paths)
		self.load_src(self.src_paths, self.src_packages)
	
	def load_configs(self, paths=[]):
		'''Registers all specified config files and directories'''
		if len(paths):
			
			for path in paths:
				if os.path.isdir(path):
					self.register_config_dir(path, recursive=True)
				elif os.path.isfile(path):
					fname = os.path.basename(path)
					parts = fname.split('.')
					if len(parts) > 1 and parts[-1] in {'yml', 'yaml'}:
						self.register_config(parts[0], path)
	
	def load_src(self, srcs=[], packages=[]):
		'''Imports all specified packages and runs the specified python files'''
		include_package(*packages)
		include_files(*[src for src in srcs])

	def meta_rules(self):
		return view_meta_rules()

	def meta_rules_fns(self):
		return meta_rule_fns()
	
	# region Registration
	
	def reset_registries(self):
		if not self.silent:
			prt.debug(f'Resetting registries of {self}')
		self.scripts = Script_Registry()
		self.components = Component_Registry()
		self.modifiers = Modifier_Registry()
		self.configs = Config_Registry()
		
		self._registries = dict(script=self.scripts, component=self.components,
		                        modifier=self.modifiers, config=self.configs)
	
	def register_artifact(self, atype, name, info):
		
		registry = self._registries.get(atype, None)
		if registry is None:
			raise UnknownArtifactError(atype)
		
		if not self.silent:
			msg_name = name if atype is None else f'{atype} {name}'
			if name in registry:
				prt.warning(f'A {msg_name} has already been registered in {self}, now overwriting')
			else:
				prt.debug(f'Registering {msg_name} in {self}')
		
		registry.new(name, **info)
	
	def register_script(self, name, fn, description=None, use_config=False):
		'''
		Function to register a script

		:param name: name of script
		:param fn: script function (usually a callable that expects the config object)
		:param use_config: :code:`True` if the config should be passed as only arg when calling the script function, otherise it will automatically pull all arguments in the script function signature
		:param description: a short description of what the script does
		:return:
		'''
		self.register_artifact('script', name, info=dict(fn=fn, description=description,
		                                                 use_config=use_config, project=self))
	
	def register_component(self, name, fn, description=None):
		'''
		`fn` takes a single input - a Config object
		The config object is guaranteed to have at least one entry with key "_type" and the value is the same as
		the registered name of the component.

		:param name: str (should be unique)
		:param fn: callable accepting one arg (a Config object) (these should usually be classes)
		:param description: description of what this component is about
		'''
		self.register_artifact('component', name, info=dict(fn=fn, description=description,
		                                                    project=self))
	
	def register_modifier(self, name, fn, description=None, expects_config=False):
		'''
		`fn` takes as input a component and a Config object.

		:param name: str (should be unique)
		:param fn: callable accepting one arg (the "create_fn" of a registered component) (these should usually be classes)
		:param description: description of what this modifier is about
		'''
		self.register_artifact('modifier', name, info=dict(fn=fn, description=description,
		                                                   expects_config=expects_config, project=self))
	
	def register_config(self, name, path):
		'''
		Register a file as a named config

		:param name: str (should be unique)
		:param path: full path to the config
		'''
		self.register_artifact('config', name, info=dict(path=path, project=self))
	
	def register_config_dir(self, path, recursive=False, prefix=None, joiner='/'):
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
		assert os.path.isdir(path), f'invalid dir: {path}'
		for fname in os.listdir(path):
			parts = fname.split('.')
			candidate = os.path.join(path, fname)
			if os.path.isfile(candidate) and len(parts) > 1 and parts[-1] in {'yml', 'yaml'}:
				name = parts[0]
				if prefix is not None:
					name = joiner.join([prefix, name])
				self.register_config(name, os.path.join(path, fname))
			elif recursive and os.path.isdir(candidate):
				newprefix = fname if prefix is None else joiner.join([prefix, fname])
				self.register_config_dir(candidate, recursive=recursive, prefix=newprefix, joiner=joiner)
	
	# endregion
	
	# region Artifacts
	
	def has_artifact(self, atype, name):
		registry = self._registries.get(atype, None)
		if registry is None:
			raise UnknownArtifactError(atype)
		return name in registry
	
	def find_artifact(self, atype, name):
		
		registry = self._registries.get(atype, None)
		if registry is None:
			raise UnknownArtifactError(atype)
		
		artifact = registry.get(name, None)
		if artifact is None:
			assert atype in artifact_errors, f'Missing error for {atype}'
			raise artifact_errors[atype](name)
		
		return artifact
	
	def has_script(self, name):
		return self.has_artifact('script', name)
	def find_script(self, name):
		return self.find_artifact('script', name)
	def view_scripts(self):
		return self.scripts.copy()
	
	def has_component(self, name):
		return self.has_artifact('component', name)
	def find_component(self, name):
		return self.find_artifact('component', name)
	def view_components(self):
		return self.components.copy()
	
	def has_modifier(self, name):
		return self.has_artifact('modifier', name)
	def find_modifier(self, name):
		return self.find_artifact('modifier', name)
	def view_modifiers(self):
		return self.modifiers.copy()
	
	def has_config(self, name):
		if self.has_artifact('config', name):
			return True
		path = Path(name)
		return path.suffix in {'.yaml', '.yml'} and path.is_file()
	def find_config(self, name):
		try:
			entry = self.find_artifact('config', name)
		except MissingConfigError:
			path = Path(name)
			if path.suffix in {'.yaml', '.yml'} and path.is_file():
				return str(path)
			raise
		return entry.path
	def view_configs(self):
		return self.configs.copy()
	
	# endregion
	
	# region Create/Run
	
	def run(self, script_name=None, config=None, **meta_args):
		'''
		This actually runs the script given the ``config`` object.

		Before starting the script, all meta rules are executed in order of priority (low to high)
		as they may change the config or script behavior, then the run mode is created, which is
		then called to execute the script specified in the config object (or manually overridden
		using ``script_name``)

		:param script_name: registered script name to run (overrides what is specified in ``config``)
		:param config: config object (usually created with :func:`get_config()` (see :ref:`config:Config System`)
		:param meta_args: Any additional meta arguments to include before running
		:return: script output
		'''
		if config is None:
			config = self.create_config()
		else:
			config.set_project(self)
		
		if script_name is not None:
			config.push('_meta.script_name', script_name, overwrite=True, silent=True)
		for k, v in meta_args.items():
			config.push(f'_meta.{k}', v, overwrite=True, silent=True)
		# config._meta.update(meta_args)
		
		for rule in self.meta_rules_fns():
			config = rule(config.sub('_meta'), config)
		
		config.push('_meta._type', 'run_mode/default', overwrite=False, silent=True)
		silent = config.pull('_meta._quiet_run_mode', True, silent=True)
		mode = config.pull('_meta', silent=silent)
		# config = mode.process(config)
		
		return mode.run(config.sub('_meta'), config)
	
	def create_component(self, info):
		'''
		Creates the component specified in info (checks component registry using info.pull('_type'),
		and modifier registry for info.pull('_mod'))

		_mod can be a list, in which case they will be applied in the given order, eg:

		let mods = [A, B, C]

		component <- C(B(A(component)))

		_mod can also be a dict, in which case the keys should be the mod names and the values the order (low to high).
		So for the same behavior as above, a _mod could also be {A:0, B:1, C:2}

		NOTE: generally, modifiers should be ordered from more specific to more general

		:param info: should be a config object with attribute "_type" (and optionally "_mod")
		:return: component created using the provided config (``info``)
		'''
		
		name = info.pull('_type', silent=True)
		
		component = self.find_component(name).fn
		
		allow_missing_mods = info.pull('allow-missing-mods', False, silent=True)
		
		mod_names = info.pull('_mod', None, silent=True)
		if mod_names is not None:
			
			if isinstance(mod_names, dict):
				mod_names = sorted(mod_names.keys(), key=lambda k: mod_names[k])
			
			if not isinstance(mod_names, (list, tuple)):
				mod_names = mod_names,
			
			for mod_name in mod_names:  # WARNING: apply modifications in reverse order
				
				try:
					mod = self.find_modifier(mod_name)
				except MissingModifierError:
					if allow_missing_mods:
						prt.error(f'Could not find mod "{mod_name}" for component "{name}"')
						continue
					else:
						raise
				component = mod.fn(component, info) if mod.expects_config else mod.fn(component)
		
		return component(info)
	
	# endregion
	
	# region Config
	
	def process_argv(self, argv=(), script_name=None):
		'''
		Parses the command line arguments to identify the meta arguments, script name
		(optionally overridden using ``script_name``), and config args

		From that, this builds the config and meta config object.

		:param argv: list of all command line arguments to parse in order
		:param script_name: optional script name to override any script specified in ``argv``
		:return: config object (containing meta config under ``_meta``)
		'''
		
		# check for meta args and script name
		
		meta = {}
		
		waiting_key = None
		waiting_meta = 0
		
		remaining = []
		for i, arg in enumerate(argv):
			
			if waiting_meta > 0:
				if waiting_key in meta and isinstance(meta[waiting_key], list):
					meta[waiting_key].append(parse_arg(arg))
				else:
					meta[waiting_key] = parse_arg(arg)
				waiting_meta -= 1
				if waiting_meta == 0:
					waiting_key = None
			
			elif arg.startswith('-') and not arg.startswith('--'):
				text = arg[1:]
				for rule in self.meta_rules():
					name = rule.name
					code = rule.code
					if code is not None and text.startswith(code):
						text = text[len(code):]
						num = rule.num_args
						if num:
							if len(text):
								raise AmbiguousRuleError(code, text)
							waiting_key = name
							waiting_meta = num
							if num > 1:
								meta[waiting_key] = []
						else:
							meta[name] = True
					if not len(text):
						break
			
			elif arg == '_' or script_name is not None:
				remaining = argv[i + int(script_name is None):]
				break
			
			else:
				script_name = arg
		
		if script_name is not None:
			meta['script_name'] = script_name
		
		# create config with remaining argv
		config = self.create_config(*remaining)
		config.sub('_meta').update(meta)
		
		return config
	
	def _load_config_from_path(self, path, process=True):
		'''
		Load the yaml file and transform data to a config object

		Generally, ``get_config`` should be used instead of this method

		:param path: must be the full path to a yaml file
		:param process: if False, the loaded yaml data is passed without converting to a config object
		:return: loaded data from path (usually as a config object)
		'''
		# path = find_config_path(path)
		data = load_yaml(path)  # TODO setup global enable other file types
		
		if data is None:
			data = {}
		
		if process:
			return configurize(data)
		return data
	
	def _merge_configs(self, configs, parent_defaults=True):
		'''
		configs should be ordered from oldest to newest (ie. parents first, children last)

		This is an internal method used by ``get_config()`` and should generally not be called manually.
		'''
		
		if not len(configs):
			return self.create_config()
		
		child = configs.pop()
		merged = self._merge_configs(configs, parent_defaults=parent_defaults)
		
		# load = child.load if 'load' in child else None
		merged.update(child)
		
		return merged
	
	def _process_single_config(self, data, process=True, parents=None):
		'''
		This loads the data (if a path or name is provided) and then checks for parents and loads those as well

		Generally, ``get_config`` should be used instead of this method

		:param data: config name or path or raw data (dict/list) or config object
		:param process: configurize loaded data
		:param parents: if None, no parents are loaded, otherwise it must be a dict where the keys are the absolute paths to the config (yaml) file and values are the loaded data
		:return: loaded data (as a config object or raw)
		'''
		
		if isinstance(data, str):
			data = self.find_config(data)
			data = self._load_config_from_path(data, process=process)
		
		if parents is not None and 'parents' in data:
			todo = []
			for parent in data['parents']:  # prep new parents
				# ppath = _config_registry[parent] if parent in _config_registry else parent
				ppath = self.find_config(parent)
				if ppath not in parents:
					todo.append(ppath)
					parents[ppath] = None
			for ppath in todo:  # load parents
				parents[ppath] = self._process_single_config(ppath, parents=parents)
		
		return data
	
	def create_config(self, *contents, **parameters):  # Top level function
		'''
		Top level function for users. This is the best way to load/create a config object.

		All parent config (registered names or paths) that should be loaded
		must precede any manual entries, and will be loaded in reverse order (like python class inheritance).

		If the key ``_history_key`` is specified and not :code:`None`, a flattened list of all parents of
		this config is pushed to the given key.

		:param contents: registered configs or paths or manual entries (like in terminal)
		:param parameters: specify parameters manually as key value pairs
		:return: config object
		'''
		root = configurize({})
		if len(contents) + len(parameters) == 0:
			root.set_project(self)
			return root
		
		reg = []
		terms = {**parameters}
		allow_reg = True
		waiting_key = None
		
		for term in contents:
			
			if term.startswith('--'):
				allow_reg = False
				if waiting_key is not None:
					terms[waiting_key] = True
				waiting_key = term[2:]
			
			elif waiting_key is not None:
				terms[waiting_key] = parse_arg(term)
				waiting_key = None
			
			elif allow_reg:
				reg.append(term)
			
			else:
				raise Exception(f'Parsing error: {term} in {contents}')
		
		if waiting_key is not None:
			terms[waiting_key] = True
		
		root.update(configurize(terms))
		
		if len(reg) == 0:
			root.set_project(self)
		
			return root
		
		root['parents'] = configurize(data=reg + (list(root['parents']) if 'parents' in root else []))
		
		parents = {}
		
		root = self._process_single_config(root, parents=parents)
		
		pnames = []
		if len(parents):  # topo sort parents
			
			# TODO: maybe clean up?
			
			root_id = ' root'
			src = defaultdict(list)
			
			names = {self.find_config(p): p for p in root['parents']} if 'parents' in root else {}
			src[root_id] = list(names.keys())
			
			for n, data in parents.items():
				connections = {self.find_config(p): p for p in data['parents']} if 'parents' in data else {}
				names.update(connections)
				src[n] = list(connections.keys())
			
			order = linearize(src, heads=[root_id], order=True)[root_id]
			
			pnames = [names[p] for p in order[1:]]
			order = [root] + [parents[p] for p in order[1:]]
			
			# for analysis, record the history of all loaded parents
			order = list(reversed(order))
		
		else:  # TODO: clean up
			order = [root]
		
		root = self._merge_configs(order, )
		root.set_project(self)
		
		include_history = root.pull('_history_key', None, silent=True)
		if include_history is not None:
			root.push(include_history, pnames, silent=True)
		
		root.push('parents', '_x_', silent=True)
		
		return root
	
	# endregion
	
	pass


