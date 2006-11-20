# vim: sw=4 sts=4 et fileencoding=latin1 nomod

r'''Multi-language text.
'''

import locale
import re
from six.input import *
from six.text import *

__all__ = ['multilang']

class multilang(object):

    r'''A piece of text with forms in more than one language.  Used for
    representing country names and the like.

        >>> t = multilang('Spain')
        >>> t
        multilang('Spain')

        >>> t = multilang(en='Spain', es=u'España')
        >>> t
        multilang(en='Spain', es=u'Espa\xf1a')

    '''

    def __init__(self, *args, **kwargs):
        if len(args) == 1:
            assert len(kwargs) == 0
            assert isinstance(args[0], basestring)
            self.text = args[0]
        else:
            self.alt = {}
            assert len(args) == 0
            assert len(kwargs) >= 1
            for lang, text in kwargs.iteritems():
                assert isinstance(lang, str)
                assert len(lang) in (2, 5)
                assert lang[:2].isalpha()
                if len(lang) == 5:
                    assert lang[2] == '_'
                    assert lang[3:].isalpha()
                    assert lang[3:].isupper()
                assert isinstance(text, basestring)
                self.alt[lang] = text

    def __unicode__(self):
        r'''Return the localised form of the text that depends on the current
        locale.  If there is no form in the current locale's language, then
        return a form at random.

            >>> t = multilang(en='Spain', es=u'España')
            >>> loc = locale.getlocale(locale.LC_MESSAGES)
            >>> try:
            ...     locale.setlocale(locale.LC_MESSAGES, 'en_AU')
            ...     unicode(t)
            ...     locale.setlocale(locale.LC_MESSAGES, 'es_ES')
            ...     unicode(t)
            ... finally:
            ...     dum = locale.setlocale(locale.LC_MESSAGES, loc)
            'en_AU'
            u'Spain'
            'es_ES'
            u'Espa\xf1a'

        '''
        return self.__as(unicode)

    def __str__(self):
        r'''Return the localised form of the text as for __unicode__(), encoded
        to a string using the current encoding.  This may raise an exception if
        the current encoding cannot encode the form.

            >>> t = multilang(en='Spain', es=u'España')
            >>> loc = locale.getlocale(locale.LC_MESSAGES)
            >>> try:
            ...     locale.setlocale(locale.LC_MESSAGES, 'en_AU')
            ...     str(t)
            ... finally:
            ...     dum = locale.setlocale(locale.LC_MESSAGES, loc)
            'en_AU'
            'Spain'
            >>> try:
            ...     locale.setlocale(locale.LC_MESSAGES, 'es_ES')
            ...     str(t)
            ... finally:
            ...     dum = locale.setlocale(locale.LC_MESSAGES, loc)
            Traceback (most recent call last):
            UnicodeEncodeError: 'ascii' codec can't encode character u'\xf1' in position 4: ordinal not in range(128)

        '''
        return self.__as(str)

    def __as(self, strtype):
        if hasattr(self, 'alt'):
            lang = locale.getlocale(locale.LC_MESSAGES)[0]
            if lang is not None:
                try:
                    return strtype(self.local(lang))
                except KeyError:
                    pass
            return strtype(self.alt.values()[0])
        return strtype(self.text)

    def local(self, lang):
        r'''Return a localised form of the text (str or unicode), given the
        local language.  If there is no form in the given language, then raise
        ValueError.

            >>> t = multilang(en='Spain', es=u'España')
            >>> t.local('en')
            'Spain'
            >>> t.local('es')
            u'Espa\xf1a'
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

    def __repr__(self):
        classname = self.__class__.__name__
        if hasattr(self, 'text'):
            return '%s(%r)' % (classname, self.text)
        return '%s(%s)' % (classname,
               ', '.join(('%s=%r' % (k, self.alt[k])
                          for k in sorted(self.alt.keys()))))

    def matches(self, text):
        text = text_match_key(text)
        if hasattr(self, 'text'):
            return text_match_key(self.text) == text
        for v in self.alt.itervalues():
            if text_match_key(v) == text:
                return True
        return False

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

            >>> multilang.parse(u'en:"Spain" es:"España" abc')
            (u'abc', multilang(en=u'Spain', es=u'Espa\xf1a'))

            >>> multilang.parse(itext.new(u'en:"Spain" "España" abc', loc=iloc(column=1)))
            Traceback (most recent call last):
            InputError: column 12: bare text mixed with language text

        '''
        bare = None
        alt = None
        while text:
            m = class_._re_parse.match(text)
            if m is None:
                break
            text = text[m.end():]
            lang = m.group(1) and str(m.group(1))
            string = m.group(2)
            if lang:
                if bare is not None:
                    raise InputError('bare text mixed with language text',
                                     char=m.group())
                if alt is None:
                    alt = dict()
                if lang in alt:
                    raise InputError('duplicate language %r' % lang,
                                     char=m.group())
                alt[lang] = string
            else:
                if bare is not None:
                    raise InputError('more than one bare text', char=m.group())
                if alt is not None:
                    raise InputError('bare text mixed with language text',
                                     char=m.group())
                bare = string
        if bare is not None:
            return text, class_(bare)
        if alt is not None:
            return text, class_(**alt)
        return (text, None)
