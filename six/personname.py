# vim: sw=4 sts=4 et fileencoding=latin1 nomod

r'''Personal names.
'''

import operator
from six.input import InputError

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
        in a private phone book, for example.
        @raise ValueError: if the casual name cannot be formed
        '''
        return None

    @name_method
    def familiar_name(self):
        r'''The name of the person in an informal context.  This friends,
        family, or co-workers in daily use, such as the spoken greeting,
        "Hello, <Informal_name>".  It is also used as the salutation in
        informal correspondence.
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
            part = unicode(parts.pop(0))
            if (text.startswith(part) and
                (len(text) == len(part) or text[len(part)].isspace())):
                text = text[len(part):].lstrip()
        return not text

    def __str__(self):
        r'''The str representation of a name is simply the unicode
        representation encoded in the current encoding, so it could fail with a
        UnicodeEncodingError.
        '''
        return str(unicode(self))

    def __hash__(self):
        r'''The hash depends on all the elements of the name.
        '''
        if self.__hash is None:
            self.__hash = reduce(operator.xor, map(hash, self._elements()))
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
                           for k, v in self._initargs().iteritems() if v)))

class EnglishSpanishName(PersonName):

    r'''A conventional English or Spanish name.  The following table shows how
    the different elements of the name are used in the various forms of the
    name.

                            Given   Middle  Family  Family2
        Legal name           y      [y]      y      [y]
        Full name           (i)     (i)      y      [y]
        Casual name         (ii)    (ii)     y       -
        Familiar name       (ii)    (ii)     -       -
        Title name           -       -       y       -
        Collation name      (i)      [y]     y      [y]

    [y] Only used if known.

    (i) If the given/middle name is not known in these cases, then initials are
    used, if known.

    (ii) The given/middle name(s) used in these cases are the contracted
    (short) form, if known.  If only the initials are known, they are not used.

    Note that for Anglic names, which only have a single family name, the full
    name and casual name forms are the same if there is no contracted given
    name (short name).

        >>> n = EnglishSpanishName(given="Zacharias", family="Smith", \
        ...                        short="Zack")
        >>> n.complete_name()
        'Zacharias Smith'
        >>> n.legal_name()
        'Zacharias Smith'
        >>> n.full_name()
        'Zacharias Smith'
        >>> n.casual_name()
        'Zack Smith'
        >>> n.familiar_name()
        'Zack'
        >>> n.social_name()
        Traceback (most recent call last):
        ValueError: no social name for Zacharias [Zack] Smith
        >>> n.formal_name()
        Traceback (most recent call last):
        ValueError: no formal name for Zacharias [Zack] Smith
        >>> n.formal_salutation_name()
        Traceback (most recent call last):
        ValueError: no formal salutation name for Zacharias [Zack] Smith
        >>> n.collation_name()
        'Smith, Zacharias'
        >>> unicode(n)
        u'Zacharias [Zack] Smith'
        >>> str(n)
        'Zacharias [Zack] Smith'

        >>> eval(repr(n)) == n
        True

        >>> n.matches('Zack')
        True
        >>> n.matches('Zack Smith')
        True
        >>> n.matches('Zacharias Smith')
        True
        >>> n.matches('Smith')
        True
        >>> n.matches('Smith Zacharias')
        False

        >>> n = EnglishSpanishName(giveni="Z.", family="Smith")
        >>> n.complete_name()
        'Z. Smith'
        >>> n.legal_name()
        Traceback (most recent call last):
        ValueError: no legal name for Z. Smith
        >>> n.full_name()
        'Z. Smith'
        >>> n.casual_name()
        Traceback (most recent call last):
        ValueError: no casual name for Z. Smith
        >>> n.familiar_name()
        Traceback (most recent call last):
        ValueError: no familiar name for Z. Smith
        >>> n.social_name()
        Traceback (most recent call last):
        ValueError: no social name for Z. Smith
        >>> n.formal_name()
        Traceback (most recent call last):
        ValueError: no formal name for Z. Smith
        >>> n.formal_salutation_name()
        Traceback (most recent call last):
        ValueError: no formal salutation name for Z. Smith
        >>> n.collation_name()
        'Smith, Z.'
        >>> unicode(n)
        u'Z. Smith'
        >>> str(n)
        'Z. Smith'

        >>> eval(repr(n)) == n
        True

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
            Paco or Fran for Francisco, and Maite for Maria Teresa -- the name
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
        assert given is None or isinstance(given, basestring) and given
        assert short is None or isinstance(short, basestring) and short
        assert giveni is None or isinstance(giveni, basestring) and giveni
        assert middle is None or isinstance(middle, basestring) and middle
        assert middlei is None or isinstance(middlei, basestring) and middlei
        assert family is None or isinstance(family, basestring) and family
        assert family2 is None or isinstance(family2, basestring) and family2
        if not (short or given or family):
            raise ValueError('%s() missing name' % self.__class__.__name__)
        if family2 and not family:
            raise ValueError('%s() family2 given without family' %
                             self.__class__.__name__)
        if middle and not given:
            raise ValueError('%s() middle name without given name' %
                             self.__class__.__name__)
        PersonName.__init__(self)
        self.given = given and given.strip()
        self.short = short and short.strip()
        self.giveni = giveni and giveni.strip()
        self.middle = middle and middle.strip()
        self.middlei = middlei and middlei.strip()
        self.family = family and family.strip()
        self.family2 = family2 and family2.strip()

    def _elements(self):
        return [self.giveni, self.short, self.given, self.middlei, self.middle,
                self.family, self.family2]

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

    def __unicode__(self):
        r'''The default string representation of a name contains almost all
        known elements, but it is not necessarily how one would normally write
        the name, because it may mix casual and formal parts not normally used
        together.
        '''
        r = []
        if self.given:
            r.append(self.given)
            if self.giveni:
                r.append('[' + self.giveni + ']')
        elif self.giveni:
            r.append(self.giveni)
        if self.middle:
            assert self.given
            r.append(self.middle)
            if self.middlei:
                r.append('[' + self.middlei + ']')
        elif self.middlei:
            r.append(self.middlei)
        if self.short:
            r.append('[' + self.short + ']')
        if self.family:
            r.append(self.family)
        if self.family2:
            r.append(self.family2)
        return u' '.join(r)

    @name_method
    def complete_name(self):
        return ' '.join(filter(bool,
                        [self.given or self.short or self.giveni,
                         self.middle or self.middlei,
                         self.family,
                         self.family2]))

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
    def casual_name(self):
        return ' '.join([self.short or self.given, self.family])

    @name_method
    def familiar_name(self):
        return self.short or self.given

    @name_method
    def title_name(self):
        return self.family

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
        assert isinstance(single, basestring) and single
        self.single = single and single.strip()

    def _elements(self):
        return [self.single]

    def sortkey(self):
        return self.single,

    def _initargs(self):
        return {'single': self.single}

    def __unicode__(self):
        r'''The default string representation of a name contains all known
        elements, so it is not necessarily how one would normally write the
        name.
        '''
        return self.single

    @name_method
    def legal_name(self):
        return self.single

    @name_method
    def full_name(self):
        return self.single

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

    def __unicode__(self):
        return unicode(self._wrapped)

    @defer_to_wrapped
    def complete_name(self):
        return None

    @defer_to_wrapped
    def legal_name(self):
        return None

    @defer_to_wrapped
    def full_name(self):
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

        >>> n = EnglishSpanishName(given="Zacharias", family="Smith", \
        ...                        short='Zack')
        >>> d = DecoratedName(n, letters="B.Med.", title="Dr", \
        ...         honorific="The Good Doctor", salutation="Zacko")
        >>> unicode(d)
        u'[The Good Doctor] Dr Zacharias [Zack] Smith, B.Med. [Zacko]'
        >>> d.formal_name()
        'The Good Doctor Zacharias Smith, B.Med.'
        >>> d.social_name()
        'Dr Smith'
        >>> d.full_name()
        'Zacharias Smith'
        >>> d.casual_name()
        'Zack Smith'
        >>> d.familiar_name()
        'Zack'
        >>> d.collation_name()
        'Smith, Zacharias'

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

        >>> n = EnglishSpanishName(giveni="Z.", family="Smith")
        >>> d = DecoratedName(n, title="Dr")
        >>> unicode(d)
        u'Dr Z. Smith'
        >>> d.formal_name()
        'Dr Z. Smith'
        >>> d.social_name()
        'Dr Smith'
        >>> d.full_name()
        'Z. Smith'
        >>> d.casual_name()
        Traceback (most recent call last):
        ValueError: no casual name for Z. Smith
        >>> d.familiar_name()
        Traceback (most recent call last):
        ValueError: no familiar name for Z. Smith
        >>> d.collation_name()
        'Smith, Z.'

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
        assert title is None or isinstance(title, basestring)
        assert salutation is None or isinstance(salutation, basestring)
        assert honorific is None or isinstance(honorific, basestring)
        assert letters is None or isinstance(letters, basestring)
        if honorific and not title:
            raise ValueError('%s() honorific without title' %
                             self.__class__.__name__)
        if title and not has(wrapped.title_name):
            raise ValueError('%s() title without title name' %
                             self.__class__.__name__)
        super(DecoratedName, self).__init__(wrapped)
        self.title = title and title.strip()
        self.salutation = salutation and salutation.strip()
        self.honorific = honorific and honorific.strip()
        self.letters = letters and letters.strip()

    def _elements(self):
        return [self.title, self.salutation, self.honorific] + \
               self._wrapped._elements() + \
               [self.letters]

    def _initargs(self):
        r = {'title': self.title,
             'salutation': self.salutation,
             'honorific': self.honorific,
             'letters': self.letters}
        r.update(NameWrapper._initargs(self))
        return r

    def __unicode__(self):
        r'''The default string representation of a decorated name contains all
        elements, so it is not necessarily how one would normally write the
        name.
        '''
        r = []
        if self.honorific:
            r.append(u'[')
            r.append(self.honorific)
            r.append(u'] ')
        if self.title:
            r.append(self.title)
            r.append(u' ')
        r.append(unicode(self._wrapped))
        if self.letters:
            r.append(u', ')
            r.append(self.letters)
        if self.salutation:
            r.append(u' [')
            r.append(self.salutation)
            r.append(u']')
        return u''.join(r)

    @defer_to_wrapped
    def social_name(self):
        return ' '.join([self.title, self.title_name()])

    @defer_to_wrapped
    def formal_name(self):
        return ', '.join(filter(bool, [' '.join([self.honorific or self.title,
                                                 self.full_name()]),
                                       self.letters]))

    @defer_to_wrapped
    def formal_salutation_name(self):
        return self.salutation or self.social_name()

    @defer_to_wrapped
    def complete_name(self):
        return ', '.join(filter(bool, [self.honorific or self.title,
                                       self._wrapped.complete_name(),
                                       self.letters]))

