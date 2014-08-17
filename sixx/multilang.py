# vim: sw=4 sts=4 et fileencoding=utf8 nomod

r'''Multi-language text.
'''

import locale
import re
from sixx.input import *
from sixx.text import *

__all__ = ['multilang', 'expand_multilang_generator']

class multilang(object):

    r'''A piece of text with forms in more than one language.  Used for
    representing country names and the like.

        >>> t = multilang('Spain')
        >>> t
        multilang('Spain')

        >>> t = multilang(en='Spain', es='España')
        >>> t
        multilang(en='Spain', es='Espa\xf1a')

    '''

    def __init__(self, *args, **kwargs):
        if len(args) == 1:
            assert len(kwargs) == 0
            assert isinstance(args[0], str)
            self.text = args[0]
        else:
            self.alt = {}
            assert len(args) == 0
            assert len(kwargs) >= 1
            for lang, text in kwargs.items():
                assert isinstance(lang, str)
                assert len(lang) in (2, 5)
                assert lang[:2].isalpha()
                if len(lang) == 5:
                    assert lang[2] == '_'
                    assert lang[3:].isalpha()
                    assert lang[3:].isupper()
                assert isinstance(text, str)
                self.alt[lang] = text

    def __str__(self):
        r'''Return the localised form of the text that depends on the current
        locale.  If there is no form in the current locale's language, or the
        form is an empty string, then return a non-empty form at random.

            >>> t = multilang(en='Spain', es='España')
            >>> loc = locale.getlocale(locale.LC_MESSAGES)
            >>> try:
            ...     locale.setlocale(locale.LC_MESSAGES, 'en_AU.utf8')
            ...     str(t)
            ...     locale.setlocale(locale.LC_MESSAGES, 'es_ES.utf8')
            ...     str(t)
            ... finally:
            ...     dum = locale.setlocale(locale.LC_MESSAGES, loc)
            'en_AU.utf8'
            'Spain'
            'es_ES.utf8'
            'Espa\xf1a'

        '''
        if hasattr(self, 'alt'):
            lang = locale.getlocale(locale.LC_MESSAGES)[0]
            if lang is not None:
                try:
                    s = self.local(lang)
                    if s:
                        return str(s)
                except KeyError:
                    pass
            for s in self.alt.values():
                if s:
                    return str(s)
            return str()
        return str(self.text)


    def __bool__(self):
        r'''Tests as true if contains any non-empty string.
        '''
        if hasattr(self, 'alt'):
            for alt in self.alt.values():
                if alt:
                    return True
            return False
        return bool(self.text)

    def upper(self):
        r'''Return a new multilang object with all texts in uppercase.

            >>> t = multilang(en='Spain', es='España')
            >>> t.upper()
            multilang(en='SPAIN', es='ESPA\xd1A')

        '''
        u = type(self).__new__(type(self))
        if hasattr(self, 'alt'):
            u.alt = dict((lang, text.upper())
                         for lang, text in self.alt.items())
        else:
            u.text = self.text.upper()
        return u

    def local(self, lang):
        r'''Return a localised form of the text (str), given the local
        language.  If there is no form in the given language, then raise
        ValueError.

            >>> t = multilang(en='Spain', es='España')
            >>> t.local('en')
            'Spain'
            >>> t.local('es')
            'Espa\xf1a'
            >>> t.local('de')
            Traceback (most recent call last):
            ValueError: text has no form in language 'de'

        '''
        if hasattr(self, 'text'):
            return self.text
        try:
            return self.alt[lang]
        except KeyError:
            pass
        if len(lang) > 2:
            try:
                return self.alt[lang[:2]]
            except KeyError:
                pass
        raise ValueError('text has no form in language %r' % lang)

    def itertexts(self, lang=None):
        r'''Iterates over all the texts in all languages, starting with the
        given language, or if not specified, the language of the current
        locale, followed by all other languages in undefined order.

            >>> t = multilang(en='Spain', es='España')
            >>> list(t.itertexts('en'))
            ['Spain', 'Espa\xf1a']
            >>> list(t.itertexts('es'))
            ['Espa\xf1a', 'Spain']

        '''
        if lang is None:
            lang = locale.getlocale(locale.LC_MESSAGES)[0]
        first = None
        try:
            first = self.local(lang)
            yield first
        except KeyError:
            pass
        if hasattr(self, 'text'):
            if self.text != first:
                yield self.text
        else:
            for alt in self.alt.values():
                if alt != first:
                    yield alt

    def __repr__(self):
        classname = self.__class__.__name__
        if hasattr(self, 'text'):
            return '%s(%r)' % (classname, self.text)
        return '%s(%s)' % (classname,
               ', '.join(('%s=%r' % (k, self.alt[k])
                          for k in sorted(self.alt.keys()))))

    def matches(self, text):
        if hasattr(self, 'text'):
            return self.text == text
        for v in self.alt.values():
            if v == text:
                return True
        return False

    def imatches(self, itext):
        if hasattr(self, 'text'):
            return itext in text_match_key(self.text)
        for v in self.alt.values():
            if itext in text_match_key(v):
                return True
        return False

    def loc(self):
        r'''Return the input location of the string that was parsed to
        produce this multilang.  If the multilang was not produced by parsing
        input, then return None.

            >>> m = multilang.parse(itext('"abc"', loc=8))[1]
            >>> m.loc()
            8

            >>> m = multilang(itext('abc', loc=15))
            >>> m.loc()
            15

            >>> m = multilang.parse('"abc"')[1]
            >>> m.loc() is None
            True

            >>> m = multilang('abc')
            >>> m.loc() is None
            True
        '''
        if hasattr(self, '_parsed'):
            return loc_of(self._parsed)
        if hasattr(self, 'text'):
            return loc_of(self.text)
        if self.alt:
            return min([loc_of(a) for a in self.alt.values()])
        return None

    _re_parse = re.compile(r'(?:([a-z]{2}):)?"([^"]*)"\s*')

    @classmethod
    def parse(class_, text):
        r'''
            >>> multilang.parse('')
            ('', None)

            >>> multilang.parse('abc')
            ('abc', None)

            >>> multilang.parse('"abc" ')
            ('', multilang('abc'))

            >>> multilang.parse('en:"Spain" es:"España" abc')
            ('abc', multilang(en='Spain', es='Espa\xf1a'))

            >>> multilang.parse(itext('en:"Spain" "España" abc', loc=iloc(column=1)))
            Traceback (most recent call last):
            sixx.input.InputError: column 12: bare text mixed with language text

        '''
        otext = text
        bare = None
        alt = None
        while text:
            m = class_._re_parse.match(text)
            if m is None:
                break
            lang = m.group(1) and str(m.group(1))
            string = text[m.start(2):m.end(2)]
            matched = text[m.start():m.end()]
            text = text[m.end():]
            if lang:
                if bare is not None:
                    raise InputError('bare text mixed with language text', char=matched)
                if alt is None:
                    alt = dict()
                if lang in alt:
                    raise InputError('duplicate language %r' % lang, char=matched)
                alt[lang] = string
            else:
                if bare is not None:
                    raise InputError('more than one bare text', char=matched)
                if alt is not None:
                    raise InputError('bare text mixed with language text', char=matched)
                bare = string
        obj = None
        if bare is not None:
            obj = class_(bare)
        elif alt is not None:
            obj = class_(**alt)
        if obj is not None:
            obj._parsed = otext
        return (text, obj)

    @classmethod
    def optparse(class_, text):
        r'''Parse a string as a complete multilang, or if that fails, then
        just as a plain string.  Don't accept a mixture.
        '''
        t, m = class_.parse(text)
        if m is None:
            return text
        if t:
            raise InputError('multilang mixed with plain text',
                             char=text)
        return m

def expand_multilang_generator(func):
    r'''Decorator for generator functions that expands every multilang object
    into its alternative texts.

        >>> @expand_multilang_generator
        ... def f():
        ...     yield multilang(en='Spain', es='España')
        ...     yield 'Australia'
        ...     yield multilang(en='Germany', es='Alemania')
        >>> list(f())
        ['Spain', 'Espa\xf1a', 'Australia', 'Germany', 'Alemania']

    '''
    def newfunc(*args, **kwargs):
        for value in func(*args, **kwargs):
            if isinstance(value, multilang):
                for alt in value.itertexts():
                    yield alt
            else:
                yield value
    newfunc.__name__ = func.__name__
    newfunc.__doc__ = func.__doc__
    newfunc.__module__ = func.__module__
    return newfunc
