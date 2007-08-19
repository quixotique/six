# vim: sw=4 sts=4 et fileencoding=latin1 nomod

r'''Data model - sorting.
'''

from itertools import imap, ifilter, chain
from six.node import *
from six.text import *
from six.uniq import uniq

__all__ = ['SortItem', 'Sorter']

class Sorter(object):
    r'''A Sorter is a set-like object to which nodes may be added, and
    retrieved in sorted order.
    '''

    def __init__(self):
        self._nodes = set()
        self._items = None
        self._sorted = None

    def update(self, nodes):
        r'''Append the given Nodes to the sorter.
        '''
        for node in nodes:
            assert isinstance(node, Node)
            if node not in self._nodes:
                self._nodes.add(node)
                self._items = None
                self._sorted = None

    def discard(self, node):
        r'''Remove the given Node from the sorter.
        '''
        if node in self._nodes:
            self._nodes.remove(node)
            self._items = None
            self._sorted = None

    def __iter__(self):
        r'''Iterate over all the Nodes added to date, in arbitrary order.
        '''
        return iter(self._nodes)

    def __contains__(self, node):
        r'''Return true if the given Node has been added to the sorter and not
        discarded since.
        '''
        return node in self._nodes

    def items(self):
        r'''Iterate over SortItem objects for all Nodes in the sorter, in
        arbitrary order.  There will be at least one SortItem for each Node.
        The 'single' attribute of each SortItem will always refer to the
        principal SortItem for that Node, which corresponds to the first key
        returned by the Node's sort_keys() method.
        '''
        if self._items is None:
            self._sorted = None
            self._items = set()
            for node in self:
                items = [SortItem(node, key) for key in node.sort_keys()]
                assert items
                for item in items:
                    item.single = items[0]
                    self._items.add(item)
        return iter(self._items)

    def sorted(self):
        r'''Iterate over SortItems, in sorted order.
        '''
        if self._sorted is None:
            self._sorted = list(self.items())
            self._sorted.sort()
        return iter(self._sorted)

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
        # The key could be a multilang, so we must ensure it is a string for
        # collation purposes.
        self.sortkey = text_sort_key(key)
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
