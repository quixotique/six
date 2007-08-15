# vim: sw=4 sts=4 et fileencoding=latin1 nomod

r'''The uniq() function and associated tools.
'''

__all__ = ['uniq', 'uniq_generator']

def uniq(seq, key=None):
    r'''Iterate over all elements in a given iterable, omitting elements that
    have already appeared once, according to their equality relation.  If the
    'key' argument is given, it must be a callable that converts each element
    of the sequence into a value that is used for equality comparison instead
    of the element itself.
    '''
    u = set()
    for v in seq:
        if key:
            k = key(v)
        else:
            k = v
        if k not in u:
            yield v
            u.add(k)

def uniq_generator(func, key=None):
    r'''Decorator for generator functions to ensure that they only return
    unique values.
    '''
    def newfunc(*args, **kwargs):
        return uniq(func(*args, **kwargs), key=key)
    newfunc.__name__ = func.__name__
    newfunc.__doc__ = func.__doc__
    newfunc.__module__ = func.__module__
    return newfunc
