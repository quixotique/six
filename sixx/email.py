# vim: sw=4 sts=4 et fileencoding=utf8 nomod

r'''Data model - email addresses.
'''


import re
from sixx.input import InputError
from sixx.node import *
from sixx.telephone import At_home, At_work

__all__ = [
        'Email', 'URI',
        'Has_email', 'Has_email_home', 'Has_email_work',
        'Has_web_page',
    ]

class Email(Node):

    r'''
        >>> e = Email('andrewb@zip.com.au')
        >>> e
        Email('andrewb@zip.com.au')
        >>> str(e)
        'andrewb@zip.com.au'

    '''

    def __init__(self, address):
        assert isinstance(address, str)
        super(Email, self).__init__()
        self.address = address

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.address)

    def __str__(self):
        return self.address

    def format(self, name=None, encoding='ascii'):
        r = []
        if name:
            name = str(name)
            if encoding:
                try:
                    name.encode(encoding)
                except UnicodeEncodeError:
                    from email.header import Header
                    try:
                        name = Header(name, 'iso-8859-1').encode()
                    except UnicodeEncodeError:
                        name = Header(name, 'utf-8').encode()
            m = self._re_atoms.match(name)
            if not (m and m.end() == len(name)):
                name = self._quote(name)
            r.append(name)
            r.append(' <')
        r.append(self.address)
        if name:
            r.append('>')
        return ''.join(r)

    # These taken directly from RFC 822.  Should be upgraded to RFC 2822.
    _atom = r'''[!#$%&'*+\-/0-9=?A-Za-z^_`{}|~]+'''
    _dtext = r'[^[\]\\\n]'
    _qtext = r'[^"\\\n]'
    _quoted_pair = r'\\.'
    _quoted_string = r'"(?:' + _qtext + '|' + _quoted_pair + r')*"'
    _word = r'(?:' + _atom + '|' + _quoted_string + ')'
    _phrase = r'(?:' + _word + r'(?:\s+' + _word + r')*)'
    _domain_ref = _atom
    _domain_literal = r'\[(?:' + _dtext + '|' + _quoted_pair + r')*\]'
    _sub_domain = r'(?:' + _domain_ref + '|' + _domain_literal + r')'
    _domain = _sub_domain + r'(?:\.' + _sub_domain + r')*'
    _local_part = _word + r'(?:\.' + _word + r')*'
    _addr_spec = _local_part + r'@' + _domain
    _route = r'@' + _domain + r':'
    _route_addr = r'<(?:' + _route + r')?' + _addr_spec + r'>'
    _mailbox = r'(?:' + _phrase + _route_addr + '|' + _addr_spec + r')'
    _group = _phrase + r':(?:|' + _mailbox + r'(?:,' + _mailbox + r')*);'
    _address = r'(?:' + _mailbox + '|' + _group + r')'

    _re_atoms = re.compile(_atom + r'(?:\s+' + _atom + r')*')
    _re_addr_spec = re.compile(_addr_spec)

    @classmethod
    def parse(class_, text, world=None, place=None, default_place=None):
        r'''
            >>> Email.parse('andrewb@zip.com.au   wah')
            (Email('andrewb@zip.com.au'), 'wah')

            >>> Email.parse('andrewb@zip.com.au   wäh')
            (Email('andrewb@zip.com.au'), 'w\xe4h')

            >>> Email.parse('andréwb@zip.com.au')
            Traceback (most recent call last):
            sixx.input.InputError: malformed email address

            >>> Email.parse('wah')
            Traceback (most recent call last):
            sixx.input.InputError: malformed email address

            >>> Email.parse('wah@.com')
            Traceback (most recent call last):
            sixx.input.InputError: malformed email address

            >>> Email.parse('@bar.com')
            Traceback (most recent call last):
            sixx.input.InputError: malformed email address

            >>> Email.parse('foo@bar')
            (Email('foo@bar'), None)

        '''
        m = class_._re_addr_spec.match(text)
        if m is None:
            raise InputError('malformed email address', char=text)
        address = str(m.group())
        comment = text[m.end():].strip() or None
        return class_(address), comment

    @staticmethod
    def _quote(text):
        return '"' + text.replace('"', r'\"') + '"'

class URI(Node):

    r'''
        >>> w = URI('http://www.zip.com.au/~andrewb/')
        >>> w
        URI('http://www.zip.com.au/~andrewb/')
        >>> str(w)
        'http://www.zip.com.au/~andrewb/'

    '''

    def __init__(self, uri):
        assert isinstance(uri, str)
        super(URI, self).__init__()
        self.uri = uri

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.uri)

    def __str__(self):
        return self.uri

    # These taken directly from RFC 2396.
    _alpha = r'[A-Za-z]'
    _num = r'[0-9]'
    _hex = r'[0-9A-Fa-f]'
    _alphanum = '[' + _alpha[1:-1] + _num[1:-1] + ']'
    _mark = r'''[\-_.!~*'()]'''
    _unreserved = '[' + _alphanum[1:-1] + _mark[1:-1] + ']'
    _reserved = r'[;/?:@&=+$,]'
    _escaped = '%' + _hex + _hex
    _uric = r'(?:[' + _reserved[1:-1] + _unreserved[1:-1] + r']|' + \
                      _escaped + ')'
    _uric_no_slash = r'(?:[;?:@&=+$,' + _unreserved[1:-1] + r']|' + \
                      _escaped + ')'
    _fragment = _uric + r'*'
    _scheme = r'(?:' + _alpha + '[' + _alphanum[1:-1] + r'+\-.]*)'
    _userinfo = r'(?:[' + _unreserved[1:-1] + ';:&=+$,]|' + _escaped + r')*'
    _domainlabel = r'(?:' + _alphanum + r'(?:[' + _alphanum[1:-1] + r'\-]*' + \
                            _alphanum + r')?)'
    _toplabel = r'(?:' + _alpha + r'(?:[' + _alphanum[1:-1] + r'\-]*' + \
                         _alphanum + r')?)'
    _hostname = r'(?:' + _domainlabel + r'\.)*' + _toplabel + r'\.?'
    _IPv4address = r'\d+\.\d+\.\d+\.\d+'
    _host = r'(?:' + _hostname + '|' + _IPv4address + r')'
    _port = r'\d*'
    _hostport = _host + r'(?::' + _port + r')?'
    _server = r'(?:(?:' + _userinfo + r'@)?' + _hostport + r')?'
    _reg_name = r'(?:[' + _unreserved[1:-1] + r'$,;:@&=+]|' + _escaped + r')+'
    _authority = r'(?:' + _server + '|' + _reg_name + ')'
    _query = _uric + '*'
    _pchar = r'(?:[' + _unreserved[1:-1] + r':@&=+$,]|' + _escaped + r')'
    _param = _pchar + r'*'
    _segment = _pchar + r'*(?:;' + _param + r')*'
    _path_segments = _segment + r'(?:/' + _segment + r')*'
    _abs_path = r'/' + _path_segments
    _net_part = r'//' + _authority + r'(?:' + _abs_path + r')?'
    _heir_part = r'(?:' + _net_part + '|' + _abs_path + r')(?:\?' + _query + ')?'
    _opaque_part = _uric_no_slash + _uric + r'*'
    _absolute_uri = _scheme + r':(?:' + _heir_part + '|' + _opaque_part + ')'

    _re_uri = re.compile(_absolute_uri + r'(?:#' + _fragment + ')?')

    @classmethod
    def parse(class_, text, world=None, place=None, default_place=None):
        r'''
            >>> URI.parse('http://www.zip.com.au/~andrewb/   wah')
            (URI('http://www.zip.com.au/~andrewb/'), 'wah')

        '''
        m = class_._re_uri.match(text)
        if m is None:
            raise InputError('malformed absolute URI', char=text)
        uri = str(m.group())
        comment = text[m.end():].strip() or None
        return class_(uri), comment

class Has_email(Link):

    def __init__(self, who, email, comment=None, timestamp=None):
        from sixx.person import Person
        from sixx.family import Family
        from sixx.org import Organisation, Works_at
        from sixx.links import Resides_at
        assert isinstance(who, (Person, Family, Organisation, Works_at,
                                Resides_at))
        assert isinstance(email, Email)
        assert comment is None or isinstance(comment, str)
        super(Has_email, self).__init__(who, email, timestamp=timestamp)
        self.who = who
        self.email = email
        self.comment = comment

class Has_email_home(Has_email, At_home): pass
class Has_email_work(Has_email, At_work): pass

class Has_web_page(Link):

    def __init__(self, who, uri, comment=None, timestamp=None):
        from sixx.person import Person
        from sixx.family import Family
        from sixx.org import Organisation, Works_at
        from sixx.links import Resides_at
        assert isinstance(who, (Person, Family, Organisation, Works_at,
                                Resides_at))
        assert isinstance(uri, URI)
        assert comment is None or isinstance(comment, str)
        super(Has_web_page, self).__init__(who, uri, timestamp=timestamp)
        self.who = who
        self.uri = uri
        self.comment = comment
