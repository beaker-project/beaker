from threading import Thread, Event
import Queue, copy
from logging import getLogger

log = getLogger(__name__)

class _QueueAccess:

    def __init__(self, in_q, out_q):
        self.in_queue = in_q
        self.out_queue = out_q


class BkrThreadPool:
    _qpool = {}
    _tpool = {}

    @classmethod
    def create_and_run(cls, name, target_f, target_args, num=30, *args, **kw):
        if name in cls._qpool:
            raise Exception('%s has already been initialised in the BkrThreadPool' % name)

        out_q = Queue.Queue()
        in_q = Queue.Queue()
        cls._qpool[name] =  _QueueAccess(in_q, out_q)
        cls._tpool[name] = []
        for i in range(num):
            t = Thread(target=target_f, args=target_args)
            cls._tpool[name].append(t)
            t.setDaemon(False)
            t.start()

    @classmethod
    def get(self, name):
        return self._qpool[name]

    @classmethod
    def join(cls, name, timeout):
        tpool = cls._tpool[name]
        for t in tpool:
            t.join(timeout)
            if t.isAlive():
                log.warn('Thread %s did not shutdown cleanly' % t.ident)


class RepeatTimer(Thread):

    def __init__(self, interval, function, stop_on_exception=True, args=[], kwargs={}):
        Thread.__init__(self)
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.stop_on_exception = stop_on_exception
        self.finished = Event()

    def stop(self):
        self.done = True
        self.finished.set()

    def run(self):
        self.done = False
        while True:
            self.finished.wait(self.interval)
            if self.done:
                self.finished.clear()
                break
            if not self.finished.is_set():
                try:
                    self.function(*self.args, **self.kwargs)
                except Exception, e:
                    if self.stop_on_exception:
                        self.finished.clear()
                        raise
                    # XXX Not strictly for auth'ing, think of something better
                    log.exception('Login Fail')
            self.finished.clear()


def curry(f, *arg, **kw):
    def curried(*more_args, **more_kw):
        return f(*(arg + more_args), **dict(kw, **more_kw))
    return curried
