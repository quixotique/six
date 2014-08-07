# vim: sw=4 sts=4 et fileencoding=latin1 nomod

r'''Data model - sorting.
'''

from sixx.node import *
from sixx.text import *
from sixx.uniq import uniq
from sixx.enum import Enum

__all__ = ['SortMode', 'SortItem', 'Itemiser', 'cull_references']

class SortMode(Enum('ALL_NAMES', 'FIRST_NAME', 'LAST_NAME')):
    r'''When collating and sorting nodes, the sort keys at which each node
    appears can be controlled using the optional 'sort_mode' parameter.
    '''
    pass

class Itemiser(object):
    r'''An Itemiser is a set-like object to which nodes may be added, and
    SortItem objects retrieved, based on the nodes added to date.
    '''

    def __init__(self, sort_mode=SortMode.ALL_NAMES):
        assert isinstance(sort_mode, SortMode)
        self.sort_mode = sort_mode
        self._nodes = set()
        self._items = None

    def add(self, node):
        r'''Append the given Node to the itemiser.
        '''
        assert isinstance(node, Node)
        if node not in self._nodes:
            self._nodes.add(node)
            self._items = None

    def update(self, nodes):
        r'''Append the given Nodes to the itemiser.
        '''
        for node in nodes:
            self.add(node)

    def discard(self, node):
        r'''Remove the given Node from the itemiser.
        '''
        if node in self._nodes:
            self._nodes.remove(node)
            self._items = None

    def __iter__(self):
        r'''Iterate over all the Nodes added to date, in arbitrary order.
        '''
        return iter(self._nodes)

    def __contains__(self, node):
        r'''Return true if the given Node has been added to the itemiser and
        not discarded since.
        '''
        return node in self._nodes

    def __len__(self):
        r'''Return the number of distinct Nodes added to the itemiser and not
        discarded since.
        '''
        return len(self._nodes)

    def __getitem__(self, node):
        r'''Return the Node to which the given Node is a reference.
        '''
        self.items(node).next().single.node

    def items(self, node=None):
        r'''Iterate over SortItem objects, in arbitrary order, for all the
        given node, or for all nodes in the itemiser if the 'node' argument is
        None.  There will be at least one SortItem for each Node.  The 'single'
        attribute of each SortItem will always refer to the first SortItem for
        that Node, which corresponds to the first key returned by the Node's
        sort_keys() method.
        '''
        if self._items is None:
            self._items = dict()
            for node1 in self:
                items = [SortItem(node1, key) for key in node1.sort_keys(sort_mode=self.sort_mode)]
                assert items
                for item in items:
                    item.single = items[0]
                self._items[node1] = items
        if node is None:
            for items in self._items.itervalues():
                for item in items:
                    yield item
        else:
            for item in self._items[node]:
                yield item

    def alias_items(self, aliases=()):
        r'''Iterate over SortItem objects generated from the given sequence
        of (src, dst) node pairs.  Each 'dst' node must be present in the
        itemiser already.
        '''
        for src, dst in aliases:
            di = self.items(dst).next()
            for key in src.sort_keys(sort_mode=self.sort_mode):
                si = SortItem(dst, key)
                si.single = di
                yield si

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

def cull_references(itemlist, horizon=8):
    r'''Cull unnecessary references from a sorted list of Items.
    '''
    # Remove entries that reference a nearby entry.  The horizon is a
    # heuristic for how far we expect a user will search around for an entry
    # which is out of order.
    for i, item in enumerate(itemlist):
        if item is item.single:
            lim = 0
            for j in xrange(i - 1, -1, -1):
                if itemlist[j].sortkey[:3] != item.sortkey[:3]:
                    break
                if itemlist[j].node:
                    lim += 1
                    if lim > horizon:
                        break
                    if itemlist[j].node is item.node:
                        itemlist[j].node = None
    # Remove top-level entries that reference the same entry as another nearby,
    # prior entry.
    for i, item in enumerate(itemlist):
        if item is not item.single:
            lim = 0
            for j in xrange(i - 1, -1, -1):
                if itemlist[j].sortkey[:3] != item.sortkey[:3]:
                    break
                if itemlist[j].node:
                    lim += 1
                    if lim > horizon:
                        break
                    if itemlist[j].node is item.node:
                        item.node = None
                        break
