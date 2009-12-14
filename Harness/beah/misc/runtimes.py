import pickle
import exceptions
import traceback
from beah.core.controller import RuntimeBase

class PickleRuntime(RuntimeBase):

    def def_rt():
        return {'variables':{}, 'MAGIC':("CONTROLLER", "RUNTIME"), 'VER':(1, 0)}
    def_rt = staticmethod(def_rt)

    def __init__(self, fname):
        self.__fname = fname
        try:
            f = open(fname, "rb")
            rt = pickle.load(f)
            f.close()
            del f
        except:
            rt = self.def_rt()
        try:
            if not isinstance(rt, dict):
                raise exceptions.TypeError("Runtime should be a dictionary!")
            if rt['MAGIC'] != self.def_rt()['MAGIC']:
                raise exceptions.RuntimeError("MAGIC field has to be set properly!")
            if rt['VER'] != self.def_rt()['VER']:
                raise exceptions.RuntimeError("version does not match!")
        except:
            # FIXME: Handle this: move affected file to other place. Fresh
            # start. Report.
            print "Corrupted runtime file containing %r" % rt
            print traceback.format_exc()
            rt = self.def_rt()
        RuntimeBase.__init__(self, variables=rt['variables'])

    def set_var(self, key, value):
        RuntimeBase.set_var(self, key, value)
        rt = self.def_rt()
        rt['variables'] = self.get_vars()
        f = open(self.__fname, "wb")
        # FIXME: Saving rt as a whole. Optimize if necessary, but at the moment
        # RT will be rather small
        pickle.dump(rt, f)
        f.close()

if __name__ == '__main__':

    say_hi = 'Hello World!'

    rt = PickleRuntime('/tmp/pickleruntime.tmp')
    rt.set_var('say_hi', say_hi)
    del rt

    rt = PickleRuntime('/tmp/pickleruntime.tmp')
    assert rt.get_var('say_hi') == say_hi
    del rt

