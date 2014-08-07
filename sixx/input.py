# vim: sw=4 sts=4 et fileencoding=utf8 nomod

r'''Traceable input.  An L{itext} string keeps track of the origin of every one
of its characters using an L{iloc} object, which stores a path name, line
number, and column number.  Slices of L{itext} strings are also L{itext}
strings.  This makes it easy for an application to generate helpful diagnostic
messages based on any fragment of the input, because the L{itext} string will
correctly supply the location of that fragment in the application's input.

'''
import collections



__all__ = ['itext', 'iloc', 'InputError', 'loc_of']

class itext(str):

    r'''All input text is treated as Unicode.

        >>> l = itext('abc\n', loc=50)
        >>> l
        itext('abc\n', loc=50)
        >>> str(l)
        'abc\n'
        >>> len(l)
        4
        >>> l.loc()
        50
    '''

    def __new__(cls, text='', loc=None):
        r'''Since we're overriding the builtin L{str} class, we can't mess
        with the constructor, so we use this special class method to construct
        itext instances.
        @param text: any object that supports str(text)
        @param loc: either None or any object that supports integer addition
            and subtraction: loc +- int -> loc
        '''
        obj = super(itext, cls).__new__(cls, text)
        obj.__loc = []
        if loc is not None:
            obj.__loc.append((0, len(obj), loc))
        return obj

    def __reduce__(self):
        r'''We pickle ourselves to a string.
        '''
        return (str, (str(self),))

    def loc(self):
        r'''Return the location of the first "located" character in this
        string, or if the string has no location, then return None.

            >>> a = itext('abc\n', loc=5)
            >>> a.loc()
            5
            >>> b = '...' + a
            >>> b
            itext('...')+itext('abc\n', loc=5)
            >>> b.loc()
            5
            >>> b[0]
            itext('.')
            >>> b[0].loc() is None
            True
        '''
        if not self.__loc:
            return None
        return self.__loc[0][2]

    def __repr__(self):
        r'''The repr() of an L{itext} string is an expression which can be
        evaluated to create an identical string.

            >>> a = itext('abc\n', loc=5)
            >>> b = 'xyz' + a + 'def' + a + 'ghi'
            >>> b
            itext('xyz')+itext('abc\n', loc=5)+itext('def')+itext('abc\n', loc=5)+itext('ghi')
            >>> b == eval(repr(b))
            True
        '''
        classname = self.__class__.__name__
        r = []
        pos = 0
        for start, end, loc in self.__loc:
            assert start >= pos
            if pos != start:
                r.append('%s(%r)' % (classname, str(self)[pos:start]))
            r.append('%s(%r, loc=%r)' % (classname, str(self)[start:end], loc))
            pos = end
        assert pos <= len(self)
        if pos != len(self):
            r.append('%s(%r)' % (classname, str(self)[pos:]))
        return '+'.join(r)

    def __add__(self, text):
        r'''
            >>> a = itext('abc\n', loc=2)
            >>> b = a + 'def'
            >>> b
            itext('abc\n', loc=2)+itext('def')
            >>> b[3]
            itext('\n', loc=5)
            >>> b[4]
            itext('d')
        '''
        if not isinstance(text, str):
            return NotImplemented
        r = type(self)(str(self) + str(text))
        r.__loc = list(self.__loc)
        if isinstance(text, itext):
            for start, end, loc in text.__loc:
                r.__loc.append((start + len(self), end + len(self), loc))
        return r

    def __radd__(self, text):
        r'''
            >>> a = itext('def\n', loc=2)
            >>> b = 'abc' + a
            >>> b
            itext('abc')+itext('def\n', loc=2)
            >>> b[2]
            itext('c')
            >>> b[3]
            itext('d', loc=2)
        '''
        if not isinstance(text, str):
            return NotImplemented
        r = type(self)(str(text) + str(self))
        r.__loc = []
        if isinstance(text, itext):
            r.__loc.extend(text.__loc)
        for start, end, loc in self.__loc:
            r.__loc.append((start + len(text), end + len(text), loc))
        return r

    def __makeslice(self, text, start=0):
        loc = []
        assert type(text) is str
        r = type(self)(text)
        assert len(r) <= len(self)
        if len(r):
            end = start + len(r)
            for s, e, l in self.__loc:
                if s <= start:
                    if e > start:
                        loc.append((0, min(len(r), e - start), l + start - s))
                elif s < end:
                    loc.append((s - start, min(len(r), e - start), l))
        assert len(r.__loc) == 0
        r.__loc.extend(loc)
        return r

    def __getitem__(self, i):
        r'''A single char is an L{itext} with an offset loc.

            >>> l = itext('abc\n', loc=5)
            >>> l[1]
            itext('b', loc=6)
            >>> l[-2]
            itext('c', loc=7)

        A slice is an L{itext} with an offset loc.

            >>> a = itext('abc\n', loc=5)
            >>> a[1:]
            itext('bc\n', loc=6)
            >>> a[:-2]
            itext('ab', loc=5)
            >>> a[-3:-1]
            itext('bc', loc=6)
            >>> b = 'xyz' + a + 'def' + a + 'ghi'
            >>> b[2:8]
            itext('z')+itext('abc\n', loc=5)+itext('d')
            >>> b[4:11]
            itext('bc\n', loc=6)+itext('def')+itext('a', loc=5)
        '''
        if type(i) is slice:
            i, j = i.start, i.stop
        else:
            if i < 0:
                i += len(self)
            if not 0 <= i < len(self):
                raise IndexError('string index out of range')
            j = i + 1
        if i is None:
            i = 0
        elif i < 0:
            i += len(self)
            if i < 0:
                i = 0
        elif i > len(self):
            i = len(self)
        if j is None or j > len(self):
            j = len(self)
        elif j < 0:
            j += len(self)
            if j < 0:
                j = 0
        return self.__makeslice(str(self)[i:j], i)

    def split(self, sep=None, maxsplit=-1):
        r'''
            >>> a = itext('  abc\nabc \n abc \n', loc=10)
            >>> a.split('b')
            [itext('  a', loc=10), itext('c\na', loc=14), itext('c \n a', loc=18), itext('c \n', loc=24)]
            >>> a.split()
            [itext('abc', loc=12), itext('abc', loc=16), itext('abc', loc=22)]

            >>> b = ' a ' + itext(' b', loc=2) + '  c' + itext('d  ', loc=100) + 'e'
            >>> b.split()
            [itext('a'), itext('b', loc=3), itext('c')+itext('d', loc=100), itext('e')]
        '''
        uni = str(self)
        spl = uni.split(sep, maxsplit)
        pos = 0
        r = []
        for u in spl:
            if sep is None:
                pos += len(uni[pos:]) - len(uni[pos:].lstrip())
            r.append(self.__makeslice(u, pos))
            pos += len(u)
            if sep is not None:
                pos += len(sep)
        return r

    def splitlines(self, keepends=False):
        r'''
            >>> a = itext('  abc\nabc \n abc \n', loc=10)
            >>> a.splitlines()
            [itext('  abc', loc=10), itext('abc ', loc=16), itext(' abc ', loc=21)]
            >>> a.splitlines(True)
            [itext('  abc\n', loc=10), itext('abc \n', loc=16), itext(' abc \n', loc=21)]
        '''
        uni = str(self)
        spl = uni.splitlines(keepends)
        pos = 0
        r = []
        for u in spl:
            r.append(self.__makeslice(u, pos))
            pos += len(u)
            if not keepends:
                pos += 1
        return r

    def join(self, seq):
        r'''
            >>> itext('x', loc=1).join(['a', itext('b'), itext('c', loc=10)])
            itext('a')+itext('x', loc=1)+itext('b')+itext('x', loc=1)+itext('c', loc=10)
        '''
        r = type(self)(str(self).join(seq))
        pos = 0
        assert len(r.__loc) == 0
        if len(seq):
            if isinstance(seq[0], itext):
                for start, end, loc in seq[0].__loc:
                    r.__loc.append((start + pos, end + pos, loc))
            pos += len(seq[0])
            for elt in seq[1:]:
                for start, end, loc in self.__loc:
                    r.__loc.append((start + pos, end + pos, loc))
                pos += len(self)
                if isinstance(elt, itext):
                    for start, end, loc in elt.__loc:
                        r.__loc.append((start + pos, end + pos, loc))
                pos += len(elt)
        return r

    def strip(self, chars=None):
        r'''
            >>> a = itext('  abc  \n', loc=1)
            >>> a.strip()
            itext('abc', loc=3)
        '''
        return self.lstrip(chars).rstrip(chars)

    def lstrip(self, chars=None):
        r'''
            >>> a = itext('  abc  \n', loc=3)
            >>> a.lstrip()
            itext('abc  \n', loc=5)
        '''
        s = str.lstrip(self, chars)
        return self.__makeslice(s, start= len(self) - len(s))

    def rstrip(self, chars=None):
        r'''
            >>> a = itext('  abc  \n', loc=3)
            >>> a.rstrip()
            itext('  abc', loc=3)
        '''
        return self.__makeslice(str.rstrip(self, chars))

    def capitalize(self):
        r'''
            >>> a = itext('abc', loc=3)
            >>> a.capitalize()
            itext('Abc', loc=3)
        '''
        return self.__makeslice(str.capitalize(self))

    def lower(self):
        r'''
            >>> a = itext('ABc', loc=3)
            >>> a.lower()
            itext('abc', loc=3)
        '''
        return self.__makeslice(str.lower(self))

    def swapcase(self):
        r'''
            >>> a = itext('ABc', loc=3)
            >>> a.swapcase()
            itext('abC', loc=3)
        '''
        return self.__makeslice(str.swapcase(self))

    def title(self):
        r'''
            >>> a = itext('one two THREE', loc=3)
            >>> a.title()
            itext('One Two Three', loc=3)
        '''
        return self.__makeslice(str.title(self))

    def upper(self):
        r'''
            >>> a = itext('Abc', loc=3)
            >>> a.upper()
            itext('ABC', loc=3)
        '''
        return self.__makeslice(str.upper(self))

    def center(self, width, fillchar=' '):
        r'''
            >>> a = itext('abc', loc=3)
            >>> a.center(10)
            itext('   ')+itext('abc', loc=3)+itext('    ')
        '''
        pad = width - len(self)
        return fillchar * (pad // 2) + self + fillchar * ((pad + 1) // 2)

    def ljust(self, width, fillchar=' '):
        r'''
            >>> a = itext('abc', loc=3)
            >>> a.ljust(10)
            itext('abc', loc=3)+itext('       ')
        '''
        return self + fillchar * (width - len(self))

    def rjust(self, width, fillchar=' '):
        r'''
            >>> a = itext('abc', loc=3)
            >>> a.rjust(10)
            itext('       ')+itext('abc', loc=3)
        '''
        return fillchar * (width - len(self)) + self

    def zfill(self, width):
        r'''
            >>> a = itext('abc', loc=3)
            >>> a.zfill(6)
            itext('000')+itext('abc', loc=3)
        '''
        return self.rjust(width, fillchar='0')

class iloc(object):

    r'''Describes the location in the input to which an itext coresponds.
    Suitable for passing as the 'loc' argument of L{itext()}.
    '''

    def __init__(self, path=None, line=None, column=None):
        self.path = path
        self.line = line
        self.column = column

    def as_line(self):
        r'''Return an equivalent iloc object without a column number.
            >>> iloc('wah', 14, 7).as_line()
            iloc(path='wah', line=14)
        '''
        return type(self)(path=self.path, line=self.line)

    def __add__(self, n):
        r'''iloc + int produces a new iloc object if the original iloc object
        has a (non-zero) column number.  Otherwise, it just yields the original
        iloc object.
            >>> iloc('wah', 5, 10) + 3
            iloc(path='wah', line=5, column=13)
            >>> iloc('wah') + 3
            iloc(path='wah')
        '''
        if self.column:
            assert self.column + n > 0
            return type(self)(path=self.path, line=self.line,
                              column=self.column + n)
        return self

    def __sub__(self, n):
        return self.__add__(-n)

    def __str__(self):
        r = []
        if self.path:
            r.append(repr(self.path))
        if self.line:
            r.append('line %d' % self.line)
        if self.column:
            r.append('column %d' % self.column)
        return ', '.join(r)

    def __repr__(self):
        r = []
        if self.path:
            r.append('path=%r' % self.path)
        if self.line:
            r.append('line=%d' % self.line)
        if self.column:
            r.append('column=%d' % self.column)
        return '%s(%s)' % (self.__class__.__name__, ', '.join(r))

    def __lt__(self, other):
        r'''To help in reporting errors in lexical order, iloc objects have a
        natural order.

            >>> iloc('a') < iloc('b')
            True

            >>> iloc('a', 2) > iloc('a', 1)
            True

            >>> iloc('a', 2, 10) < iloc('a', 2, 11)
            True

            >>> iloc('a', 2, 10) > iloc('a', 2)
            True

            >>> iloc('b', 2, 10) > iloc('a', 2, 10)
            True

            >>> iloc('a', 2, 10) == iloc('a', 2, 10)
            True

        '''
        if not isinstance(other, iloc):
            return NotImplemented
        if self.path is None:
            return other.path is not None
        if other.path is None or self.path > other.path:
            return False
        if self.path < other.path:
            return True
        if self.line is None:
            return other.line is not None
        if other.line is None or self.line > other.line:
            return False
        if self.line < other.line:
            return True
        if self.column is None:
            return other.column is not None
        if other.column is None or self.column > other.column:
            return False
        if self.column < other.column:
            return True
        return False

    def __eq__(self, other):
        if not isinstance(other, iloc):
            return NotImplemented
        return self.path == other.path and self.line == other.line and self.column == other.column

    def __hash__(self):
        r'''To allow loc objects to be kept in sets.

            >>> s = set([iloc('a', 2, 10)])
            >>> iloc('a', 2, 10) in s
            True
            >>> iloc('a', 2) in s
            False

        '''
        return hash(self.path) ^ hash(self.line) ^ hash(self.column)

class InputError(Exception):

    r'''
        >>> e = InputError('wah', loc=iloc('name', 4))
        >>> str(e)
        "'name', line 4: wah"

        >>> e = InputError('wah', char=itext('abc', loc=2))
        >>> str(e)
        '2: wah'

        >>> e = InputError('wah', chars=[itext('abc', loc=2), itext('def', loc=1)])
        >>> str(e)
        '1: wah'

        >>> InputError('wah', input=3)
        Traceback (most recent call last):
        TypeError: invalid keyword argument for InputError(): "input="

    '''

    def __init__(self, msg, **kwargs):
        Exception.__init__(self, str(msg))
        if len(kwargs) != 1:
            raise TypeError('%s() expects single keyword arg' %
                            self.__class__.__name__)
        self.loc = None
        try:
            if 'loc' in kwargs:
                self.loc = kwargs['loc']
            elif 'locs' in kwargs:
                self.loc = sorted(kwargs['locs'])[0]
            elif 'chars' in kwargs:
                self.loc = sorted(self._locs_of(kwargs['chars']))[0]
            elif 'char' in kwargs:
                self.loc = loc_of(kwargs['char'])
            elif 'lines' in kwargs:
                self.loc = self._as_line(sorted(self._locs_of(kwargs['lines']))[0])
            elif 'line' in kwargs:
                self.loc = self._as_line(loc_of(kwargs['line']))
            else:
                raise TypeError('invalid keyword argument for %s(): "%s="' %
                                (self.__class__.__name__, list(kwargs.keys())[0]))
        except IndexError:
            pass

    @staticmethod
    def _locs_of(objs):
        return sorted(filter(bool, (loc_of(obj) for obj in objs)))

    @staticmethod
    def _as_line(obj):
        if hasattr(obj, 'as_line') and isinstance(obj.as_line, collections.Callable):
            return obj.as_line()
        return obj

    def __str__(self):
        r = []
        if self.loc is not None:
            r.append(str(self.loc))
        r.append(Exception.__str__(self))
        return ': '.join(r)

def loc_of(obj):
    if hasattr(obj, 'loc') and isinstance(obj.loc, collections.Callable):
        return obj.loc()
    try:
        return obj + 0
    except TypeError:
        return None

