from typing import List, Dict, Tuple, Optional, Union, Any, Hashable
from datetime import datetime, timezone
from collections import OrderedDict, UserList
from omnibelt import agnosticmethod, unspecified_argument, sign, OrderedSet
# from omnibelt import SpaceTimeNode


class OmniStructure:
	pass


class IntrinsicStructure(OmniStructure):
	def register(self, node: 'OmniNode') -> OmniStructure:
		raise NotImplementedError
	
	
	def deregister(self, node: 'OmniNode') -> 'OmniNode':
		raise NotImplementedError



class ExtrinsicStructure(OmniStructure):
	def register(self, addr: Hashable, node: 'OmniNode') -> OmniStructure:
		raise NotImplementedError
	
	
	def deregister(self, addr: Hashable) -> 'OmniNode':
		raise NotImplementedError



class OmniNode:
	def __init__(self, structure: OmniStructure = None, **kwargs):
		super().__init__(**kwargs)
		self._structure: OmniStructure = self._create_structure(structure)
	
	
	def _create_structure(self, structure: OmniStructure = None, **kwargs) -> OmniStructure:
		raise NotImplementedError # should include a call to OmniStructure.register(self)


	def _deregister(self):
		raise NotImplementedError # should include a call to OmniStructure.deregister(self)

	
	def __copy__(self, structure: Optional[OmniStructure] = unspecified_argument, **kwargs):
		if structure is unspecified_argument:
			structure = self._structure
		return self.__class__(structure=structure, **kwargs)
		
	
	def isolated_copy(self, structure=None, **kwargs):
		return self.__copy__(structure=None, **kwargs)
	
	
	@property
	def payload(self):
		raise NotImplementedError
	


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


	def deregister(self, node: IdentNode) -> IdentNode:
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



class EdgeStructure(IntrinsicStructure, OrderedDict):
	class NodeEdges(TableStructure):
		def __init__(self, base: OmniNode, graph: 'EdgeStructure'):
			super().__init__()
			self.base = base
			self.graph = graph
			
		
		def deregister_base(self):
			pass
		
	
	def register(self, node: IdentNode) -> NodeEdges:
		edges = self.NodeEdges(node, self)
		self[node.identifier] = edges
		return edges
	
	
	def deregister(self, node: IdentNode) -> OmniNode:
		self[node.identifier].deregister_base()
		del self[node.identifier]
		return node



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



class SubNode(OmniNode):
	class SubSpace(TableStructure):
		pass
	
	
	def __init__(self, sub=unspecified_argument, **kwargs):
		super().__init__(**kwargs)
		if sub is unspecified_argument:
			sub = self.SubSpace()
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
	
	

# class Delta:
# 	pass
#
#
#
# class Aggregator:
# 	class Conflict(Exception):
# 		pass
#
#
# 	def aggregate(self, *deltas):
# 		pass



class LeafNode(OmniNode):
	def __init__(self, payload=unspecified_argument, **kwargs):
		super().__init__(**kwargs)
		self._payload = payload

	
	@property
	def payload(self):
		return self._payload



# class ConfigNode(Node):
# 	AntiNode = AntiNode
# 	ReferenceNode = ReferenceNode



class SpaceTimeNode:
	def past(self, addr=None):
		raise NotImplementedError
	
	def future(self, addr=None):
		raise NotImplementedError
	
	def super(self, addr=None):
		raise NotImplementedError
	
	def sub(self, addr=None):
		raise NotImplementedError
	


class AddressNode(SpaceTimeNode):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self._past_nodes = self.AddressBook()
		self._future_nodes = self.AddressBook()
		self._sub_nodes = self.AddressBook()
		self._super_nodes = self.AddressBook()


	class AddressBook:
		def __init__(self, **kwargs):
			super().__init__(**kwargs)
			self._addresses = []
			self._address_index = {}

		def cut(self, addr):
			if addr in self._address_index:
				index = self._address_index[addr]
				del self._addresses[index]
				del self._address_index[addr]

		def push(self, addr):
			if addr not in self._address_index:
				self._addresses.append(addr)
				self._address_index[addr] = len(self._addresses) - 1


		def recover(self, addr):
			if addr in self._address_index:
				return self._addresses[self._address_index[addr]]


		def next(self, addr=None):
			if addr is None and len(self._addresses) > 0:
				return self._addresses[0]
			if addr not in self._address_index or self._address_index[addr] == len(self._addresses) - 1:
				return None
			return self._addresses[self._address_index[addr] + 1]


		def search(self, addr=None):
			current = 0 if addr is None or addr not in self._address_index else self._address_index[addr]+1
			while current < len(self._addresses):
				yield self._addresses[current]
				current += 1


		def __len__(self):
			return len(self._addresses)


		def __contains__(self, item):
			return item in self._address_index


	def past(self, addr=None):
		return self._past_nodes.next(addr)


	def future(self, addr=None):
		return self._future_nodes.next(addr)


	def sub(self, addr=None):
		return self._sub_nodes.next(addr)


	def super(self, addr=None):
		return self._super_nodes.next(addr)



class DataNode(SpaceTimeNode):
	def __init__(self, payload=None, **kwargs):
		super().__init__(**kwargs)
		self.data = payload



class ReferenceNode(AddressNode, DataNode):
	pass



class LeafNode(AddressNode, DataNode):
	pass


class Structure:
	def update(self, addr=None, **kwargs):
		raise NotImplementedError

	def attach(self, addr=None, **kwargs):
		raise NotImplementedError


	def assemble(self, base=None, **kwargs):
		raise NotImplementedError

	def forecast(self, base=None, **kwargs):
		raise NotImplementedError

	def external(self, addr=None, **kwargs):
		raise NotImplementedError

	def internal(self, addr=None, **kwargs):
		raise NotImplementedError

	def owners(self, base=None, **kwargs):
		raise NotImplementedError

	def followers(self, base=None, **kwargs):
		raise NotImplementedError




class BranchNode(AddressNode, DataNode):

	class _missing_value:
		pass


	class PullError(KeyError):
		def __init__(self, addr):
			super().__init__(str(addr))
			self.addr = addr


	def attach(self, node):
		self._sub_nodes.push(node)
		node._super_nodes.push(self)


	def update(self, node):
		self._future_nodes.push(node)
		node._past_nodes.push(self)


	def nodify(self, obj):
		'''Returns a node from the given object.'''
		raise NotImplementedError


	def pull(self, *addrs, default=unspecified_argument, **construct_args):
		trace = self._trace_pull(*addrs, default=default)
		return self.construct(trace, **construct_args)


	def pull_node(self, *addrs, default=unspecified_argument):
		trace = self._trace_pull(*addrs, default=default)
		return trace[-1]
		raise NotImplementedError


	class AddressTrace:
		def __init__(self, addrs=None, default=None, **kwargs):
			super().__init__(**kwargs)
			self.addrs = addrs
			self.default = default
			self.records = None


		class TracedRecord:
			__slots__ = ('trace', 'predecessor', 'record')
			def __init__(self, trace, predecessor=None, **kwargs):
				super().__init__(**kwargs)
				self.trace = trace
				self.predecessor = predecessor
				self.record = None

			def collect(self):
				records = [self.record]
				record = self
				while record.predecessor is not None:
					records.append(record.record)
					record = record.predecessor
				self.trace.records = records[::-1]

			def append(self, *args, **kwargs):
				self.record = args, kwargs
				return self.trace.create_record(predecessor=self, **kwargs)


		def create_record(self, predecessor=None, trace=None, **kwargs):
			if trace is None:
				trace = self
			return self.TracedRecord(trace=trace, predecessor=predecessor, **kwargs)


		def append(self, *args, **kwargs):
			return self.create_record(predecessor=self).append(*args, **kwargs)


		@classmethod
		def _flatten_trace(cls, path, node):
			'''Flattens the given trace.'''
			trace = [node]
			while len(path) > 1:
				trace.append(path[-1])
				path = path[0]
			trace.append(path[0])
			return trace[::-1]


	def _trace_pull(self, *addrs, default=unspecified_argument, trace=None):
		if default is not unspecified_argument:
			default = self.nodify(default)
		if trace is None:
			trace = self.AddressTrace(addrs=addrs, default=default)
		for addr in addrs:
			try:
				result = self._pull_remote(addr, trace=trace.append(addr=addr, node=self))
			except self.PullError:
				pass
			else:
				return result.collect()
		if default is not unspecified_argument:
			return trace
		raise self.PullError(addrs)



	def _pull_remote(self, addr, trace=None):
		try:
			return self._pull_local(addr, trace=trace)
		except self.PullError:
			# for past in self._past_nodes.search():
			# 	try:
			# 		return past._pull_remote(addr, trace=None if trace is None else trace.append(up=past))
			# 	except self.PullError:
			# 		pass
			for sup in self._super_nodes.search():
				try:
					return sup._pull_remote(addr, trace=None if trace is None else trace.append(left=sup))
				except self.PullError:
					pass
		raise self.PullError(addr)


	@staticmethod
	def _parse_addr(addr):
		if addr is None:
			return None
		if isinstance(addr, tuple):
			return addr
		if isinstance(addr, list):
			return tuple(addr)
		if isinstance(addr, str):
			if len(addr) == 0:
				return None
			return tuple(addr.split('.'))
		return (addr,)


	def _pull_local(self, addr, trace=None):

		terms = self._parse_addr(addr)
		if trace is not None and terms != addr:
			trace = trace.append(terms=terms, addr=addr)
		try:
			if terms is None or len(terms) == 0:
				return trace.append(terms=terms)

			if terms[0] == '':
				if len(terms) > 1:
					return self.super()._pull_local(terms[1:], trace=None if trace is None else trace.append(left=sup))
				return
			sub = self._sub_nodes.recover(terms[0])
			trace = (_trace, sub)
			if len(terms) > 1:
				return sub._pull_local(terms[1:], _trace=trace)
			return trace
		except self.PullError:
			for past in self._past_nodes.search():
				try:
					return past._pull_local(addr, _trace=trace)
				except self.PullError:
					pass
		raise self.PullError(addr)


	def push(self, addr, val):
		raise NotImplementedError


	def construct(self, trace, **kwargs):
		'''Processes and returns the payload of the node.'''
		return self.data

	pass


class Integral:
	def touch(self, node):
		pass
	
	def mark(self, node):
		pass
	
	def untouched(self, nodes):
		pass


class Trajectory:
	def step(self, current, target):
		pass




class Node:
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._up = {}
		self._down = {}
		self._left = {}
		self._right = {}
	
	
	def _move_along_edge(self, direction, edges, key):
		if edges is None:
			return None
		return edges.get(key)


	def _set_single_edge(self, direction, edges, key, val=None):
		edges[key] = val
		return edges
	
	
	def up(self, key=None):
		return self._move_along_edge('up', edges=self._up, key=key)

		
	def down(self, key=None):
		return self._move_along_edge('down', edges=self._down, key=key)

	
	def left(self, key=None):
		return self._move_along_edge('left', edges=self._left, key=key)

	
	def right(self, key=None):
		return self._move_along_edge('right', edges=self._right, key=key)

	
	def set_up(self, key, val=None):
		self._set_single_edge('up', edges=self._up, key=key, val=val)


	def set_down(self, key, val=None):
		self._set_single_edge('down', edges=self._down, key=key, val=val)


	def set_left(self, key, val=None):
		self._set_single_edge('left', edges=self._left, key=key, val=val)


	def set_right(self, key, val=None):
		self._set_single_edge('right', edges=self._right, key=key, val=val)



class DataNode(Node):
	def __init__(self, payload=None, **kwargs):
		super().__init__(**kwargs)
		self._payload = payload


	@property
	def payload(self):
		return self._payload










