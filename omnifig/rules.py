
from heapq import heapify, heappop

from omnibelt import get_printer, Entry_Registry

prt = get_printer(__name__)

class _Rules_Registry(Entry_Registry, components=['fn', 'priority', 'code', 'num_args', 'description']):
	pass
_rules_registry = _Rules_Registry()

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
	rules = [(-r.priority, r) for r in _rules_registry.values()]
	heapify(rules)
	
	while len(rules):
		yield heappop(rules)[1]

def meta_rule_fns():
	for rule in view_meta_rules():
		yield rule.fn

# def get_meta_rule_codes():
# 	codes = {}
#
# 	for rule in view_meta_rules():
# 		if rule.code is not None:
# 			if rule.code in codes:
# 				prt.warning(f'Didnt overwrite {rule.code} for {rule.name}, since {codes[rule.code]} is first')
# 			codes[rule.code] = rule.name
#
# 	return codes
#
# def get_meta_rule_num_args():
# 	return {rule.name : rule.num_args
# 	        for rule in view_meta_rules()
# 	        if rule.num_args > 0}


def Meta_Rule(name, priority=0, code=None, expects_args=0, description=None):
	def _reg(fn):
		register_meta_rule(name, fn=fn, priority=priority, code=code, expects_args=expects_args,
		                   description=description)
		return fn
	return _reg

