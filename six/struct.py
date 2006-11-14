# vim: sw=4 sts=4 et fileencoding=latin1 nomod

r'''Generic data structure.

    >>> s = struct(a=1, b=2, c=3)
    >>> s.a
    1
    >>> s.b
    2
    >>> s.c
    3
    >>> s
    struct(a=1, b=2, c=3)
'''

__all__ = ['struct']

class struct(object):

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__,
                ', '.join(('%s=%r' % i
                           for i in sorted(self.__dict__.iteritems()))))

    def __eq__(self, other):
        if not isinstance(other, struct):
            raise NotImplemented
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        if not isinstance(other, struct):
            raise NotImplemented
        return not self.__eq__(other)
