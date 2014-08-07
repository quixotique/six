# vim: sw=4 sts=4 et fileencoding=utf8 nomod

r'''Data model - text utilities.
'''

import unicodedata
import collections

__all__ = ['text_sort_key', 'text_match_key', 'sortstr']

def text_sort_key(text):
    r'''Convert a text into a string used for sorting.  If the text is a
    sortstr instance, then extract the collation part from it.

        >>> text_sort_key('One Two Three33! 456 seven')
        'one two three seven'

        >>> text_sort_key('Muñoz Güell, José')
        'munoz guell, jose'

        >>> t = sortstr('Dr José Muñoz Güell, B.Med.')
        >>> t.sortslice = slice(3, 19)
        >>> text_sort_key(t)
        'jose munoz guell'

    '''
    if hasattr(text, 'sortstr') and isinstance(text.sortstr, collections.Callable):
        text = text.sortstr()
    else:
        text = str(text)
    return ' '.join(w for w in (''.join(c.lower() for c in word if c.isalpha() or c == ',') for word in remove_diacriticals(text).split()) if w)

def text_match_key(text):
    r'''Convert a text into a string used for matching searches.

        >>> text_match_key('One Two Three33! 456 seven')
        ' one two three33 456 seven'

        >>> text_match_key('Muñoz Güell, José')
        ' munoz guell jose'

    '''
    return ' '.join([''] + list(w for w in (''.join(c.lower() for c in word if c.isalnum()) for word in remove_diacriticals(text).split()) if w))

def remove_diacriticals(text):
    r'''Remove diacritical marks from letters.
    '''
    if isinstance(text, str):
        return unicodedata.normalize('NFD', text)
    return text

class sortstr(str):

    r'''A subclass of str that can be used for strings that are to be
    both displayed and sorted.  A single slice() object is associated with the
    string, in the mutable 'sortslice' attribute, which defines the part of the
    string which is to be used for collation.  The preceding and following
    parts are just for display.  This allows, for example, a name like "Dr Good
    Fellow, Q.C." to be sorted just on the "Good Fellow" part, but still
    displayed in full, possibly with emphasis on the "Good Fellow" part to aid
    the eye in seeing the collation order.

        >>> s = sortstr('abc')
        >>> s
        sortstr.new('abc')
        >>> s.sortstr()
        'abc'
        >>> s.sortslice = slice(1, 2)
        >>> s.sortstr()
        'b'

    '''

    def __new__(class_, *args):
        r'''The 'sortslice' attribute is initialised to cover the whole string.
        '''
        obj = str.__new__(class_, *args)
        obj.sortslice = slice(len(obj))
        return obj

    def sortstr(self):
        r'''Return the portion of the string that is to be used for sorting.
        '''
        return self[self.sortslice]

    def sortsplit(self):
        r'''Return the three-tuple (self[:self.sortslice.start],
        self.sortstr(), self[self.sortslice.stop:]).
        '''
        return (self[:self.sortslice.start],
                self.sortstr(),
                self[self.sortslice.stop:])

    def __repr__(self):
        r = [repr(str(self))]
        if self.sortslice != slice(len(self)):
            r.append(repr(self.sortslice))
        return '%s.new(%s)' % (self.__class__.__name__, ', '.join(r))

    @classmethod
    def new(class_, string, sortsl=None):
        r'''Virtual constructor.
        '''
        if sortsl is not None:
            assert type(sortsl) is slice
        s = class_(string)
        if sortsl is not None:
            s.sortslice = sortsl
        return s
