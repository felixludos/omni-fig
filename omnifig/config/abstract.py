from typing import List, Dict, Tuple, Optional, Union, Any, Hashable, Sequence, Callable, Generator, Type, Iterable, \
	Iterator, NamedTuple, ContextManager
from omnibelt import Primitive, unspecified_argument

from ..abstract import AbstractConfig



class AbstractSearch:
	def __init__(self, origin: AbstractConfig, queries: Optional[Sequence[str]], default: Optional[Any], **kwargs):
		super().__init__(**kwargs)

	class SearchFailed(AbstractConfig.SearchFailed):
		def __init__(self, *queries: str):
			super().__init__(', '.join(queries))
			self.queries = queries

	def find_node(self, silent: Optional[bool] = None) -> AbstractConfig:
		raise NotImplementedError

	def find_product(self, silent: Optional[bool] = None) -> Any:
		raise NotImplementedError

	def sub_search(self, origin: 'AbstractSearch', queries: Optional[List[str]]) -> 'AbstractSearch':
		raise NotImplementedError


class AbstractReporter:
	@staticmethod
	def log(*msg, end='\n', sep=' ', silent=None) -> str:
		raise NotImplementedError

	def get_key(self, trace: 'AbstractSearch') -> str:
		raise NotImplementedError

	def report_node(self, node: 'AbstractConfig', *, silent: bool = None) -> Optional[str]:
		raise NotImplementedError

	def report_product(self, node: 'AbstractConfig', *, silent: bool = None) -> Optional[str]:
		raise NotImplementedError

	def report_default(self, node: 'AbstractConfig', default: Any, *, silent: bool = None) -> Optional[str]:
		raise NotImplementedError

	def report_iterator(self, node: 'AbstractConfig', product: bool = False, include_key: bool = False,
	                    silent: bool = None) -> Optional[str]:
		raise NotImplementedError

	def reuse_product(self, node: 'AbstractConfig', product: Any, *, silent: bool = None) -> Optional[str]:
		raise NotImplementedError

	def create_primitive(self, node: 'AbstractConfig', value: Primitive = unspecified_argument, *,
	                     silent: bool = None) -> Optional[str]:
		raise NotImplementedError

	def create_container(self, node: 'AbstractConfig', *, silent: bool = None) -> Optional[str]:
		raise NotImplementedError

	def create_component(self, node: 'AbstractConfig', *, component_type: str = None,
	                     modifiers: Optional[Sequence[str]] = None, creator_type: str = None,
	                     silent: bool = None) -> Optional[str]:
		raise NotImplementedError






