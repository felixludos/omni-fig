

from omnibelt import SpaceTimeNode


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


		def push(self, addr):
			self._addresses.append(addr)
			self._address_index[addr] = len(self._addresses) - 1


		def next(self, addr=None):
			if addr is None and len(self._addresses) > 0:
				return self._addresses[0]
			if addr not in self._address_index or self._address_index[addr] == len(self._addresses) - 1:
				return None
			return self._addresses[self._address_index[addr] + 1]


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















