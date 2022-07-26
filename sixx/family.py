# vim: sw=4 sts=4 et fileencoding=utf8 nomod

r'''Data model - Family.
'''

from collections import defaultdict
from collections.abc import Callable
from sixx.node import *
from sixx.person import Person
from sixx.uniq import uniq_generator
from sixx.multilang import *
from sixx.sort import SortMode

__all__ = ['Family']

class Family(NamedNode):

    r'''A family is created whenever two or more people are grouped together in
    the input file without a common organisation.  Instead of each person being
    assigned a residence, phone numbers, etc., the people are linked as
    belonging to the family, and all the common nodes linked to the family
    node.  A family's name is formed from the familiar names of the "heads" of
    the family, which correspond to the people with "+" delimiters.
    '''

    def _name(self, first=None, by_last_name=False):
        r'''Form the name of the family from the names of all the heads of
        family, in order.  If the 'first' argument is given, then place that
        person at the front of the name.
        '''
        people = []
        if first:
            assert isinstance(first, Person)
            people.append(first)
        for person in self.heads():
            if person != first:
                people.append(person)
        r = []
        surname = None
        for person in people:
            hn = person.family_head_name()
            try:
                tn = ' ' + person.name.title_name()
            except ValueError:
                tn = None
            if tn:
                if hn.endswith(tn):
                    hn = hn[:-len(tn)]
                else:
                    tn = None
            if surname != tn:
                if surname:
                    if by_last_name:
                        r.insert(-1, surname + ', ')
                    else:
                        r.append(surname)
                surname = tn
            if r:
                r.append(' & ')
            r.append(hn)
        if surname:
            if by_last_name:
                r.insert(-1, surname + ', ')
            else:
                r.append(surname)
        return ''.join(r)

    def only_place(self):
        r'''A family's place depends on its residence(s), or if there are none,
        its postal address(es), or if none, its phone number(s).
        '''
        from sixx.links import Resides_at, Has_postal_address
        from sixx.telephone import Has_phone
        return self.derive_only_place(outgoing & is_link(Resides_at),
                                      outgoing & is_link(Has_postal_address),
                                      outgoing & is_link(Has_phone))

    def _all_places(self):
        from sixx.links import Resides_at, Has_postal_address, Belongs_to
        from sixx.telephone import Has_phone
        for tup in self.find_nodes((outgoing & is_link(Resides_at)) |
                                   (outgoing & is_link(Has_postal_address)) |
                                   (incoming & is_link(Belongs_to)) |
                                   (outgoing & is_link(Has_phone))):
            if tup[-1].place:
                yield tup[-1].place

    def heads(self):
        from sixx.links import Belongs_to
        for link in sorted(self.links(incoming & is_link(Belongs_to) &
                                      is_link(test_attr('is_head'))),
                           key=lambda l: (not l.person.full_name_known(),
                                          l.sequence or 0,
                                          l.person.sortkey())):
            yield link.person

    def tails(self):
        from sixx.links import Belongs_to
        for link in sorted(self.links(incoming & is_link(Belongs_to) &
                                      ~is_link(test_attr('is_head')))):
            yield link.person

    @uniq_generator
    @expand_multilang_generator
    def sort_keys(self, sort_mode):
        r'''Iterate over all the sort keys that this family can have.  This
        starts with the full name of the family formed from the names of all
        the heads, which is then permuted to start with each of the heads.
        Then the collation name (if known) of each head.  Finally any AKAs.
        '''
        for head in self.heads():
            yield self._name(head, by_last_name = sort_mode is SortMode.LAST_NAME)
        if sort_mode is SortMode.ALL_NAMES:
            coll = defaultdict(list)
            for head in self.heads():
                try:
                    cn = head.name.collation_name()
                    fn, gn = cn.split(', ')
                    coll[fn].append(gn)
                except ValueError:
                    pass
            for fn, gns in coll.items():
                yield fn + ', ' + ' & '.join(gns)
        for aka in self.aka:
            yield aka

    @uniq_generator
    def names(self, with_aka=True):
        r'''Iterate over all the names that this family may be listed under.
        This only returns the principle name of the family, formed from the
        names of the heads in proper order.  This avoids listings that show
        alternate names for the family, but just with the order of the names
        swapped, which is of no use to anyone.
        '''
        yield self._name()
        if with_aka:
            for aka in self.aka:
                yield aka

    def matches(self, text):
        r'''Return true if the name of this family matches the given text.
        '''
        heads = list(self.heads())
        parts = list(filter(bool, [p.strip() for p in text.split('&')]))
        if len(parts) == len(heads):
            for h, p in zip(heads, parts):
                if not h.matches(p):
                    break
            else:
                return True
        for name in self.aka:
            if hasattr(name, 'matches') and isinstance(name.matches, Callable):
                if name.matches(text):
                    return True
            elif name.startswith(text):
                return True
        return False

    def __repr__(self):
        return '%s()' % self.__class__.__name__
