import exceptions

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

    """
    Writer class buffering data.

    It buffers data up to capacity length.
    If no_split is set, data submitted in one write won't be broken into more
    chunks.
    """

    def __init__(self, capacity=4096, no_split=False):
        self.capacity = capacity
        if no_split:
            self.quant = None
        else:
            self.quant = self.capacity
        self.buffer = ""

    def cache_append(self, data):
        self.buffer += data

    def cache_len(self):
        return len(self.buffer)

    def cache_get(self, length=None):
        if length is None or length >= len(self.buffer):
            return self.buffer
        else:
            return self.buffer[:length]

    def cache_pop(self, length):
        if length >= len(self.buffer):
            self.buffer = ""
        else:
            self.buffer = self.buffer[length:]

    def write_(self):
        while self.cache_len() >= self.capacity:
            data = self.cache_get(self.quant)
            self.send(data)
            self.cache_pop(len(data))

    def write(self, obj):
        self.cache_append(self.repr(obj))
        self.write_()

    def flush(self):
        if self.cache_len() > 0:
            data = self.cache_get()
            self.send(data)
            self.cache_pop(len(data))

class JournallingWriter(CachingWriter):

    """
    Writer saving all data to a journal.

    Subclass should override set_offset to write to persistent location.
    """

    def __init__(self, journal, offset=-1, capacity=4096, no_split=False):
        """
        journal: file-like object.
        offset: position of data which were not sent. -1 - EOF.
        """
        self.journal = journal
        if offset < 0:
            self.journal.seek(0, 2)
            self.set_offset(self.journal.tell())
            unflushed_cache = ""
        else:
            self.set_offset(offset)
            self.journal.seek(offset)
            unflushed_cache = self.journal.read()
        CachingWriter.__init__(self, capacity=capacity, no_split=no_split)
        if unflushed_cache:
            CachingWriter.cache_append(self, unflushed_cache)
            self.write_()

    def cache_append(self, data):
        self.journal.write(data)
        CachingWriter.cache_append(self, data)

    def cache_pop(self, length):
        self.set_offset(self.get_offset()+length)
        CachingWriter.cache_pop(self, length)

    def set_offset(self, offset):
        self._offset = offset

    def get_offset(self):
        return self._offset


if __name__ == '__main__':
    from beah.misc import assertp as assertf

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

    l = []
    wr = CachingWriter(4, True)
    wr.repr = lambda obj: "%s" % obj
    wr.send = l.append
    wr.write('0')
    assertf(l, [])
    wr.write('12')
    assertf(l, [])
    wr.write('345678')
    assertf(l, ['012345678'])
    wr.write('0')
    assertf(l, ['012345678'])
    wr.write('1')
    assertf(l, ['012345678'])
    wr.write('2')
    assertf(l, ['012345678'])
    wr.write('3')
    assertf(l, ['012345678', '0123'])
    wr.write('012')
    wr.close()
    assertf(l, ['012345678', '0123', '012'])

    class TestWriter(JournallingWriter):
        def __init__(self, ss, l, offs=-1, wroff=lambda x: None):
            self.l = l
            self.wroff = wroff
            JournallingWriter.__init__(self, ss, offs, 4)
        def set_offset(self, offs):
            self.wroff(offs)
            JournallingWriter.set_offset(self, offs)
        def repr(self, obj):
            return "%s" % obj
        def send(self, data):
            self.l.append(data)
        def clear(self):
            # close without flushing
            self.wroff = lambda x: None
            self.cache_pop(len(self.cache_get()))
            self.close()

    class MemoryCell(object):
        def __init__(self, value=0): self.value = value
        def set(self, offset): self.value = offset
        def get(self): return self.value

    from StringIO import StringIO

    mem = MemoryCell()
    wroff = mem.set
    l = []
    l_expected = []
    ss = StringIO()
    ss_expected = StringIO()

    def test():
        assertf(l, l_expected)
        assertf(ss.getvalue(), ss_expected.getvalue())
        assertf(mem.get(), sum([len(str_) for str_ in l_expected]))
    def test_wr(str_, new_items):
        ss_expected.write(str_)
        wr.write(str_)
        l_expected.extend(new_items)
        test()

    wr = TestWriter(ss, l, -1, wroff)
    test()
    test_wr('012345', ['0123'])
    test_wr('', [])
    test_wr('6', [])
    test_wr('7', ['4567'])
    test_wr('8901', ['8901'])
    test_wr('2', [])
    wr.clear()
    test()

    wr = TestWriter(ss, l, mem.get(), wroff)
    test()

    test_wr('34', [])

    wr.flush()
    l_expected.append('234')
    test()

    test_wr('012345', ['0123'])

    wr.close()
    l_expected.append('45')
    test()

