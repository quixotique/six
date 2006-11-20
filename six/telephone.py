# vim: sw=4 sts=4 et fileencoding=latin1 nomod

r'''Data model - telephone numbers.
'''

import re
from six.multilang import multilang
from six.input import InputError
from six.node import *
from six.world import *

__all__ = [
        'Telephone',
        'Has_phone', 'At_home', 'At_work',
        'Has_mobile', 'Has_mobile_home', 'Has_mobile_work',
        'Has_fixed', 'Has_fixed_home', 'Has_fixed_work',
        'Has_fax', 'Has_fax_home', 'Has_fax_work',
    ]

class Telephone(Node):

    r'''
        >>> au = Country('AU', 'en', '61', multilang('Australia'), \
        ...              aprefix='0', sprefix='1')
        >>> t = Telephone(place=Place(au), acode='8', local='123-4567')
        >>> t
        Telephone(place=Place(Country('AU', 'en_AU', '61', multilang('Australia'), aprefix='0', sprefix='1')), acode='8', local='123-4567')
        >>> str(t)
        '+61 8 123-4567'
        >>> t.only_place()
        Place(Country('AU', 'en_AU', '61', multilang('Australia'), aprefix='0', sprefix='1'))
        >>> t.acode
        '8'
        >>> t.local
        '123-4567'
    '''

    def __init__(self, place, local, acode=None):
        r'''
        @param place: a Place object that specifies the country and optionally
            the area in which the telephone number is located
        @type place: L{Place}
        @param local: the local part of the phone number (omitting the country
            and area codes)
        @type local: str
        @param acode: if the country (given by place.country) has area codes,
            but the place does not specify an area (place.area), then the area
            code must be given in this argument; otherwise, if this argument is
            given, it must agree with place.area
        '''
        assert isinstance(place, Place)
        assert isinstance(local, str) and \
               local.replace('-', '').isdigit()
        if place.country.aprefix:
            if place.area:
                if acode is not None:
                    assert isinstance(acode, str) and acode.isdigit()
                    if acode != place.area.acode:
                        raise ValueError('area code (%s) is not in %s' %
                                         (acode, place.country))
                else:
                    acode = place.area.acode
        elif acode is not None:
            raise ValueError('area codes are not used in %s' % place.country)
        super(Telephone, self).__init__()
        self.place = place
        self.local = local
        self.acode = acode

    def __unicode__(self):
        return unicode(str(self))

    def __str__(self):
        return self.absolute()

    def __repr__(self):
        r = ['place=%r' % self.place]
        if self.acode:
            r.append('acode=%r' % self.acode)
        r.append('local=%r' % self.local)
        return '%s(%s)' % (self.__class__.__name__, ', '.join(r))

    def absolute(self):
        return '+' + ' '.join(filter(bool,
            [self.place.country.ccode, self.acode, self.local]))

    def relative(self, place):
        r'''
            >>> au = Country('AU', 'en', '61', multilang('Australia'), aprefix='0', sprefix='1')
            >>> sa = Area(au, '8', multilang('SA'), \
            ...           multilang(en='South Australia', es='Australia Meridional'))
            >>> es = Country('ES', 'es', '34', multilang('Spain'))
            >>> w = World(countries=[au, es])

            >>> t = Telephone(place=Place(au), acode='8', local='223-4567')
            >>> t.relative(Place(sa))
            '223-4567'
            >>> t.relative(Place(au))
            '08 223-4567'
            >>> t.relative(Place(es))
            '+61 8 223-4567'

            >>> t = Telephone(place=Place(au), local='411-123-456')
            >>> t.relative(Place(sa))
            '0411-123-456'
            >>> t.relative(Place(au))
            '0411-123-456'
            >>> t.relative(Place(es))
            '+61 411-123-456'

            >>> t = Telephone(place=Place(au), local='131-151')
            >>> t.relative(Place(sa))
            '131-151'
            >>> t.relative(Place(au))
            '131-151'
            >>> t.relative(Place(es))
            '+61 131-151'
        '''
        if place is not None:
            assert isinstance(place, Place)
        if not place or self.place.country is not place.country:
            return self.absolute()
        r = [str(self.local)]
        assert place.country
        if place.area:
            assert place.area.country is place.country
        if self.acode:
            assert place.country.aprefix
            if not place.area or self.acode != place.area.acode:
                r.insert(0, ' ')
                r.insert(0, str(self.acode))
                r.insert(0, str(self.place.country.aprefix))
        elif (place.country.aprefix and
              not (place.country.sprefix and
                   self.local.startswith(place.country.sprefix))):
            r.insert(0, place.country.aprefix)
        return ''.join(filter(bool, r))

    def __hash__(self):
        return hash(tuple((int(s.replace('-', ''))
                           for s in [self.ccode, self.acode, self.local]
                           if s)))

    def __eq__(self, other):
        r'''
            >>> us = Country('US', 'en', '1', multilang('U.S.A.'), aprefix='1')
            >>> t1 = Telephone(place=Place(us), local='234-5678')
            >>> t2 = Telephone(place=Place(us), local='234-5678')
            >>> t1 == t2
            True
            >>> t3 = Telephone(place=Place(us), acode='9', local='234-5678')
            >>> t1 == t3
            False
        '''
        if not isinstance(other, Telephone):
            return NotImplemented
        return self.place.country is other.place.country and \
               self.acode == other.acode and \
               self.local == other.local

    def __ne__(self, other):
        if not isinstance(other, Telephone):
            return NotImplemented
        return not self.__eq__(other)

    _re_parse = re.compile(r'(?:\+(?P<ccode>\d+) )?(?:(?P<acode>\d+) )?(?P<local>\d+(?:-\d+)*)')

    @classmethod
    def parse(class_, text, world, place=None, default_place=None):
        r'''
            >>> au = Country('AU', 'en', '61', multilang('Australia'), \
            ...              aprefix='0', sprefix='1')
            >>> sa = Area(au, '8', multilang('SA'), \
            ...           multilang(en='South Australia'))
            >>> nsw = Area(au, '2', multilang('NSW'), \
            ...           multilang(en='New South Wales'))
            >>> us = Country('US', 'en', '1', multilang('U.S.A.'), aprefix='1')
            >>> es = Country('ES', 'es', '34', multilang('Spain'))
            >>> w = World(countries=[au, us, es])

            >>> Telephone.parse('+1 234 567-8901   wah', world=w)
            (Telephone(place=Place(Country('US', 'en_US', '1', multilang('U.S.A.'), aprefix='1')), acode='234', local='567-8901'), u'wah')

            >>> Telephone.parse('+1 234 567-8901', world=w)
            (Telephone(place=Place(Country('US', 'en_US', '1', multilang('U.S.A.'), aprefix='1')), acode='234', local='567-8901'), None)

            >>> Telephone.parse('+1 234 567-8901', world=w, place=Place(us))
            (Telephone(place=Place(Country('US', 'en_US', '1', multilang('U.S.A.'), aprefix='1')), acode='234', local='567-8901'), None)

            >>> Telephone.parse('+61 2 567-8901', world=w, place=Place(us))
            Traceback (most recent call last):
            InputError: telephone number must be in U.S.A.

            >>> Telephone.parse('+1 234 567-8901', world=w, default_place=Place(us))
            (Telephone(place=Place(Country('US', 'en_US', '1', multilang('U.S.A.'), aprefix='1')), acode='234', local='567-8901'), None)

            >>> Telephone.parse('234 567-8901 wah', world=w)
            Traceback (most recent call last):
            InputError: missing country code

            >>> Telephone.parse('234 567-8901 wah', world=w, place=Place(us))
            Traceback (most recent call last):
            InputError: missing area prefix

            >>> Telephone.parse('1234 567-8901 wah', world=w, place=Place(us))
            (Telephone(place=Place(Country('US', 'en_US', '1', multilang('U.S.A.'), aprefix='1')), acode='234', local='567-8901'), u'wah')

            >>> Telephone.parse('567-8901 wah', world=w, place=Place(us))
            Traceback (most recent call last):
            InputError: missing area code

            >>> Telephone.parse('1567-8901 wah', world=w, place=Place(us))
            (Telephone(place=Place(Country('US', 'en_US', '1', multilang('U.S.A.'), aprefix='1')), local='567-8901'), u'wah')

            >>> Telephone.parse('1567-8901 wah', world=w, default_place=Place(us))
            (Telephone(place=Place(Country('US', 'en_US', '1', multilang('U.S.A.'), aprefix='1')), local='567-8901'), u'wah')

            >>> Telephone.parse('2 345-6789 wah', world=w, place=Place(au))
            Traceback (most recent call last):
            InputError: missing area prefix

            >>> Telephone.parse('0 345-6789 wah', world=w, place=Place(au))
            Traceback (most recent call last):
            InputError: missing area code

            >>> Telephone.parse('02 345-6789 wah', world=w, place=Place(au))
            (Telephone(place=Place(Country('AU', 'en_AU', '61', multilang('Australia'), aprefix='0', sprefix='1')), acode='2', local='345-6789'), u'wah')

            >>> Telephone.parse('02 345-6789 wah', world=w, place=Place(nsw))
            (Telephone(place=Place(Area(Country('AU', 'en_AU', '61', multilang('Australia'), aprefix='0', sprefix='1'), '2', multilang('NSW'), fullname=multilang(en='New South Wales'))), acode='2', local='345-6789'), u'wah')

            >>> Telephone.parse('02 345-6789 wah', world=w, place=Place(sa))
            Traceback (most recent call last):
            InputError: telephone number must be in SA

            >>> Telephone.parse('wah', world=w)
            Traceback (most recent call last):
            InputError: malformed telephone number

        '''
        m = class_._re_parse.match(text)
        if m is None or not m.group('local'):
            raise InputError('malformed telephone number', char=text)
        local = m.group('local')
        comment = unicode(text[m.end():]).strip() or None
        ccode = m.group('ccode')
        # The telephone number needs a country code, either explicitly or
        # supplied by 'place'.
        if not ccode:
            country = (place and place.country) or \
                      (default_place and default_place.country)
            if not country:
                raise InputError('missing country code', char=text)
        else:
            try:
                country = world.lookup_ccode(ccode)
            except LookupError:
                raise InputError('unknown country code %s' % ccode, char=ccode)
        # By now we know the country.
        assert country
        acode = m.group('acode')
        area = None
        if country.aprefix:
            aprefix = country.aprefix
            sprefix = country.sprefix
            # The telephone number must either have an area code or start with
            # the area prefix or the service prefix, if there is one.
            # Otherwise the default area code is prepended.  If there is not
            # default area code, then barf.
            if acode:
                # Area codes cannot start with the service prefix.
                if sprefix and acode.startswith(sprefix):
                    raise InputError('area code cannot start with %s' %
                                     sprefix, char=acode)
                # Since we have an area code, we know that 'local' truly is a
                # local number.  Local numbers must not start with the service
                # prefix.
                if sprefix and local.startswith(sprefix):
                    raise InputError('local number cannot start with %s' %
                                     sprefix, char=acode)
                if ccode:
                    # If a country code was given, then the area code must not
                    # start with the area prefix.
                    if acode.startswith(aprefix):
                        raise InputError('area prefix not permitted',
                                         char=acode)
                else:
                    # If a country code was not given, then the area code must
                    # start with the area prefix, which we strip off.
                    if not acode.startswith(aprefix):
                        raise InputError('missing area prefix', char=text)
                    acode = acode[len(aprefix):]
                    if not acode:
                        raise InputError('missing area code', char=text)
            elif ccode:
                # If the country code was given, the area code is optional,
                # because the local part may contain the area code (eg, in the
                # case of mobile phone numbers).
                pass
            else:
                # If neither country code nor area code were given, but the
                # local number starts with the area prefix, then we strip it
                # off and don't require an area code, because it is in the
                # local number.  If it starts with the service prefix, then no
                # area code is needed.  Otherwise, we take the default area, if
                # specified.
                acode = None
                if local.startswith(aprefix):
                    local = local[len(aprefix):]
                elif sprefix and local.startswith(sprefix):
                    pass
                elif place and place.area:
                    area = place.area
                    acode = area.acode
                elif default_place and default_place.area:
                    area = default_place.area
                    acode = area.acode
                else:
                    raise InputError('missing area code', char=local)
        elif acode:
            # No area codes allowed.
            raise InputError('%s does not have area codes' % country,
                             char=acode)
        # Convert the area code to str.
        if acode:
            acode = str(acode)
        # If a mandatory place was given, then ensure that the number is
        # located there.
        if place is not None:
            if country is not place.country:
                assert country != place.country
                raise InputError('telephone number must be in %s' %
                                 place.country, char=text)
            if place.area and acode != place.area.acode:
                raise InputError('telephone number must be in %s' % place.area,
                                 char=text)
        else:
            place = Place(area or country)
        return class_(place=place, acode=acode, local=str(local)), comment

class Has_phone(Link):

    def __init__(self, who, tel, comment=None, timestamp=None):
        from six.person import Person
        from six.family import Family
        from six.org import Organisation, Works_at
        from six.address import Residence
        from six.links import Resides_at
        assert isinstance(who, (Person, Family, Organisation, Residence,
                                Resides_at, Works_at))
        assert isinstance(tel, Telephone)
        assert comment is None or isinstance(comment, basestring)
        super(Has_phone, self).__init__(who, tel, timestamp=timestamp)
        self.who = who
        self.tel = tel
        self.comment = comment
        self.place = tel.place

class At_home(object):
    r'''A Has_phone mixin to mark a phone number as a home phone number if that
    can't be deduced from the context.
    '''
    pass

class At_work(object):
    r'''A Has_phone mixin to mark a phone number as a workplace phone number
    if that can't be deduced from the context.
    '''
    pass

class Has_mobile(Has_phone):

    def only_place(self):
        r'''Mobile phones can contribute country but not area information, so
        it's best to ignore them when parsing place-context-sensitive data.
        '''
        return None

class Has_mobile_home(Has_mobile, At_home): pass
class Has_mobile_work(Has_mobile, At_work): pass

class Has_fixed(Has_phone): pass
class Has_fixed_home(Has_fixed, At_home): pass
class Has_fixed_work(Has_fixed, At_work): pass

class Has_fax(Has_phone): pass
class Has_fax_home(Has_fax, At_home): pass
class Has_fax_work(Has_fax, At_work): pass
