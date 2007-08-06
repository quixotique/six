# vim: sw=4 sts=4 et fileencoding=latin1 nomod

r'''Data model - sorting.
'''

from itertools import imap, ifilter, chain
from six.node import *
from six.text import *

__all__ = ['SortItem', 'Sorter', 'uniq']

class Sorter(object):
    r'''A Sorter is a set-like object to which nodes may be added, and
    retrieved in sorted order.
    '''

    def __init__(self):
        self._nodes = set()
        self._items = None
        self._sorted = None

    def update(self, nodes):
        for node in nodes:
            assert isinstance(node, Node)
            if node not in self._nodes:
                self._nodes.add(node)
                self._items = None

    def discard(self, node):
        self._nodes.discard(node)

    def __iter__(self):
        return iter(self._nodes)

    def __contains__(self, node):
        return node in self._nodes

    def items(self):
        if self._items is None:
            self._items = set()
            for node in self._nodes:
                keys = list(uniq(node.sort_keys()))
                assert keys
                items = [SortItem(node, key) for key in keys]
                single = items[0]
                for item in items:
                    assert isinstance(item, SortItem)
                    item.single = single
                    self._items.add(item)
                    self._sorted = None
        return iter(self._items)

    def sorted(self):
        if self._sorted is None:
            self._sorted = list(self.items())
            self._sorted.sort()
        sorted = list(self._sorted)
        while sorted:
            items = [sorted.pop(0)]
            while sorted and sorted[0].node is items[0].node:
                items.append(sorted.pop(0))
            yield tuple(items)

class SortItem(object):
    r'''When sorting nodes, one node may appear in several places in the
    collation order, because it may have disparate sort keys.  For example, a
    person may be listed by their first and last names, and a family will be
    listed under the names of all its heads, eg, "Andrew & Juana", "Juana &
    Andrew".  A company may be listed under all of its "also-knowns", e.g.,
    "Austrade", "Department of Trade".  A SortItem object represents a single
    appearance of a node in the collating order, so a single node will give
    rise to one or more SortItems.
    '''

    def __init__(self, node, key, single=None):
        assert isinstance(node, Node)
        self.node = node
        self.key = key
        self.sortkey = text_sort_key(unicode(key))
        self.single = single if single is not None else self

    def __cmp__(self, other):
        if not isinstance(other, SortItem):
            return NotImplemented
        return cmp(self.sortkey, other.sortkey)

    def __repr__(self):
        r = ['node=%r' % self.node, 'key=%r' % self.key]
        if self.single is not self:
            r.append('single=%r' % self.single)
        return '%s(%s)' % (self.__class__.__name__, ', '.join(r))

def uniq(seq, key=None):
    u = set()
    for v in seq:
        if key:
            k = key(v)
        else:
            k = v
        if k not in u:
            yield v
            u.add(k)
