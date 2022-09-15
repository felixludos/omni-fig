from omnibelt import Class_Registry, Function_Registry
from .organization import Project
from .config import ConfigManager



class NovoProject(Project, name='novo'):
	ConfigManager = ConfigManager

	Script_Registry = Function_Registry
	Creator_Registry = Class_Registry
	Modifier_Registry = Class_Registry
	class Component_Registry(Class_Registry, components=['creator']): pass


	def __init__(self, config_manager=None, script_registry=None, creator_registry=None,
	             component_registry=None, modifier_registry=None, **kwargs):
		if config_manager is None:
			config_manager = self.ConfigManager(self)
		if script_registry is None:
			script_registry = self.Script_Registry()
		if creator_registry is None:
			creator_registry = self.Creator_Registry()
		if component_registry is None:
			component_registry = self.Component_Registry()
		if modifier_registry is None:
			modifier_registry = self.Modifier_Registry()
		super().__init__(**kwargs)
		self.config_manager = config_manager
		self.script_registry = script_registry
		self.creator_registry = creator_registry
		self.component_registry = component_registry
		self.modifier_registry = modifier_registry
		

	def process_argv(self, argv=(), script_name=None):
		return self.config_manager.parse_argv(argv, script_name)

	def create_config(self, *contents, **parameters):
		return self.config_manager.create_config(list(contents), parameters)

	def find_config(self, name):
		return str(self.config_manager.find_config_path(name))

	def register_config(self, name, path):
		self.config_manager.register(name, path)

	def register_config_dir(self, path, recursive=False, prefix=None, joiner='/'):
		self.config_manager.auto_register_directory(path)

	
	


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
			config = rule(config.peek('_meta'), config)

		config.push('_meta._type', 'run_mode/default', overwrite=False, silent=True)
		silent = config.pull('_meta._quiet_run_mode', True, silent=True)
		mode = config.pull('_meta', silent=silent)
		# config = mode.process(config)

		return mode.run(config.sub('_meta'), config)







