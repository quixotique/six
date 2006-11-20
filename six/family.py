# vim: sw=4 sts=4 et fileencoding=latin1 nomod

r'''Data model - Family and Belongs_to.
'''

from six.node import *
from six.sort import *

__all__ = ['Family']

class Family(NamedNode):

    r'''A family is created whenever two or more people are grouped together in
    the input file without a common organisation.  Instead of each person being
    assigned a residence, phone numbers, etc., the people are linked as
    belonging to the family, and all the common nodes linked to the family
    node.  A family's name is formed from the familiar names of the "heads" of
    the family, which correspond to the people with "+" delimiters.
    '''

    def name(self, head=None):
        r = []
        people = list(self.heads())
        if head:
            people.remove(head)
            r.append(head.name.familiar_name())
        for person in people:
            r.append(person.name.familiar_name())
        return u' & '.join(r)

    def only_place(self):
        r'''A family's place depends on its residence(s), or if there are none,
        its postal address(es), or if none, its phone number(s).
        '''
        from six.links import Resides_at, Has_postal_address
        from six.telephone import Has_phone
        return self.derive_only_place(outgoing & is_link(Resides_at),
                                      outgoing & is_link(Has_postal_address),
                                      outgoing & is_link(Has_phone))

    def _all_places(self):
        from six.links import Resides_at, Has_postal_address, Belongs_to
        from six.telephone import Has_phone
        for tup in self.find_nodes((outgoing & is_link(Resides_at)) |
                                   (outgoing & is_link(Has_postal_address)) |
                                   (incoming & is_link(Belongs_to)) |
                                   (outgoing & is_link(Has_phone))):
            if tup[-1].place:
                yield tup[-1].place

    def heads(self):
        from six.links import Belongs_to
        for link in sorted(self.links(incoming & is_link(Belongs_to) &
                                      test_link(lambda l: l.is_head))):
            yield link.person

    def tails(self):
        from six.links import Belongs_to
        for link in sorted(self.links(incoming & is_link(Belongs_to) &
                                      test_link(lambda l: not l.is_head))):
            yield link.person

    def sort_keys(self):
        r'''Iterate over all the sort keys that this family can have.
        '''
        for head in self.heads():
            yield self.name(head)

    def names(self):
        r'''Iterate over all the names that this family may be listed under.
        '''
        yield self.name()

    def __repr__(self):
        return '%s()' % self.__class__.__name__
