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
	def parent(self):
		return self._parent
	
	
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
	def __init__(self, node, **kwargs):
		super().__init__(**kwargs)
		self._current_node = node
		self._root_node = node
	
	
	@property
	def node(self) -> ConfigNode:
		return self._current_node
	
	
	@classmethod
	def from_yaml(cls, path: str, ordered=True, **kwargs):
		data = load_yaml(path, ordered=ordered, **kwargs)
		return cls(cls.nodify(data))
	
	
	LeafNode: ConfigNode = ConfigLeaf
	SequenceNode: ConfigNode = ConfigList
	TableNode: ConfigNode = ConfigDict
	
	
	@agnosticmethod
	def nodify(self, data):
		parent = None if type(self) == type else self
		if isinstance(data, (list, tuple, set)):
			node = self.SequenceNode(parent=parent)
			for element in data:
				node.add(self.nodify(element))
			return node
		if isinstance(data, dict):
			node = self.TableNode(parent=parent)
			for k, v in data.items():
				node.add_named(k, self.nodify(v))
			return node
		return self.LeafNode(payload=data, parent=parent)
	
	
	class NodeSearch:
		def __init__(self, query, allow_defaults=True):
			self.query = query
			self.allow_defaults = allow_defaults
		
		
		def search(self, node):
			path = self._search_path(node, self.query)
			steps = []
			while path is not None:
				step, path = path
				steps.append(step)
			steps = reversed(steps)
			
			if len(steps):
				
				

				
				pass
	
	
		def _search_path(self, node, query, path=None):
			if isinstance(query, str):
				query = query.split('.')
			
			if len(query) == 0:
				return (('done', node, query), path)
			
			term, query = query[0], query[1:]
			if term == '':
				parent = node.parent
				if parent is None:
					return (('error: no parent found', node, query), path)
				return self._search_path(parent, query, (('parent', node, query), path))
			
			if node.has(term):
				return self._search_path(node.get(term), query, (('found', node, query), path))
			
			if self.allow_defaults:
				parent = node.parent
				return self._search_path(parent, query, (('default', node, query), path))
			
			return ((f'error: invalid term: {term}', node, query), path)
		
	
	def search(self, query):
		result = self.NodeSearch(query).search(self._current_node)
		return result
	
	
	def _search_node(self, node, query):
		if isinstance(query, str):
			query = query.split('.')
			# if query.startswith('.'):
			# 	return self._search_node(node.parent, query[1:])
		
		if not len(query):
			return node
		
		
		
		pass
	
	
	def pull(self, q):
		raise NotImplementedError












