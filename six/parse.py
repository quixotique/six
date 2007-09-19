# vim: sw=4 sts=4 et fileencoding=latin1 nomod

r'''Data file parsing.
'''

import re
import codecs
from six.input import *
from six.multidict import multidict
from six.struct import struct

def lines(path):
    firstline = file(path).readline()
    m = re.search(r'coding[=:]\s*([-\w.]+)', firstline)
    encoding = 'ascii'
    if m:
        encoding = m.group(1)
    lnum = 1
    try:
        for line in codecs.open(path, 'r', encoding):
            yield itext.new(line, loc=iloc(path=path, line=lnum, column=1))
            lnum += 1
    except UnicodeDecodeError, e:
        raise InputError(e, loc=iloc(path=path, line=lnum))

def remove_comments(lines):
    r'''Filter out comment lines.'''
    for line in lines:
        if not line.startswith('#'):
            yield line

def blocks(lines):
    r'''Group lines into blocks.  Blocks are continguous sequences of lines
    separated by one or more blank lines, and are yielded as lists of lines.
    '''
    block = []
    for line in lines:
        if line.isspace():
            if block:
                yield block
                block = []
        else:
            block.append(line)
    if block:
        yield block

def is_control_line(line):
    r'''Return true if the given line is a control line.
    '''
    return control_text(line) is not None

def control_text(line):
    if line.startswith('%'):
        return line[1:]
    return None

def controls(block, dispatch):
    r'''Parse a block of control lines by dispatching the real work to a
    mapping keyed by the first word following the leading '%', and yielding a
    callable that is passed the remainder of the line as its single argument,
    or no argument if there is no remaining text.  Handle continuation lines.

        >>> res = []
        >>> controls(['%a 1\n', '%a 2\n', '%  3\n', '%b\n'], \
        ...     {'a':lambda a: res.append('a' + a), \
        ...      'b':lambda: res.append('b')})
        >>> res
        ['a1', 'a2 3', 'b']
    '''
    lines = []
    for line in block + [None]:
        if line is not None:
            text = control_text(line)
            if text is None:
                raise InputError('illegal non-control line in a control block',
                                 line=line)
            if text.endswith('\n'):
                text = text[:-1]
            cont = text.lstrip()
            if len(cont) != 0 and len(cont) != len(text):
                if len(lines) == 0:
                    raise InputError('misplaced continuation line', line=line)
                lines.append(' ')
                lines.append(cont)
                continue
        if len(lines) != 0:
            control = type(lines[0])().join(lines)
            lines = []
            spl = control.split(None, 1)
            word1 = spl.pop(0)
            try:
                func = dispatch[word1]
            except KeyError:
                raise InputError('unsupported control "%s"' % ('%' + word1),
                                 line=control)
            try:
                func(*spl)
            except TypeError:
                if spl:
                    raise InputError('unwanted extra text after "%s"' %
                                     ('%' + word1), char=spl[0])
                raise InputError('%s requires extra text' % ('%' + word1),
                                 line=control)
        assert len(lines) == 0
        if line is not None:
            lines.append(text)

def parts(block):
    r'''Split a data block into parts, and return a dictionary that maps from
    delimiter to a list of parts that start with that delimiter.  Parts are
    delimited by lines containing a single character.  The first part has an
    implicit preceding '' delimiter.

        >>> p = parts([':\n', 'a 1\n', 'b 2\n', 'a 3\n', ';\n', 'g 10\n', 'h 11\n'])
        >>> sorted(p.iterkeys())
        [':', ';']
        >>> p[':']
        [Part(data=[('a', '1'), ('a', '3'), ('b', '2')], delim=':')]
        >>> p[';']
        [Part(data=[('g', '10'), ('h', '11')], delim=';')]

    '''
    parts = {}
    lines = list(block)
    while lines:
        line = lines[0]
        n = len(lines)
        part = Part.parse(lines)
        if len(lines) == n:
            raise InputError('malformed line', line=lines[0])
        if len(part) == 0:
            raise InputError('empty part', line=line)
        if part.delim is None:
            part.delim = ''
        parts.setdefault(part.delim, []).append(part)
    return parts

class dataset(object):

    r'''A dataset holds the keys and values parsed from a sequence of input
    lines.  Indented lines are parsed into their own, sub-dataset which is
    attached to the value of the immediately preceding non-indented line.

        >>> d = dataset([('a','1'), ('b','2'), ('a','3'), ('c','4')], loc=10)
        >>> d.loc()
        10
        >>> eval(repr(d)) == d
        True
        >>> len(d)
        4
        >>> 'a' in d
        True
        >>> '1' in d
        False
        >>> d.get('a')
        Traceback (most recent call last):
        InputError: duplicate 'a'
        >>> d.mget('a')
        [('1', None), ('3', None)]
        >>> d.get('b')
        ('2', None)
        >>> d.mget('b')
        [('2', None)]
        >>> d.get('d')
        Traceback (most recent call last):
        InputError: 10: missing 'd'
        >>> d.getvalue('a')
        Traceback (most recent call last):
        InputError: duplicate 'a'
        >>> d.mgetvalue('a')
        ['1', '3']
        >>> d.getvalue('b')
        '2'
        >>> d.mgetvalue('b')
        ['2']

    '''

    def __init__(self, data=None, loc=None):
        self.__data = multidict()
        self._loc = loc
        if data is not None:
            try:
                items = data.iteritems()
            except AttributeError:
                items = iter(data)
            for key, value in items:
                if not isinstance(key, basestring):
                    raise TypeError('dataset key must be a string')
                if isinstance(value, tuple) and len(value) == 2:
                    if not isinstance(value[0], basestring):
                        raise TypeError('dataset value must be a string')
                    if not isinstance(value[1], dataset):
                        raise TypeError('dataset sub must be a dataset')
                    self.__data[key] = struct(value=value[0], sub=value[1])
                else:
                    if not isinstance(value, basestring):
                        raise TypeError('dataset value must be a string')
                    self.__data[key] = struct(value=value, sub=None)

    def loc(self):
        r'''This method allows a dataset object to be passed to InputError to
        give the location of the error.
        '''
        return self._loc

    def __repr__(self):
        args, kwargs = self._repr_initargs()
        return '%s(%s)' % (self.__class__.__name__,
                ', '.join(map(repr, args) +
                          ['%s=%r' % i for i in sorted(kwargs.iteritems())]))

    def _repr_initargs(self):
        a = []
        kw = {}
        # Doesn't really need to be sorted except to help doctests.
        for key, value in sorted(self.__data.iteritems(),
                                 key=lambda i: (i[0], i[1].value)):
            if value.sub is not None:
                a.append((key, (value.value, value.sub)))
            else:
                a.append((key, value.value))
        if self._loc is not None:
            kw['loc'] = self._loc
        return [a], kw

    def __eq__(self, other):
        if not isinstance(other, dataset):
            return NotImplemented
        return self.__data == other.__data

    def __ne__(self, other):
        if not isinstance(other, dataset):
            return NotImplemented
        return self.__data != other.__data

    @classmethod
    def parse(class_, lines):
        r'''Parse a list of lines into a dataset, consuming the successfully
        parsed lines from the list.  Return the parsed dataset upon
        encountering a malformed line, leaving that line and all following
        lines in the list.

            >>> lines = ['a 1\n', 'a 2\n', 'a 3\n', 'b 4\n', ' x 10\n', ' y 11\n', 'c 5\n', '+\n']
            >>> d = dataset.parse(lines)
            >>> lines
            ['+\n']
            >>> len(d)
            5
            >>> sorted(d.iterkeys())
            ['a', 'b', 'c']
            >>> d['a']
            [('1', None), ('2', None), ('3', None)]
            >>> d['b']
            [('4', dataset([('x', '10'), ('y', '11')]))]
        '''
        ds = class_()
        class_._parse(ds, lines)
        return ds

    @staticmethod
    def _parse(ds, lines):
        stack = [struct(indent=0, data=ds, lastkey=None)]
        while len(lines):
            line = lines[0]
            l = line.lstrip()
            indent = len(line) - len(l)
            spl = l.rstrip().split(None, 1)
            if len(spl) != 2:
                break
            lines.pop(0)
            assert indent >= 0
            if indent < stack[-1].indent:
                while indent < stack[-1].indent:
                    s = stack.pop()
                    assert len(stack) > 0
                    assert stack[-1].lastkey is not None
                    assert stack[-1].data.__data[stack[-1].lastkey][-1].sub is None
                    if len(s.data.__data):
                        stack[-1].data.__data[stack[-1].lastkey][-1].sub = s.data
                if indent != stack[-1].indent:
                    raise InputError('illegal indentation', line=line)
            elif indent > stack[-1].indent:
                if stack[-1].lastkey is None:
                    raise InputError('illegal indentation', line=line)
                stack.append((struct(indent=indent, data=dataset(), lastkey=None)))
            key, value = spl
            stack[-1].data.__data[key] = struct(value=value, sub=None)
            stack[-1].lastkey = key
        while len(stack) > 1:
            s = stack.pop()
            assert stack[-1].lastkey is not None
            assert stack[-1].data.__data[stack[-1].lastkey][-1].sub is None
            if len(s.data.__data):
                stack[-1].data.__data[stack[-1].lastkey][-1].sub = s.data

    def __len__(self):
        r'''Return the number of key-value pairs in the current dataset (not
        counting pairs in sub-datasets).
        '''
        return len(self.__data)

    def __iter__(self):
        r'''Iterate through the keys.
        '''
        return iter(self.__data)

    def __contains__(self, key):
        r'''Return true if the dataset contains at least one value for the
        given key.
        '''
        return key in self.__data

    def iterkeys(self):
        r'''Return an iterable over all the keys in the dataset (excluding keys
        in sub-datasets).
        '''
        return self.__data.iterkeys()

    def itervalues(self):
        r'''Return an iterable over of all the values (value, sub) in the
        dataset (excluding keys in sub-datasets).
        '''
        for value in self.__data.itervalues():
            yield (value.value, value.sub)

    def iteritems(self):
        r'''Return an iterable over of all the key-value pairs in the dataset
        (excluding keys in sub-datasets).
        '''
        for key, value in self.__data.iteritems():
            yield (key, (value.value, value.sub))

    def __getitem__(self, key):
        r'''Return a list of (value, sub) tuples for the given key.  'sub' is a
        dataset containing any data that is subject to the given key-value.  If
        there is no such key, raise KeyError.
        '''
        return [(s.value, s.sub) for s in self.__data[key]]

    def locs(self, key):
        r'''Return a list of non-None loc_of(value) for all the values
        associated with the given key.  If there is no such key, raise
        KeyError.
        '''
        return [loc for loc in (loc_of(value) for value, sub in self[key])
                    if loc is not None]

    def get(self, key, *args):
        r'''Return the single (value, sub) pair associated with the given
        key.  If there is no such key, return args[0], or raise InputError if
        no extra argument was given.  If there is more than one value for the
        given key, raise InputError.
        '''
        if len(args) > 1:
            raise TypeError('get() takes at most 3 arguments (%s given)' %
                            (2 + len(args)))
        try:
            value = self[key]
        except KeyError:
            if len(args):
                return args[0]
            raise InputError('missing %r' % key, line=self)
        assert len(value) >= 1
        if len(value) == 1:
            return value[0]
        raise InputError('duplicate %r' % key, line=value[1][0])

    def mget(self, key, *args):
        r'''Return a list of (value, sub) pairs associated with the given key.
        Equivalent to self[key] except that if there is no such key, returns
        args[0] or raises InputError (not KeyError) if no extra argument was
        passed.
        '''
        if len(args) > 1:
            raise TypeError('mget() takes at most 3 arguments (%s given)' %
                            (2 + len(args)))
        try:
            return self[key]
        except KeyError:
            if len(args):
                return args[0]
            raise InputError('missing %r' % key, line=self)

    def getvalue(self, key, *args):
        r'''Return the single value associated with the given key, ensuring
        that there is no sub-dataset associated with the value (raise
        InputError if there is).  If there is no such key, raise KeyError.  If
        there is more than one value for the given key, raise InputError.
        '''
        if len(args) > 1:
            raise TypeError('getvalue() takes at most 3 arguments (%s given)' %
                            (2 + len(args)))
        try:
            value = self[key]
        except KeyError:
            if len(args):
                return args[0]
            raise InputError('missing %r' % key, line=self)
        assert len(value) >= 1
        if len(value) != 1:
            raise InputError('duplicate %r' % key, line=value[1][0])
        value, sub = value[0]
        if sub is not None:
            raise InputError('spurious data', lines=sub)
        return value

    def mgetvalue(self, key, *args):
        r'''Return a list of the values associated with the given key, ensuring
        that there is no sub-dataset associated with any of the values (raise
        InputError if there is).  If there is no such key, raise KeyError.
        '''
        if len(args) > 1:
            raise TypeError('mgetvalue() takes at most 3 arguments (%s given)' %
                            (2 + len(args)))
        try:
            values = []
            for value, sub in self[key]:
                if sub is not None:
                    raise InputError('spurious data', lines=sub)
                values.append(value)
            return values
        except KeyError:
            if len(args):
                return args[0]
            raise InputError('missing %r' % key, line=self)

class dataset_loc_memo(object):

    r'''A wrapper around a dataset that remembers all the values that have been
    fetched using the get(), mget(), getvalue(), and mgetvalue() methods.
    
        >>> dc = dataset([('x', itext.new('8',8)), ('y', itext.new('9',9))], \
        ...              loc=15)
        >>> d = dataset([('a',itext.new('1',1)), ('b',itext.new('2',2)), \
        ...              ('a',itext.new('3',3)), ('c',(itext.new('4',4),dc))], \
        ...              loc=10)
        >>> m = dataset_loc_memo(d)
        >>> m.loc()
        10
        >>> eval(repr(m)) == m
        True
        >>> len(m)
        4
        >>> 'a' in m
        True
        >>> '1' in m
        False
        >>> m.memo
        set([])
        >>> m.get('a')
        Traceback (most recent call last):
        InputError: 3: duplicate 'a'
        >>> m.mget('a')
        [(itext.new(u'1', loc=1), None), (itext.new(u'3', loc=3), None)]
        >>> m.memo == set([1, 3])
        True
        >>> m.get('b')
        (itext.new(u'2', loc=2), None)
        >>> m.memo == set([1, 2, 3])
        True
        >>> m.mget('b')
        [(itext.new(u'2', loc=2), None)]
        >>> m.memo == set([1, 2, 3])
        True
        >>> m.get('d')
        Traceback (most recent call last):
        InputError: 10: missing 'd'
        >>> m.getvalue('a')
        Traceback (most recent call last):
        InputError: 3: duplicate 'a'
        >>> m.mgetvalue('a')
        [itext.new(u'1', loc=1), itext.new(u'3', loc=3)]
        >>> m.getvalue('b')
        itext.new(u'2', loc=2)
        >>> m.mgetvalue('b')
        [itext.new(u'2', loc=2)]
        >>> m.memo == set([1, 2, 3])
        True
        >>> m.getvalue('c')
        Traceback (most recent call last):
        InputError: spurious data
        >>> m.get('c')[0]
        itext.new(u'4', loc=4)
        >>> m.memo == set([1, 2, 3, 4])
        True
        >>> m.get('c')[1].getvalue('x')
        itext.new(u'8', loc=8)
        >>> m.memo == set([1, 2, 3, 4, 8])
        True
        >>> set(m.all_locs()) == set([1, 2, 3, 4, 8, 9])
        True

    '''

    def __init__(self, ds, memo=None):
        r'''
        @param ds: the dataset to wrap
        @type  ds: dataset
        @param memo: a set or set-like object to which values are added; if
            None then a new empty set is created and used
        '''
        self.__dataset = ds
        self.__subs = {}
        if memo is None:
            memo = set()
        self.memo = memo

    def __getattr__(self, name):
        r'''Delegate all fetches of non-defined attributes to the wrapped
        dataset.'''
        return getattr(self.__dataset, name)

    def __repr__(self):
        return '%s(%r, memo=%r)' % (self.__class__.__name__, self.__dataset,
                self.memo)

    def __len__(self):
        return len(self.__dataset)

    def __iter__(self):
        return iter(self.__dataset)

    def __contains__(self, key):
        return key in self.__dataset

    def __eq__(self, other):
        r'''Two dataset_loc_memo objects are equal if their wrapped datasets
        are equal.  The memo set is not used in the equality comparison.  A
        dataset_loc_memo object can also be compared for equality to a dataset
        object directly.
        '''
        if isinstance(other, dataset_loc_memo):
            other = other.__dataset
        return self.__dataset == other

    def __ne__(self, other):
        if isinstance(other, dataset_loc_memo):
            other = other.__dataset
        return self.__dataset != other

    def __add(self, value):
        loc = loc_of(value)
        if loc is not None:
            self.memo.add(loc)

    def __sub(self, sub):
        r'''Wrap a sub-dataset in a dataset_loc_memo, and cache the result so
        that we always return the same 'sub' object in successive get() or
        mget() calls.
        '''
        if sub is None:
            return None
        msub = self.__subs.get(sub)
        if msub is None:
            msub = self.__subs[sub] = type(self)(sub, memo=self.memo)
        return msub

    def __getitem__(self, key):
        ret = []
        for value, sub in self.__dataset[key]:
            ret.append((value, self.__sub(sub)))
        return ret

    def get(self, key, *args):
        value, sub = self.__dataset.get(key, *args)
        self.__add(value)
        return value, self.__sub(sub)

    def mget(self, key, *args):
        ret = []
        for value, sub in self.__dataset.mget(key, *args):
            self.__add(value)
            ret.append((value, self.__sub(sub)))
        return ret

    def getvalue(self, key, *args):
        value = self.__dataset.getvalue(key, *args)
        self.__add(value)
        return value

    def mgetvalue(self, key, *args):
        values = self.__dataset.mgetvalue(key, *args)
        for value in values:
            self.__add(value)
        return values

    def all_locs(self):
        r'''Return an iterable over the loc()s of all the values in the wrapped
        dataset, including in all sub datasets.
        '''
        return _iterlocs(self.__dataset)

def _iterlocs(ds):
    r'''Used by dataset_loc_memo.all_locs() to recursively iterate over all the
    loc()s of a given dataset.
    '''
    for value, sub in ds.itervalues():
        loc = loc_of(value)
        if loc is not None:
            yield loc
        if sub is not None:
            for loc in _iterlocs(sub):
                yield loc

class Part(dataset):

    r'''A part is a sequence of input lines starting with a delimiter line
    containing a single, non-alpha, non-space character, then followed by
    key-value pairs, in which there may be duplicate keys.  Keys must start
    with an alphbetic character.  The key-value lines are parsed into a
    dataset.
    '''

    def __init__(self, delim=None, data=None, loc=None):
        r'''Construct a Part.

            >>> p = Part(delim='+', data=[('a', '1'), ('b', '2')])
            >>> p
            Part(data=[('a', '1'), ('b', '2')], delim='+')

        '''
        super(Part, self).__init__(data, loc=loc)
        if delim is not None:
            assert len(delim) == 1
            assert not delim.isalpha() and not delim.isspace()
        self.delim = delim

    def _repr_initargs(self):
        a, kw = super(Part, self)._repr_initargs()
        if self.delim is not None:
            kw['delim'] = self.delim
        kw['data'] = a[0]
        return [], kw

    @classmethod
    def parse(class_, lines):
        r'''Parse a list of lines into a Part, popping all parsed lines off
        the list, leaving those that were not parsed.

            >>> lines = ['+\n', 'a 1\n', 'a 2\n', 'a 3\n', '-\n']
            >>> p = Part.parse(lines)
            >>> lines
            ['-\n']
            >>> len(p)
            3
            >>> list(p.iterkeys())
            ['a']
            >>> p['a']
            [('1', None), ('2', None), ('3', None)]
            >>> p.delim
            '+'
        '''
        assert len(lines) != 0
        line = lines[0]
        loc = None
        if hasattr(line, 'loc') and callable(line.loc):
            loc = line.loc()
        delim = None
        if (len(line) == 2 and
                not (line[0].isalpha() or line[0].isspace()) and
                line[1] == '\n'):
            delim = line[0]
            lines.pop(0)
        part = class_(delim=delim, loc=loc)
        dataset._parse(part, lines)
        for key in part.iterkeys():
            try:
                codecs.ascii_encode(key)
            except UnicodeError:
                raise InputError('invalid key - not ASCII', char=key)
            if not key[0].isalpha():
                raise InputError('invalid key - must start with letter',
                                 char=key)
        return part
