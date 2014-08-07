# vim: sw=4 sts=4 et fileencoding=utf8 nomod

r'''Personal names.
'''

import operator
from sixx.input import InputError
from sixx.text import sortstr
from functools import reduce

__all__ = ['EnglishSpanishName', 'SingleName', 'DecoratedName']

def name_method(func, what=None):
    r'''A function decorator that raises ValueError with an informative message
    if the decorated function returns None or an empty string, or raises
    TypeError or ValueError itself.  The exception message is derived from the
    name of the decorated function.

        >>> @name_method
        ... def a_b_c(self):
        ...     return 1
        >>> a_b_c('xyz')
        1

        >>> @name_method
        ... def a_b_c(self):
        ...     return None
        >>> a_b_c('xyz')
        Traceback (most recent call last):
        ValueError: no a b c for xyz

        >>> @name_method
        ... def some_name(self):
        ...     return ''
        >>> some_name('xyz')
        Traceback (most recent call last):
        ValueError: no some name for xyz

        >>> @name_method
        ... def one_two(self):
        ...     raise ValueError()
        >>> one_two(12)
        Traceback (most recent call last):
        ValueError: no one two for 12

        >>> @name_method
        ... def a_b_c(self):
        ...     raise TypeError()
        >>> a_b_c(None)
        Traceback (most recent call last):
        ValueError: no a b c for None

        >>> @name_method
        ... def a_b_c(self):
        ...     raise LookupError()
        >>> a_b_c('xyz')
        Traceback (most recent call last):
        LookupError

    '''
    def newfunc(self):
        try:
            ret = func(self)
            if ret:
                return ret
        except (TypeError, ValueError):
            pass
        raise ValueError('no %s for %s' %
                         (what or func.__name__.replace('_', ' '),
                          str(self)))
    newfunc.__name__ = func.__name__
    newfunc.__doc__ = func.__doc__
    newfunc.__module__ = func.__module__
    return newfunc

def has(method):
    r'''Return true if the given method does not raise a ValueError.
    '''
    try:
        method()
    except ValueError:
        return False
    return True

class PersonName(object):

    r'''The PersonName abstract class provides methods that cover all the
    contexts in which a real person's name might be written.  All these
    methods are decorated with 'name_method' to ensure that they can never
    retur None or an empty string -- instead they will raise an exception.
    '''

    def __init__(self):
        self.__hash = None

    @name_method
    def complete_name(self):
        r'''All the known words of the person's name, with title and letters if
        known, preferring proper names over contractions or abbreviations or
        initials if possible.  Guaranteed to succeed.
        '''
        return None

    @name_method
    def formal_index_name(self):
        r'''The person's name as it should appear in an index for personal use,
        such as an address book.  It contains as many words of the full name as
        are known except those, like the English middle name, which are usually
        kept private.  It does not contain contractions at all, but may contain
        initials where a whole words are unknown.  Guaranteed to succeed.
        '''
        return None

    @name_method
    def informal_index_name(self):
        r'''The person's informal name as it should appear in an index for
        personal use, such as an address book.  This only succeeds if any
        contracted names (ie, short forms or nicknames) are known.  It does not
        contain initials.
        @raise ValueError: if no contracted names are known
        '''
        return None

    @name_method
    def legal_name(self):
        r'''All the uncontracted words of the person's name, omitting title,
        letters and honorific, not using contractions or abbreviations or
        initials.
        @raise ValueError: if the legal name is not known (missing a word)
        '''
        return None

    @name_method
    def full_name(self):
        r'''The name of the person as it us usually written in full, without
        common contractions of given names.  In English speaking countries,
        middle names are usually omitted from full names, even in formal
        contexts (such middle names are only given in bureaucratic contexts,
        like taxation and other paperwork).  In Spanish speaking countries, all
        given names and both family names are usually used in the full name, so
        it is equivalent to the legal name.  The full name can be used as a
        sort key when sorting people by first name, especially if it differs
        from the casual name.
        @raise ValueError: if the full name cannot be formed
        '''
        return None

    @name_method
    def initials(self):
        r'''The full initials of the person, each followed by a single period,
        with no intervening spaces.  These are generally the first letters of
        all names except family names.  In English speaking countries, these
        are the first and middle names.  Some names with apostrophes, like
        "O'Grady" are represented as "O'G." instead of just "O.".
        @raise ValueError: if no initials are known
        '''
        return None

    @name_method
    def casual_name(self):
        r'''The name of the person in a casual context.  This is their full
        name, omitting any words that are normally omitted, and using any
        common contractions of given names.  In English speaking countries,
        this is usually equivalent to the full name, unless the person uses a
        very common contraction, for example "Tom" instead of "Thomas" or
        "John" instead of "Jonathon".  In Spanish speaking countries, the
        second apellido is usually omitted and common contractions are use in
        given names, such as "Maite" for "María Teresa" and "Mª" for "María".
        The casual name is used as a sort key when sorting people by first name
        in an address book for personal use.
        @raise ValueError: if the casual name cannot be formed
        '''
        return None

    @name_method
    def familiar_name(self):
        r'''The name of the person in an informal context.  This friends,
        family, or co-workers in daily use, such as the spoken greeting,
        "Hello, <Informal_name>".  It is also used as the salutation in
        informal correspondence.  If a contracted (short) form of the name,
        such as a nickname, is known, then this is used.  Otherwise it is
        usually the first name of the person.
        @raise ValueError: if the familiar name cannot be formed
        '''
        return None

    @name_method
    def title_name(self):
        r'''The name of the person that may have a title prepended.  This is
        normally the person's family name.
        @raise ValueError: if the title name is not known
        '''
        return None

    @name_method
    def social_name(self):
        r'''The name of the person in a social context, if possible.  This is
        the title followed by the title name ("Ms Thatcher"), or the optionally
        titled single name ("Sting", "Crit") if the family name is not known.
        The impersonal name is what would normally be used in the context of
        news reporting about the person, and also in the salutation of an
        informal letter to someone with whom one is not on first-name terms.
        @raise ValueError: if only the given name is known
        '''
        return None

    @name_method
    def formal_name(self):
        r'''The formal name of the person, as it should appear in the postal
        address or an official announcement.  This is usually
        "[<Honorific_or_title>] <Full_name>[, <Letters>]".  If the person has
        an honorific mode of address (like members of parliament, for example),
        the honorific is used instead of the title.
        @raise ValueError: missing title or honorific, or missing full name
        '''
        return None

    @name_method
    def formal_salutation_name(self):
        r'''The person's name as it should appear in the salutation of a formal
        letter.  If there is a special salutation known, then it is used.  This
        provides for cases where the person must be addressed by their position
        instead of name, eg, "Dear Prime Minister".  Otherwise, the social name
        is used, eg, "Dear Mr Smith".
        @raise ValueError: if the social name cannot be formed and there is
            no separate salutation known
        '''
        return None

    @name_method
    def collation_name(self):
        r'''The person's name as it whould appear in a collated list, such as
        the white pages telephone book.  This is typically "Lastnames,
        Firstnames or Initials" for western names.
        @raise ValueError: if the collation name cannot be formed
        '''
        return None

    def matches(self, text):
        r'''A name matches a given text if all of the text occurs as elements
        of the name, in order.
        '''
        parts = list(self._elements())
        while text and parts:
            part = str(parts.pop(0))
            if (text.startswith(part) and
                (len(text) == len(part) or text[len(part)].isspace())):
                text = text[len(part):].lstrip()
        return not text

    def __hash__(self):
        r'''The hash depends on all the elements of the name.
        '''
        if self.__hash is None:
            self.__hash = reduce(operator.xor, list(map(hash, self._elements())))
        return self.__hash

    def __eq__(self, other):
        r'''Two names are equal iff all their elements are equal.  This means
        that different representations of one person's name (eg, informal "John
        Smith" vs formal "Dr John M. Smith") may compare as unequal.
        '''
        if not isinstance(other, PersonName):
            return NotImplemented
        return list(self._elements()) == list(other._elements())

    def __ne__(self, other):
        if not isinstance(other, PersonName):
            return NotImplemented
        return not self.__eq__(other)

    def __repr__(self):
        r'''The repr() string of a PersonName will re-create an equivalent
        PersonName object if eval()'ed.
        '''
        return '%s(%s)' % (self.__class__.__name__,
                ', '.join(('%s=%r' % (k, v)
                           for k, v in self._initargs().items() if v)))

class EnglishSpanishName(PersonName):

    r'''A conventional English or Spanish name.  The following table shows how
    the different elements of the name are used in the various forms of the
    name.

                                  Given   Middle  Family  Family2
        Complete name          +  [ysi]   [yi]    [y]     [y]
        Formal index name      +  [yi]     -      [y]     [y]
        Informal index name        s       -      [y]      - 
        Legal name                  y     [y]      y      [y]
        Full name                   yi     -       y      [y]
        Familiar name              sy      -       -       -
        Initials                    I     [I]      -       -
        Casual name                sy      -       y       -
        Title name                 -       -       y      [y]
        Collation name            [yi]    [yi]     y      [y]
        Formal name            *
        Formal salutation name *
        Social name            *

     +  Always succeeds.
     *  Always fails because of lack of title or honorific (see DecoratedName).

     y    The usual name, fail if unknown.  Initials and short forms not used.
     s    Only the contracted (short) form of the name if known, otherwise
          fail.  Usual name and initials not used.
     sy   The contracted (short) form, if known, otherwise the usual one,
          otherwise fail.  Initials not used.
     yi   If the given/middle name is not known in these cases, then initials
          are used, if known, otherwise fails.
     I    The initials, if known, otherwise initials formed from the first
          letter(s) of all word(s), if known, otherwise fails.
    [y]   The usual name if known.
    [yi]  Same as yi, but no failure if neither is known.
    [I]   Same as I, but no failure if neither is known.
    [s]   Same as s, but no failure if neither is known.
    [ysi] The usual name if known, otherwise the short name if known, otherwise
          the initial if known.

    Note that for Anglic names, which only have a single family name, the full
    name and casual name forms are the same if there is no contracted given
    name (short name).

        >>> n = EnglishSpanishName(given="Zacharias", short="Zack", \
        ...                        middle="Quaid", middlei="Q.", \
        ...                        family="Smith")
        >>> n.complete_name()
        'Zacharias Quaid Smith'
        >>> n.formal_index_name()
        'Zacharias Smith'
        >>> n.informal_index_name()
        'Zack Smith'
        >>> n.legal_name()
        'Zacharias Quaid Smith'
        >>> n.full_name()
        'Zacharias Smith'
        >>> n.initials()
        'Z.Q.'
        >>> n.casual_name()
        'Zack Smith'
        >>> n.familiar_name()
        'Zack'
        >>> n.social_name()
        Traceback (most recent call last):
        ValueError: no social name for Zacharias [Zack] Quaid [Q.] Smith
        >>> n.formal_name()
        Traceback (most recent call last):
        ValueError: no formal name for Zacharias [Zack] Quaid [Q.] Smith
        >>> n.formal_salutation_name()
        Traceback (most recent call last):
        ValueError: no formal salutation name for Zacharias [Zack] Quaid [Q.] Smith
        >>> n.collation_name()
        'Smith, Zacharias Quaid'
        >>> str(n)
        'Zacharias [Zack] Quaid [Q.] Smith'

        >>> eval(repr(n)) == n
        True

        >>> n.matches('Zack')
        True
        >>> n.matches('Zack Smith')
        True
        >>> n.matches('Zack Q. Smith')
        True
        >>> n.matches('Zack Quaid Smith')
        True
        >>> n.matches('Zacharias Smith')
        True
        >>> n.matches('Zacharias Quaid Smith')
        True
        >>> n.matches('Zacharias Q. Smith')
        True
        >>> n.matches('Smith')
        True
        >>> n.matches('Zacharias Quaid')
        True
        >>> n.matches('Smith Zacharias')
        False
        >>> n.matches('Smith Quaid')
        False

        >>> n = EnglishSpanishName(giveni="Z.", middlei="Q.", family="Smith")
        >>> n.complete_name()
        'Z. Q. Smith'
        >>> n.formal_index_name()
        'Z. Smith'
        >>> n.informal_index_name()
        Traceback (most recent call last):
        ValueError: no informal index name for Z. Q. Smith
        >>> n.legal_name()
        Traceback (most recent call last):
        ValueError: no legal name for Z. Q. Smith
        >>> n.full_name()
        'Z. Smith'
        >>> n.initials()
        'Z.Q.'
        >>> n.casual_name()
        Traceback (most recent call last):
        ValueError: no casual name for Z. Q. Smith
        >>> n.familiar_name()
        Traceback (most recent call last):
        ValueError: no familiar name for Z. Q. Smith
        >>> n.social_name()
        Traceback (most recent call last):
        ValueError: no social name for Z. Q. Smith
        >>> n.formal_name()
        Traceback (most recent call last):
        ValueError: no formal name for Z. Q. Smith
        >>> n.formal_salutation_name()
        Traceback (most recent call last):
        ValueError: no formal salutation name for Z. Q. Smith
        >>> n.collation_name()
        'Smith, Z. Q.'
        >>> str(n)
        'Z. Q. Smith'

        >>> eval(repr(n)) == n
        True

        >>> n = EnglishSpanishName(given="Zacharias", short="Zack")
        >>> n.complete_name()
        'Zacharias'
        >>> n.formal_index_name()
        'Zacharias'
        >>> n.informal_index_name()
        'Zack'
        >>> n.legal_name()
        Traceback (most recent call last):
        ValueError: no legal name for Zacharias [Zack]
        >>> n.full_name()
        Traceback (most recent call last):
        ValueError: no full name for Zacharias [Zack]
        >>> n.initials()
        'Z.'
        >>> n.casual_name()
        Traceback (most recent call last):
        ValueError: no casual name for Zacharias [Zack]
        >>> n.familiar_name()
        'Zack'
        >>> n.social_name()
        Traceback (most recent call last):
        ValueError: no social name for Zacharias [Zack]
        >>> n.formal_name()
        Traceback (most recent call last):
        ValueError: no formal name for Zacharias [Zack]
        >>> n.formal_salutation_name()
        Traceback (most recent call last):
        ValueError: no formal salutation name for Zacharias [Zack]
        >>> n.collation_name()
        Traceback (most recent call last):
        ValueError: no collation name for Zacharias [Zack]
        >>> str(n)
        'Zacharias [Zack]'

    '''

    def __init__(self, given=None, short=None, giveni=None,
                       middle=None, middlei=None,
                       family=None, family2=None):
        r'''Construct a conventional English or Spanish name.  At least one of
        family name or given/short name must be supplied, or ValueError is
        raised.

        @param given: The person's given name (or names).  In England and
            Australia, given name is sometimes also called "christian name".
            In Spanish-speaking countries, the given name is called "nombre".
        @param short: The short form of the person's given name.  In England
            and Australia this is sometimes called the "nickname".  In Spain it
            is called the "apodo", and contractions are very common, such as
            Paco or Fran for Francisco, and Mayte for Maria Teresa -- the name
            María is very common for women, so is nearly always omitted or
            contracted in casual use.
        @param giveni: The initials of the person's given name.
        @param middle: The person's middle name (or names).  These are given
            names which follow the christian name and are usually omitted
            except on official (governmental) paperwork (eg, passport and
            tax-related) and in very formal contexts (such as weddings and
            funerals).  Spanish people seldom have such middle names.
        @param middlei: The initials of the person's middle name.
        @param family: The person's family name.  In England and Australia, the
            family name is also called "surname", and it is usually used in
            full in all contexts -- contractions or omissions are rare.  In
            Spanish-speaking countries, the family name is called "apellido"
            and consists of two names, formed from the person's paternal and
            maternal apellidos.  In this case, the family name is the first
            apellido.
        @param family2: The person's second family name.  This is not used in
            English speaking countries, but in Spanish speaking countries, it
            is the person's second apellido.  This is usually omitted in
            informal contexts, but always present in official or formal
            contexts.
        '''
        given = given and given.strip()
        short = short and short.strip()
        giveni = giveni and giveni.strip()
        middle = middle and middle.strip()
        middlei = middlei and middlei.strip()
        family = family and family.strip()
        family2 = family2 and family2.strip()
        assert given is None or isinstance(given, str) and given
        assert short is None or isinstance(short, str) and short
        assert giveni is None or isinstance(giveni, str) and giveni
        assert middle is None or isinstance(middle, str) and middle
        assert middlei is None or isinstance(middlei, str) and middlei
        assert family is None or isinstance(family, str) and family
        assert family2 is None or isinstance(family2, str) and family2
        if not (short or given or family):
            raise ValueError('%s() missing name' % self.__class__.__name__)
        if family2 and not family:
            raise ValueError('%s() family2 given without family' %
                             self.__class__.__name__)
        if middle and not given:
            raise ValueError('%s() middle name without given name' %
                             self.__class__.__name__)
        if short and given and short == given:
            raise ValueError('%s() short name same as given name' %
                             self.__class__.__name__)
        PersonName.__init__(self)
        self.given = given
        self.short = short
        self.giveni = giveni
        self.middle = middle
        self.middlei = middlei
        self.family = family
        self.family2 = family2

    def _elements(self):
        yield self.giveni
        yield self.short
        yield self.given
        yield self.middlei
        yield self.middle
        yield self.family
        yield self.family2

    def sortkey(self):
        return tuple(filter(bool, [self.given or self.short or self.giveni,
                                   self.middle or self.middlei,
                                   self.family,
                                   self.family2]))

    def _initargs(self):
        return {'given': self.given,
                'short': self.short,
                'giveni': self.giveni,
                'middle': self.middle,
                'middlei': self.middlei,
                'family': self.family,
                'family2': self.family2}

    def __str__(self):
        r'''The default string representation of a name contains almost all
        known elements, but it is not necessarily how one would normally write
        the name, because it may mix casual and formal parts not normally used
        together, and will show words and their initials together if both are
        known.
        '''
        r = []
        if self.given:
            r.append(self.given)
            if self.giveni:
                r.append('[' + self.giveni + ']')
        elif self.giveni:
            r.append(self.giveni)
        if self.short:
            r.append('[' + self.short + ']')
        if self.middle:
            assert self.given
            r.append(self.middle)
            if self.middlei:
                r.append('[' + self.middlei + ']')
        elif self.middlei:
            r.append(self.middlei)
        if self.family:
            r.append(self.family)
        if self.family2:
            r.append(self.family2)
        return ' '.join(r)

    @name_method
    def complete_name(self):
        return ' '.join(filter(bool,
                        [self.given or self.short or self.giveni,
                         self.middle or self.middlei,
                         self.family,
                         self.family2]))

    @name_method
    def formal_index_name(self):
        return ' '.join(filter(bool,
                        [self.given or self.giveni,
                         self.family,
                         self.family2]))

    @name_method
    def informal_index_name(self):
        r = [self.short]
        if self.family:
            r.append(self.family)
        return ' '.join(r)

    @name_method
    def legal_name(self):
        r = [self.given]
        if self.middle:
            r.append(self.middle)
        r.append(self.family)
        if self.family2:
            r.append(self.family2)
        return ' '.join(r)

    @name_method
    def full_name(self):
        r = [self.given or self.giveni, self.family]
        if self.family2:
            r.append(self.family2)
        return ' '.join(r)

    @name_method
    def familiar_name(self):
        return self.short or self.given

    @name_method
    def initials(self):
        r = []
        if self.giveni:
            r.append(self.giveni)
        elif self.given:
            r.extend(self.extract_initials(self.given))
        if r:
            if self.middlei:
                r.append(self.middlei)
            elif self.middle:
                r.extend(self.extract_initials(self.middle))
        return ''.join(r)

    @classmethod
    def extract_initials(cls, name):
        for word in name.split():
            if word[0].isalpha():
                if len(word) > 2 and word[1] == "'" and word[2].isalpha():
                    yield word[:3].upper() + '.'
                else:
                    yield word[0].upper() + '.'

    @name_method
    def casual_name(self):
        return ' '.join([self.short or self.given, self.family])

    @name_method
    def title_name(self):
        r = [self.family]
        if self.family2:
            r.append(self.family2)
        return ' '.join(r)

    @name_method
    def collation_name(self):
        r = [self.family]
        if self.family2:
            r.append(' ')
            r.append(self.family2)
        r.append(', ')
        r.append(self.given or self.giveni)
        if self.middle or self.middlei:
            r.append(' ')
            r.append(self.middle or self.middlei)
        return ''.join(r)

class SingleName(PersonName):
    r'''Construct an unconventional name that consists of a single word or
    several indivisible words, ie, which cannot be broken into given and family
    names.  E.g., "Sting", "Crit".
    '''

    def __init__(self, single):
        r'''
        @param single: The person's single name.  If the person only has a
            single word name (eg, "Sting", "Crit"), then this parameter allows
            it to be supplied.  If a single name is given, then neither given
            nor family name may be, and vice versa.
        '''
        single = single and single.strip()
        assert isinstance(single, str) and single
        self.single = single

    def _elements(self):
        yield self.single

    def sortkey(self):
        return self.single,

    def _initargs(self):
        return {'single': self.single}

    def __str__(self):
        r'''The default string representation of a name contains all known
        elements, so it is not necessarily how one would normally write the
        name.
        '''
        return self.single

    @name_method
    def complete_name(self):
        return self.single

    @name_method
    def formal_index_name(self):
        return self.single

    @name_method
    def legal_name(self):
        return self.single

    @name_method
    def full_name(self):
        return self.single

    @name_method
    def initials(self):
        return ''.join(EnglishSpanishName.extract_initials(self.single))

    @name_method
    def casual_name(self):
        return self.single

    @name_method
    def familiar_name(self):
        return self.single

    @name_method
    def title_name(self):
        return self.single

    @name_method
    def social_name(self):
        return self.single

    @name_method
    def formal_name(self):
        return self.single

    @name_method
    def formal_salutation_name(self):
        return self.single

def defer_to_wrapped(func):
    r'''Decorator for methods of NameWrapper and its sub classes that causes
    the decorated method to return self._wrapped.method_name() if
    self.method_name() fails (returns None or an empty string or raises
    ValueError).
    '''
    def newfunc(self):
        try:
            ret = func(self)
            if ret:
                return ret
        except (TypeError, ValueError):
            pass
        return getattr(self._wrapped, func.__name__)()
    newfunc.__name__ = func.__name__
    newfunc.__doc__ = func.__doc__
    newfunc.__module__ = func.__module__
    return newfunc

class NameWrapper(PersonName):

    r'''A super class for other name classes that "wrap" another name object.
    '''

    def __init__(self, wrapped):
        assert isinstance(wrapped, PersonName)
        super(NameWrapper, self).__init__()
        self._wrapped = wrapped

    def _elements(self):
        return self._wrapped._elements()

    def sortkey(self):
        return self._wrapped.sortkey()

    def _initargs(self):
        return {'wrapped': self._wrapped}

    def __str__(self):
        return str(self._wrapped)

    @defer_to_wrapped
    def complete_name(self):
        return None

    @defer_to_wrapped
    def formal_index_name(self):
        return None

    @defer_to_wrapped
    def informal_index_name(self):
        return None

    @defer_to_wrapped
    def legal_name(self):
        return None

    @defer_to_wrapped
    def full_name(self):
        return None

    @defer_to_wrapped
    def initials(self):
        return None

    @defer_to_wrapped
    def casual_name(self):
        return None

    @defer_to_wrapped
    def familiar_name(self):
        return None

    @defer_to_wrapped
    def title_name(self):
        return None

    @defer_to_wrapped
    def social_name(self):
        return None

    @defer_to_wrapped
    def formal_name(self):
        return None

    @defer_to_wrapped
    def formal_salutation_name(self):
        return None

    @defer_to_wrapped
    def collation_name(self):
        return None

class DecoratedName(NameWrapper):

    r'''Adds decorations like title, honorific, letters, etc. to an existing
    name.

        >>> n = EnglishSpanishName(given="Zacharias", short='Zack',
        ...                        middle="Quaid", middlei="Q.", \
        ...                        family="Smith")
        >>> d = DecoratedName(n, letters="B.Med.", title="Dr", \
        ...         honorific="The Good Doctor", salutation="Zacko")
        >>> str(d)
        '[The Good Doctor] Dr Zacharias [Zack] Quaid [Q.] Smith, B.Med. [Zacko]'
        >>> d.complete_name()
        sortstr.new('The Good Doctor Zacharias Quaid Smith, B.Med.', slice(16, 37, None))
        >>> d.formal_index_name()
        sortstr.new('Dr Zacharias Smith', slice(3, 18, None))
        >>> d.informal_index_name()
        'Zack Smith'
        >>> d.formal_name()
        sortstr.new('The Good Doctor Zacharias Smith, B.Med.', slice(16, 31, None))
        >>> d.social_name()
        sortstr.new('Dr Smith', slice(3, 8, None))
        >>> d.full_name()
        'Zacharias Smith'
        >>> d.casual_name()
        'Zack Smith'
        >>> d.familiar_name()
        'Zack'
        >>> d.formal_salutation_name()
        'Zacko'
        >>> d.collation_name()
        sortstr.new('Dr Smith, Zacharias Quaid', slice(3, 25, None))

        >>> eval(repr(d)) == d
        True

        >>> d.matches('Zack Smith')
        True
        >>> d.matches('Dr Zack Smith')
        True
        >>> d.matches('The Good Doctor Zacharias Smith')
        True
        >>> d.matches('Zacko')
        True
        >>> d.matches('Smith Dr')
        False

        >>> n = EnglishSpanishName(giveni="Z.", middlei="Q.", family="Smith")
        >>> d = DecoratedName(n, title="Dr")
        >>> str(d)
        'Dr Z. Q. Smith'
        >>> d.complete_name()
        sortstr.new('Dr Z. Q. Smith', slice(3, 14, None))
        >>> d.formal_index_name()
        sortstr.new('Dr Z. Smith', slice(3, 11, None))
        >>> d.informal_index_name()
        Traceback (most recent call last):
        ValueError: no informal index name for Z. Q. Smith
        >>> d.formal_name()
        sortstr.new('Dr Z. Smith', slice(3, 11, None))
        >>> d.social_name()
        sortstr.new('Dr Smith', slice(3, 8, None))
        >>> d.full_name()
        'Z. Smith'
        >>> d.casual_name()
        Traceback (most recent call last):
        ValueError: no casual name for Z. Q. Smith
        >>> d.familiar_name()
        Traceback (most recent call last):
        ValueError: no familiar name for Dr Z. Q. Smith
        >>> d.formal_salutation_name()
        sortstr.new('Dr Smith', slice(3, 8, None))
        >>> d.collation_name()
        sortstr.new('Dr Smith, Z. Q.', slice(3, 15, None))

        >>> eval(repr(d)) == d
        True

    '''

    def __init__(self, wrapped, title=None, salutation=None, honorific=None,
                       letters=None):
        r'''A decorated name takes a normal name and adds optional social
        decorations.
        @param wrapped: The person's bare name, without any decoration.
        @param title: The person's title, such as "Mr", "Ms", "Miss", "Dr".
            The title is used to form the salutation name ("<Title>
            <Surname>"), if the salutation name is not provided.  The title is
            also used in the postal address on an envelope ("<Title>
            <Full_name>"), if the envelope name is not provided.  If the title
            is given then either a single name or family name must also be
            given, or ValueError is raised.
        @param salutation: The salutation name, as used in the opening line of
            a formal letter e.g., "Dear <Salutation_name>".  If not provided,
            then it is formed as "<Title> <Family_name>".
        @param honorific: The honorific is the correct form of address for the
            person in an official capacity, e.g., "The Honourable" for state
            government ministers in Australia".  If an honorific is not given,
            then the person's title is used instead.  If an honorific is given,
            then a title must also be given.
        @param letters: The letters are appended to the person's name in
            official forms of address, such as in the postal address on an
            envelope.
        '''
        title = title and title.strip()
        salutation = salutation and salutation.strip()
        honorific = honorific and honorific.strip()
        letters = letters and letters.strip()
        assert title is None or isinstance(title, str) and title
        assert salutation is None or isinstance(salutation, str) and \
                salutation
        assert honorific is None or isinstance(honorific, str) and \
                honorific
        assert letters is None or isinstance(letters, str) and letters
        if honorific and not title:
            raise ValueError('%s() honorific without title' %
                             self.__class__.__name__)
        if title and not has(wrapped.title_name):
            raise ValueError('%s() title without title name' %
                             self.__class__.__name__)
        super(DecoratedName, self).__init__(wrapped)
        self.title = title
        self.salutation = salutation
        self.honorific = honorific
        self.letters = letters

    def _elements(self):
        yield self.title
        yield self.salutation
        yield self.honorific
        for e in self._wrapped._elements():
            yield e
        yield self.letters

    def _initargs(self):
        r = {'title': self.title,
             'salutation': self.salutation,
             'honorific': self.honorific,
             'letters': self.letters}
        r.update(NameWrapper._initargs(self))
        return r

    def __str__(self):
        r'''The default string representation of a decorated name contains all
        elements, so it is not necessarily how one would normally write the
        name.
        '''
        r = []
        if self.honorific:
            r.append('[')
            r.append(self.honorific)
            r.append('] ')
        if self.title:
            r.append(self.title)
            r.append(' ')
        r.append(str(self._wrapped))
        if self.letters:
            r.append(', ')
            r.append(self.letters)
        if self.salutation:
            r.append(' [')
            r.append(self.salutation)
            r.append(']')
        return ''.join(r)

    @defer_to_wrapped
    def social_name(self):
        prefix = self.title
        tn = self._wrapped.title_name()
        n = ' '.join([prefix, tn])
        if prefix:
            n = sortstr(n)
            start = len(prefix) + 1
            n.sortslice = slice(start, start + len(tn))
        return n

    @defer_to_wrapped
    def formal_name(self):
        prefix = self.honorific or self.title
        fn = self._wrapped.full_name()
        n = ', '.join(filter(bool, [' '.join([prefix, fn]), self.letters]))
        if prefix or self.letters:
            n = sortstr(n)
            start = len(prefix) + 1 if prefix else 0
            n.sortslice = slice(start, start + len(fn))
        return n

    @defer_to_wrapped
    def formal_salutation_name(self):
        return self.salutation or self.social_name()

    @name_method
    def complete_name(self):
        prefix = self.honorific or self.title
        cn = self._wrapped.complete_name()
        n = ', '.join(filter(bool, [' '.join(filter(bool, [prefix, cn])),
                                    self.letters]))
        if prefix or self.letters:
            n = sortstr(n)
            start = len(prefix) + 1 if prefix else 0
            n.sortslice = slice(start, start + len(cn))
        return n

    @defer_to_wrapped
    def formal_index_name(self):
        prefix = self.title or self.honorific
        fin = self._wrapped.formal_index_name()
        n = ' '.join([prefix, fin])
        if prefix:
            n = sortstr(n)
            start = len(prefix) + 1
            n.sortslice = slice(start, start + len(fin))
        return n

    @name_method
    def familiar_name(self):
        r'''The familiar name of a decorated name only succeeds if the wrapped
        name has a familiar name that is distinct from its complete name.
        '''
        fn = self._wrapped.familiar_name()
        cn = self._wrapped.complete_name()
        return fn if not cn.startswith(fn + ' ') else None

    @defer_to_wrapped
    def collation_name(self):
        prefix = self.title or self.honorific
        cn = self._wrapped.collation_name()
        n = ' '.join([prefix, cn])
        if prefix:
            n = sortstr(n)
            start = len(prefix) + 1
            n.sortslice = slice(start, start + len(cn))
        return n
