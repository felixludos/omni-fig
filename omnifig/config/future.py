from .nodes import SimpleConfigNode


class AskParentNode(SimpleConfigNode):
	_ask_parent = True
	_confidential_prefix = '_'


class VolatileNode(SimpleConfigNode):
	_volatile_prefix = '__'


class StorageNodes(VolatileNode):
	_weak_storage_prefix = '<?>'
	_strong_storage_prefix = '<!>'
	# created components are stored under __obj and can be access with prefix
	# (where weak creates component when missing)
	pass


class ReferenceNode(SimpleConfigNode):
	reference_prefix = '<>'
	origin_reference_prefix = '<o>'

	def package(self, value):
		if value is None:
			return None
		return self.ref.package(value)




