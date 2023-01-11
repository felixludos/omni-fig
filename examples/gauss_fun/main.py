

import sys
import random
import omnifig as fig

@fig.script('sample', description='Sample a low probability event')
def sample_low_prob(config): # config object
	'''Uses complicated algorithms to find reasonably large/small numbers'''

	mylogger = config.pull('logger') # create a logger object according to specifications in the config

	num_events = config.pull('num_events', 10) # default value is 10 if "num_events" is not specified in the config

	interest_criterion = config.pull('criterion', 5.)
	important_criterion = config.pull('important_criterion', 5.2)

	mu, sigma = config.pull('mu',0.), config.pull('sigma', 1.)
	sigma = max(sigma, 1e-8) # ensure sigma is positive

	print('Sampling...')

	events = []
	count = 0
	while len(events) < num_events:
		x = random.gauss(mu, sigma)
		if abs(x) > interest_criterion:
			mylogger.log_line(f'Found important {x:.2f}\n', important=abs(x)>important_criterion)
			events.append(x)
		count += 1

	mylogger.log_line(f'Finding {num_events} low prob samples required {count} samples.\n',
	                  include_credits=True, important=True)

	mylogger.close()

	return events

@fig.autocomponent('stdout') # automatically pulls all arguments in signature before creating
def _get_stdout(): # in this case, we don't need any arguments
	return sys.stdout

@fig.autocomponent('file')
def _get_file(path):
	return open(path, 'a+')

@fig.component('mylogger')
class Logger(fig.Configurable):
	def __init__(self, always_log=False, print_stream=None, credits=[]):
		self.always_log = always_log
		self.print_stream = print_stream
		self.credits = credits
		if not isinstance(self.credits, list):
			self.credits = list(self.credits)

	def log_line(self, line, stream=None, important=False, include_credits=False):
		if stream is None:
			stream = self.print_stream
		if stream is not None and (important or self.always_log):
			stream.write(line)
			if include_credits and len(self.credits):
				stream.write('Credits: {}\n'.format(', '.join(self.credits)))

	def close(self):
		if self.print_stream is not None:
			self.print_stream.close()


@fig.modifier('multi')
class MultiStream(fig.Configurable):
	@fig.config_aliases(streams=['print_streams', 'print_stream'])
	def __init__(self, streams=(), **kwargs):
		if not isinstance(streams, (list, tuple)):
			streams = [streams]
		super().__init__(print_stream=None, **kwargs) # initialize any dynamically added superclasses (-> Logger)
		self.print_streams = streams

	def log_line(self, line, stream=None, important=False, include_credits=False):
		if stream is not None:
			return super().log_line(line, stream=stream, important=important, include_credits=include_credits)
		for stream in self.print_streams:
			return super().log_line(line, stream=stream, important=important, include_credits=include_credits)

	def close(self):
		for stream in self.print_streams:
			stream.close()


@fig.modifier('remove-credits')
class NoCredit(fig.Configurable):
	def __init__(self, *args, remove_names=(), **kwargs):
		super().__init__(*args, **kwargs)
		for name in remove_names:
			if name in self.credits:
				self.credits.remove(name)
				print(f'Removed {name} from credits')



if __name__ == '__main__':
	fig.entry('sample')
