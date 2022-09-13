import pickle
# import cloudpickle
# pickle.Pickler = cloudpickle.Pickler
# from multiprocessing import reduction
# import cloudpickle
# reduction.ForkingPickler = cloudpickle.Pickler
import multiprocessing as mp
# import cloudpickle as pickle
# import multiprocess as mp
# import dill as pickle
# mp.set_start_method('spawn')
# mp.set_start_method('spawn', True)

from omnibelt import Class_Registry



def foo(*args, **kwargs):
    print('in foo', args, kwargs)
    return kwargs


table = Class_Registry()
register = table.get_decorator()


class Tracked:
    
    _tracked_sources = None
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        register(cls.__name__)(cls)
        cls._tracked_sources = cls.__name__,
    
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        
    def __repr__(self):
        return f'{self.__class__.__name__}({self.__dict__})'
    
    @staticmethod
    def merge_sources(*names):
        if len(names) == 1:
            return table.get_class(names[0])
        srcs = [table.get_class(name) for name in names]
        new = type('_'.join(names), tuple(srcs), {})
        new._tracked_sources = names
        globals()[new.__name__] = new
        # setattr(__mp_main__, new.__name__, new)
        return new
    
    @classmethod
    def auto_create(cls, *names, **kwargs):
        return cls.merge_sources(*names)(**kwargs)
    
    # def __reduce__(self):
    #     return self.auto_create, self._tracked_sources, self.__dict__
    

class A(Tracked): pass


class B(Tracked): pass


def make_AB():
    return Tracked.merge_sources('A', 'B')#(**kwargs)


class WorkerPool:
    @staticmethod
    def worker_loop(fn, in_q, out_q):
        print('worker_loop started')
        while True:
            i, args = in_q.get(block=True)
            print('worker', i, 'got', args)
            if args is None:
                break
            args, kwargs = args
            out_q.put((i, fn(*args, **kwargs)))
        out_q.put((None, None))
    
    
    def __init__(self, fn, n_workers=1):
        self.fn = fn
        self.n_workers = n_workers
        self.in_q = mp.Queue()
        self.out_q = mp.Queue()
        self.workers = [mp.Process(target=self.worker_loop, args=(fn, self.in_q, self.out_q))
                        for _ in range(n_workers)]
        for w in self.workers:
            w.start()
    
    def __call__(self, *args, **kwargs):
        self.in_q.put((None, (args, kwargs)))
    
    def __del__(self):
        for _ in self.workers:
            self.in_q.put((None, None))
        for w in self.workers:
            w.join()
    
    def multi_call(self, args_list):
        N = 0
        for i, args in enumerate(args_list):
            self.in_q.put((i, args))
            N += 1
        out_list = [None] * N
        for _ in range(N):
            i, out = self.get()
            out_list[i] = out
        return out_list
    
    def get(self, block=True):
        return self.out_q.get(block=block)
    
    def get_all(self):
        while True:
            yield self.get()


if __name__ == '__main__':
    in_q = mp.Queue()
    out_q = mp.Queue()
    p = mp.Process(target=worker_loop, args=(foo, in_q, out_q))
    p.start()

    AB = make_AB()
    ab = AB(qwert=123)

    code = pickle.dumps(ab)
    print('pickled', code)
    ab2 = pickle.loads(code)
    print('unpickled', ab2)
    
    print('sending input...')

    in_q.put((0, ((), {
        # 'typ': AB,
        'obj': ab
    })))
    
    print('output', out_q.get(block=True))
    p.terminate()



