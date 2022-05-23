
from omnibelt import agnosticmethod, unspecified_argument
# from omnibelt import SpaceTimeNode


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








