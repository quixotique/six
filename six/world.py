# vim: sw=4 sts=4 et fileencoding=latin1 nomod

r'''Country and area.
'''

import re
from six.multilang import multilang
from six.input import InputError
from six.node import *

__all__ = ['World', 'Country', 'Area', 'Place']

class World(Node):

    r'''The world is a single node that has links to all the known country
    nodes.

        >>> w = World()
        >>> w
        World()
        >>> au = Country('AU', 'en', '61', multilang('Australia'))
        >>> au in w
        False
        >>> w.add(au)
        >>> w
        World(countries=[Country('AU', 'en_AU', '61', multilang('Australia'))])
        >>> au in w
        True
        >>> Country('AU', 'en', '61', multilang('Australia')) in w
        False
    '''

    def __init__(self, countries=None):
        super(World, self).__init__()
        self._countries = dict(((c.iso3166_a2, c) for c in countries or []))
        self._ccodes = dict(((c.ccode, c) for c in countries or []))
        self._lookup_country_cache = {}
        self._lookup_area_cache = {}

    def __repr__(self):
        r = []
        if self._countries:
            r += ['countries=%r' % sorted(self._countries.values())]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(r))

    def add(self, country):
        Has_country(self, country)

    def add_link(self, link):
        super(World, self).add_link(link)
        if isinstance(link, Has_country):
            if link.country.iso3166_a2 in self._countries:
                raise ValueError, 'duplicate country %s' % link.country.iso3166_a2
            if link.country.ccode in self._ccodes:
                raise ValueError, 'duplicate country code %s' % link.country.ccode
            self._countries[link.country.iso3166_a2] = link.country
            self._ccodes[link.country.ccode] = link.country

    def __contains__(self, country):
        return self._countries.get(country.iso3166_a2) is country

    def lookup_country(self, name, *args):
        if len(args) > 1:
            raise TypeError(
                    'lookup_country() takes at most 3 arguments (%s given)' %
                    (2 + len(args)))
        try:
            return self._lookup_country_cache[name]
        except KeyError:
            pass
        matched = []
        for country in self._countries.itervalues():
            if country.matches(name):
                matched.append(country)
        if len(matched) == 0:
            if not args:
                raise LookupError('no country matching %s' % name)
            return args[0]
        if len(matched) > 1:
            raise LookupError('ambiguous country name %r matches %s' % (
                    name, ' and '.join((str(c.name) for c in matches))))
        found = matched[0]
        self._lookup_country_cache[name] = found
        return found

    def lookup_ccode(self, ccode):
        return self._ccodes[ccode]

    def lookup_area(self, name, *args):
        if len(args) > 1:
            raise TypeError(
                    'lookup_area() takes at most 3 arguments (%s given)' %
                    (2 + len(args)))
        try:
            return self._lookup_area_cache[name]
        except KeyError:
            pass
        matched = []
        for country in self._countries.itervalues():
            for area in country.iterareas():
                if area.matches(name):
                    matched.append(area)
        if len(matched) == 0:
            if not args:
                raise LookupError('no area matching %s' % name)
            return args[0]
        if len(matched) > 1:
            raise LookupError('ambiguous area name %r matches %s' % (
                    name, ' and '.join((str(a.name) for a in matches))))
        found = matched[0]
        self._lookup_area_cache[name] = found
        return found

    def lookup_place(self, name):
        country = self.lookup_country(name, None)
        if country:
            return Place(country)
        area = self.lookup_area(name, None)
        if area:
            return Place(area)
        raise InputError('no country or area matching "%s"' % name,
                         char=name)

    def parse_country(self, text):
        r'''Parse a country definition, and add the country to the world.
        Raise InputError if the country cannot be added because its ISO 3166
        code is already added to the world.
        '''
        assert len(text) != 0
        country = Country.parse(text)
        try:
            self.add(country)
        except ValueError, e:
            raise InputError(e, line=text)
        return country

    def parse_area(self, text, country):
        r'''Parse an area definition for an area within the most recently
        parsed country definition.  Raise InputError if no country definition
        has been parsed yet.
        '''
        assert len(text) != 0
        return Area.parse(text, country)

    def parse_place(self, text):
        r'''Parse a place name into a Place object.
        '''
        assert len(text) != 0
        try:
            return self.lookup_place(text)
        except LookupError, e:
            raise InputError(e, char=text)

class Country(Node):

    r'''
        >>> c = Country('AU', 'en', '61', multilang(en='Australia'), \
        ...             aprefix='0', sprefix='1')
        >>> c
        Country('AU', 'en_AU', '61', multilang(en='Australia'), aprefix='0', sprefix='1')
        >>> c
        Country('AU', 'en_AU', '61', multilang(en='Australia'), aprefix='0', sprefix='1')
        >>> unicode(c)
        u'Australia'
        >>> c.matches('au')
        True
        >>> c.matches('aust')
        True
        >>> c.matches('oz')
        False
    '''

    def __init__(self, iso3166_a2, language, ccode, name, fullname=None,
                 aprefix=None, sprefix=None, areas=None):
        super(Country, self).__init__()
        assert isinstance(iso3166_a2, str)
        assert len(iso3166_a2) == 2
        assert iso3166_a2.isalpha()
        assert iso3166_a2.isupper()
        self.iso3166_a2 = iso3166_a2
        assert isinstance(language, str)
        assert len(language) in (2, 5)
        assert language[:2].isalpha()
        assert language[:2].islower()
        if len(language) == 2:
            language += '_' + iso3166_a2
        else:
            assert language[2] == '_'
            assert language[3:].isalpha()
            assert language[3:].isupper()
        self.language = language
        assert isinstance(ccode, str)
        assert ccode.isdigit()
        self.ccode = ccode
        if aprefix is not None:
            assert isinstance(aprefix, str) and aprefix.isdigit()
        self.aprefix = aprefix
        if sprefix is not None:
            assert aprefix is not None
            assert isinstance(sprefix, str) and sprefix.isdigit()
            assert sprefix != aprefix
        self.sprefix = sprefix
        assert isinstance(name, multilang)
        self.name = name
        self.fullname = fullname or name
        assert isinstance(self.fullname, multilang)
        self._areas = {}
        if areas is not None:
            for area in areas:
                self.add(area)

    def __unicode__(self):
        return unicode(self.name)

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        if getattr(self.__class__, self.iso3166_a2, None) is self:
            return '%s.%s' % (self.__class__.__name__, self.iso3166_a2)
        r = [repr(self.iso3166_a2),
             repr(self.language),
             repr(self.ccode),
             repr(self.name)]
        if self.aprefix is not None:
            r += ['aprefix=%r' % self.aprefix]
        if self.sprefix is not None:
            r += ['sprefix=%r' % self.sprefix]
        if self.fullname != self.name:
            r += ['fullname=%r' % self.fullname]
        areas = list(self.iterareas())
        #if areas:
        #    r += ['areas=%r' % areas]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(r))

    def __cmp__(self, other):
        return cmp(self.iso3166_a2, other.iso3166_a2)

    def matches(self, name):
        return name.upper() == self.iso3166_a2 or \
               self.name.matches(name) or self.fullname.matches(name)

    def add(self, area):
        assert area.country is self
        Has_area(self, area)

    def add_link(self, link):
        super(Country, self).add_link(link)
        if isinstance(link, Has_area):
            name = link.area.name.local(self.language)
            if name in self._areas:
                raise ValueError('duplicate area "%s" in %s' % (name, self.name))
            self._areas[name] = link.area

    def __contains__(self, area):
        return area in self._areas

    def iterareas(self):
        return self._areas.itervalues()

    @classmethod
    def parse(class_, text):
        r'''Parse a country definition text.

            >>> Country.parse(u'AU lang=en cc=61 ap=0 sp=1 "Australia"')
            Country('AU', 'en_AU', '61', multilang(u'Australia'), aprefix='0', sprefix='1')

        '''
        otext = text
        iso3166_a2, text = text.split(None, 1)
        iso3166_a2 = str(iso3166_a2)
        if not (len(iso3166_a2) == 2 and
                iso3166_a2.isalpha() and
                iso3166_a2.isupper()):
            raise InputError('invalid ISO3166 country code %r' % iso3166_a2,
                             char=iso3166_a2)
        ccode = None
        aprefix = None
        sprefix = None
        language = None
        name = None
        fullname = None
        while len(text):
            m = re.match(r'(cc|ap|sp)=(\d+)\s*', text)
            if m is not None:
                text = text[m.end():]
                if m.group(1) == 'cc':
                    ccode = str(m.group(2))
                elif m.group(1) == 'ap':
                    aprefix = str(m.group(2))
                elif m.group(1) == 'sp':
                    sprefix = str(m.group(2))
                continue
            m = re.match(r'(lang)=([a-z]{2}(?:_[A-Z]{2})?)\s*', text)
            if m is not None:
                text = text[m.end():]
                if m.group(1) == 'lang':
                    language = str(m.group(2))
                continue
            if name is None:
                text, name = multilang.parse(text)
                if name is None:
                    raise InputError('missing country name', char=text)
                continue
            if text.startswith('/'):
                if fullname is not None:
                    raise InputError('too many "/" separators', char=text)
                text, fullname = multilang.parse(text[1:].lstrip())
                if fullname is None:
                    raise InputError('missing country full name', char=text)
                continue
            raise InputError('malformed country description', char=text)
        if ccode is None:
            raise InputError('missing cc=', line=otext)
        if aprefix:
            if sprefix == aprefix:
                raise InputError('sp= and ap= must be different', line=otext)
        else:
            if sprefix is not None:
                raise InputError('sp= without ap=', line=otext)
        if language is None:
            raise InputError('missing lang=', line=otext)
        if name is None:
            raise InputError('missing name', line=otext)
        return class_(iso3166_a2, language, ccode, name, fullname=fullname,
                      aprefix=aprefix, sprefix=sprefix)

class Area(Node):

    r'''
        >>> au = Country('AU', 'en', '61', multilang(en='Australia'))
        >>> sa = Area(au, '8', multilang('SA'), multilang(en='South Australia', es='Australia Meridional'))
        >>> sa
        Area(Country('AU', 'en_AU', '61', multilang(en='Australia')), '8', multilang('SA'), fullname=multilang(en='South Australia', es='Australia Meridional'))
        >>> str(sa)
        'SA'
        >>> sa.matches('au')
        True
        >>> sa.matches('aust')
        True
        >>> sa.matches('sa')
        True
        >>> sa.matches('south')
        True
    '''

    def __init__(self, country, acode, name, fullname=None):
        assert isinstance(country, Country)
        assert isinstance(acode, str) and acode.isdigit()
        assert isinstance(name, multilang)
        self.country = country
        self.acode = acode
        self.name = name
        self.fullname = fullname or name
        assert isinstance(self.fullname, multilang)
        super(Area, self).__init__()
        self.country.add(self)

    def __unicode__(self):
        return unicode(self.name)

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        r = [repr(self.country),
             repr(self.acode),
             repr(self.name)]
        if self.fullname != self.name:
            r += ['fullname=%r' % self.fullname]
        return '%s(%s)' % (self.__class__.__name__, ', '.join(r))

    def matches(self, name):
        return self.name.matches(name) or self.fullname.matches(name)

    @classmethod
    def parse(class_, text, country):
        r'''Parse an area definition text.
        '''
        otext = text
        acode = None
        name = None
        fullname = None
        while len(text):
            m = re.match(r'(ac)=(\d+)\s*', text)
            if m is not None:
                text = text[m.end():]
                if m.group(1) == 'ac':
                    acode = str(m.group(2))
                continue
            if name is None:
                text, name = multilang.parse(text)
                if name is None:
                    raise InputError('missing area name', char=text)
                continue
            if text.startswith('/'):
                if fullname is not None:
                    raise InputError('too many "/" separators', char=text)
                text, fullname = multilang.parse(text[1:].lstrip())
                if fullname is None:
                    raise InputError('missing area full name', char=text)
                continue
            raise InputError('malformed area description', char=text)
        if acode is None:
            raise InputError('missing ac=', line=otext)
        if name is None:
            raise InputError('missing name', line=otext)
        try:
            return class_(country, acode, name, fullname)
        except ValueError, e:
            raise InputError(e, line=otext)

class Has_country(Link):
    def __init__(self, world, country, timestamp=None):
        assert isinstance(world, World)
        assert isinstance(country, Country)
        self.world = world
        self.country = country
        super(Has_country, self).__init__(world, country, timestamp=timestamp)

class Has_area(Link):
    def __init__(self, country, area, timestamp=None):
        assert isinstance(country, Country)
        assert isinstance(area, Area)
        self.country = country
        self.area = area
        super(Has_area, self).__init__(country, area, timestamp=timestamp)

class Place(object):

    r'''Represents a place (country and optionally area).

        >>> au = Country('AU', 'en', '61', multilang(en='Australia'))
        >>> sa = Area(au, '8', multilang('SA'))

        >>> p = Place(au)
        >>> p
        Place(Country('AU', 'en_AU', '61', multilang(en='Australia')))
        >>> unicode(p)
        u'Australia'
        >>> p.country is au
        True
        >>> p.area is None
        True

        >>> p = Place(sa)
        >>> p
        Place(Area(Country('AU', 'en_AU', '61', multilang(en='Australia')), '8', multilang('SA')))
        >>> unicode(p)
        u'SA, Australia'
        >>> p.country is au
        True
        >>> p.area is sa
        True
    '''

    def __init__(self, where):
        if isinstance(where, Area):
            self.node = self.area = where
            self.country = where.country
            assert isinstance(self.country, Country)
        elif isinstance(where, Country):
            self.area = None
            self.node = self.country = where
        else:
            raise TypeError('Place() expects Country or Area argument')

    def __unicode__(self):
        if self.area:
            return u', '.join([unicode(self.area), unicode(self.country)])
        return unicode(self.country)

    def __str__(self):
        return str(unicode(self))

    def __repr__(self):
        if self.area is not None:
            assert self.area.country is self.country
            arg = self.area
        else:
            assert self.country is not None
            arg = self.country
        return '%s(%r)' % (self.__class__.__name__, arg)

    def __hash__(self):
        return hash(self.area) ^ hash(self.country)

    def __eq__(self, other):
        if not isinstance(other, Place):
            return NotImplemented
        return self.country == other.country and self.area == other.area

    def __ne__(self, other):
        if not isinstance(other, Place):
            return NotImplemented
        return not self.__eq__(other)
