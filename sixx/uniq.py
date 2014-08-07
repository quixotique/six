# vim: sw=4 sts=4 et fileencoding=utf8 nomod

r'''The uniq() function and associated tools.
'''

__all__ = ['uniq', 'uniq_generator', 'uniqa_group']

def uniq(seq, key=None):
    r'''Iterate over all elements in a given iterable, omitting elements that
    have already appeared once, according to their equality relation.  If the
    'key' argument is given, it must be a callable that converts each element
    of the sequence into a value that is used for equality comparison instead
    of the element itself.

        >>> list(uniq([1, 2, 3]))
        [1, 2, 3]

        >>> list(uniq([1, 1, 2, 3]))
        [1, 2, 3]

        >>> list(uniq([1, 2, 3, 1]))
        [1, 2, 3]

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

        >>> @uniq_generator
        ... def f():
        ...     yield 1
        ...     yield 2
        ...     yield 3
        ...     yield 1
        >>> list(f())
        [1, 2, 3]

    '''
    def newfunc(*args, **kwargs):
        return uniq(func(*args, **kwargs), key=key)
    newfunc.__name__ = func.__name__
    newfunc.__doc__ = func.__doc__
    newfunc.__module__ = func.__module__
    return newfunc

def uniqa_group(seq, key=None):
    r'''Iterate over tuples of all elements in a given iterable, combining
    adjacent elements that compare equal into a single tuple.  If the 'key'
    argument is given, it must be a callable that converts each element of the
    sequence into a value that is used for equality comparison instead of the
    element itself.

        >>> list(uniqa_group([1, 2, 3]))
        [(1,), (2,), (3,)]

        >>> list(uniqa_group([1, 1, 2, 3]))
        [(1, 1), (2,), (3,)]

        >>> list(uniqa_group([1, 2, 3, 1]))
        [(1,), (2,), (3,), (1,)]

        >>> list(uniqa_group([1, 2, 3, 3]))
        [(1,), (2,), (3, 3)]

    '''
    values = []
    for v in seq:
        if key:
            k = key(v)
        else:
            k = v
        if values and lastkey != k:
            yield tuple(values)
            values = []
        values.append(v)
        lastkey = k
    if values:
        yield tuple(values)
