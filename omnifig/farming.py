
import sys, traceback

from omnibelt import unspecified_argument, InitWall

import multiprocessing

from .decorators import Component
from .config import configurize, pythonize, ConfigType
from .top import get_config, run
from .common import Configurable


class ExceptionWrapper(object):
	r"""Wraps an exception plus traceback to communicate across threads"""
	def __init__(self, exc_info):
		# It is important that we don't store exc_info, see
		# NOTE [ Python Traceback Reference Cycle Problem ]
		self.exc_type = exc_info[0]
		self.exc_msg = "".join(traceback.format_exception(*exc_info))


def _fmt_worker_config(config, ID=None):
	config = configurize(config)
	config.push('worker_ID', ID, silent=True)
	config.set_process_id(ID)
	return config


def _worker_loop(ID, in_q, out_q, config):
	
	config = _fmt_worker_config(config, ID=ID)
	
	try:
		worker = config.pull_self()
	except Exception:
		print(f'** Worker {ID} failed **')
		out_q.put(ExceptionWrapper(sys.exc_info()))
		return
	
	while True:
		config = in_q.get()

		if config is None:
			break
		try:
			config = _fmt_worker_config(config, ID=ID)
			out = worker(config)
		except Exception:
			out_q.put(ExceptionWrapper(sys.exc_info()))
		else:
			out_q.put(out)


class Worker(Configurable):
	def __call__(self, config):
		raise NotImplementedError


@Component('worker')
class ScriptWorker(Worker):
	def __init__(self, A, **kwargs):
		
		init_script = A.pull('init_script', None)
		script = A.pull('script')
		
		update_config = A.pull('update_config', False)
		
		super().__init__(A, **kwargs)
		
		self.script = script
		
		if init_script is not None:
			out = run(init_script, A)
			replace_config = A.pull('replace_config', out is not None)
			if isinstance(out, ConfigType) and replace_config:
				A = out
		
		self.config = A if update_config else None
		
	def __call__(self, config):
		if self.config is not None and isinstance(config, ConfigType):
			self.config.update(config)
			config = self.config
		return run(self.script, config)



class FarmerBase(InitWall):
	def __init__(self, worker_script=None, worker_init_script=None, worker_config=None,
	             update_worker_config=None, waiting=None, auto_dispatch=True,
	             num_workers=0, timeout=20, mp_lib=None, **other):
		
		if worker_config is None:
			assert worker_script is not None, 'no worker script or config provided'
			worker_config = get_config()
		
		worker_config.push('script', worker_script, overwrite=False, silent=True)
		if worker_init_script is not None:
			worker_config.push('init_script', worker_init_script, overwrite=False, silent=True)
		if update_worker_config is not None:
			worker_config.push('update_worker_config', update_worker_config, overwrite=False, silent=True)
		
		super().__init__(**other)
		
		worker_config.push('_type', 'worker', silent=True, overwrite=False)
		
		if mp_lib is None:
			mp_lib = multiprocessing
		self.mp_lib = mp_lib
		
		self.worker_config = worker_config
		
		self.waiting = waiting
		self.auto_dispatch = auto_dispatch
		
		self.num_workers = num_workers
		self.timeout = timeout
		
		self.worker = None
		self.workers = None
		
		self.start()
	
	
	def start(self, num_workers=None):
		
		if num_workers is None:
			num_workers = self.num_workers
		
		if self.workers is not None:
			self.stop()
		
		self.in_queue = self.mp_lib.Queue()
		self.out_queue = self.mp_lib.Queue()
		
		if num_workers > 0:
			self.workers = [
				self.mp_lib.Process(target=_worker_loop, args=(i, self.in_queue, self.out_queue, self.worker_config))
				for i in range(num_workers)]
			
			for w in self.workers:
				w.daemon = True  # ensure that the worker exits on process exit
				w.start()
			
			if self.waiting is None:
				self.waiting = num_workers if self.auto_dispatch else 0
			self.send(self.waiting)
		
		else:
			self.worker = self.worker_config.pull_self()
		
		
	def stop(self):
		
		self.in_queue.close()
		self.in_queue = None
		self.out_queue.close()
		self.out_queue = None
		
		if self.worker is not None:
			self.worker = None
		else:
			for _ in self.workers:
				self.dispatch(None)
			
			for worker in self.workers:
				worker.stop()
	
	
	def dispatch(self, config=unspecified_argument):
		if config is unspecified_argument:
			config = self._next_job()
		
		if self.worker is None:
			self.in_queue.put(pythonize(config))
		else:
			self.out_queue.put(self.worker(config))
	
	
	def quick_dispatch(self, *args, **kwargs):
		return self.dispatch(get_config(*args, **kwargs) if len(args) or len(kwargs) else None)
	
	
	def send(self, num=None, block=False, timeout=unspecified_argument):
		if num is None or num == 0:
			self.dispatch()
		else:
			for _ in range(num):
				self.dispatch()
		
		if block:
			return self.receive(num=num, timeout=timeout)
	
	
	def receive(self, num=None, timeout=unspecified_argument):
		if timeout is unspecified_argument:
			timeout = self.timeout
		
		if num is None or num == 0:
			return self.out_queue.get(block=True, timeout=timeout)
		return [self.out_queue.get(block=True, timeout=timeout) for _ in range(num)]
	
	def complete(self):
		return self.send(len(self), block=True)
	
	def _next_job(self):
		'''creates config object to send to the worker, or throws StopIteration if there are no more jobs'''
		raise NotImplementedError
	
	def __len__(self):
		raise NotImplementedError
	
	def __iter__(self):
		return self
	
	
	def __next__(self):
		return self.send(block=True)



class Farmer(Configurable, FarmerBase):
	def __init__(self, A, worker_script=unspecified_argument, worker_init_script=unspecified_argument,
	             worker_config=unspecified_argument,
	             update_worker_config=None, waiting=unspecified_argument, auto_dispatch=None,
	             num_workers=None, timeout=unspecified_argument, **kwargs):
		
		if worker_script is unspecified_argument:
			worker_script = A.pull('script', None)
		
		if worker_init_script is unspecified_argument:
			worker_init_script = A.pull('init-script', None)
			
		if worker_config is unspecified_argument:
			worker_config = A.pull('worker-config', '<>worker', None, raw=True)
		
		if update_worker_config is None:
			update_worker_config = A.pull('update_worker_config', False)
			
		if waiting is unspecified_argument:
			waiting = A.pull('waiting', None)
		
		if auto_dispatch is None:
			auto_dispatch = A.pull('auto-dispatch', False)
			
		if num_workers is None:
			num_workers = A.pull('num-workers', 0)
			
		if timeout is unspecified_argument:
			timeout = A.pull('timeout', 20)
		
		super().__init__(A, worker_script=worker_script, worker_init_script=worker_init_script,
		                 worker_config=worker_config,
	             update_worker_config=update_worker_config, waiting=waiting, auto_dispatch=auto_dispatch,
	             num_workers=num_workers, timeout=timeout, **kwargs)






