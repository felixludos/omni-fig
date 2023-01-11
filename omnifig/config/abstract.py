from typing import Optional, Any, Sequence, ContextManager
from omnibelt import Primitive, unspecified_argument

from ..abstract import AbstractConfig



class AbstractSearch:
	'''Abstract class for search objects used by the config object to find the format data'''
	def __init__(self, origin: AbstractConfig, queries: Optional[Sequence[str]], default: Optional[Any], **kwargs):
		super().__init__(**kwargs)


	class SearchFailed(AbstractConfig.SearchFailed):
		'''Raised when a search fails to find a value'''
		def __init__(self, *queries: str):
			super().__init__(', '.join(queries))
			self.queries = queries


	def find_node(self, silent: Optional[bool] = None) -> AbstractConfig:
		'''Finds the node that contains the product'''
		raise NotImplementedError


	def find_product(self, silent: Optional[bool] = None) -> Any:
		'''Finds the node that contains the product, and then extracts the product'''
		raise NotImplementedError


	@staticmethod
	def sub_search(origin: 'AbstractSearch') -> 'ContextManager':
		'''Creates a context manager for new searches to be able to reference the original search `origin`'''
		raise NotImplementedError



class AbstractReporter:
	'''Abstract class for reporters used by the config object to report changes'''
	@staticmethod
	def log(*msg, end='\n', sep=' ', silent=None) -> str:
		'''Prints the given message to the console'''
		raise NotImplementedError


	def get_key(self, trace: 'AbstractSearch') -> str:
		'''Returns the key of the node resulting of the search'''
		raise NotImplementedError


	def report_node(self, node: 'AbstractConfig', *, silent: bool = None) -> Optional[str]:
		'''Reports information about a config node'''
		raise NotImplementedError


	def report_product(self, node: 'AbstractConfig', *, silent: bool = None) -> Optional[str]:
		'''Reports the product of a config node'''
		raise NotImplementedError


	def report_default(self, node: 'AbstractConfig', default: Any, *, silent: bool = None) -> Optional[str]:
		'''Reports a config node defaulted to the given value'''
		raise NotImplementedError


	def report_iterator(self, node: 'AbstractConfig', product: Optional[bool] = False, *,
	                    silent: Optional[bool] = None) -> Optional[str]:
		'''Reports the start of an iterator over the config node'''
		raise NotImplementedError


	def reuse_product(self, node: 'AbstractConfig', product: Any, *, silent: bool = None) -> Optional[str]:
		'''Reports that the product of the given node is being reused'''
		raise NotImplementedError


	def create_primitive(self, node: 'AbstractConfig', value: Primitive = unspecified_argument, *,
	                     silent: bool = None) -> Optional[str]:
		'''Reports that the product of the given node is a primitive'''
		raise NotImplementedError


	def create_container(self, node: 'AbstractConfig', *, silent: bool = None) -> Optional[str]:
		'''Reports that the product of the given node is a container (e.g. a dict or list)'''
		raise NotImplementedError


	def create_component(self, node: 'AbstractConfig', *, component_type: str = None,
	                     modifiers: Optional[Sequence[str]] = None, creator_type: str = None,
	                     silent: bool = None) -> Optional[str]:
		'''Reports that the product of the given node is a component'''
		raise NotImplementedError






