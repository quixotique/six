# vim: sw=4 sts=4 et fileencoding=latin1 nomod

r'''General purpose utilities.
'''

__all__ = ['iempty']

def iempty(iterator):
    r'''Return True if the given iterator is empty, ie, the first call to
    iterator.next() raises StopIteration.  This is a destructive test, because
    it consumes the first element of the iterator.

        >>> iempty(iter([1, 2, 3]))
        False

        >>> iempty(iter([]))
        True

    '''
    try:
        iterator.next()
    except StopIteration:
        return True
    return False
