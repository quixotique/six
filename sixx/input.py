# vim: sw=4 sts=4 et fileencoding=latin1 nomod

r'''Traceable input.  An L{itext} string keeps track of the origin of every one
of its characters using an L{iloc} object, which stores a path name, line
number, and column number.  Slices of L{itext} strings are also L{itext}
strings.  This makes it easy for an application to generate helpful diagnostic
messages based on any fragment of the input, because the L{itext} string will
correctly supply the location of that fragment in the application's input.

'''

from itertools import ifilter

__all__ = ['itext', 'iloc', 'InputError', 'loc_of']

class itext(unicode):

    r'''All input text is treated as Unicode.

        >>> l = itext('abc\n', loc=50)
        >>> l
        itext(u'abc\n', loc=50)
        >>> str(l)
        'abc\n'
        >>> len(l)
        4
        >>> l.loc()
        50
    '''

    def __new__(cls, text=u'', loc=None):
        r'''Since we're overriding the builtin L{unicode} class, we can't mess
        with the constructor, so we use this special class method to construct
        itext instances.
        @param text: any object that supports unicode(text)
        @param loc: either None or any object that supports integer addition
            and subtraction: loc +- int -> loc
        '''
        obj = super(itext, cls).__new__(cls, text)
        obj.__loc = []
        if loc is not None:
            obj.__loc.append((0, len(obj), loc))
        return obj

    def __reduce__(self):
        r'''We pickle ourselves to a unicode string.
        '''
        return (unicode, (unicode(self),))

    def loc(self):
        r'''Return the location of the first "located" character in this
        string, or if the string has no location, then return None.

            >>> a = itext('abc\n', loc=5)
            >>> a.loc()
            5
            >>> b = u'...' + a
            >>> b
            itext(u'...')+itext(u'abc\n', loc=5)
            >>> b.loc()
            5
            >>> b[0]
            itext(u'.')
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
            >>> b = u'xyz' + a + u'def' + a + u'ghi'
            >>> b
            itext(u'xyz')+itext(u'abc\n', loc=5)+itext(u'def')+itext(u'abc\n', loc=5)+itext(u'ghi')
            >>> b == eval(repr(b))
            True
        '''
        classname = self.__class__.__name__
        r = []
        pos = 0
        for start, end, loc in self.__loc:
            assert start >= pos
            if pos != start:
                r.append('%s(%r)' % (classname,
                        unicode.__getslice__(self, pos, start)))
            r.append('%s(%r, loc=%r)' % (classname,
                     unicode.__getslice__(self, start, end), loc))
            pos = end
        assert pos <= len(self)
        if pos != len(self):
            r.append('%s(%r)' % (classname,
                    unicode.__getslice__(self, pos, len(self))))
        return '+'.join(r)

    def __add__(self, text):
        r'''
            >>> a = itext('abc\n', loc=2)
            >>> b = a + u'def'
            >>> b
            itext(u'abc\n', loc=2)+itext(u'def')
            >>> b[3]
            itext(u'\n', loc=5)
            >>> b[4]
            itext(u'd')
        '''
        if not isinstance(text, basestring):
            return NotImplemented
        r = type(self)(unicode(self) + unicode(text))
        r.__loc = list(self.__loc)
        if isinstance(text, itext):
            for start, end, loc in text.__loc:
                r.__loc.append((start + len(self), end + len(self), loc))
        return r

    def __radd__(self, text):
        r'''
            >>> a = itext('def\n', loc=2)
            >>> b = u'abc' + a
            >>> b
            itext(u'abc')+itext(u'def\n', loc=2)
            >>> b[2]
            itext(u'c')
            >>> b[3]
            itext(u'd', loc=2)
        '''
        if not isinstance(text, basestring):
            return NotImplemented
        r = type(self)(unicode(text) + unicode(self))
        r.__loc = []
        if isinstance(text, itext):
            r.__loc.extend(text.__loc)
        for start, end, loc in self.__loc:
            r.__loc.append((start + len(text), end + len(text), loc))
        return r

    def __makeslice(self, text, start=0):
        loc = []
        assert type(text) is unicode
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
            itext(u'b', loc=6)
            >>> l[-2]
            itext(u'c', loc=7)
        '''
        if i < 0:
            i += len(self)
        if not 0 <= i < len(self):
            raise IndexError('string index out of range')
        return self.__getslice__(i, i + 1)

    def __getslice__(self, i, j):
        r'''A slice is an L{itext} with an offset loc.

            >>> a = itext('abc\n', loc=5)
            >>> a[1:]
            itext(u'bc\n', loc=6)
            >>> a[:-2]
            itext(u'ab', loc=5)
            >>> a[-3:-1]
            itext(u'bc', loc=6)
            >>> b = u'xyz' + a + u'def' + a + u'ghi'
            >>> b[2:8]
            itext(u'z')+itext(u'abc\n', loc=5)+itext(u'd')
            >>> b[4:11]
            itext(u'bc\n', loc=6)+itext(u'def')+itext(u'a', loc=5)
        '''
        if i < 0:
            i = 0
        elif i > len(self):
            i = len(self)
        if j < 0:
            j = 0
        elif j > len(self):
            j = len(self)
        return self.__makeslice(unicode.__getslice__(self, i, j), i)

    def split(self, sep=None, maxsplit=-1):
        r'''
            >>> a = itext('  abc\nabc \n abc \n', loc=10)
            >>> a.split('b')
            [itext(u'  a', loc=10), itext(u'c\na', loc=14), itext(u'c \n a', loc=18), itext(u'c \n', loc=24)]
            >>> a.split()
            [itext(u'abc', loc=12), itext(u'abc', loc=16), itext(u'abc', loc=22)]

            >>> b = u' a ' + itext(' b', loc=2) + u'  c' + itext(u'd  ', loc=100) + u'e'
            >>> b.split()
            [itext(u'a'), itext(u'b', loc=3), itext(u'c')+itext(u'd', loc=100), itext(u'e')]
        '''
        uni = unicode(self)
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
            [itext(u'  abc', loc=10), itext(u'abc ', loc=16), itext(u' abc ', loc=21)]
            >>> a.splitlines(True)
            [itext(u'  abc\n', loc=10), itext(u'abc \n', loc=16), itext(u' abc \n', loc=21)]
        '''
        uni = unicode(self)
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
            >>> itext('x', loc=1).join([u'a', itext(u'b'), itext(u'c', loc=10)])
            itext(u'a')+itext(u'x', loc=1)+itext(u'b')+itext(u'x', loc=1)+itext(u'c', loc=10)
        '''
        r = type(self)(unicode(self).join(seq))
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
            itext(u'abc', loc=3)
        '''
        return self.lstrip(chars).rstrip(chars)

    def lstrip(self, chars=None):
        r'''
            >>> a = itext('  abc  \n', loc=3)
            >>> a.lstrip()
            itext(u'abc  \n', loc=5)
        '''
        s = unicode.lstrip(self, chars)
        return self.__makeslice(s, start= len(self) - len(s))

    def rstrip(self, chars=None):
        r'''
            >>> a = itext('  abc  \n', loc=3)
            >>> a.rstrip()
            itext(u'  abc', loc=3)
        '''
        return self.__makeslice(unicode.rstrip(self, chars))

    def capitalize(self):
        r'''
            >>> a = itext('abc', loc=3)
            >>> a.capitalize()
            itext(u'Abc', loc=3)
        '''
        return self.__makeslice(unicode.capitalize(self))

    def lower(self):
        r'''
            >>> a = itext('ABc', loc=3)
            >>> a.lower()
            itext(u'abc', loc=3)
        '''
        return self.__makeslice(unicode.lower(self))

    def swapcase(self):
        r'''
            >>> a = itext('ABc', loc=3)
            >>> a.swapcase()
            itext(u'abC', loc=3)
        '''
        return self.__makeslice(unicode.swapcase(self))

    def title(self):
        r'''
            >>> a = itext('one two THREE', loc=3)
            >>> a.title()
            itext(u'One Two Three', loc=3)
        '''
        return self.__makeslice(unicode.title(self))

    def upper(self):
        r'''
            >>> a = itext('Abc', loc=3)
            >>> a.upper()
            itext(u'ABC', loc=3)
        '''
        return self.__makeslice(unicode.upper(self))

    def center(self, width, fillchar=u' '):
        r'''
            >>> a = itext('abc', loc=3)
            >>> a.center(10)
            itext(u'   ')+itext(u'abc', loc=3)+itext(u'    ')
        '''
        pad = width - len(self)
        return fillchar * (pad / 2) + self + fillchar * ((pad + 1) / 2)

    def ljust(self, width, fillchar=u' '):
        r'''
            >>> a = itext('abc', loc=3)
            >>> a.ljust(10)
            itext(u'abc', loc=3)+itext(u'       ')
        '''
        return self + fillchar * (width - len(self))

    def rjust(self, width, fillchar=u' '):
        r'''
            >>> a = itext('abc', loc=3)
            >>> a.rjust(10)
            itext(u'       ')+itext(u'abc', loc=3)
        '''
        return fillchar * (width - len(self)) + self

    def zfill(self, width):
        r'''
            >>> a = itext('abc', loc=3)
            >>> a.zfill(6)
            itext(u'000')+itext(u'abc', loc=3)
        '''
        return self.rjust(width, fillchar=u'0')

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

    def __cmp__(self, other):
        r'''To help in reporting errors in lexical order, iloc objects have a
        natural order.

            >>> cmp(iloc('a'), iloc('b'))
            -1

            >>> cmp(iloc('a', 2), iloc('a', 1))
            1

            >>> cmp(iloc('a', 2, 10), iloc('a', 2, 11))
            -1

            >>> cmp(iloc('a', 2, 10), iloc('a', 2))
            1

            >>> cmp(iloc('b', 2, 10), iloc('a', 2, 10))
            1

            >>> cmp(iloc('a', 2, 10), iloc('a', 2, 10))
            0

        '''
        if not isinstance(other, iloc):
            return NotImplemented
        return cmp(self.path, other.path) or \
               cmp(self.line, other.line) or \
               cmp(self.column, other.column)

    def __hash__(self):
        r'''To allow loc objects to be kept in sets.

            >>> s = set([iloc('a', 2, 10)])
            >>> iloc('a', 2, 10) in s
            True
            >>> iloc('a', 2) in s
            False

        '''
        return hash(self.path) ^ hash(self.line) ^ hash(self.column)

class InputError(StandardError):

    r'''
        >>> e = InputError('wah', loc=iloc('name', 4))
        >>> str(e)
        "'name', line 4: wah"

        >>> e = InputError('wah', char=itext(u'abc', loc=2))
        >>> str(e)
        '2: wah'

        >>> e = InputError('wah', chars=[itext(u'abc', loc=2), itext(u'def', loc=1)])
        >>> str(e)
        '1: wah'

        >>> InputError('wah', input=3)
        Traceback (most recent call last):
        TypeError: invalid keyword argument for InputError(): "input="

    '''

    def __init__(self, msg, **kwargs):
        StandardError.__init__(self, unicode(msg).encode('ascii', 'replace'))
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
                self.loc = self._as_line(sorted(self._locs_of(kwargs['lines']))
                                         [0])
            elif 'line' in kwargs:
                self.loc = self._as_line(loc_of(kwargs['line']))
            else:
                raise TypeError('invalid keyword argument for %s(): "%s="' %
                                (self.__class__.__name__, kwargs.keys()[0]))
        except IndexError:
            pass

    @staticmethod
    def _locs_of(objs):
        return sorted(ifilter(bool, (loc_of(obj) for obj in objs)))

    @staticmethod
    def _as_line(obj):
        if hasattr(obj, 'as_line') and callable(obj.as_line):
            return obj.as_line()
        return obj

    def __str__(self):
        r = []
        if self.loc is not None:
            r.append(str(self.loc))
        r.append(StandardError.__str__(self))
        return ': '.join(r)

def loc_of(obj):
    if hasattr(obj, 'loc') and callable(obj.loc):
        return obj.loc()
    try:
        return obj + 0
    except TypeError:
        return None

