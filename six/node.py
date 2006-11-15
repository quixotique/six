# vim: sw=4 sts=4 et fileencoding=latin1 nomod

r'''Data model - Node and Link superclasses, and link predicate algebra.
'''

import datetime
import unicodedata

__all__ = [
        'Node', 'Link', 'NamedNode',
        'incoming', 'outgoing', 'is_link', 'is_link_only',
        'from_node', 'to_node',
        'has_place', 'test_link', 'name_matches',
    ]

class Node(object):

    r'''A node in the model graph.  To be subclassed.

    @ivar place: used when parsing to help provide a context for
        place-dependent data which is linked to this node, eg, phone numbers.
    '''

    def __init__(self):
        self._links = set()

    def add_link(self, r):
        r'''Used by Link().'''
        assert isinstance(r, Link)
        if r not in self._links:
            self._links.add(r)

    def place(self):
        r'''Deduce the place (area or country) to which this node pertains,
        based on its links to other nodes.
        '''
        return None

    def __unicode__(self):
        return unicode(str(self))

    def __str__(self):
        return self.__class__.__name__

    def derive_place(self, *preds):
        r'''Determine the place of this node, based on the links that satisfy
        a series of predicates.
        '''
        place = None
        for pred in preds:
            for link in self.links(pred):
                if place is None:
                    place = link.place()
                elif place != link.place():
                    place = None
                    break
            if place is not None:
                break
        return place

    def links(self, pred=lambda n, l: True):
        r'''Iterate over all the links for this node that satisfy the given
        predicate.

            >>> class A(Node): pass
            >>> class B(A): pass
            >>> class C(Node): pass
            >>> a = A()
            >>> b = B()
            >>> c = C()
            >>> n = Node()
            >>> lna = Link(n, a)
            >>> lan = Link(a, n)
            >>> lnb = Link(n, b)
            >>> lnc = Link(n, c)
            >>> lab = Link(a, b)
            >>> set(n.links()) == set([lna, lnb, lnc, lan])
            True
            >>> set(n.links(to_node(A))) == set([lna, lnb])
            True
            >>> set(n.links(to_node(A) & to_node(B))) == set([lnb])
            True
            >>> set(n.links(to_node(A) & to_node(C))) == set([])
            True

        '''
        for link in self._links:
            if pred(self, link):
                yield link

    def link(self, pred):
        r'''Return the single link that satisfies the given predicate, or None
        if there is no such link.  Raise an assertion error if there is more
        than one.

            >>> class A(Node): pass
            >>> class B(A): pass
            >>> class C(Node): pass
            >>> a = A()
            >>> b = B()
            >>> c = C()
            >>> n = Node()
            >>> lna = Link(n, a)
            >>> lan = Link(a, n)
            >>> lnb = Link(n, b)
            >>> lnc = Link(n, c)
            >>> lab = Link(a, b)
            >>> n.link(to_node(A))
            Traceback (most recent call last):
            AssertionError
            >>> n.link(to_node(A) & to_node(B)) is lnb
            True
            >>> n.link(to_node(A) & to_node(C)) is None
            True

        '''
        links = list(self.links(pred))
        assert len(links) <= 1
        return links[0] if len(links) else None

    def nodes(self, pred=lambda n, l: True):
        r'''Iterate over all the nodes linked to this node that satisfy the
        given predicates.

            >>> class A(Node): pass
            >>> class B(A): pass
            >>> a = A()
            >>> b = B()
            >>> n = Node()
            >>> la = Link(n, a)
            >>> lb = Link(n, b)
            >>> set(n.nodes()) == set([a, b])
            True
            >>> set(n.nodes(to_node(A))) == set([a, b])
            True
            >>> set(n.nodes(to_node(B))) == set([b])
            True

        '''
        for link in self.links(pred):
            yield link.other(self)

    def node(self, pred):
        r'''Return the single node that satisfies the given predicate, or None
        if there is no such node.  Raise an assertion error if there is more
        than one.

            >>> class A(Node): pass
            >>> class B(A): pass
            >>> class C(Node): pass
            >>> a = A()
            >>> b = B()
            >>> n = Node()
            >>> la = Link(n, a)
            >>> lb = Link(n, b)
            >>> n.node(to_node(A))
            Traceback (most recent call last):
            AssertionError
            >>> n.node(to_node(B)) is b
            True
            >>> n.node(to_node(C)) is None
            True

        '''
        nodes = list(self.nodes(pred))
        assert len(nodes) <= 1
        return nodes[0] if len(nodes) else None

    def find_nodes(self, traverse, select=lambda node: True,
                                   stop=lambda node: False):
        r'''
        @param traverse: predicate that selects the links to follow from each
            node
        @param select: a predicate that selects the nodes to return
        @param stop: a predicate that selects the links not to follow from each
            node, overrides 'traverse'
        @return: iterator over (link, node, link, node, ...) tuples, where the
            last element is the found link or node, and the preceding elements
            are all the links and nodes that were traversed to reach it
        '''
        visited = set([id(self)])
        todo = [(self,)]
        while todo:
            nodes = todo.pop()
            node = nodes[-1]
            for link in node.links(traverse):
                for visit in (link,), (link, link.other(node)):
                    if not stop(visit[-1]) and id(visit[-1]) not in visited:
                        visited.add(id(visit[-1]))
                        todo.append(nodes + visit)
                        if select(todo[-1][-1]):
                            yield todo[-1][1:]

class Link(Node):

    r'''A directional link between two nodes.  Intended to be subclassed.
    A link is itself a node, because sometimes information (other nodes)
    is associated with the _relationship_ between two entities, and not
    either entity in isolation.  For example, if a person works for a company,
    then their individual telephone extension, email address, and employee id
    at that company is a property of the 'works-at' link from the person to the
    company.
    '''

    def __init__(self, n1, n2, timestamp=None):
        assert isinstance(n1, Node)
        assert isinstance(n2, Node)
        if timestamp is not None:
            assert isinstance(timestamp, datetime.date)
        super(Link, self).__init__()
        self.node1 = n1
        self.node2 = n2
        n1.add_link(self)
        n2.add_link(self)
        self.timestamp = timestamp

    def other(self, node):
        r'''Return the node at other end of the link from the given node.

            >>> n1 = Node()
            >>> n2 = Node()
            >>> l = Link(n1, n2)
            >>> l.other(n1) is n2
            True
            >>> l.other(n2) is n1
            True

        '''
        if node is self.node1:
            return self.node2
        else:
            assert node is self.node2
            return self.node1

class link_predicate(object):

    r'''A predicate function wrapper that allows predicates to be combined
    using logical operators '&' and '|' and '~' (in place of 'and', 'or',
    'not', which cannot be overloaded in Python).
    '''

    def __init__(self, func):
        self._func = func

    def __call__(self, node, link):
        return self._func(node, link)

    def __and__(self, other):
        if not isinstance(other, link_predicate):
            return NotImplemented
        return link_predicate(lambda node, link: self._func(node, link) and
                                        other._func(node, link))

    def __or__(self, other):
        if not isinstance(other, link_predicate):
            return NotImplemented
        return link_predicate(lambda node, link: self._func(node, link) or
                                        other._func(node, link))

    def __invert__(self):
        return link_predicate(lambda node, link: not self._func(node, link))

@link_predicate
def outgoing(node, link):
    r'''Node.nodes() and Node.links() predicate that selects only links that
    point from the queried node.

        >>> class A(Link): pass
        >>> class B(A): pass
        >>> class C(Link): pass
        >>> n1 = Node()
        >>> n2 = Node()
        >>> n3 = Node()
        >>> a12 = A(n1, n2)
        >>> a23 = A(n2, n3)
        >>> a31 = A(n3, n1)
        >>> b13 = B(n1, n3)
        >>> b32 = B(n3, n2)
        >>> b21 = B(n2, n1)
        >>> c12 = C(n1, n2)
        >>> c21 = C(n2, n1)
        >>> set(n1.links(outgoing)) == set([a12, b13, c12])
        True
        >>> set(n2.links(outgoing)) == set([a23, b21, c21])
        True
        >>> set(n3.links(outgoing)) == set([a31, b32])
        True

    '''
    return node is link.node1

@link_predicate
def incoming(node, link):
    r'''Node.nodes() and Node.links() predicate that selects only links that
    point to the queried node.

        >>> class A(Link): pass
        >>> class B(A): pass
        >>> class C(Link): pass
        >>> n1 = Node()
        >>> n2 = Node()
        >>> n3 = Node()
        >>> a12 = A(n1, n2)
        >>> a23 = A(n2, n3)
        >>> a31 = A(n3, n1)
        >>> b13 = B(n1, n3)
        >>> b32 = B(n3, n2)
        >>> b21 = B(n2, n1)
        >>> c12 = C(n1, n2)
        >>> c21 = C(n2, n1)
        >>> set(n1.links(incoming)) == set([a31, b21, c21])
        True
        >>> set(n2.links(incoming)) == set([a12, b32, c12])
        True
        >>> set(n3.links(incoming)) == set([a23, b13])
        True

    '''
    return node is link.node2

def is_link(typ):
    r'''Return a predicate that matches links of the given type.

        >>> class A(Link): pass
        >>> class B(A): pass
        >>> class C(Link): pass
        >>> n1 = Node()
        >>> n2 = Node()
        >>> n3 = Node()
        >>> a12 = A(n1, n2)
        >>> a23 = A(n2, n3)
        >>> a31 = A(n3, n1)
        >>> b13 = B(n1, n3)
        >>> b32 = B(n3, n2)
        >>> b21 = B(n2, n1)
        >>> c12 = C(n1, n2)
        >>> c21 = C(n2, n1)
        >>> set(n1.links(is_link(A))) == set([a12, a31, b13, b21])
        True
        >>> set(n1.links(~is_link(A))) == set([c12, c21])
        True
        >>> set(n1.links(is_link(A) & outgoing)) == set([a12, b13])
        True
        >>> set(n1.links(is_link(B))) == set([b21, b13])
        True
        >>> set(n1.links(is_link(C))) == set([c12, c21])
        True
        >>> set(n1.links(is_link(C) | is_link(B))) == set([b21, b13, c12, c21])
        True
        >>> set(n1.links(outgoing & (is_link(C) | is_link(B)))) == set([b13, c12])
        True

    '''
    return link_predicate(lambda node, link: isinstance(link, typ))

def is_link_only(typ):
    r'''Return a predicate that matches links of the given type but not
    subtypes thereof.

        >>> class A(Link): pass
        >>> class B(A): pass
        >>> class C(Link): pass
        >>> n1 = Node()
        >>> n2 = Node()
        >>> n3 = Node()
        >>> a12 = A(n1, n2)
        >>> a23 = A(n2, n3)
        >>> a31 = A(n3, n1)
        >>> b13 = B(n1, n3)
        >>> b32 = B(n3, n2)
        >>> b21 = B(n2, n1)
        >>> c12 = C(n1, n2)
        >>> c21 = C(n2, n1)
        >>> set(n1.links(is_link_only(A))) == set([a12, a31])
        True
        >>> set(n1.links(~is_link_only(A))) == set([b13, b21, c12, c21])
        True
        >>> set(n1.links(is_link_only(A) & outgoing)) == set([a12])
        True
        >>> set(n1.links(is_link_only(B))) == set([b21, b13])
        True
        >>> set(n1.links(is_link_only(C))) == set([c12, c21])
        True
        >>> set(n1.links(is_link_only(C) | is_link_only(B))) == set([b21, b13, c12, c21])
        True
        >>> set(n1.links(outgoing & (is_link_only(C) | is_link_only(B)))) == set([b13, c12])
        True

    '''
    return link_predicate(lambda node, link: type(link) is typ)

def from_node(node):
    r'''Return a predicate that selects links from the given node, or from a
    class of nodes.

        >>> class A(Node): pass
        >>> class B(A): pass
        >>> class C(Node): pass
        >>> a = A()
        >>> b = B()
        >>> c = C()
        >>> ab = Link(a, b)
        >>> ba = Link(b, a)
        >>> bc = Link(b, c)
        >>> cb = Link(c, b)
        >>> ca = Link(c, a)
        >>> ac = Link(a, c)
        >>> set(a.links(from_node(a))) == set([ab, ac])
        True
        >>> set(a.links(from_node(b))) == set([ba])
        True
        >>> set(a.links(from_node(c))) == set([ca])
        True
        >>> set(a.links(from_node(A))) == set([ab, ba, ac])
        True
        >>> set(b.links(from_node(A))) == set([ab, ba, bc])
        True
        >>> set(c.links(from_node(A))) == set([ac, bc])
        True
        >>> set(c.links(from_node(B))) == set([bc])
        True

    '''
    if type(node) is type:
        assert issubclass(node, Node)
        return link_predicate(lambda node0, link: isinstance(link.node1, node))
    assert isinstance(node, Node)
    return link_predicate(lambda node0, link: link.node1 is node)

def to_node(node):
    r'''Return a predicate that selects links to the given node, or to a class
    of nodes.

        >>> class A(Node): pass
        >>> class B(A): pass
        >>> class C(Node): pass
        >>> a = A()
        >>> b = B()
        >>> c = C()
        >>> ab = Link(a, b)
        >>> ba = Link(b, a)
        >>> bc = Link(b, c)
        >>> cb = Link(c, b)
        >>> ca = Link(c, a)
        >>> ac = Link(a, c)
        >>> set(a.links(to_node(a))) == set([ba, ca])
        True
        >>> set(b.links(to_node(a))) == set([ba])
        True
        >>> set(c.links(to_node(a))) == set([ca])
        True
        >>> set(a.links(to_node(A))) == set([ab, ba, ca])
        True
        >>> set(a.links(to_node(B))) == set([ab])
        True
        >>> set(a.links(to_node(C))) == set([ac])
        True

    '''
    if type(node) is type:
        assert issubclass(node, Node)
        return link_predicate(lambda node0, link: isinstance(link.node2, node))
    assert isinstance(node, Node)
    return link_predicate(lambda node0, link: link.node2 is node)

def has_place(place):
    r'''Return a predicate that selects links with the given place.
    '''
    return link_predicate(lambda node, link: link.place() == place)

def test_link(func):
    r'''Return a predicate that selects links with a given named attribute with
    a given value.
    '''
    return link_predicate(lambda node, link: func(link))

class NamedNode(Node):

    r'''A node with one or more names.
    '''

    def names(self):
        r'''Iterate over all the names that this node may be listed under.
        '''
        return self.sort_keys()

    def matches(self, text):
        r'''Return true if any of the names of this node start with the given
        text.
        '''
        for name in self.names():
            if name.startswith(text):
                return True
        return False

    def __unicode__(self):
        return unicode(self.names().next())

    def __str__(self):
        return str(unicode(self))

def name_matches(text):
    r'''Return a predicate that selects links to named nodes whose name(s)
    match the given text.
    '''
    itext = _istr(text)
    def _match(node, link):
        oth = link.other(node)
        if not isinstance(oth, NamedNode):
            return False
        for name in oth.names():
            if itext in _istr(name):
                return True
        return False
    return link_predicate(_match)

def _istr(text):
    r'''Convert a text into an index string, used for matching searches.

        >>> _istr('One Two Three33! 456 seven')
        ' one two three33 456 seven'

        >>> _istr(u'José Muñoz Güell')
        u' jose munoz guell'

    '''
    if isinstance(text, unicode):
        text = unicodedata.normalize('NFD', text)
    return ' '.join([''] +
                    filter(len, [filter(lambda c: c.isalnum(), word).lower()
                                 for word in text.split()]))
