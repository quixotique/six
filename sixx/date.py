# vim: sw=4 sts=4 et fileencoding=utf8 nomod

r'''Dates and times.
'''

import re
import locale
import datetime
import calendar
import time
from sixx.input import InputError

__all__ = ['Datetime']

class Datetime(object):
    r'''Represents a parsed date/time string in which some elements may be
    missing.
    '''

    max_tzoffset = 12 * 60 - 1

    def __init__(self, year=None, month=None, day=None, hour=None, minute=None,
                       second=None, tzoffset=None, weekday=None):
        #import sys
        #print >>sys.stderr, 'Datetime(year=%r, month=%r, day=%r, hour=%r,' \
        #        ' minute=%r, second=%r, tzoffset=%r, weekday=%r)' % (
        #        year, month, day, hour, minute, second, tzoffset, weekday)
        if year is not None:
            assert 1900 <= year <= 9999
        if month is not None:
            assert 1 <= month <= 12
        if day is not None:
            assert 1 <= day <= 31
        if hour is not None:
            assert 0 <= hour < 24
        if minute is not None:
            assert 0 <= minute < 60
        if second is not None:
            assert 0 <= second < 60
        if tzoffset is not None:
            assert -self.max_tzoffset <= tzoffset <= self.max_tzoffset
        if weekday is not None:
            assert 0 <= weekday < 6
        self.year = year
        self.month = month
        self.day = day
        self.hour = hour
        self.minute = minute
        self.second = second
        self.tzoffset = tzoffset
        self.weekday = weekday
        self.tzinfo = None
        self.date = None
        self.time = None
        self.datetime = None
        if (self.year is not None and self.month is not None and
                self.day is not None and
                datetime.MINYEAR <= self.year <= datetime.MAXYEAR):
            self.date = datetime.date(self.year, self.month, self.day)
            if self.weekday is not None and self.weekday != self.date.weekday():
                t = list(self.date.timetuple())
                t[6] = self.weekday
                t = tuple(t)
                raise ValueError(
                        time.strftime('incorrect day of week %A ', t) +
                        self.date.strftime('(should be %A)'))
        if tzoffset is not None:
            self.tzinfo = TZ(tzoffset)
        if (self.hour is not None and self.minute is not None and
                self.second is not None):
            self.time = datetime.time(self.hour, self.minute, self.second, 0,
                                      self.tzinfo)
        if self.date is not None and self.time is not None:
            self.datetime = datetime.datetime.combine(self.date, self.time)

    def __repr__(self):
        r = []
        for kw in ('year', 'month', 'day', 'hour', 'minute', 'second',
                   'tzoffset', 'weekday'):
            val = getattr(self, kw)
            if val is not None:
                r.append('%s=%r' % (kw, val))
        return '%s.%s(%s)' % (self.__class__.__module__,
                self.__class__.__name__, ', '.join(r))

    def as_date(self):
        r'''Return a datetime.date() object, or raise ValueError if a necessary
        field is missing.

            >>> Datetime(year=2006, month=10, day=9).as_date()
            datetime.date(2006, 10, 9)

            >>> Datetime(year=2006).as_date()
            Traceback (most recent call last):
            ValueError: missing month and day

        '''
        if self.date is not None:
            return self.date
        raise ValueError('missing %s' % ' and '.join(
                [what for what in ('year', 'month', 'day')
                      if getattr(self, what) is None]))

    @classmethod
    def parse(class_, text,
                      with_date=True, with_time=True, with_timezone=True,
                      pivot_year=1969):
        r'''Parse a text into a date and time, being fairly permissive about
        the presence of the elements in the text and the punctuation used to
        separate them.  It assumes that day always comes before month and both
        of these before year, like European dates DD/MM/YY; American dates
        MM/DD/YY will not work if both DD and MM are in the range 1-12, and the
        problem is compounded if a double digit year in the range 01-12 is
        used.  Unfortunately, ISO dates YYYY-MM-DD will have the same problem.

            >>> Datetime.parse('mon oct 9 9:48am 2006 +09:30')
            sixx.date.Datetime(year=2006, month=10, day=9, hour=9, minute=48, second=0, tzoffset=570, weekday=0)

            >>> Datetime.parse('January 1st, 1970')
            sixx.date.Datetime(year=1970, month=1, day=1)

            >>> Datetime.parse('January 1st, 1970')
            sixx.date.Datetime(year=1970, month=1, day=1)

        The day of week is optional:

            >>> Datetime.parse('9/10/2006 09:48:00 +0930')
            sixx.date.Datetime(year=2006, month=10, day=9, hour=9, minute=48, second=0, tzoffset=570)

        If the day of week is incorrect, an exception is raised:

            >>> Datetime.parse('tue 9/10/2006 09:48:00 +0930')
            Traceback (most recent call last):
            sixx.input.InputError: incorrect day of week Tuesday (should be Monday)

        You can omit the year, which makes it useful for birthdays when the
        age is unknown:

            >>> Datetime.parse('mon oct 9 9:48am +09:30')
            sixx.date.Datetime(month=10, day=9, hour=9, minute=48, second=0, tzoffset=570, weekday=0)

            >>> Datetime.parse('September 11th')
            sixx.date.Datetime(month=9, day=11)

        You can omit the month:

            >>> Datetime.parse('mon 9 9:48am 2006 +09:30')
            sixx.date.Datetime(year=2006, day=9, hour=9, minute=48, second=0, tzoffset=570, weekday=0)

        You can omit the day, but then the month number may be interpreted as
        the day, so the month is best given textually:

            >>> Datetime.parse('oct 9:48am 2006 +09:30')
            sixx.date.Datetime(year=2006, month=10, hour=9, minute=48, second=0, tzoffset=570)

            >>> Datetime.parse('10/ 9:48am 2006 +09:30')
            sixx.date.Datetime(year=2006, day=10, hour=9, minute=48, second=0, tzoffset=570)

        Day must be in range:

            >>> Datetime.parse('mon feb 29 9:48am 2006 +09:30')
            Traceback (most recent call last):
            sixx.input.InputError: day is out of range for month

        You can omit the time:

            >>> Datetime.parse('mon oct 9 2006 +09:30')
            sixx.date.Datetime(year=2006, month=10, day=9, tzoffset=570, weekday=0)

        '''
        orig_text = text
        class_._init_names()
        year = month = day = None
        hour = minute = second = None
        weekday = tzoffset = None
        # Timezone.
        if with_timezone:
            m = class_._re_tzoffset.search(text)
            if m is not None:
                tzoffset = int(m.group(2)) * 60 + int(m.group(3))
                assert -1439 <= tzoffset <= 1439
                if m.group(1) == '-':
                    tzoffset = -tzoffset
                text = text[:m.start()] + text[m.end():]
        # Year four digits.
        if with_date:
            m = class_._re_year4.search(text)
            if m is not None:
                yr = int(m.group())
                if 1900 <= yr:
                    year = yr
                    text = text[:m.start()] + text[m.end():]
            # Month (name).
            month, text = class_._find_name(text, class_._months)
            assert month is None or 1 <= month <= 12
            # Day of week.
            weekday, text = class_._find_name(text, class_._weekdays)
            assert weekday is None or 0 <= weekday <= 6
        # Hours, minutes, seconds.
        if with_time:
            m = class_._re_hms.search(text)
            if m is not None:
                set_hour = None
                hr = int(m.group('hour'))
                min = m.group('min') and int(m.group('min')) or None
                sec = m.group('sec') and int(m.group('sec')) or None
                ampm = m.group('ampm') and m.group('ampm').lower() or ''
                # The hour must be followed by either :MM or AM/PM or both.
                if min is not None or ampm:
                    if ampm.startswith('p'):
                        if 1 <= hr < 12:
                            set_hour = hr + 12
                        elif hr == 12:
                            set_hour = 0
                        elif 12 < hr <= 23:
                            set_hour = hr
                    elif ampm.startswith('a'):
                        if 0 <= hr <= 12:
                            set_hour = hr % 12
                    elif 0 <= hr <= 23:
                        set_hour = hr
                if set_hour is not None:
                    hour = set_hour
                    minute = min or 0
                    second = sec or 0
                    text = text[:m.start()] + text[m.end():]
        if with_date:
            # Day.  If an ordinal form, eg "2nd", then it definitely is the
            # day.  Otherwise, it might not be, so we save it in 'found_day'
            # for later.
            m = class_._re_day.search(text)
            if m is not None:
                day = int(m.group('day'))
                assert 1 <= day <= 31
                text = text[:m.start()] + text[m.end():]
            # Month (number, if no name found above).
            if month is None:
                m = class_._re_month.search(text)
                if m is not None:
                    month = int(m.group())
                    assert 1 <= month <= 12
                    text = text[:m.start()] + text[m.end():]
            # Year two digits (if no four-digit year found above).
            if year is None:
                m = class_._re_year2.search(text)
                if m is not None:
                    year = 1900 + int(m.group())
                    if year < pivot_year:
                        year += 100
                    text = text[:m.start()] + text[m.end():]
        # If there is any alphnumeric left over, then we failed to parse
        # something.
        for i in range(len(text)):
            if text[i].isalnum():
                raise InputError('malformed date/time at "%s"' %
                                 text[i:].split(None, 1)[0], char=text[i])
        local = locals()
        kw = dict(((k, v) for k, v in
                    ((k, local[k]) for k in
                     ('year', 'month', 'day', 'hour', 'minute', 'second',
                      'tzoffset', 'weekday',))
                    if v is not None))
        try:
            return class_(**kw)
        except ValueError as e:
            raise InputError(e, char=orig_text)

    _re_tzoffset = re.compile(r'([+\-])(0\d|1[012]):?(\d\d)\b')
    _re_year4 = re.compile(r'\b(\d\d\d\d)\b')
    _re_year2 = re.compile(r'\b(\d\d)\b')
    _re_month = re.compile(r'\b([1-9]|1[012])\b')
    _re_day = re.compile(r'''
            \b(?:
                (?P<day> [1-9] | [12]\d | 3[01] )
                (?P<ord> (?: (?<=1\d)th | (?<=1)st | (?<=2)nd | (?<=3)rd |
                             (?<=[04-9])th )? )
            )\b''',
            re.VERBOSE)
    _re_hms = re.compile(r'''
            \b
            (?P<hour> [01]?\d | 2[0-4] )(?= :\d\d | \s*[AP]\.?M(?:\b|\.) )
            (?: : (?P<min> [0-5]\d ) )?
            (?: : (?P<sec> [0-5]\d ) )?
            (?: \s* (?P<ampm> [AP] \.? M (?: \b | \. ) ) | \b )
            ''',
            re.IGNORECASE | re.VERBOSE)

    _months = None
    _weekdays = None

    @classmethod
    def _init_names(class_):
        r'''Initialise the class's _months and _weekdays name-to-ordinal maps.
        '''
        if class_._months is not None:
            return
        class_._months = []
        class_._weekdays = []
        oloc = locale.getlocale(locale.LC_TIME)
        locale.setlocale(locale.LC_TIME, 'C')
        for d in range(7):
            n = (d + 1) % 7 + 1 # 0 = Monday = locale.DAY_2
            class_._weekdays.append(
                (locale.nl_langinfo(getattr(locale, 'DAY_%d' % n)).lower(), d))
            class_._weekdays.append(
                (locale.nl_langinfo(getattr(locale, 'ABDAY_%d' % n)).lower(), d))
        for m in range(1, 13):
            class_._months.append(
                (locale.nl_langinfo(getattr(locale, 'MON_%d' % m)).lower(), m))
            class_._months.append(
                (locale.nl_langinfo(getattr(locale, 'ABMON_%d' % m)).lower(), m))
        locale.setlocale(locale.LC_TIME, oloc)
        class_._months.sort(key=lambda x: (len(x[0]), x[1]))

    @classmethod
    def _find_name(class_, text, _names):
        r'''Search text for a name in the given name-ordinal map, and if found,
        return the ordinal and a modified text with the name excised.

        >>> Datetime._find_name('one two three', [('two', 2)])
        (2, 'one  three')

        >>> Datetime._find_name('one two three', [('three', 3), ('two', 2)])
        (3, 'one two ')

        >>> Datetime._find_name('one two three', [('one', 1), ('three', 3), ('two', 2)])
        (1, ' two three')

        '''
        textl = text.lower()
        for name, ord in _names:
            i = textl.find(name)
            if i == -1:
                continue
            if i != 0 and textl[i-1].isalpha():
                continue
            j = i + len(name)
            if j != len(textl) and textl[j].isalpha():
                continue
            return ord, text[:i] + text[j:]
        return None, text

class TZ(datetime.tzinfo):

    r'''A concrete subclass of the abstract datetime.tzinfo class that
    represents a fixed offset, in minutes, from GMT.
    '''

    def __init__(self, minutes=0):
        self.minutes = minutes

    def utcoffset(self, dt):
        return timedelta(minutes=self.minutes)

    def dst(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        r'''
            >>> TZ(-328).tzname(None)
            '-05:28'
            >>> TZ(629).tzname(None)
            '+10:29'
        '''
        #if not self.minutes:
        #    return None
        return '%s%02u:%02u' % ((self.minutes < 0 and '-' or '+',) + \
                divmod(abs(self.minutes), 60))

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.minutes)
