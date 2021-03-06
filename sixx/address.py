# vim: sw=4 sts=4 et fileencoding=utf8 nomod

r'''Data model - addresses.
'''

from sixx.multilang import multilang
from sixx.input import InputError
from sixx.node import *
from sixx.world import *

__all__ = ['Residence', 'PostalAddress', 'Location']

class Address(Node):

    r'''
        >>> au = Country('AU', 'en', '61', multilang('Australia'))
        >>> isinstance(au, Node)
        True
        >>> a = Address(['50 Clifton St', 'Maylands SA 5069'], Place(au))
        >>> str(a)
        '50 Clifton St; Maylands SA 5069; AUSTRALIA'
    '''

    def __init__(self, lines, place):
        assert isinstance(place, Place)
        super(Address, self).__init__()
        self.lines = tuple(lines)
        self.place = place
        from sixx.links import Is_in
        Is_in(self, place)

    def as_string(self, with_country=True):
        lines = list(self.lines)
        if with_country:
            lines.append(str(self.place.country).upper())
        return '; '.join(lines)

    def __str__(self):
        return self.as_string(with_country=True)

    def __repr__(self):
        return '%s(lines=%r, place=%r)' % (self.__class__.__name__,
                self.lines, self.place)

    def absolute(self):
        return self.as_string(with_country=True)

    def relative(self, place):
        r'''
            >>> au = Country('AU', 'en', '61', multilang('Australia'), aprefix='0', sprefix='1')
            >>> sa = Area(au, '8', multilang('SA'), \
            ...           multilang(en='South Australia', es='Australia Meridional'))
            >>> es = Country('ES', 'es', '34', multilang('Spain'))
            >>> w = World(countries=[au, es])

            >>> a = Address(['50 Clifton St', 'Maylands SA 5069'], Place(sa))
            >>> str(a)
            '50 Clifton St; Maylands SA 5069; AUSTRALIA'
            >>> a.relative(Place(sa))
            '50 Clifton St; Maylands SA 5069'
            >>> a.relative(Place(au))
            '50 Clifton St; Maylands SA 5069'
            >>> a.relative(Place(es))
            '50 Clifton St; Maylands SA 5069; AUSTRALIA'

        '''
        country = None
        if place is not None:
            assert isinstance(place, Place)
            country = place.country
        if place and self.place.country is place.country:
            return self.as_string(with_country=False)
        return self.absolute()

    def __hash__(self):
        return hash(self.place) ^ hash(self.lines)

    def __eq__(self, other):
        if not isinstance(other, Address):
            return NotImplemented
        return self.place == other.place and self.lines == other.lines

    def __ne__(self, other):
        if not isinstance(other, Address):
            return NotImplemented
        return not self.__eq__(other)

    def matches(self, text):
        return self.lines[0] == text

    @classmethod
    def parse(class_, text, world, place=None, default_place=None):
        r'''Parse a piece of text into an Address object.  If there is a
        semicolon anywhere in the text, then semicolon is used as the line
        delimiter, otherwise comma is used.  This supports addresses that
        contain commas.

        If the last line of the address is uppercase, then it is treated as the
        country name.  If a place argument was given, then the named country
        must be the same as place.country, otherwise InputError is raised.  If
        the last line of the address is not a country name, then the country is
        taken from place.country or default_place.country in that order.  If
        neither of these was given, then an InputError is raised.

        The line of the address preceding the country name is used to look up
        the area name within the country.  The last all-alphabetic word in that
        line is taken as the area name.  If a place argument was given with a
        non-None place.area attribute, then the named area must be ths same as
        place.area, otherwise InputError is raised.

            >>> w = World()
            >>> es = Country('ES', 'es', '34', multilang(en='Spain', es=u'España'))
            >>> w.add(es)
            >>> au = Country('AU', 'en', '61', multilang('Australia'))
            >>> sa = Area(au, '8', multilang('SA'), multilang('South Australia'))
            >>> w.add(au)
            >>> a, com = Address.parse('50 Clifton St, Maylands SA 5069, AUSTRALIA', w)
            >>> a
            Address(lines=('50 Clifton St', 'Maylands SA 5069'), place=Place(Area(Country('AU', 'en_AU', '61', multilang('Australia')), '8', multilang('SA'), fullname=multilang('South Australia'))))
            >>> com is None
            True
            >>> a.only_place().country is au
            True
            >>> a.only_place().area is sa
            True

            >>> a, com = Address.parse('50 Clifton St, Maylands SA 5069, AUSTRALIA', w, place=Place(au))

            >>> a, com = Address.parse('50 Clifton St, Maylands SA 5069, AUSTRALIA', w, place=Place(sa))

            >>> b, com = Address.parse('50 Clifton St, Maylands SA 5069', w, place=Place(au))
            >>> b == a
            True

            >>> b, com = Address.parse('50 Clifton St, Maylands SA 5069', w, place=Place(sa))
            >>> b == a
            True

            >>> a, com = Address.parse(u'C/ Bienandanza, 6; 45216 Carranque Toledo; ESPAÑA', w, place=Place(au))
            Traceback (most recent call last):
            sixx.input.InputError: address must be in Australia

            >>> a, com = Address.parse(u'C/ Bienandanza, 6; 45216 Carranque Toledo; ESPAÑA', w, default_place=Place(au))
            >>> a.only_place().country is es
            True
            >>> a.only_place().area is None
            True

            >>> a, com = Address.parse(u'C/ Bienandanza, 6; 45216 Carranque Toledo; ESPAÑA', w, place=Place(sa))
            Traceback (most recent call last):
            sixx.input.InputError: address must be in Australia

            >>> a, com = Address.parse('1A Campbell St, Balmain NSW 2041', w, place=Place(sa))
            Traceback (most recent call last):
            sixx.input.InputError: address must be in SA

            >>> a, com = Address.parse(u'C/ Bienandanza, 6; 45216 Carranque Toledo; ESPAÑA', w, default_place=Place(sa))
            >>> a.only_place().country is es
            True
            >>> a.only_place().area is None
            True

            >>> a, com = Address.parse(u'C/ Bienandanza, 6; 45216 SA; ESPAÑA', w, default_place=Place(sa))
            >>> a.only_place().country is es
            True
            >>> a.only_place().area is None
            True

        The string representation of an Address should, of course, parse to an
        equivalent Address object, given the same world:

            >>> Address.parse(str(a), w)[0] == a
            True

        @param text: the text to parse
        @param world: A World object, used to look up country and area names
        @param place: either None or an object with 'country' and 'area'
            attributes
        @param default_place: either None or an object with a 'country'
            attribute
        '''
        if ';' in text:
            lines = list(filter(len, (s.strip() for s in text.split(';'))))
        else:
            lines = list(filter(len, (s.strip() for s in text.split(','))))
        assert len(lines) != 0
        country = world.lookup_country(lines[-1], None)
        if country is not None:
            lines = lines[:-1]
        elif lines[-1].isupper():
            raise InputError('unknown country "%s"' % lines[-1], char=lines[-1])
        elif place is not None:
            country = place.country
        elif default_place is not None:
            country = default_place.country
        else:
            raise InputError('missing country', char=text)
        assert isinstance(country, Country)
        if not lines:
            raise InputError('address too short', char=text)
        area = None
        try:
            area = country.lookup_area(
                    [word for word in lines[-1].split() if word.isalpha()][-1],
                    None)
        except IndexError:
            pass
        if place is not None:
            if country is not place.country:
                assert country != place.country
                raise InputError('address must be in %s' % place.country,
                                 char=lines[-1])
            if place.area and area is not place.area:
                assert area != place.area
                raise InputError('address must be in %s' % place.area,
                                 char=lines[-1])
        return class_(lines, place=Place(area or country)), None

class Residence(Address):
    pass

class PostalAddress(Address):
    pass

class Location(Address):

    r'''
        >>> au = Country('AU', 'en', '61', multilang('Australia'))
        >>> isinstance(au, Node)
        True
        >>> a = Address(['50 Clifton St', 'Maylands SA 5069'], Place(au))
        >>> a1 = Location(['The Stately Manor'], a)
        >>> str(a1)
        'The Stately Manor; 50 Clifton St; Maylands SA 5069; AUSTRALIA'
    '''

    def __init__(self, qualifying_lines, orig_address):
        assert isinstance(orig_address, Address)
        super(Location, self).__init__(lines=tuple(qualifying_lines) + orig_address.lines, place= orig_address.place)
