from typing import List, Dict, Tuple, Optional, Union, Any, Hashable, Sequence, Callable
from datetime import datetime, timezone
from collections import OrderedDict, UserList
from omnibelt import agnosticmethod, unspecified_argument, sign, OrderedSet
# from omnibelt import SpaceTimeNode


class OmniStructure:
	pass



class OmniNode:
	def __copy__(self, **kwargs):
		return self.__class__(**kwargs)



class IntrinsicStructure(OmniStructure):
	'''The structure is fully defined by the collection of nodes (eg. linked list)'''
	def register(self, node: OmniNode) -> OmniStructure:
		raise NotImplementedError
	
	
	def deregister(self, node: OmniNode) -> OmniNode:
		raise NotImplementedError



class ExtrinsicStructure(OmniStructure):
	'''The structure includes auxillary information beyond the nodes (eg. dict)'''
	def register(self, addr: Hashable, node: OmniNode) -> OmniStructure:
		raise NotImplementedError
	
	
	def deregister(self, addr: Hashable) -> OmniNode:
		raise NotImplementedError



class ContextStructure(OmniStructure): # abstract
	_structure_instance_for_context = None
	def __new__(cls, *args, **kwargs):
		if cls._structure_instance_for_context is None:
			return super().__new__(cls, *args, **kwargs)
		return cls._structure_instance_for_context
	
	
	def __enter__(self):
		self.__class__._structure_instance_for_context = self
	
	
	def __exit__(self, exc_type, exc_val, exc_tb):
		del self.__class__._structure_instance_for_context



class PayloadNode(OmniNode):
	@property
	def payload(self) -> Any:
		raise NotImplementedError



class StructureNode(OmniNode):
	def __init__(self, structure: OmniStructure = None, **kwargs):
		super().__init__(**kwargs)
		self._structure = None
		self._structure = self._create_structure(structure)


	@property
	def structure(self) -> OmniStructure:
		return self._structure
	
	
	Structure = None
	def _create_structure(self, structure: OmniStructure = None, **kwargs) -> OmniStructure:
		if structure is None:
			structure = self.Structure(**kwargs)
		return structure.register(self)


	def _deregister(self):
		raise NotImplementedError

	
	def __copy__(self, structure: Optional[OmniStructure] = unspecified_argument, **kwargs):
		if structure is unspecified_argument:
			structure = self._structure
		return super().__copy__(structure=structure, **kwargs)
		
	
	def isolated_copy(self, structure=None, **kwargs):
		return self.__copy__(structure=None, **kwargs)
	


class AssertiveIntrinsicStructure(IntrinsicStructure):
	def register(self, node: StructureNode) -> OmniStructure:
		if node.structure is not self:
			node._structure = self
		return super().register(node)
		


class IdentNode(OmniNode):
	@property
	def identifier(self) -> Hashable:
		return hex(id(self))[2:]
	
	
	def __str__(self):
		return self.identifier
	
	
	def __repr__(self):
		return f'{self.__class__.__name__}:{self.identifier}'
	
	
	def __eq__(self, other):
		return self.identifier == other.identifier
	
	
	def __hash__(self):
		return hash(self.identifier)



class ExtrinsicToIntrinsicStructure(ExtrinsicStructure, IntrinsicStructure):
	def register(self, node: IdentNode) -> OmniStructure:
		return super().register(node.identifier, node)


	def deregister(self, node: IdentNode) -> OmniNode:
		return super().deregister(node.identifier)



class SequenceStructure(IntrinsicStructure, OrderedSet):
	def register(self, node: OmniNode) -> 'SequenceStructure':
		self.add(node)
		return self
	
	
	def deregister(self, node: OmniNode) -> 'SequenceStructure':
		self.remove(node)
		return self



class TableStructure(ExtrinsicStructure, OrderedDict):
	def register(self, addr: Hashable, node: OmniNode) -> 'TableStructure':
		self[addr] = node
		return self
	
	
	def deregister(self, addr: Hashable) -> OmniNode:
		node = self[addr]
		del self[addr]
		return node
	
	
	
class BaseStructure(OmniStructure):
	def __init__(self, base: OmniNode, structure: OmniStructure = None):
		super().__init__()
		self.base = base
		self.structure = structure
	
	
	def deregister_base(self):
		pass



class NodeEdgeStructure(IntrinsicStructure, OrderedDict):
	class NodeEdges(BaseStructure):
		pass


	def register(self, node: IdentNode, **kwargs) -> NodeEdges:
		ID = node.identifier
		if ID in self:
			return self[ID]
		edges = self.NodeEdges(node, self, **kwargs)
		self[ID] = edges
		return edges


	def deregister(self, node: IdentNode) -> IdentNode:
		ID = node.identifier
		self[ID].deregister_base()
		del self[ID]
		return node



class AbstractParentNode(OmniNode):
	@property
	def parent(self) -> OmniNode:
		raise NotImplementedError


	@property
	def children(self) -> OmniStructure:
		raise NotImplementedError



class ParentNode(AbstractParentNode): # single parent, many children
	def __init__(self,
	             parent: Optional[AbstractParentNode] = None,
	             children: Optional[Sequence[AbstractParentNode]] = None,
	             **kwargs):
		super().__init__(**kwargs)
		self._parent: Union[ParentNode, None] = None
		self.parent = parent
		if children is not None:
			self.add_children(*children)
	
	
	@property
	def parent(self) -> 'ParentNode':
		return self._parent
	@parent.setter
	def parent(self, parent: 'ParentNode'):
		if self._parent is not None:
			self.parent.children.deregister(self)
		if parent is not None:
			parent.children.register(self)
		self._parent = parent


	@property
	def children(self) -> IntrinsicStructure:
		raise NotImplementedError
	
	
	def add_children(self, *children: OmniNode) -> 'ParentNode':
		registry = self.children
		for child in children:
			registry.register(child)
		return self



class AbstractMultiParentNode(OmniNode):
	@property
	def parents(self) -> OmniStructure:
		raise NotImplementedError


	@property
	def children(self) -> OmniStructure:
		raise NotImplementedError



class MultiParentNode(AbstractMultiParentNode):  # single parent, many children
	def __init__(self,
	             parents: Optional[Sequence[AbstractMultiParentNode]] = None,
	             children: Optional[Sequence[AbstractMultiParentNode]] = None,
	             **kwargs):
		super().__init__(**kwargs)
		if parents is not None:
			self.add_parents(*parents)
		if children is not None:
			self.add_children(*children)
	

	def add_parents(self, *parents: 'MultiParentNode') -> 'MultiParentNode':
		registry = self.parents
		for parent in parents:
			registry.register(parent)
			# parent.children.register(self)
		return self
	
	
	def add_children(self, *children: 'MultiParentNode') -> 'MultiParentNode':
		registry = self.children
		for child in children:
			registry.register(child)
			# child.parents.register(self)
		return self



class GraphNode(StructureNode):
	class Structure(NodeEdgeStructure):
		class NodeEdges(NodeEdgeStructure.NodeEdges, SequenceStructure):
			def register(self, node: StructureNode) -> 'NodeEdges':
				node.structure.add(self.base)
				return super().register(node)
			
			
			def deregister(self, node: StructureNode) -> ParentNode:
				node = super().deregister(node)
				node.structure.remove(self.base)
				return node
			
			
			def deregister_base(self):
				for node in self:
					node.structure.remove(self.base)
				return super().deregister_base()



class TreeNode(ParentNode, StructureNode):
	@property
	def children(self) -> OmniStructure:
		return self.structure
	
	
	class Structure(NodeEdgeStructure):
		class NodeEdges(NodeEdgeStructure.NodeEdges):
			def register(self, node: ParentNode) -> 'NodeEdges':
				node._parent = self.base
				return super().register(node)
			
			
			def deregister(self, node: ParentNode) -> ParentNode:
				node = super().deregister(node)
				node._parent = None
				return node
			
			
			def deregister_base(self):
				for node in self:
					node._parent = None



class DiGraphNode(MultiParentNode, StructureNode):
	class Structure(NodeEdgeStructure):
		class Parents(BaseStructure, SequenceStructure):
			def register(self, node: 'DiGraphNode') -> 'NodeEdges':
				node.children.add(self.base)
				return super().register(node)
			
			def deregister(self, node: 'DiGraphNode') -> 'DiGraphNode':
				node = super().deregister(node)
				node.children.remove(self.base)
				return node
			
			def deregister_base(self):
				for node in self:
					node.children.remove(self.base)
				return super().deregister_base()
		
		
		class Children(BaseStructure, SequenceStructure):
			def register(self, node: 'DiGraphNode') -> 'NodeEdges':
				node.parents.add(self.base)
				return super().register(node)
			
			def deregister(self, node: 'DiGraphNode') -> 'DiGraphNode':
				node = super().deregister(node)
				node.parents.remove(self.base)
				return node
			
			def deregister_base(self):
				for node in self:
					node.parents.remove(self.base)
				return super().deregister_base()
		
		
		class NodeEdges(NodeEdgeStructure.NodeEdges):
			def __init__(self, base: OmniNode, structure: OmniStructure,
			             parents: 'Parents', children: 'Children'):
				super().__init__(base, structure)
				self._parents = parents
				self._children = children
			
			
			@property
			def parents(self) -> 'Parents':
				return self._parents
			
			
			@property
			def children(self) -> 'Children':
				return self._children


			def deregister_base(self):
				for parent in self.parents:
					parent.children.deregister(self.base)
				for child in self.children:
					child.parents.deregister(self.base)
		
		
		def register(self, node: IdentNode, parents=unspecified_argument, children=unspecified_argument,
		             **kwargs) -> NodeEdges:
			if parents is unspecified_argument:
				parents = self.Parents(node, self)
			if children is unspecified_argument:
				children = self.Children(node, self)
			return super().register(node, parents=parents, children=children, **kwargs)

	
	@property
	def parents(self) -> 'Structure.Parents':
		return self.structure.parents

	
	@property
	def children(self) -> 'Structure.Children':
		return self.structure.children



class StampedNode(OmniNode):
	def __init__(self, timestamp=unspecified_argument, **kwargs):
		super().__init__(**kwargs)
		self._timestamp = datetime.now(tz=timezone.utc) if timestamp is unspecified_argument else timestamp
	
	
	def copy(self, timestamp=unspecified_argument, **kwargs):
		if timestamp is unspecified_argument:
			timestamp = self.timestamp
		return self.__copy__(timestamp=timestamp, **kwargs)
	
	
	@property
	def timestamp(self):
		return self._timestamp
	
	
	# def __hash__(self):
	# 	return hash(self.timestamp)
	#
	# def __eq__(self, other):
	# 	return self.timestamp == other.timestamp
	
	
	def __lt__(self, other):
		return self.timestamp < other.timestamp
	
	
	def __le__(self, other):
		return self.timestamp <= other.timestamp
	
	
	def __gt__(self, other):
		return self.timestamp > other.timestamp
	
	
	def __ge__(self, other):
		return self.timestamp >= other.timestamp



class SubNode(PayloadNode):
	class SubStructure(TableStructure):
		pass
	
	
	def __init__(self, sub=unspecified_argument, **kwargs):
		super().__init__(**kwargs)
		if sub is unspecified_argument:
			sub = self.SubStructure()
		self._sub = sub
	
	
	@property
	def payload(self):
		return OrderedDict([(key, value.payload) for key, value in self._sub.items()])
	
	
	def sub(self, addr=unspecified_argument):
		return self._sub.get(addr)
	
	
	def subs(self, items=False):
		if items:
			return self._sub.items()
		return self._sub.keys()
	
	
	def add_sub(self, addr: Hashable, node: OmniNode):
		return self._sub.register(addr, node)
	
	
	def del_sub(self, addr: Hashable):
		return self._sub.deregister(addr)



class LeafNode(PayloadNode):
	def __init__(self, payload=unspecified_argument, **kwargs):
		super().__init__(**kwargs)
		self._payload = payload

	
	@property
	def payload(self):
		return self._payload



class TimelineNode(StructureNode):
	Structure = SequenceStructure
	
	
	def origin(self):
		idx = self.structure.index(self)
		for i in range(0, idx):
			yield self.structure[i]
	
	
	def past(self):
		pass
	
	
	def future(self):
		pass
	
	
	pass



# class ConfigNode(Node):
# 	AntiNode = AntiNode
# 	ReferenceNode = ReferenceNode


#
# class SpaceTimeNode:
# 	def past(self, addr=None):
# 		raise NotImplementedError
#
# 	def future(self, addr=None):
# 		raise NotImplementedError
#
# 	def super(self, addr=None):
# 		raise NotImplementedError
#
# 	def sub(self, addr=None):
# 		raise NotImplementedError
	


# class AddressNode(SpaceTimeNode):
# 	def __init__(self, **kwargs):
# 		super().__init__(**kwargs)
# 		self._past_nodes = self.AddressBook()
# 		self._future_nodes = self.AddressBook()
# 		self._sub_nodes = self.AddressBook()
# 		self._super_nodes = self.AddressBook()
#
#
# 	class AddressBook:
# 		def __init__(self, **kwargs):
# 			super().__init__(**kwargs)
# 			self._addresses = []
# 			self._address_index = {}
#
# 		def cut(self, addr):
# 			if addr in self._address_index:
# 				index = self._address_index[addr]
# 				del self._addresses[index]
# 				del self._address_index[addr]
#
# 		def push(self, addr):
# 			if addr not in self._address_index:
# 				self._addresses.append(addr)
# 				self._address_index[addr] = len(self._addresses) - 1
#
#
# 		def recover(self, addr):
# 			if addr in self._address_index:
# 				return self._addresses[self._address_index[addr]]
#
#
# 		def next(self, addr=None):
# 			if addr is None and len(self._addresses) > 0:
# 				return self._addresses[0]
# 			if addr not in self._address_index or self._address_index[addr] == len(self._addresses) - 1:
# 				return None
# 			return self._addresses[self._address_index[addr] + 1]
#
#
# 		def search(self, addr=None):
# 			current = 0 if addr is None or addr not in self._address_index else self._address_index[addr]+1
# 			while current < len(self._addresses):
# 				yield self._addresses[current]
# 				current += 1
#
#
# 		def __len__(self):
# 			return len(self._addresses)
#
#
# 		def __contains__(self, item):
# 			return item in self._address_index
#
#
# 	def past(self, addr=None):
# 		return self._past_nodes.next(addr)
#
#
# 	def future(self, addr=None):
# 		return self._future_nodes.next(addr)
#
#
# 	def sub(self, addr=None):
# 		return self._sub_nodes.next(addr)
#
#
# 	def super(self, addr=None):
# 		return self._super_nodes.next(addr)
#
#
#
# class DataNode(SpaceTimeNode):
# 	def __init__(self, payload=None, **kwargs):
# 		super().__init__(**kwargs)
# 		self.data = payload
#
#
#
# class ReferenceNode(AddressNode, DataNode):
# 	pass
#
#
#
# class LeafNode(AddressNode, DataNode):
# 	pass
#
#
# class Structure:
# 	def update(self, addr=None, **kwargs):
# 		raise NotImplementedError
#
# 	def attach(self, addr=None, **kwargs):
# 		raise NotImplementedError
#
#
# 	def assemble(self, base=None, **kwargs):
# 		raise NotImplementedError
#
# 	def forecast(self, base=None, **kwargs):
# 		raise NotImplementedError
#
# 	def external(self, addr=None, **kwargs):
# 		raise NotImplementedError
#
# 	def internal(self, addr=None, **kwargs):
# 		raise NotImplementedError
#
# 	def owners(self, base=None, **kwargs):
# 		raise NotImplementedError
#
# 	def followers(self, base=None, **kwargs):
# 		raise NotImplementedError
#
#
#
#
# class BranchNode(AddressNode, DataNode):
#
# 	class _missing_value:
# 		pass
#
#
# 	class PullError(KeyError):
# 		def __init__(self, addr):
# 			super().__init__(str(addr))
# 			self.addr = addr
#
#
# 	def attach(self, node):
# 		self._sub_nodes.push(node)
# 		node._super_nodes.push(self)
#
#
# 	def update(self, node):
# 		self._future_nodes.push(node)
# 		node._past_nodes.push(self)
#
#
# 	def nodify(self, obj):
# 		'''Returns a node from the given object.'''
# 		raise NotImplementedError
#
#
# 	def pull(self, *addrs, default=unspecified_argument, **construct_args):
# 		trace = self._trace_pull(*addrs, default=default)
# 		return self.construct(trace, **construct_args)
#
#
# 	def pull_node(self, *addrs, default=unspecified_argument):
# 		trace = self._trace_pull(*addrs, default=default)
# 		return trace[-1]
# 		raise NotImplementedError
#
#
# 	class AddressTrace:
# 		def __init__(self, addrs=None, default=None, **kwargs):
# 			super().__init__(**kwargs)
# 			self.addrs = addrs
# 			self.default = default
# 			self.records = None
#
#
# 		class TracedRecord:
# 			__slots__ = ('trace', 'predecessor', 'record')
# 			def __init__(self, trace, predecessor=None, **kwargs):
# 				super().__init__(**kwargs)
# 				self.trace = trace
# 				self.predecessor = predecessor
# 				self.record = None
#
# 			def collect(self):
# 				records = [self.record]
# 				record = self
# 				while record.predecessor is not None:
# 					records.append(record.record)
# 					record = record.predecessor
# 				self.trace.records = records[::-1]
#
# 			def append(self, *args, **kwargs):
# 				self.record = args, kwargs
# 				return self.trace.create_record(predecessor=self, **kwargs)
#
#
# 		def create_record(self, predecessor=None, trace=None, **kwargs):
# 			if trace is None:
# 				trace = self
# 			return self.TracedRecord(trace=trace, predecessor=predecessor, **kwargs)
#
#
# 		def append(self, *args, **kwargs):
# 			return self.create_record(predecessor=self).append(*args, **kwargs)
#
#
# 		@classmethod
# 		def _flatten_trace(cls, path, node):
# 			'''Flattens the given trace.'''
# 			trace = [node]
# 			while len(path) > 1:
# 				trace.append(path[-1])
# 				path = path[0]
# 			trace.append(path[0])
# 			return trace[::-1]
#
#
# 	def _trace_pull(self, *addrs, default=unspecified_argument, trace=None):
# 		if default is not unspecified_argument:
# 			default = self.nodify(default)
# 		if trace is None:
# 			trace = self.AddressTrace(addrs=addrs, default=default)
# 		for addr in addrs:
# 			try:
# 				result = self._pull_remote(addr, trace=trace.append(addr=addr, node=self))
# 			except self.PullError:
# 				pass
# 			else:
# 				return result.collect()
# 		if default is not unspecified_argument:
# 			return trace
# 		raise self.PullError(addrs)
#
#
#
# 	def _pull_remote(self, addr, trace=None):
# 		try:
# 			return self._pull_local(addr, trace=trace)
# 		except self.PullError:
# 			# for past in self._past_nodes.search():
# 			# 	try:
# 			# 		return past._pull_remote(addr, trace=None if trace is None else trace.append(up=past))
# 			# 	except self.PullError:
# 			# 		pass
# 			for sup in self._super_nodes.search():
# 				try:
# 					return sup._pull_remote(addr, trace=None if trace is None else trace.append(left=sup))
# 				except self.PullError:
# 					pass
# 		raise self.PullError(addr)
#
#
# 	@staticmethod
# 	def _parse_addr(addr):
# 		if addr is None:
# 			return None
# 		if isinstance(addr, tuple):
# 			return addr
# 		if isinstance(addr, list):
# 			return tuple(addr)
# 		if isinstance(addr, str):
# 			if len(addr) == 0:
# 				return None
# 			return tuple(addr.split('.'))
# 		return (addr,)
#
#
# 	def _pull_local(self, addr, trace=None):
#
# 		terms = self._parse_addr(addr)
# 		if trace is not None and terms != addr:
# 			trace = trace.append(terms=terms, addr=addr)
# 		try:
# 			if terms is None or len(terms) == 0:
# 				return trace.append(terms=terms)
#
# 			if terms[0] == '':
# 				if len(terms) > 1:
# 					return self.super()._pull_local(terms[1:], trace=None if trace is None else trace.append(left=sup))
# 				return
# 			sub = self._sub_nodes.recover(terms[0])
# 			trace = (_trace, sub)
# 			if len(terms) > 1:
# 				return sub._pull_local(terms[1:], _trace=trace)
# 			return trace
# 		except self.PullError:
# 			for past in self._past_nodes.search():
# 				try:
# 					return past._pull_local(addr, _trace=trace)
# 				except self.PullError:
# 					pass
# 		raise self.PullError(addr)
#
#
# 	def push(self, addr, val):
# 		raise NotImplementedError
#
#
# 	def construct(self, trace, **kwargs):
# 		'''Processes and returns the payload of the node.'''
# 		return self.data
#
# 	pass
#
#
# class Integral:
# 	def touch(self, node):
# 		pass
#
# 	def mark(self, node):
# 		pass
#
# 	def untouched(self, nodes):
# 		pass
#
#
# class Trajectory:
# 	def step(self, current, target):
# 		pass
#
#
#
#
# class Node:
# 	def __init__(self, *args, **kwargs):
# 		super().__init__(*args, **kwargs)
# 		self._up = {}
# 		self._down = {}
# 		self._left = {}
# 		self._right = {}
#
#
# 	def _move_along_edge(self, direction, edges, key):
# 		if edges is None:
# 			return None
# 		return edges.get(key)
#
#
# 	def _set_single_edge(self, direction, edges, key, val=None):
# 		edges[key] = val
# 		return edges
#
#
# 	def up(self, key=None):
# 		return self._move_along_edge('up', edges=self._up, key=key)
#
#
# 	def down(self, key=None):
# 		return self._move_along_edge('down', edges=self._down, key=key)
#
#
# 	def left(self, key=None):
# 		return self._move_along_edge('left', edges=self._left, key=key)
#
#
# 	def right(self, key=None):
# 		return self._move_along_edge('right', edges=self._right, key=key)
#
#
# 	def set_up(self, key, val=None):
# 		self._set_single_edge('up', edges=self._up, key=key, val=val)
#
#
# 	def set_down(self, key, val=None):
# 		self._set_single_edge('down', edges=self._down, key=key, val=val)
#
#
# 	def set_left(self, key, val=None):
# 		self._set_single_edge('left', edges=self._left, key=key, val=val)
#
#
# 	def set_right(self, key, val=None):
# 		self._set_single_edge('right', edges=self._right, key=key, val=val)
#
#
#
# class DataNode(Node):
# 	def __init__(self, payload=None, **kwargs):
# 		super().__init__(**kwargs)
# 		self._payload = payload
#
#
# 	@property
# 	def payload(self):
# 		return self._payload










