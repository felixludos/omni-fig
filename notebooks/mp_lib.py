from omnibelt import Class_Registry
import multiprocessing as mp
# mp.set_start_method('spawn')

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
        # globals()[new.__name__] = new
        # setattr(__mp_main__, new.__name__, new)
        return new
    
    @classmethod
    def auto_create(cls, *names, **kwargs):
        return cls.merge_sources(*names)(**kwargs)
    
    def __reduce__(self):
        return self.auto_create, self._tracked_sources, self.__dict__
    

class A(Tracked): pass


class B(Tracked): pass


def make_AB():
    return Tracked.merge_sources('A', 'B')#(**kwargs)

import pickle


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

    in_q.put((0, ((), {
        # 'typ': AB,
        'obj': ab
    })))
    
    print('output', out_q.get(block=True))
    p.terminate()



