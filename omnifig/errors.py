


class NoValidProjectError(Exception):
	'''Raised when no project is found for the given identifier (which should be the name or path to the project)'''
	def __init__(self, ident):
		super().__init__(f'Not a valid project: {ident}')

class YamlifyError(Exception):
	'''Raised when an object is unable to be turned into a yaml object (primitives, dicts, lists)'''
	def __init__(self, obj):
		super().__init__('Unable to yamlify: {} (type={})'.format(obj, type(obj)))
		self.obj = obj

class UnknownActionError(Exception):
	'''Raised when trying to record an unrecognized action with the config object'''
	pass
	
class ScriptNotFoundError(Exception):
	'''Raised when trying to run a script that has not been registered'''
	pass
	
class ConfigNotFoundError(Exception):
	'''Raised when a config parameter is not found and no viable defaults are provided'''
	def __init__(self, ident):
		super().__init__(f'Unknown config: {ident}')

class MissingConfigError(Exception):
	'''Raised when a config parameter was not found, and no viable defaults were provided'''
	def __init__(self, key):
		super().__init__(key)

class InvalidKeyError(Exception):
	'''Only raised when a key cannot be converted to an index for a :class:`ConfigList`'''
	pass

# class NoConfigFound(Exception):
# 	def __init__(self):
# 		super().__init__(
# 			'Either provide a config name/path as the first argument, or set your $FOUNDATION_CONFIG environment variable to a config name/path')


