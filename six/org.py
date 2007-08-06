# vim: sw=4 sts=4 et fileencoding=latin1 nomod

r'''Data model - Organisation and Works_at.
'''

from six.node import *
from six.sort import *
from six.multilang import multilang

__all__ = [
            'Organisation', 'Company', 'Department',
            'Has_department',
            'Works_at',
        ]

class Organisation(NamedNode):

    r'''An organisation is a company or department or division thereor, or any
    other named (usually incorporated) entity, where people work or can be
    contacted, or which provide context for personal data.
    '''

    def __init__(self, name, aka=None, prefer=None):
        r'''
        @param name: full legal name
        @type  name: basestring or multilang
        @param aka: other names
        @param prefer: preferred name
        '''
        assert isinstance(name, (basestring, multilang))
        aka = list(aka) if aka is not None else []
        for a in aka:
            assert isinstance(a, (basestring, multilang))
        if prefer is not None:
            assert prefer == name or prefer in aka
        super(Organisation, self).__init__()
        self.name = name
        self.aka = aka
        self.prefer = prefer

    def only_place(self):
        r'''An organisation's place depends on its residence(s), or if none,
        then its postal address(es), or if none, then its phone number(s), or
        if none, then if it is a department, its company's place.
        '''
        from six.links import Resides_at, Has_postal_address, Belongs_to
        from six.telephone import Has_phone
        return self.derive_only_place(outgoing & is_link(Resides_at),
                                      outgoing & is_link(Has_postal_address),
                                      outgoing & is_link(Has_phone),
                                      incoming & is_link(Has_department))

    def _all_places(self):
        from six.links import Resides_at, Has_postal_address
        from six.telephone import Has_phone
        for tup in self.find_nodes((outgoing & is_link(Resides_at)) |
                                   (outgoing & is_link(Has_postal_address)) |
                                   (outgoing & is_link(Has_department)) |
                                   (outgoing & is_link(Has_phone))):
            if tup[-1].place:
                yield tup[-1].place

    @uniq_generator
    def sort_keys(self):
        r'''Iterate over all the sort keys (names) that this organisation can
        have.  If the name or any of the aka names is a multilang, then this
        iterates over all the alternative languages in each.
        '''
        if self.prefer is not None:
            yield unicode(self.prefer)
        if isinstance(self.name, multilang):
            for alt in self.name.itertexts():
                yield alt
        else:
            yield self.name
        for aka in self.aka:
            if isinstance(aka, multilang):
                for alt in aka.itertexts():
                    yield alt
            else:
                yield aka

    def __repr__(self):
        r = ['name=%r' % self.name, 'aka=%r' % map(str, self.aka)]
        if self.prefer is not None:
            r.append('prefer=%r' % self.prefer)
        return '%s(%s)' % (self.__class__.__name__, ', '.join(r))

class Department(Organisation):

    r'''A department is a named part of an organisation which can have its
    own distinct contact details.
    '''

class Company(Organisation):

    r'''A company is a top-level organisation that can have departments but is
    not itself a department of any other organisation.
    '''

class Has_department(Link):

    r'''The only possible relationship between a Company and a Department.
    '''

    def __init__(self, company, dept, timestamp=None):
        assert isinstance(company, Company)
        assert isinstance(dept, Department)
        super(Has_department, self).__init__(company, dept, timestamp=timestamp)
        self.company = company
        self.dept = dept

from six.links import Association

class Works_at(Association):

    r'''An association between a person and an organisation, which implies
    certain things, such as the existence of some kind of employment contract,
    that the person is contactable at the organisation during business hours,
    and that the person may represent the organisation in some way.
    '''

    def __init__(self, person, org, position=None, sequence=None,
                       timestamp=None):
        from six.person import Person
        from six.address import Residence
        assert isinstance(person, Person)
        assert isinstance(org, (Organisation, Residence))
        if position is not None:
            assert isinstance(position, (basestring, multilang))
        super(Works_at, self).__init__(person, org, position=position,
                                       timestamp=timestamp)
        self.person = person
        self.org = org
        self.sequence = sequence

    def __cmp__(self, other):
        if not isinstance(other, Works_at):
            return NotImplemented
        return (cmp(self.sequence or 0, other.sequence or 0) or
                cmp(self.person.sortkey(), other.person.sortkey()))
