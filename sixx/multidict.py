# vim: sw=4 sts=4 et fileencoding=utf8 nomod

r'''Multi-value dictionary.
'''

__all__ = ['multidict']

class multidict(object):

    r'''A multidict is a set of key-value pairs in which each key may have one
    or more values.  It behaves as a dict whose values are tuples.  Setting an
    item appends a value to that item's tuple.
    '''

    def __init__(self, data=None):
        r'''Construct a new multidict from either another multidict object, or
        an iterable of (key, value) pairs (or iterables), or a mapping object
        (that supports the iteritems() method).
        '''
        self.__data = {}
        self.__len = 0
        if data is not None:
            self.update(data)

    def __len__(self):
        r'''Returns the total number of values, which may be greater than or
        equal to the number of keys.

            >>> d = multidict(((1, 'a'), (2, 'b'), (3, 'c'), (1, 'A')))
            >>> len(d)
            4
            >>> len(d.keys())
            3
            >>> d[2] = 'B'
            >>> len(d)
            5
            >>> del d[1]
            >>> len(d)
            4
            >>> del d[1]
            >>> len(d)
            3
        '''
        return self.__len

    def __getitem__(self, key):
        r'''Return a tuple of all the values that have been set to this key, in
        the order they were set.  The tuple is guaranteed to be non-empty,
        because if there are no values for the given key, then KeyError is
        raised.

            >>> d = multidict(((1, 'a'), (2, 'b'), (3, 'c'), (1, 'A')))
            >>> d[1]
            ('a', 'A')
            >>> d[2]
            ('b',)
            >>> d[4]
            Traceback (most recent call last):
            KeyError: 4
        '''
        return tuple(self.__data[key])

    def __setitem__(self, key, value):
        r'''Set the key to have the given value.  If the key already has any
        values, then the new value is appended to them.

            >>> d = multidict(((1, 'a'), (2, 'b'), (3, 'c'), (1, 'A')))
            >>> d[4] = 'd'
            >>> d[4]
            ('d',)
            >>> d[2] = 'B'
            >>> d[2]
            ('b', 'B')
        '''
        self.__data.setdefault(key, []).append(value)
        self.__len += 1

    def __delitem__(self, key):
        r'''Remove a single value from the given key; the one most recently
        set.

            >>> d = multidict(((1, 'a'), (2, 'b'), (3, 'c'), (1, 'A')))
            >>> del d[1]
            >>> d[1]
            ('a',)
            >>> del d[1]
            >>> d[1]
            Traceback (most recent call last):
            KeyError: 1
        '''
        vl = self.__data[key]
        assert len(vl) > 0
        assert self.__len > 0
        vl.pop()
        if not vl:
            del self.__data[key]
        self.__len -= 1

    def clear(self):
        r'''Remove all keys and values, leaving the multidict empty.

            >>> d = multidict(((1, 'a'), (2, 'b'), (3, 'c'), (1, 'A')))
            >>> d.clear()
            >>> len(d)
            0
            >>> list(d.keys())
            []
        '''
        self.__data.clear()
        self.__len = 0

    def copy(self):
        r'''Return a shallow copy of the multidict.

            >>> d = multidict(((1, 'a'), (2, 'b'), (3, 'c'), (1, 'A')))
            >>> e = d.copy()
            >>> d == e
            True
            >>> d is e
            False
        '''
        return type(self)(self)

    def has_key(self, key):
        r'''Return true if the multidict contains one or more values for the
        given key.

            >>> d = multidict(((1, 'a'), (2, 'b'), (3, 'c'), (1, 'A')))
            >>> d.has_key(1)
            True
            >>> d.has_key(4)
            False
        '''
        return key in self.__data

    def __contains__(self, key):
        r'''Return true if the multidict contains one or more values for the
        given key.

            >>> d = multidict(((1, 'a'), (2, 'b'), (3, 'c'), (1, 'A')))
            >>> 1 in d
            True
            >>> 4 in d
            False
        '''
        return key in self.__data

    def __iter__(self):
        r'''Same as keys().
        '''
        return iter(self.keys())

    def items(self):
        r'''Return an iterable over (key, (value,...)) tuples in undefined order.

            >>> d = multidict(((1, 'a'), (2, 'b'), (3, 'c'), (1, 'A')))
            >>> sorted(d.items())
            [(1, 'A'), (1, 'a'), (2, 'b'), (3, 'c')]
        '''
        for key, values in self.__data.items():
            for value in values:
                yield key, value

    def keys(self):
        r'''Return an iterable over all keys, in undefined order.

            >>> d = multidict(((1, 'a'), (2, 'b'), (3, 'c'), (1, 'A')))
            >>> sorted(d.keys())
            [1, 2, 3]
        '''
        return self.__data.keys()

    def update(self, *args, **kwargs):
        r'''Add key, value pairs to the multidict, equivalent to doing
        multidict.__setitem__(key, value).  Takes either another multidict
        object, or an iterable of (key, value) pairs (or iterables), or a
        mapping object (that supports the iteritems() method), or zero or more
        keyword arguments.

            >>> d = multidict(((1, 'a'), (2, 'b'), (3, 'c'), (1, 'A')))
            >>> d.update(((1, 'aa'), (2, 'B'), (1, 'AA')))
            >>> d[1]
            ('a', 'A', 'aa', 'AA')
            >>> d[2]
            ('b', 'B')

            >>> d = multidict(((1, 'a'), (2, 'b'), (3, 'c'), (1, 'A')))
            >>> d.update(dict(((1, 'aa'), (2, 'B'), (1, 'AA'))))
            >>> d[1]
            ('a', 'A', 'AA')
            >>> d[2]
            ('b', 'B')

            >>> d = multidict(((1, 'a'), (2, 'b'), (3, 'c'), (1, 'A')))
            >>> d.update(multidict(((1, 'aa'), (2, 'B'), (1, 'AA'))))
            >>> d[1]
            ('a', 'A', 'aa', 'AA')
            >>> d[2]
            ('b', 'B')

        '''
        if args:
            if len(args) > 1:
                raise TypeError('update expected at most 1 arguments, got %d' %
                                len(args))
            try:
                for key, value in args[0].items():
                    self[key] = value
            except AttributeError:
                for key, value in args[0]:
                    self[key] = value
        else:
            for key, value in kwargs.items():
                self[key] = value

    @classmethod
    def fromkeys(class_, seq, value=None):
        r'''Construct a new multidict from the keys in seq.

            >>> d = multidict.fromkeys([1, 2, 3, 1], value='x')
            >>> len(d)
            4
            >>> sorted(d.keys())
            [1, 2, 3]
            >>> d[1]
            ('x', 'x')
            >>> d[2]
            ('x',)
            >>> d[3]
            ('x',)
        '''
        md = class_()
        for key in seq:
            md[key] = value
        return md

    def values(self):
        r'''Return an iterator over values in undefined order.

            >>> d = multidict(((1, 'a'), (2, 'b'), (3, 'c'), (1, 'A')))
            >>> sorted(d.values())
            ['A', 'a', 'b', 'c']
        '''
        for values in self.__data.values():
            for value in values:
                yield value

    def get(self, key, value=None):
        r'''Return self[key] if key is in self, otherwise return value.

            >>> d = multidict(((1, 'a'), (2, 'b'), (3, 'c'), (1, 'A')))
            >>> d.get(1)
            ('a', 'A')
            >>> d.get(2)
            ('b',)
            >>> d.get(4) is None
            True
        '''
        try:
            return self[key]
        except KeyError:
            return value

    def setdefault(self, key, value=None):
        r'''Return self[key] if key is in self, otherwise set self[key] = value
        and return (value,).

            >>> d = multidict(((1, 'a'), (2, 'b'), (3, 'c'), (1, 'A')))
            >>> d.setdefault(1)
            ('a', 'A')
            >>> d.setdefault(2)
            ('b',)
            >>> d.setdefault(4)
            (None,)
        '''
        try:
            return self[key]
        except KeyError:
            self[key] = value
            return (value,)

    def pop(self, key, *args):
        r'''If key is in self, then do "del self[key] and return the removed
        value, otherwise if value is given, return the value, otherwise raise
        KeyError.

            >>> d = multidict(((1, 'a'), (2, 'b'), (3, 'c'), (1, 'A')))
            >>> d.pop(1, 'x')
            'A'
            >>> d.pop(1, 'x')
            'a'
            >>> d.pop(1, 'x')
            'x'
            >>> d.pop(1)
            Traceback (most recent call last):
            KeyError: 1
        '''
        if len(args) > 2:
            raise TypeError('pop expected at most 2 arguments, got %d' %
                            len(args) + 1)
        try:
            ret = self[key][-1]
            del self[key]
            return ret
        except KeyError:
            if args:
                return args[0]
            raise

    def popitem(self):
        r'''Return an arbitrary (key, value) pair from the multidict, deleting
        it in the process.  Raise KeyError if the dictionary is empty.

            >>> d = multidict(((1, 'a'), (2, 'b'), (3, 'c'), (1, 'A')))
            >>> items = []
            >>> while d:
            ...     items.append(d.popitem())
            >>> sorted(items)
            [(1, 'A'), (1, 'a'), (2, 'b'), (3, 'c')]
        '''
        if self.__len == 0:
            raise KeyError('popitem(): multidict is empty')
        assert len(self.__data) != 0
        key = next(iter(self.__data.keys()))
        return key, self.pop(key)

    def __eq__(self, other):
        r'''Return true if 'other' is a mapping with the same length and
        containing identical (key, value) pairs.
        '''
        try:
            if len(other) != self.__len:
                return False
            for key, value in other.items():
                if key not in self.__data or value not in self.__data[key]:
                    return False
            return True
        except AttributeError:
            return NotImplemented

    def __ne__(self, other):
        ret = self.__eq__(other)
        if ret is not NotImplemented:
            ret = not ret
        return ret

    def __hash__(self):
        h = 0
        for key, values in self.__data.items():
            h ^= hash(key)
            for value in values:
                h ^= hash(value)
        return h
