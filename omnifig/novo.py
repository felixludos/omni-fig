from typing import List, Dict, Tuple, Optional, Union, Any, Hashable, Sequence, Callable, Generator, Type, Iterable, Iterator
from omnibelt import unspecified_argument, Singleton
from omnibelt.nodes import AutoTreeNode, AutoTreeSparseNode, AutoTreeDenseNode


class ConfigNode(AutoTreeNode):
	class QueryNotFoundError(KeyError): pass
	
	class QueryFormatter(Singleton):
		def __init__(self, indent=' > ', prefix='| ', transfer=' -> ', link=': ', suffix_fmt=' ({})',
		             silent=False, **kwargs):
			super().__init__(**kwargs)
			self.level = 0
			self.indent = indent
			self.prefix = prefix
			self.transfer = transfer
			self.link = link
			self.suffix_fmt = suffix_fmt
			self._silent = silent
		
		@property
		def silent(self):
			return self._silent
		@silent.setter
		def silent(self, value):
			self._silent = value
		
		def log_msg(self, msg, silent=None):
			if silent is None:
				silent = self.silent
			if silent:
				return
			print(msg)
			return msg
		
		def inc_indent(self):
			self.level += 1
		
		def dec_indent(self):
			self.level = max(0, self.level-1)
		
		# def present_node(self, node):
		#
		# 	pass
		
		def search_report(self, queries, result=None, default=unspecified_argument, silent=None):
			indent = self.level * self.indent
			key = self.transfer.join(queries)
			
			suffix = ''
			
			line = f'{self.prefix}{indent}{key}{self.link}{value}{}'
			
			style = self.style
			src = '' if self.src is None else f'({self.src}) '
			prefix = style + src + indent
			
			msg = raw.replace('\n', '\n' + prefix)
			if not self.is_new_line:
				prefix = ''
			msg = f'{prefix}{msg}{end}'
			pass
			
			
		
		
	def __init__(self, *args, formatter=None, **kwargs):
		if formatter is None:
			formatter = self.QueryFormatter()
		super().__init__(*args, **kwargs)
		self.formatter = formatter
		
	@property
	def silent(self):
		return self.formatter.silent
	@silent.setter
	def silent(self, value):
		self.formatter.silent = value
	
	@classmethod
	def _clean_up_search_path(cls, path: Tuple[Tuple[str, 'ConfigNode', str], Tuple]):
		if len(path):
			seq = cls._clean_up_search_path(path[1])
			seq.append(path[0])
			return seq
		return []
	
	def search(self, *queries, default=unspecified_argument, silent=None):
		for query in queries:
			try:
				path = self._search_path(query, path=())
			except self.QueryNotFoundError:
				path = None
			else:
				path = self._clean_up_search_path(path)
				break
		
		return self.package(path, default=default, silent=silent)
	
	
	def _search_path(self, query: str, path: Tuple):
		raise NotImplementedError
	
	
	def package(self, value):
		pass
	
	pass



class ConfigSparseNode(AutoTreeSparseNode, ConfigNode): pass
class ConfigDenseNode(AutoTreeDenseNode, ConfigNode): pass
ConfigNode.DefaultNode = AutoTreeSparseNode
ConfigNode.SparseNode = AutoTreeSparseNode
ConfigNode.DenseNode = AutoTreeDenseNode













