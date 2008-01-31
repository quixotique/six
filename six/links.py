# vim: sw=4 sts=4 et fileencoding=latin1 nomod

r'''Data model - Link subclasses.
'''

from six.node import *
from six.multilang import multilang

__all__ = [
        'Is_in',
        'Belongs_to',
        'Resides_at', 'Has_postal_address',
        'Association', 'With', 'Ex',
    ]

class Is_in(Link):

    r'''Indicates when a node intrinsically pertains to a country or area.
    This is not suitable for people, because they can move around.  It is
    suitable for phone numbers and addresses, which are embedded within their
    national and regional context.  It may be suitable for Companies, which are
    generally incorporated within a single legal juristiction pertaining to a
    country or area.
    '''

    def __init__(self, node, place, timestamp=None):
        from six.world import Place
        assert isinstance(place, Place)
        super(Is_in, self).__init__(node, place.node, timestamp=timestamp)
        self.node = node
        self.where = place

    def only_place(self):
        return self.where

class Belongs_to(Link):

    r'''Indicates that a person is part of a family, either as one of the
    "heads" of the family (typically the parents), or simply as a member
    (typically the offspring).
    '''

    def __init__(self, person, family, is_head=False, sequence=None,
                       timestamp=None):
        from six.person import Person
        from six.family import Family
        assert isinstance(person, Person)
        assert isinstance(family, Family)
        super(Belongs_to, self).__init__(person, family, timestamp=timestamp)
        self.person = person
        self.family = family
        self.is_head = bool(is_head)
        self.sequence = sequence

    def only_place(self):
        return self.family.only_place()

class Resides_at(Link):

    r'''Indicates that the person, family, or organisation resides at a given
    residential address.
    '''

    def __init__(self, who, residence, timestamp=None):
        from six.person import Person
        from six.family import Family
        from six.org import Organisation
        from six.address import Residence
        assert isinstance(who, (Person, Family, Organisation))
        assert isinstance(residence, Residence)
        super(Resides_at, self).__init__(who, residence, timestamp=timestamp)
        self.who = who
        self.residence = residence

    def only_place(self):
        r'''A residence's place determines a person's place, but if the
        residence's place is unknown, then the residential phone numbers can
        give a clue.
        '''
        place = self.residence.only_place()
        if place:
            return place
        return self.derive_only_place(outgoing & linked(Has_phone))

    def __repr__(self):
        r = ['who=%r' % self.who, 'residence=%r' % self.residence]
        if self.timestamp:
            r.append('timestamp=%r' % self.timestamp)
        return '%s(%s)' % (self.__class__.__name__, ', '.join(r))

class Has_postal_address(Link):

    r'''Indicates that a person, family, or organisation may be contacted by
    post to the given postal address.
    '''

    def __init__(self, who, postal, timestamp=None):
        from six.person import Person
        from six.family import Family
        from six.org import Organisation, Works_at
        from six.address import PostalAddress
        assert isinstance(who, (Person, Family, Organisation, Works_at))
        assert isinstance(postal, PostalAddress)
        super(Has_postal_address, self).__init__(who, postal, timestamp=timestamp)
        self.who = who
        self.postal = postal

    def only_place(self):
        r'''A postal address's place can determine a person's place.
        '''
        return self.postal.only_place()

class Association(Link):

    r'''An association between two nodes could mean almost anything.  To
    explain the association, the 'description' may be used.  Subclasses of
    Association are defined to narrow the meaning, and may impose specific
    semantics on 'description'.
    '''

    def __init__(self, node1, node2, position=None, timestamp=None):
        if position is not None:
            assert isinstance(position, (basestring, multilang))
        super(Association, self).__init__(node1, node2, timestamp=timestamp)
        self.position = position

    def __repr__(self):
        return '%s(node1=%r, node2=%r)' % (type(self).__name__, self.node1,
                                           self.node2)

class With(Association):

    r'''A 'With' association between two nodes represents a real-world
    connection of some sort, which may act as the context for comments, data,
    and even contact details.  For example:
     - Person-Person: family relationships, eg parent-child, sibling,
       (ex-)partner, godparent; professional relationships, eg, attourney,
       physician, tax agent
     - Person-Organisation: employee, member, client, supplier, director
     - Family-Organisation: client, member
    '''

class Ex(Association):

    r'''A historical association between a person and an organisation,
    indicating a stronger relationship (eg, employment, membership) which once
    existed but has since come to an end.
    '''
