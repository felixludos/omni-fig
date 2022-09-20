
from omnibelt import Entry_Registry, get_printer

prt = get_printer(__name__)

class Artifact_Registry(Entry_Registry):
	def export(self):
		return list(self.keys())



class Script_Registry(Artifact_Registry, components=['fn', 'use_config', 'description', 'project']):
	pass

class Component_Registry(Artifact_Registry, components=['fn', 'description', 'project']):
	pass

class Modifier_Registry(Artifact_Registry, components=['fn', 'description', 'expects_config', 'project']):
	pass

class Config_Registry(Artifact_Registry, components=['path', 'project']):
	@classmethod
	def default(cls, path):
		return cls.entry_cls(path, path, None)
# DefaultConfigEntry = Config_Registry.entry_cls

class Rules_Registry(Entry_Registry, components=['fn', 'priority', 'code', 'num_args', 'description']):
	pass

