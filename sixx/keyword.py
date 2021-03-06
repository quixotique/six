# vim: sw=4 sts=4 et fileencoding=utf8 nomod

r'''Data model - keywords.
'''

import re
from sixx.input import InputError
from sixx.node import *
from sixx.person import *
from sixx.family import *
from sixx.org import *

__all__ = ['Keyword', 'Keyed_with', 'keyed_with']

class Keyword(Node):

    r'''
        >>> k = Keyword('abc')
        >>> k
        Keyword('abc')
        >>> str(k)
        'abc'

    '''

    def __init__(self, keyword):
        assert isinstance(keyword, str), 'keyword=%r' % (keyword,)
        super(Keyword, self).__init__()
        self.keyword = keyword

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.keyword)

    def __str__(self):
        return self.keyword

    def __hash__(self):
        return hash(self.keyword)

    def __eq__(self, other):
        if not isinstance(other, Keyword):
            return NotImplemented
        return self.keyword == other.keyword

    def __ne__(self, other):
        if not isinstance(other, Keyword):
            return NotImplemented
        return self.keyword != other.keyword

    _re_keyword = re.compile(r'^[0-9a-zA-Z_]+$')

    @classmethod
    def parse(class_, text):
        r'''
            >>> Keyword.parse('foo   bar')
            (Keyword('foo'), 'bar')

            >>> Keyword.parse('-abc')
            Traceback (most recent call last):
            sixx.input.InputError: malformed keyword '-abc'

            >>> Keyword.parse('abc!')
            Traceback (most recent call last):
            sixx.input.InputError: malformed keyword 'abc!'

            >>> Keyword.parse('äbc')
            Traceback (most recent call last):
            sixx.input.InputError: malformed keyword '\xe4bc'

        '''
        spl = text.split(None, 1)
        keyword = spl.pop(0)
        if not class_._re_keyword.match(keyword):
            raise InputError('malformed keyword %r' % str(keyword), char=keyword)
        comment = spl and spl[0] or None
        return class_(str(keyword)), comment

class Keyed_with(Link):

    def __init__(self, who, keyword, timestamp=None):
        assert isinstance(who, (Person, Family, Organisation, Works_at)), \
                'cannot attach Keyword to %r' % who
        assert isinstance(keyword, Keyword)
        super(Keyed_with, self).__init__(who, keyword, timestamp=timestamp)
        self.who = who
        self.keyword = keyword

from sixx.node import node_predicate

def keyed_with(keyword):
    r'''Return a predicate that returns true if the node at the other end of
    the link linked to the given keyword node.
    '''
    def _pred(node):
        return bool(node.link(outgoing & is_link(Keyed_with) &
                              to_node(keyword)))
    return node_predicate(_pred)
