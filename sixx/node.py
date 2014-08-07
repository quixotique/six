# vim: sw=4 sts=4 et fileencoding=latin1 nomod

r'''Data model - Node and Link superclasses, and link predicate algebra.
'''

import datetime
from sixx.text import *
from sixx.uniq import uniq, uniq_generator
from sixx.multilang import *

__all__ = [
        'Node', 'Link', 'NamedNode',
        'incoming', 'outgoing', 'is_other', 'is_link',
        'instance_p', 'type_p',
        'from_node', 'to_node',
        'in_place', 'test_attr',
        'name_imatches',
    ]

class Node(object):

    r'''A node in the model graph.  To be subclassed.

    @ivar place: used when parsing to help provide a context for
        place-dependent data which is linked to this node, eg, phone numbers.
    '''

    def __init__(self):
        self._links = set()
        self.place = None

    def add_link(self, r):
        r'''Used by Link().'''
        assert isinstance(r, Link), '%r is not a Link' % r
        if r not in self._links:
            self._links.add(r)

    def only_place(self):
        r'''Deduce the place (area or country) to which this node pertains,
        based on its links to other nodes.
        '''
        return self.place

    def all_places(self):
        r'''Iterate over all the places (areas and/or countries) to which this
        node pertains, based on its links to other nodes.
        '''
        return uniq(self._all_places())

    def _all_places(self):
        r'''Internal implementation of all_places() that can yield the same
        place more than once.
        '''
        if self.place:
            yield self.place

    def __unicode__(self):
        return unicode(str(self))

    def __str__(self):
        return self.__class__.__name__

    def derive_only_place(self, *preds):
        r'''Determine the place of this node, based on the links that satisfy
        a series of predicates.
        '''
        place = None
        for pred in preds:
            for link in self.links(pred):
                if place is None:
                    place = link.only_place()
                elif place != link.only_place():
                    place = None
                    break
            if place is not None:
                break
        return place

    def links(self, pred=None):
        r'''Iterate over all the links attached to this node that satisfy the
        given selection predicate, link predicate, or whose node at the other
        end of the link satisfies the given node predicate.

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
            >>> set(n.links(to_node(instance_p(A)))) == set([lna, lnb])
            True
            >>> set(n.links(to_node(instance_p(A)) & to_node(instance_p(B)))) == set([lnb])
            True
            >>> set(n.links(to_node(instance_p(A)) & to_node(instance_p(C)))) == set([])
            True

        '''
        if pred is None:
            pred = selection_predicate(lambda n, l: True)
        else:
            pred = selection_predicate.cast(pred)
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
            >>> n.link(to_node(instance_p(A)))
            Traceback (most recent call last):
            AssertionError
            >>> n.link(to_node(instance_p(A)) & to_node(instance_p(B))) is lnb
            True
            >>> n.link(to_node(instance_p(A)) & to_node(instance_p(C))) is None
            True

        '''
        links = list(self.links(pred))
        assert len(links) <= 1
        return links[0] if len(links) else None

    def nodes(self, pred=None):
        r'''Iterate over all the nodes linked to this node which satisfy the
        given node predicate, or which are connected by a link which satisfies
        the given selection predicate or link predicate.

            >>> class A(Node): pass
            >>> class B(A): pass
            >>> a = A()
            >>> b = B()
            >>> n = Node()
            >>> la = Link(n, a)
            >>> lb = Link(n, b)
            >>> set(n.nodes()) == set([a, b])
            True
            >>> set(n.nodes(to_node(instance_p(A)))) == set([a, b])
            True
            >>> set(n.nodes(to_node(instance_p(B)))) == set([b])
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
            >>> n.node(to_node(instance_p(A)))
            Traceback (most recent call last):
            AssertionError
            >>> n.node(to_node(instance_p(B))) is b
            True
            >>> n.node(to_node(instance_p(C))) is None
            True

        '''
        nodes = list(self.nodes(pred))
        assert len(nodes) <= 1
        return nodes[0] if len(nodes) else None

    def find_nodes(self, traverse, select=None, stop=None):
        r'''
        @param traverse: selection predicate that selects the links to follow
            from each node
        @param select: node predicate that selects the nodes to return
        @param stop: link predicate that selects the links not to follow from
            each node, overrides 'traverse'
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
                    if ((stop is None or not stop(visit[-1])) and
                        id(visit[-1]) not in visited):
                        visited.add(id(visit[-1]))
                        todo.append(nodes + visit)
                        if select is None or select(todo[-1][-1]):
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
        assert isinstance(n1, Node), 'n1=%r is not a Node' % n1
        assert isinstance(n2, Node), 'n2=%r is not a Node' % n2
        if timestamp is not None:
            assert isinstance(timestamp, datetime.date), \
                    'timestamp=%r is not a datetime.date' % timestamp
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

class node_predicate(object):

    r'''A node predicate N is a callable N(Node) which returns True if the node
    satisfies the criteria of the predicate.

    The 'node_predicate' class is a wrapper that allows node predicates to be
    combined using logical operators '&' and '|' and '~' (which ideally should
    be 'and', 'or', 'not', but those operators cannot be overloaded in Python).
    '''

    def __init__(self, func):
        self._func = func

    def __call__(self, node):
        assert isinstance(node, Node), '%r is not a Node' % node
        return self._func(node)

    def __and__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return type(self)(lambda node: self._func(node) and
                                           other._func(node))

    def __or__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return type(self)(lambda node: self._func(node) or
                                           other._func(node))

    def __invert__(self):
        return type(self)(lambda node: not self._func(node))

class link_predicate(node_predicate):

    r'''A link predicate is a specialisation of a node predicate which only
    accepts Link objects.  A link predicate L is a callable L(Link) which
    returns True if the link satisfies the criteria of the predicate.

    The 'link_predicate' class is a wrapper that allows link predicates to be
    combined using logical operators '&' and '|' and '~' (which ideally should
    be 'and', 'or', 'not', but those operators cannot be overloaded in Python).
    '''

    def __call__(self, link):
        assert isinstance(link, Node), '%r is not a Link' % link
        return self._func(link)

class selection_predicate(object):

    r'''A selection predicate S is a callable S(Node, Link) which is invoked in
    the context of an origin node O, for example by O.links(S) or O.nodes(S).
    The first argument passed to the selection predicate is the origin node, O,
    and the second argument L is the Link node in question.  The the node at
    the other end of O can be found using "L.other(O)".
    
    The 'selection_predicate' class is a wrapper that allows selection
    predicates to be combined using logical operators '&' and '|' and '~'
    (which ideally should be 'and', 'or', 'not', but those operators cannot be
    overloaded in Python).
    '''

    def __init__(self, func):
        self._func = func

    @classmethod
    def cast(cls, pred):
        r'''If a node predicate is given where a selection predicate is needed,
        then it is converted to a selection predicate that applies the node
        predicate to the node at the other end of the link, not to the
        originating node.  If a link predicate is given where a selection
        predicate is needed, then it is converted to a selection predicate that
        applies the link predicate to the link.
        '''
        if isinstance(pred, link_predicate):
            pred = is_link(pred)
        elif isinstance(pred, node_predicate):
            pred = is_other(pred)
        if not isinstance(pred, selection_predicate):
            raise NotImplementedError
        return pred

    def __call__(self, node, link):
        assert isinstance(node, Node), '%r is not a Node' % node
        assert isinstance(link, Node), '%r is not a Link' % link
        return self._func(node, link)

    def __and__(self, other):
        try:
            other = self.cast(other)
        except NotImplementedError:
            return NotImplemented
        return selection_predicate(lambda node, link:
                            self._func(node, link) and other._func(node, link))

    def __rand__(self, other):
        try:
            other = self.cast(other)
        except NotImplementedError:
            return NotImplemented
        return selection_predicate(lambda node, link:
                            other._func(node, link) and self._func(node, link))

    def __or__(self, other):
        try:
            other = self.cast(other)
        except NotImplementedError:
            return NotImplemented
        return selection_predicate(lambda node, link:
                            self._func(node, link) or other._func(node, link))

    def __ror__(self, other):
        try:
            other = self.cast(other)
        except NotImplementedError:
            return NotImplemented
        return selection_predicate(lambda node, link:
                            other._func(node, link) or self._func(node, link))

    def __invert__(self):
        return selection_predicate(lambda node, link:
                            not self._func(node, link))

@selection_predicate
def outgoing(node, link):
    r'''A selection predicate that selects only links that point outward from
    the orginal node (ie, whose 'node1' attribute is the origin node).

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

@selection_predicate
def incoming(node, link):
    r'''A selection predicate that selects only links that point inward to the
    orginal node (ie, whose 'node2' attribute is the origin node).

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

def is_other(pred):
    r'''Return a selection predicate that applies the given node predicate to
    the node at the other end of the link.
    '''
    assert isinstance(pred, node_predicate)
    return selection_predicate(lambda node, link: pred(link.other(node)))

def is_link(pred):
    r'''Return a link predicate that applies the given link predicate to the
    link.  As a convenience, if L is a subclass of Link, then is_link(L) means
    is_link(instance_p(L)).

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
    if type(pred) is type and issubclass(pred, Link):
        pred = instance_p(pred)
    return selection_predicate(lambda node, link: pred(link))

def instance_p(typ):
    r'''Return a node predicate that returns True if the given Node object is
    an instance of the given type or subclass thereof.
    '''
    if issubclass(typ, Link):
        return link_predicate(lambda link: isinstance(link, typ))
    if issubclass(typ, Node):
        return node_predicate(lambda node: isinstance(node, typ))
    raise ValueError('instance_p(%r): invalid argument' % typ)

def type_p(typ):
    r'''Return a node predicate that returns True if the given Node object is
    an instance of the given type, but not any subclass thereof.

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
        >>> set(n1.links(is_link(type_p(A)))) == set([a12, a31])
        True
        >>> set(n1.links(~is_link(type_p(A)))) == set([b13, b21, c12, c21])
        True
        >>> set(n1.links(is_link(type_p(A)) & outgoing)) == set([a12])
        True
        >>> set(n1.links(is_link(type_p(B)))) == set([b21, b13])
        True
        >>> set(n1.links(is_link(type_p(C)))) == set([c12, c21])
        True
        >>> set(n1.links(is_link(type_p(C)) | is_link(type_p(B)))) == set([b21, b13, c12, c21])
        True
        >>> set(n1.links(outgoing & (is_link(type_p(C)) | is_link(type_p(B))))) == set([b13, c12])
        True

    '''
    if issubclass(typ, Link):
        return link_predicate(lambda link: type(link) is typ)
    if issubclass(typ, Node):
        return node_predicate(lambda node: type(node) is typ)
    raise ValueError('type_p(%r): invalid argument' % typ)

def from_node(node):
    r'''If 'node' is a Node object, return a link predicate that selects links
    that originate from (ie whose 'node1' attribute is) the given node.  If
    'node' is a node predicate, then return a link predicate that selects links
    that originate (ie whose 'node1' attribute is) from nodes that satisfy the
    given predicate.
    
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
        >>> set(a.links(from_node(instance_p(A)))) == set([ab, ba, ac])
        True
        >>> set(b.links(from_node(instance_p(A)))) == set([ab, ba, bc])
        True
        >>> set(c.links(from_node(instance_p(A)))) == set([ac, bc])
        True
        >>> set(c.links(from_node(instance_p(B)))) == set([bc])
        True

    '''
    if isinstance(node, Node):
        return link_predicate(lambda link: link.node1 is node)
    if isinstance(node, node_predicate):
        return link_predicate(lambda link: node(link.node1))
    raise ValueError('from_node(%r): invalid argument' % node)

def to_node(node):
    r'''If 'node' is a Node object, return a link predicate that selects Links
    that point to (ie whose 'node2' attribute is) the given node.  If 'node' is
    a node predicate, then return a link predicate that selects links that
    point to (ie whose 'node2' attribute is) from nodes that satisfy the given
    predicate.

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
        >>> set(a.links(to_node(instance_p(A)))) == set([ab, ba, ca])
        True
        >>> set(a.links(to_node(instance_p(B)))) == set([ab])
        True
        >>> set(a.links(to_node(instance_p(C)))) == set([ac])
        True

    '''
    if isinstance(node, Node):
        return link_predicate(lambda link: link.node2 is node)
    if isinstance(node, node_predicate):
        return link_predicate(lambda link: node(link.node2))
    raise ValueError('to_node(%r): invalid argument' % node)

def in_place(place):
    r'''Return a node predicate that selects nodes that are in a given place.
    '''
    @node_predicate
    def test_is_in(node):
        for p in node.all_places():
            if place.area is not None:
                if p.area == place.area:
                    return True
            elif p.country == place.country:
                return True
        return False
    return test_is_in

def test_attr(name):
    r'''Return a node predicate that selects nodes with a given named attribute
    whose value is true.
    '''
    return node_predicate(lambda node: bool(getattr(node, name, False)))

class NamedNode(Node):

    r'''A node with one or more names.
    '''

    def __init__(self, aka=None):
        r'''
        @param aka: other names
        '''
        super(NamedNode, self).__init__()
        aka = list(uniq(aka)) if aka else []
        for a in aka:
            assert isinstance(a, (basestring, multilang))
        self.aka = aka

    def names(self, with_aka=True):
        r'''Iterate over all the aka names that this organisation has.  This
        method will almost certainly be overridden by all subclasses of
        NamedNode.
        '''
        if with_aka:
            return iter(self.aka)

    @uniq_generator
    @expand_multilang_generator
    def sort_keys(self, sort_mode):
        r'''The sort keys under which this node may be listed are all the names
        that this node has.  If any name is a multilang, then this expands it
        into all its languages.
        '''
        return self.names()

    def matches(self, text):
        r'''Return true if any of the names of this node match the given text.
        If the name has a matches() method, then use that (eg, multilang).
        Otherwise, a simple string matches the text if it starts with the text.
        '''
        for name in self.names():
            if hasattr(name, 'matches') and callable(name.matches):
                if name.matches(text):
                    return True
            elif name == text:
                return True
        return False

    def __unicode__(self):
        return unicode(self.names().next())

    def __str__(self):
        return str(unicode(self))

def name_imatches(text):
    r'''Return a node predicate that selects named nodes whose name(s) contains
    an inner match for the given text.
    '''
    itext = text_match_key(text)
    @node_predicate
    def _match(node):
        if not isinstance(node, NamedNode):
            return False
        for name in node.names():
            if hasattr(name, 'imatches') and callable(name.imatches):
                if name.imatches(itext):
                    return True
            elif itext in text_match_key(name):
                return True
        return False
    return _match
