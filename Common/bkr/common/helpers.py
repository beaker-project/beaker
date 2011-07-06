from threading import Thread
import Queue, copy

class _QueueAccess:

    def __init__(self, in_q, out_q):
        self.in_queue = in_q
        self.out_queue = out_q


class BkrThreadPool:
    _pool = {}

    @classmethod
    def create_and_run(cls, name, target_f, target_args, num=30, *args, **kw):
        if name in cls._pool:
            raise Exception('%s has already been initialised in the BkrThreadPool' % name)

        out_q = Queue.Queue()
        in_q = Queue.Queue()
        cls._pool[name] =  _QueueAccess(in_q, out_q)

        for i in range(num):
            t = Thread(target=target_f, args=target_args)
            t.setDaemon(False)
            t.start()

    @classmethod
    def get(self, name):
        return self._pool[name]


def curry(f, *arg, **kw):
    def curried(*more_args, **more_kw):
        return f(*(arg + more_args), **dict(kw, **more_kw))
    return curried
