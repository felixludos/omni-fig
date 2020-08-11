

import sys
import random
import omnifig as fig

@fig.Script('sample-low-prob')
def sample_low_prob(A): # config object

	mylogger = A.pull('logger') # create a logger object according to specifications in the config

	num_events = A.pull('num_events', 10) # default value is 10 if "num_events" is not specified in the config

	interest_criterion = A.pull('criterion', 5.)
	important_criterion = A.pull('important_criterion', 5.2)

	mu, sigma = A.pull('mu',0.), A.pull('sigma', 1.)
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

@fig.AutoComponent('stdout') # automatically pulls all arguments in signature before creating
def _get_stdout(): # in this case, we don't need any arguments
	return sys.stdout

@fig.AutoComponent('file')
def _get_file(path):
	return open(path, 'a+')

@fig.Component('mylogger')
class Logger:
	def __init__(self, A): # "A" refers to the config object
		self.always_log = A.pull('always_log', False) # value defaults to False if not found in the config
		self.print_stream = A.pull('print_stream', None) # values can also be components themselves
		self.credits = A.pull('credits', []) # pulled values can also be dicts or lists (with defaults)
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


@fig.AutoModifier('multi')
class MultiStream:
	def __init__(self, A):

		streams = A.pull('print_streams', '<>print_stream', []) # use prefix "<>" to default to a different key
		if not isinstance(streams, (list, tuple)):
			streams = [streams]

		A.push('print_stream', None) # push to replace values in the config

		super().__init__(A) # initialize any dynamically added superclasses (-> Logger)

		self.print_streams = streams

	def log_line(self, line, stream=None, important=False, include_credits=False):

		if stream is not None:
			return super().log_line(line, stream=stream, important=important, include_credits=include_credits)
		for stream in self.print_streams:
			return super().log_line(line, stream=stream, important=important, include_credits=include_credits)

	def close(self):
		for stream in self.print_streams:
			stream.close()

@fig.Modification('remove-credits')
def remove_names(logger, A):
	for name in A.pull('remove_names', []):
		if name in logger.credits:
			logger.credits.remove(name)
			print(f'Removed {name} from credits')
	return logger



if __name__ == '__main__':
	fig.entry('sample-low-prob')
