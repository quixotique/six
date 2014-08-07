# vim: sw=4 sts=4 et fileencoding=latin1 nomod

r'''Data model.
'''

import time
from sixx.input import InputError
from sixx.node import *
from sixx.sort import *
from sixx.uniq import uniq_generator
from sixx.multilang import *
from sixx.personname import (PersonName, EnglishSpanishName, SingleName,
                            DecoratedName)
from sixx.date import Datetime

__all__ = ['Person', 'Birthday', 'Born_on']

class Person(NamedNode):

    r'''A Person represents a real person, with a name.
     - A person may belong to at most one family.
     - A person may may work at several organisations and/or departments
       thereof, possibly with a different title at each one.
     - A person may have one or several phone numbers, which are probably
       mobiles unless his/her residence is not known, in which case fixed lines
       and faxes may also be linked directly to a person.
     - A person may have one or more email addresses.
    '''

    def __init__(self, name, aka=None):
        assert isinstance(name, PersonName)
        super(Person, self).__init__(aka=aka)
        self.name = name

    def only_place(self):
        r'''A person's place depends on his/her residence(s), or if none, then
        his/her postal address(es), or if none, then his/her phone number(s),
        or if none, then his/her family's place.
        '''
        from sixx.links import Resides_at, Has_postal_address, Belongs_to
        from sixx.telephone import Has_phone
        return self.derive_only_place(outgoing & is_link(Resides_at),
                                      outgoing & is_link(Has_postal_address),
                                      outgoing & is_link(Belongs_to),
                                      outgoing & is_link(Has_phone),)

    def _all_places(self):
        from sixx.links import Resides_at, Has_postal_address, Belongs_to
        from sixx.org import Works_at, Has_department
        from sixx.telephone import Has_phone
        for tup in self.find_nodes((outgoing & is_link(Resides_at)) |
                                   (outgoing & is_link(Works_at)) |
                                   (incoming & is_link(Has_department)) |
                                   (outgoing & is_link(Belongs_to)) |
                                   (outgoing & is_link(Has_postal_address)) |
                                   (outgoing & is_link(Has_phone))):
            if tup[-1].place:
                yield tup[-1].place

    def matches(self, text):
        return self.name.matches(text)

    @uniq_generator
    @expand_multilang_generator
    def sort_keys(self, sort_mode):
        r'''Iterate over all the sort keys that this person can have.
        '''
        yielded = 0
        if sort_mode is SortMode.LAST_NAME:
            try:
                yield self.name.collation_name()
                yielded += 1
            except ValueError:
                pass
        else:
            try:
                yield self.name.informal_index_name()
                yielded += 1
            except ValueError:
                pass
        if sort_mode is SortMode.ALL_NAMES or yielded == 0:
            yield self.name.formal_index_name()
            yielded += 1
        if sort_mode is SortMode.ALL_NAMES:
            try:
                yield self.name.collation_name()
                yielded += 1
            except ValueError:
                pass
        for aka in self.aka:
            yield aka
            yielded += 1

    @uniq_generator
    def names(self, with_aka=True):
        r'''Iterate over all the names that this person has.  First comes the
        person's informal name if it can be formed, followed by the complete
        name which contains all known words in the name, in uncontracted form,
        or initials where only initials are known.  Then, follows the person's
        familiar name if it differs from the first words in the complete name.
        Finally, all the aka names.
        '''
        try:
            yield self.name.informal_index_name()
        except ValueError:
            pass
        yield self.name.complete_name()
        if with_aka:
            for aka in self.aka:
                yield aka

    def complete_name(self):
        r'''Return the most complete form of the person's name, omitting any
        pieces that we don't know.
        '''
        return self.name.complete_name()

    def familiar_name(self):
        r'''Return the person's name as used in a familiar context.
        '''
        try:
            return self.name.familiar_name()
        except ValueError:
            return self.family_head_name()

    def family_head_name(self):
        r'''Return the person's name as used in a the context as the head of a
        family.  This is used for forming the name of a family.
        '''
        try:
            return self.name.casual_name() # given-name surname if known
        except ValueError:
            return self.name.complete_name() # else as much as we know

    def email_address_name(self):
        r'''Return the person's name as used in forming an email address.
        '''
        try:
            return self.name.casual_name()
        except ValueError:
            pass
        try:
            return self.name.full_name()
        except ValueError:
            pass
        return self.name.complete_name()

    def full_name_known(self):
        r'''Used when ordering the heads of a family -- those whose full names
        are known come first.
        '''
        try:
            self.name.full_name()
            return True
        except ValueError:
            return False

    def birthday(self):
        try:
            return self.links(outgoing & is_link(Born_on)).next()
        except StopIteration:
            return None

    def family(self):
        r'''A person can belong to exactly zero or one familiy.
        @return: tuple (None, None) or tuple (Belongs_to, Family)
        '''
        from sixx.links import Belongs_to
        families = list(self.links(outgoing & is_link(Belongs_to)))
        if not families:
            return None, None
        assert len(families) == 1
        assert families[0].person is self
        return families[0], families[0].family 
    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.name)

    def sortkey(self):
        return self.name.sortkey()

    @staticmethod
    def initargs(part):
        kw = {}
        def set(kwname, *keys):
            value = None
            for key in keys:
                if key in part:
                    value = part.getvalue(key)
                    break
            if value is not None:
                kw[kwname] = value
        set('single', 'n')
        if not kw:
            set('short', 'fn-')
            set('giveni', 'fn.')
            set('given', 'fn')
            set('middle', 'mn')
            set('middlei', 'mn.')
            set('family', 'ln')
            set('family2', 'ln2')
            set('title', 'tit')
            set('honorific', 'hon')
            set('salutation', 'sal')
            set('letters', 'let')
        return kw

    @classmethod
    def from_initargs(class_, kw, **kwargs):
        assert len(kw) != 0
        try:
            nkw = {}
            dkw = {}
            for key in kw:
                if key in ('title', 'salutation', 'honorific', 'letters'):
                    dkw[key] = kw[key]
                else:
                    nkw[key] = kw[key]
            if not nkw:
                raise ValueError('missing name')
            if 'single' in nkw:
                name = SingleName(**nkw) 
            else:
                name = EnglishSpanishName(**nkw) 
            if dkw:
                name = DecoratedName(name, **dkw)
            return class_(name, **kwargs)
        except ValueError, e:
            raise InputError(e, lines=kw.values())

class Birthday(Node):

    r'''Representation of a person's birthday as day and month.
    '''

    def __init__(self, day, month):
        super(Birthday, self).__init__()
        self.day = day
        self.month = month

    def __str__(self):
        return str(unicode(self))

    def __unicode__(self):
        return self.format()

    def format(self, year=None):
        fmt = '%-d-%b'
        if year is not None:
            fmt += '-%Y'
        else:
            year = 1970
        return time.strftime(fmt, time.struct_time(
                             (year, self.month, self.day, 0, 0, 0, 0, 0, 0)))

    def __cmp__(self, other):
        if not isinstance(other, Birthday):
            return NotImplemented
        return cmp(self.month, other.month) or cmp(self.day, other.day)

    @classmethod
    def parse(class_, text):
        dt = Datetime.parse(text, with_time=False, with_timezone=False)
        if dt.month is None:
            raise InputError('missing month', char=text)
        if dt.day is None:
            raise InputError('missing day', char=text)
        return class_(dt.day, dt.month), dt.year

class Born_on(Link):
    def __init__(self, person, birthday, year=None):
        assert isinstance(person, Person)
        assert isinstance(birthday, Birthday)
        super(Born_on, self).__init__(person, birthday)
        self.person = person
        self.birthday = birthday
        self.year = year

    def __str__(self):
        return str(unicode(self))

    def __unicode__(self):
        return self.format()

    def format(self):
        return self.birthday.format(self.year)
