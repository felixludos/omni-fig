


class YamlifyError(Exception):
	def __init__(self, obj):
		super().__init__('Unable to yamlify: {} (type={})'.format(obj, type(obj)))
		self.obj = obj

class ParsingError(Exception):
	pass


class NoConfigFound(Exception):
	def __init__(self):
		super().__init__(
			'Either provide a config name/path as the first argument, or set your $FOUNDATION_CONFIG environment variable to a config name/path')


