# vim: sw=4 sts=4 et fileencoding=utf8 nomod

r'''Data model - Organisation and Works_at.
'''

from sixx.node import *
from sixx.sort import *
from sixx.uniq import uniq_generator
from sixx.multilang import multilang

__all__ = [
            'Organisation', 'Company', 'Department',
            'Has_department',
            'Works_at', 'Located_at',
        ]

class Organisation(NamedNode):

    r'''An organisation is a company or department or division thereof, or any
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
        assert isinstance(name, (str, multilang))
        if prefer is not None:
            assert prefer == name or prefer in aka
        super(Organisation, self).__init__(aka=aka)
        self.name = name
        self.prefer = prefer

    @uniq_generator
    def names(self, with_aka=True):
        r'''Iterate over all the names that this organisation can have.
        '''
        if self.prefer:
            yield self.prefer
        yield self.name
        if with_aka:
            for name in self.aka:
                yield name

    def sortkey(self):
        return next(self.names())

    def all_parents(self):
        r'''Iterate through all the organisations that this organisation
        belongs to, in breadth-wise bottom-up order (ie, each organisation of
        which this is a department is followed immediately by its parents).
        '''
        for org in self.nodes(incoming & is_link(Has_department)):
            yield org
            for org1 in org.all_parents():
                yield org1

    def only_place(self):
        r'''An organisation's place, if not explicitly set, is derived from its
        residence(s), or if none, then its postal address(es), or if none, then
        its phone number(s), or if none, then if it is a department, its
        company's place.
        '''
        from sixx.links import Resides_at, Has_postal_address, Belongs_to
        from sixx.telephone import Has_phone
        if self.place:
            return self.place
        return self.derive_only_place(outgoing & is_link(Resides_at),
                                      outgoing & is_link(Has_postal_address),
                                      outgoing & is_link(Has_phone),
                                      incoming & is_link(Has_department))

    def _all_places(self):
        from sixx.links import Resides_at, Has_postal_address
        from sixx.telephone import Has_phone
        if self.place:
            yield self.place
        for tup in self.find_nodes((outgoing & is_link(Resides_at)) |
                                   (outgoing & is_link(Has_postal_address)) |
                                   (outgoing & is_link(Has_department)) |
                                   (outgoing & is_link(Has_phone))):
            if tup[-1].place:
                yield tup[-1].place

    def __repr__(self):
        r = ['name=%r' % self.name, 'aka=%r' % list(map(repr, self.aka))]
        if self.prefer is not None:
            r.append('prefer=%r' % self.prefer)
        return '%s(%s)' % (self.__class__.__name__, ', '.join(r))

class Department(Organisation):

    r'''A department is a named part of an organisation which can have its
    own distinct contact details.
    '''

    def company(self):
        r'''Return the parent Company to which this department belongs, going
        up through all parent departments to reach it.  There must always be
        exactly one parent company.
        '''
        com = list(self.find_nodes(incoming & is_link(Has_department),
                                   select=instance_p(Company)))
        assert len(com) == 1
        return com[0][-1]

class Company(Organisation):

    r'''A company is a top-level organisation that can have departments but is
    not itself a department of any other organisation.
    '''

class Has_department(Link):

    r'''The only possible relationship between a Company and a Department.
    A department can only belong to a single company.
    '''

    def __init__(self, company, dept, is_head=False, timestamp=None):
        assert isinstance(company, Company)
        assert isinstance(dept, Department)
        self.company = company
        self.dept = dept
        self.is_head = bool(is_head)
        dups = list(dept.links(incoming & is_link(Has_department)))
        if dups:
            raise ValueError('%s is already a department of %s' % str(dups[0].dept), str(dups[0].company))
        super(Has_department, self).__init__(company, dept, timestamp=timestamp)

    def __lt__(self, other):
        if not isinstance(other, Has_department):
            return NotImplemented
        if self.is_head:
            if not other.is_head:
                return True
        elif other.is_head:
            if not other.is_head:
                return False
        return self.dept.sortkey() < other.dept.sortkey()

    def only_place(self):
        r'''The place of a company is the default place of its departments.
        '''
        return self.company.only_place()

from sixx.links import Association

class Works_at(Association):

    r'''An association between a person and an organisation, which implies
    certain things, such as the existence of some kind of employment contract,
    that the person is contactable at the organisation during business hours,
    and that the person may represent the organisation in some way.
    '''

    def __init__(self, person, org, position=None, is_head=False, sequence=None, timestamp=None):
        from sixx.person import Person
        from sixx.address import Residence
        assert isinstance(person, Person)
        assert isinstance(org, (Organisation, Residence))
        if position is not None:
            assert isinstance(position, (str, multilang))
        self.person = person
        self.org = org
        self.is_head = bool(is_head)
        self.sequence = sequence
        super(Works_at, self).__init__(person, org, position=position, timestamp=timestamp)

    def __lt__(self, other):
        if not isinstance(other, Works_at):
            return NotImplemented
        if not self.sequence:
            if other.sequence:
                return True
        elif self.sequence:
            if not other.sequence:
                return False
        return self.person.sortkey() < other.person.sortkey()

    def __repr__(self):
        r = ['person=%r' % self.person,
             'org=%r' % self.org,
             'is_head=%r' % self.is_head,
             'sequence=%r' % self.sequence,]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(r))

class Located_at(Association):

    r'''An association between any two organisations, indicating that the first
    is located at or contactable through the second.  This can be used in lieu
    of a residential address for a company or department; the host
    organisation's contact details (including its name) become part of the
    contact address for the client organisation.
    '''

    def __init__(self, client, host, sequence=None, timestamp=None):
        assert isinstance(client, Organisation)
        assert isinstance(host, Organisation)
        self.client = client
        self.host = host
        self.sequence = sequence
        super(Located_at, self).__init__(client, host, timestamp=timestamp)

    def __lt__(self, other):
        if not isinstance(other, Located_at):
            return NotImplemented
        if not self.sequence:
            if other.sequence:
                return True
        elif self.sequence:
            if not other.sequence:
                return False
        return self.client.sortkey() < other.client.sortkey()

    def __repr__(self):
        r = ['client=%r' % self.client,
             'host=%r' % self.host,
             'sequence=%r' % self.sequence,]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(r))
