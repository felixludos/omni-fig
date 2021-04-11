import sys
import traceback

from omnibelt import get_printer

from ..rules import Meta_Rule

CODE = 'q'
NAME = 'quiet'

prt = get_printer(__name__)


@Meta_Rule(NAME, priority=10, code=NAME, description='Set config to silent')
def quiet_rule(meta, config):
	'''
	When activated, this rule sets the config object to silent mode, which means pulls/pushes are not printed to stdout

	:param meta: meta config object
	:param config: full config object
	:return: possibly silenced config object
	'''
	
	quiet = meta.pull(NAME, False, silent=True)
	if quiet:
		config.set_silent()
	return config

