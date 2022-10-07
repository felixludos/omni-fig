

# region Containers

class NoValidProjectError(Exception):
	'''Raised when no project is found for the given identifier (which should be the name or path to the project)'''
	def __init__(self, ident):
		super().__init__(f'Not a valid project: {ident}')

class AmbiguousRuleError(Exception):
	def __init__(self, code, text):
		super().__init__(f'Can\'t combine multiple meta-rules if they require params: {code} in {text}')

# endregion

# region Artifacts

class UnknownArtifactError(Exception):
	pass

class MissingArtifactError(Exception):
	def __init__(self, atype, name):
		super().__init__(name)
		self.atype = atype
		self.name = name

class MissingComponentError(MissingArtifactError):
	def __init__(self, name):
		super().__init__('component', name)

class MissingModifierError(MissingArtifactError):
	def __init__(self, name):
		super().__init__('modifier', name)

class MissingConfigError(MissingArtifactError):
	def __init__(self, name):
		super().__init__('config', name)

class MissingScriptError(MissingArtifactError):
	def __init__(self, name):
		super().__init__('script', name)

artifact_errors = {'script': MissingScriptError, 'component': MissingComponentError,
                   'modifier': MissingModifierError, 'config': MissingConfigError}

# endregion

# region Config

class ConfigNotFoundError(Exception):
	'''Raised when a config parameter is not found and no viable defaults are provided'''
	
	def __init__(self, ident):
		super().__init__(f'Unknown config: {ident}')

class MissingParameterError(Exception):
	'''Raised when a config parameter was not found, and no viable defaults were provided'''
	def __init__(self, key):
		super().__init__(key)

class InvalidKeyError(Exception):
	'''Only raised when a key cannot be converted to an index for a :class:`ConfigList`'''
	pass

class UnknownActionError(Exception):
	'''Raised when trying to record an unrecognized action with the config object'''
	pass

# endregion

# region Misc


class PythonizeError(Exception):
	'''Raised when an object is unable to be turned into a yaml object (primitives, dicts, lists)'''
	def __init__(self, obj):
		super().__init__('Unable to yamlify: {} (type={})'.format(obj, type(obj)))
		self.obj = obj


class WrongInfoContainerType(Exception):
	'''Raised when trying to load a container, but the container expects a different type (ie. subclass).'''
	def __init__(self, ctype, ctype_src=None):
		super().__init__(f'Reload container using custom subclass: {ctype}')
		self.ctype = ctype
		self.ctype_src = ctype_src
	
	def get_ctype(self):
		return self.ctype
	
	def get_mtype_src(self):
		return self.ctype_src

class ConfigurizeFailed(Exception):
	'''Raised when trying to configurize an object by type, but it ends up not working'''
	pass

# endregion

