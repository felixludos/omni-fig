
from heapq import heapify, heappop

from omnibelt import get_printer, Entry_Registry

from .registry import Rules_Registry

prt = get_printer(__name__)


_rules_registry = Rules_Registry()


def Meta_Rule(name: str, priority: int = 0, code: str = None,
              expects_args: int = 0, description: str = None):
	'''
	Decorator used to register meta rules.

	:param name: Name of the meta rule (and key in meta config for any required arguments)
	:param priority: priority of this meta rule (the higher it is the earlier it is run relative to other meta rules)
	:param code: Command line code (usually a single letter) preceded by "-" to activate this meta rule
	:param expects_args: number of command line arguments required when activating
	:param description: short description of what this rule does for the help message
	:return: decorator function to register the meta rule
	'''
	
	def _reg(fn):
		register_meta_rule(name, fn=fn, priority=priority, code=code, expects_args=expects_args,
		                   description=description)
		return fn
	
	return _reg


def register_meta_rule(name, fn, priority=0, code=None, expects_args=0, description=None):
	'''
	Meta Rules are expected to be a callable of the form:
	
	config <= fn(meta, config)
	
	where ``meta`` is the meta config, and the output should be the processed ``config``
	
	:param name: name of the new rule
	:param fn: callable to enforce rule
	:param priority: priority of this rule (rules are enforced by priority high to low)
	:param code: (optional) single letter code used to activate rule from the terminal
	:param expects_args: number of arguments expected by this meta rule through the terminal
	:param description: one line description of what the rule does
	:return: None
	'''
	
	_rules_registry.new(name, fn=fn, priority=priority, code=code, num_args=int(expects_args),
	                    description=description)

def view_meta_rules():
	'''Returns an iterator over all registered meta rule entries in order of priority (low to high)'''
	rules = [(-r.priority, r) for r in _rules_registry.values()]
	heapify(rules)
	
	while len(rules):
		yield heappop(rules)[1]

def meta_rule_fns():
	'''Returns an iterator over all meta rule functions in order of priority'''
	for rule in view_meta_rules():
		yield rule.fn

