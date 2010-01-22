class Writer(object):

    # PUBLIC INTERFACE:

    def write(self, obj):
        self.send(self.repr(obj))

    def flush(self):
        pass

    def close(self):
        self.flush()

    # METHODS TO OVERRIDE:

    def repr(self, obj):
        """
        Data transformation function.

        This method should return obj's representation understood by receiver.
        """
        return obj

    def send(self, data):
        """
        Write data to receiver.
        """
        pass

class CachingWriter(Writer):

    def __init__(self, capacity=4096):
        self.capacity = capacity
        self.buffer = ""

    def write(self, obj):
        self.buffer += self.repr(obj)
        l = self.capacity
        while len(self.buffer) >= l:
            self.send(self.buffer[:l])
            self.buffer = self.buffer[l:]

    def flush(self):
        if self.buffer:
            self.send(self.buffer)
            self.buffer = ""

if __name__ == '__main__':
    def assert_(result, *expecteds):
        for expected in expecteds:
            if result == expected:
                return result
        print >> sys.stderr, "ERROR: got %r\n\texpected: %r" % (result, expecteds)
        assert result == expected
    def printr(obj):
        print "%r" % obj
        return obj
    def assertp(result, *expecteds):
        print "OK: %r" % assert_(result, *expecteds)
        return result
    assertf = assertp

    l = []
    wr = Writer()
    wr.repr = lambda obj: "%r\n" % obj
    wr.send = l.append
    wr.write(1)
    assertf(l, ['1\n'])
    wr.write('a')
    assertf(l, ['1\n', "'a'\n"])

    l = []
    wr = CachingWriter(4)
    wr.repr = lambda obj: "%s" % obj
    wr.send = l.append
    wr.write('012345')
    assertf(l, ['0123'])
    wr.write('')
    assertf(l, ['0123'])
    wr.write('6')
    assertf(l, ['0123'])
    wr.write('789012')
    assertf(l, ['0123', '4567', '8901'])
    wr.flush()
    assertf(l, ['0123', '4567', '8901', '2'])
    wr.write('012345')
    assertf(l, ['0123', '4567', '8901', '2', '0123'])
    wr.close()
    assertf(l, ['0123', '4567', '8901', '2', '0123', '45'])

