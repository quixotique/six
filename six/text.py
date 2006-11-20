# vim: sw=4 sts=4 et fileencoding=latin1 nomod

r'''Data model - text utilities.
'''

import unicodedata

__all__ = ['text_sort_key', 'text_match_key']

def text_sort_key(text):
    r'''Convert a text into a string used for sorting.

        >>> text_sort_key('One Two Three33! 456 seven')
        'one two three seven'

        >>> text_sort_key(u'Muñoz Güell, José')
        u'munoz guell, jose'

    '''
    return ' '.join(filter(len,
            (filter(lambda c: c.isalpha() or c == ',', word).lower()
             for word in remove_diacriticals(text).split())))

def text_match_key(text):
    r'''Convert a text into a string used for matching searches.

        >>> text_match_key('One Two Three33! 456 seven')
        ' one two three33 456 seven'

        >>> text_match_key(u'Muñoz Güell, José')
        u' munoz guell jose'

    '''
    return ' '.join([''] +
                filter(len, (filter(lambda c: c.isalnum(), word).lower()
                             for word in remove_diacriticals(text).split())))

def remove_diacriticals(text):
    r'''Remove diacritical marks from letters.
    '''
    if isinstance(text, unicode):
        return unicodedata.normalize('NFD', text)
    return text
