from typing import Any, Dict, List, Optional, Union, Hashable, Sequence, Tuple
from collections import OrderedDict
from omnibelt import nodes, unspecified_argument, load_yaml, agnosticmethod, OrderedSet



class ConfigNode:
	class _null_value(Exception): pass
	
	def __init__(self, parent: 'ConfigNode' = None, **kwargs):
		super().__init__(**kwargs)
		self._parent = parent
	
	
	def __copy__(self, parent=unspecified_argument, payload=unspecified_argument, **kwargs):
		if parent is unspecified_argument:
			parent = self._parent
		return self.__class__(parent=parent, **kwargs)
	
	
	def __eq__(self, other):
		return self is other
	
	
	def __hash__(self):
		return id(self)
	
	
	@property
	def is_leaf(self):
		raise NotImplementedError



class ConfigLeaf(ConfigNode):
	def __init__(self, payload: Any, **kwargs):
		super().__init__(**kwargs)
		self._payload = payload
	
	
	def __copy__(self, payload=unspecified_argument, **kwargs):
		if payload is unspecified_argument:
			payload = self._payload
		return super().__copy__(payload=payload, **kwargs)


	@property
	def is_leaf(self):
		return True
	
	
	@property
	def payload(self) -> Any:
		return self._payload



class ConfigStructure: pass



class ConfigBranch(ConfigNode):
	SubStructure: ConfigStructure = None
	
	def __init__(self, children: ConfigStructure = unspecified_argument, **kwargs):
		if children is not None:
			children = self.SubStructure() if children is unspecified_argument else self.SubStructure(children)
		super().__init__(**kwargs)
		self._children = children
	
	
	def __copy__(self, children=unspecified_argument, payload=unspecified_argument, **kwargs):
		if children is unspecified_argument:
			children = self._children
		return super().__copy__(children=children, **kwargs)


	@property
	def is_leaf(self):
		return False
	
	
	def get(self, addr: Hashable) -> ConfigNode:
		raise NotImplementedError
	
	def has(self, node: ConfigNode) -> bool:
		raise NotImplementedError
	
	def add(self, node: ConfigNode) -> ConfigNode:
		raise NotImplementedError
	
	def add_named(self, addr: Hashable, node: ConfigNode) -> ConfigNode:
		raise NotImplementedError
	
	def register(self, *nodes: ConfigNode, **items: Tuple[Hashable, ConfigNode]):
		for node in nodes:
			self.add(node)
		for addr, node in items.items():
			self.add_named(addr, node)
	
	def children(self) -> Sequence[ConfigNode]:
		raise NotImplementedError
	
	def named_children(self) -> Dict[Hashable, ConfigNode]:
		raise NotImplementedError



class ConfigDict(ConfigBranch):
	class SubStructure(ConfigStructure, OrderedDict):
		pass


	@property
	def payload(self) -> Dict[Hashable, Any]:
		return OrderedDict([(key, value.payload) for key, value in self._named_sub()])
	
	def get(self, addr: Hashable) -> ConfigNode:
		return self._children[addr]
	
	# def has(self, node: ConfigNode) -> bool:
	# 	raise NotImplementedError
	#
	# def add(self, node: ConfigNode) -> ConfigNode:
	# 	raise NotImplementedError
	
	def add_named(self, addr: Hashable, node: ConfigNode) -> ConfigNode:
		self._children[addr] = node
		return self._children[addr]
	
	def children(self):
		return self._children.values()
	
	def named_children(self):
		return self._children.items()



class ConfigList(ConfigNode):
	class SubStructure(nodes.SequenceStructure):
		pass


	@property
	def payload(self) -> Sequence[Any]:
		return [value.payload for value in self.children()]
	
	def get(self, addr: Union[str, int]) -> ConfigNode:
		if isinstance(addr, str):
			addr = int(addr)
		assert 0 <= addr < len(self._children), f'Index out of range {addr} from {len(self._children)}'
		return self._children[addr]
	
	def has(self, node: ConfigNode):
		return node in self._children
	
	def add(self, node: ConfigNode):
		return self._children.append(node)
	
	def add_named(self, addr: Union[str, int], node: ConfigNode):
		if isinstance(addr, str):
			addr = int(addr)
		assert -len(self._children) < addr <= len(self._children), \
			f'Index out of range {addr} from {len(self._children)}'
		self._children.insert(addr, node)
		return self._children[addr]
	
	def children(self):
		return self._children
	
	def named_children(self):
		return enumerate(self._children)



class ConfigBase:
	pass



class Config(ConfigBase):
	
	@classmethod
	def from_yaml(cls, path: str, ordered=True, **kwargs):
		data = load_yaml(path, ordered=ordered, **kwargs)
		return cls.nodify(data)
	
	
	LeafNode: ConfigNode = ConfigLeaf
	SequenceNode: ConfigNode = ConfigList
	TableNode: ConfigNode = ConfigDict
	
	
	@agnosticmethod
	def nodify(self, data):
		parent = None if type(self) == type else self
		if isinstance(data, (list, tuple, set)):
			node = self.ConfigSequence(parent=parent)
			for element in data:
				node._add(node.nodify(element))
			return node
		if isinstance(data, dict):
			node = self.ConfigTable(parent=parent)
			for k, v in data.items():
				node._named_add(k, node.nodify(v))
			return node
		return self.ConfigLeaf(payload=data, parent=parent)
	
	
	def query(self, q, ):
		raise NotImplementedError
	
	
	def pull(self, q):
		raise NotImplementedError












