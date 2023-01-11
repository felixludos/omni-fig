from typing import Any, Dict, List, Optional

from .. import __logger__ as prt
from ..abstract import AbstractBehavior, AbstractConfig
from ..top import get_profile



class Behavior(AbstractBehavior):
	'''Recommended parent class for meta rules.'''

	name = None
	code = None
	priority = 0
	num_args = 0
	description = None

	def __init_subclass__(cls, name: Optional[str] = None, description: Optional[str] = None,
	                      code: Optional[str] = None, priority: Optional[int] = None,
	                      num_args: Optional[int] = None, **kwargs):
		super().__init_subclass__(**kwargs)

		# default to class attributes
		if name is None:
			name = getattr(cls, 'name', None)
		if code is None:
			code = getattr(cls, 'code', None)
		if priority is None:
			priority = getattr(cls, 'priority', 0)
		if num_args is None:
			num_args = getattr(cls, 'num_args', 0)
		if description is None:
			description = getattr(cls, 'description', None)

		# infer missing
		if code is not None and name is None:
			prt.warning(f'No name for {Behavior.__name__} {cls.__name__} provided, will default to {cls.__name__!r}')
			name = cls.__name__
		if code is None and name is not None:
			prt.error(f'No code for {Behavior.__name__} {name!r} provided, '
			          f'cannot register a {Behavior.__name__} without a code')

		# registration
		if name is not None:
			cls.name = name
			cls.code = code
			cls.num_args = num_args
			cls.priority = priority
			cls.description = description
			get_profile().register_behavior(name, cls, description=description)


	def __gt__(self, other):
		'''Compares the behavior to another behavior for ordering.'''
		return self.priority > other.priority


	def __lt__(self, other):
		'''Compares the behavior to another behavior for ordering.'''
		return self.priority < other.priority


	def parse_argv(self, meta: Dict[str, Any], argv: List[str],
	               script_name: Optional[str] = None) -> Optional[List[str]]:
		'''
		Optionally modifies the arguments when the project's :meth:`main()` is called.

		Args:
			meta: Meta-data extracted from the argv so far (can be modified here).
			argv: List of arguments to parse (expected to be :code:`sys.argv[1:]`).
			script_name: Manually specified name of the script (if not provided, it will be parsed from argv).

		Returns:
			Modified list of arguments (or :code:`None` if no modification is needed).

		'''

		if self.code is not None:
			term = f'-{self.code}'
			if term in argv: # trigger this behavior
				idx = argv.index(term)
				assert len(argv) > idx + self.num_args, f'Expected {self.num_args} argument/s after {term!r} for' \
				                                        f'behavior {self.name!r} but only {len(argv) - idx - 1} ' \
				                                        f'were provided'

				meta[self.name] = argv[idx + 1:idx + 1 + self.num_args] if self.num_args > 0 else True
				if self.num_args > 0:
					argv = argv[:idx] + argv[idx + 1 + self.num_args:]
				argv = [a for a in argv if a != term] # remove all instances of the term
				return argv


	def include(self, meta: AbstractConfig) -> bool:
		'''
		Checks if the current behavior should be included before running the given config.

		Args:
			config: Config object to use.

		Returns:
			:code:`True` if the behavior should be included, :code:`False` otherwise.

		'''
		return self.name in meta and (self.num_args > 0 or meta.pull(self.name, False, silent=True))













