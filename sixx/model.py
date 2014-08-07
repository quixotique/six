# vim: sw=4 sts=4 et fileencoding=latin1 nomod

r'''Data model.
'''

import stackless
import copy
from itertools import chain
from sixx.struct import struct
import sixx.parse as parse
from sixx.multilang import multilang
from sixx.input import InputError
from sixx.world import *
from sixx.node import *
from sixx.node import link_predicate
from sixx.links import *
from sixx.person import *
from sixx.family import *
from sixx.org import *
from sixx.address import *
from sixx.telephone import *
from sixx.email import *
from sixx.keyword import *
from sixx.date import *
from sixx.data import *
from sixx.comment import *

__all__ = ['Model', 'ModelParser', 'In_model', 'is_principal']

class Model(Node):

    r'''The data model consists of a graph (network) of data nodes joined by
    directional links.  Some types of nodes are indexed by the model so they
    can be found by textual search.  Other nodes are intended to be found from
    one or more starting nodes by selectively traversing the graph.

    A data model is populated by a ModelParser.
    '''

    def __init__(self):
        super(Model, self).__init__()
        self.registered = {}
        self.data_keys = {}

    def register(self, node, principal=True):
        r'''Register an object for searching later.  If an equivalent object is
        already registered, then use it instead.
        '''
        typ = type(node)
        if typ not in self.registered:
            reg = self.registered[typ] = dict()
        else:
            reg = self.registered[typ]
        if node in reg:
            node = reg[node]
            link = node.link(outgoing & is_link(In_model))
            assert link.principal == principal
        else:
            reg[node] = node
            In_model(node, self, principal=principal)
        return node

    def _registered(self):
        r'''Iterate over all the registered nodes.
        '''
        for reg in self.registered.itervalues():
            for node in reg.itervalues():
                yield node

    def keyword(self, key):
        r'''Look up a Keyword node in the model.
        '''
        return self.registered[Keyword][Keyword(key)]

    def find(self, typ, text):
        r'''Find a single registered node that matches the given text.
        @return: the single node of the given type that matches the text
        @raise FindError: more than one node matches
        @raise LookupError: no node matches
        '''
        found = None
        for rtyp, objs in self.registered.iteritems():
            if issubclass(rtyp, typ):
                for obj in objs:
                    if obj.matches(text):
                        if found is None:
                            found = obj
                        else:
                            raise FindError('ambiguous %s "%s"' %
                                            (_type_names(typ), text))
        if found is not None:
            return found
        raise LookupError('no such %s "%s"' % (_type_names(typ), text))

    def lookup_place(self, name):
        r'''Return a Place object with the Country or Area node that matches
        the given name.
        '''
        return Place(self.find((Country, Area), name))

def _type_names(typ):
    if type(typ) is type:
        return typ.__name__
    return '/'.join((t.__name__ for t in typ))

class FindError(LookupError):
    r'''A find error is raised by Model.find() if more than one node matches
    the given text.  By raising a distinct exception type, the caller can
    distinguish between that, and the case where no node matches, when
    resolving the reference dependency order.
    '''
    pass

class ModelParser(object):

    r'''A model parser provides methods for compiling text source into a model.
    '''

    def __init__(self, model):
        self.model = model
        self.world = World()
        self.last_country = None
        self.defaults = struct(place=None, keywords=[])
        self.dfactory = {}
        self.dfactory_default = Data_factory_context()
        self.last_dfactory = None
        self._data_block_parsers = []
        self._suspended = set()
        self._no_suspend = False

    def parse_block(self, block):
        r'''Parse a block of lines and add the data to the data model.
        The block is either a "control" block (lines starting with '%') or
        a data block.  Each is handled separately.
        
        Control blocks are parsed immediately, and modify the 'world' and
        'defaults' attributes of the parser.  These attributes are used when
        parsing data blocks.

        Data blocks are parsed by instantiating a new tasklet,
        _parse_data_block, and running it, which either parses until it
        finishes, or suspends itself in the first find() that fails to find a
        node. The tasklet is passed a copy of the 'defaults' struct so that if
        more control blocks are parsed while it is suspended, that will not
        affect it.
        '''

        if parse.is_control_line(block[0]):
            parse.controls(block, {
                'country': self.parse_country,
                'area': self.parse_area,
                'default': self.parse_default,
                'in': self.parse_control_in,
                'data': self.parse_control_data,
            })
        else:
            parser = stackless.tasklet(self._parse_data_block)
            parser.setup(block, copy.copy(self.defaults))
            parser.run()

    def finish_parsing(self):
        r'''Finish parsing all the data blocks that were started by
        parse_block() since the model parser was instantiated, or since the
        last call to finish_parsing().

        All suspended tasklets are awoken, to give them a chance to resolve
        their node references.  If none of them succeed, then it means we must
        have a circular reference, or that the remaining references are just
        incorrect, so we proceed to awaken the tasklets with the '_no_suspend'
        attribute set, which will cause the first one that wakes to raise
        LookupError.
        '''
        while self._suspended:
            retry = self._suspended
            self._suspended = set()
            try:
                hung = len(retry)
                while retry:
                    channel, reason = retry.pop()
                    channel.close()
                    channel.send(None)
                if len(self._suspended) == hung:
                    # This debug can help resolve circular references.
                    #for channel, reason in self._suspended:
                    #    print reason
                    self._no_suspend = True
            finally:
                self._suspended.update(retry)

    def finalise(self):
        r'''Shut down all remaining, suspended tasklets.  This should be done
        before calling sys.exit(), otherwise things could get ugly.
        '''
        while self._suspended:
            self._suspended.pop()[0].send_exception(TaskletExit)

    def find(self, typ, text):
        r'''Call self.model.find() and if it fails to find any node, suspend
        the current tasklet and queue ourselves to be resumed later.
        '''
        while True:
            self._suspend('find(%r, %r)' % (typ, text))
            try:
                return self.model.find(typ, text)
            except FindError, e:
                # Found more than one node - bail out.
                raise
            except LookupError, e:
                # Found no node.  If we are bailing out, then re-raise the
                # exception, otherwise suspend and try again.
                if self._no_suspend:
                    raise 

    def _suspend(self, why=None):
        r'''Suspend the running tasklet until awoken.
        '''
        ch = stackless.channel()
        self._suspended.add((ch, why))
        ch.receive()
        assert ch not in (c for c, w in self._suspended)
        del ch

    def parse_default(self, text):
        r'''Parse a '%default' control line, and update the 'defaults' struct
        of the model accordingly.
        '''
        spl = text.split(None, 1)
        if len(spl) == 2:
            key, value = spl
        else:
            key, value = spl[0], ''
        if key == 'in':
            if not value:
                raise InputError('%default in: missing place or "none"',
                                 line=text)
            if value == 'none':
                self.defaults.place = None
            else:
                self.defaults.place = self.world.parse_place(value)
        elif key == 'key':
            self.defaults.keywords = list(self.split_keywords(value))
        else:
            raise InputError('unsupported %default', char=key)

    def parse_country(self, text):
        r'''Parse a '%country' declaration control line, and add the parsed
        country to the model's 'world' World() object.
        '''
        self.last_country = self.model.register(self.world.parse_country(text))
        Has_country(self.model, self.last_country)
        return self.last_country

    def parse_area(self, text):
        r'''Parse a '%area' declaration control line, and add the parsed area
        to the model's 'world' World() object.
        '''
        if self.last_country is None:
            raise InputError('no preceding country definition', line=text)
        return self.model.register(
                self.world.parse_area(text, self.last_country))

    def parse_control_in(self, text):
        r'''Parse a '%in' control line, which sets the place context for
        subsequent '%data' lines.
        '''
        text = text.rstrip()
        if not text.rstrip().endswith(':'):
            raise InputError('missing colon ":"', char=text[-1])
        text = text[:-1]
        if text == 'none':
            self.last_dfactory = Data_factory_nocontext()
        else:
            place = self.world.parse_place(text)
            self.last_dfactory = Data_factory_place(place)

    def parse_control_data(self, text):
        r'''Parse a '%data' control line, and update the model's dictionary
        that associates a data factory with data id.
        '''
        if self.last_dfactory is None:
            raise InputError('no preceding "%in"', line=text)
        id, value = self.split_data(text)
        if id in self.dfactory:
            raise InputError('duplicate data declaration', line=text)
        self.dfactory[id] = self.last_dfactory

    def _parse_data_block(self, block, defaults):
        r'''Parse a data block.  This callable is invoked as a tasklet by
        parse_block().
        '''
        # Split the block into its parts.
        parts = parse.parts(block)
        for key in parts.iterkeys():
            if key not in ('', '+', '-', '='):
                raise InputError('illegal delimiter', line=key)
        # Identify the "common" part and "member" parts.
        if len(parts) == 1:
            common = parts.itervalues().next()[0]
            members = []
        else:
            assert len(parts) > 1
            if '=' not in parts:
                raise InputError('missing "=" part', line=block[0])
            if len(parts['=']) > 1:
                    raise InputError('duplicate "=" part',
                                     line=parts['='][1].delim)
            common = parts['='][0]
            members = parts.get('', []) + parts.get('+', []) + \
                      parts.get('-', [])
            members.sort(key=lambda part: part.loc())
        # Wrap the dataset parts in dataset_loc_memo obects, which remember
        # the values we have fetched so that we can report any unused lines
        # at the end of parsing this block.
        common = parse.dataset_loc_memo(common)
        members = [parse.dataset_loc_memo(p) for p in members]
        # Parse the 'in' and 'upd' lines and add 'defaults, 'place' and
        # 'updated' attributes in all the parts and sub-parts thereof.
        self.prepare(common, defaults)
        seq = 0
        for member in members:
            seq += 1
            member.sequence = seq
            self.prepare(member, defaults, common.updated)
        # Now handle the specific cases.  If there is a single "member"
        # part and a "common" part, then the member part must define a
        # person, and the common part must define an organisation
        # (one-person families don't make sense).  Otherwise, if there is
        # only a single "common" part, then it defines either a single
        # person, or an organisation, or a combination of both, or a
        # residence.  If there is more than one "member" part, then the
        # "common" part must define an organisation, or else it is taken to
        # define a family.
        if len(members) == 0:
            # "common" could be a company or department, or person, or both, or
            # if neither then it must define a residence.  Never a family.
            org = self.parse_company_or_dept(common, optional=True)
            per = self.parse_person(common, optional=True, with_aka=not org,
                                    principal=False if org else True)
            if org:
                self.parse_residences(common, org)
            elif per:
                self.parse_residences(common, per)
            # Now that all the named nodes are registered, we can parse contact
            # details (which might suspend in find()).
            if org:
                self.parse_org_con(common, org)
                if per:
                    self.parse_works_at(common, per, org)
                else:
                    self.parse_org_extra(common, org)
            elif per:
                self.parse_contacts_work(common, per)
            else:
                res = self.parse_ad(common, common.getvalue('ad'))
                self.parse_con(common, res, 'ph', Telephone, Has_fixed)
                self.parse_con(common, res, 'fax', Telephone, Has_fax)
                self.parse_con(common, res, 'com', Comment, Has_comment)
            # Parse a person's contact details after he or she has been
            # associated with the company, because the "Works_at" link may help
            # determine the person's place.  Or may not.
            if per:
                self.parse_person_con(common, per, org)
        elif len(members) == 1:
            # "Common" must be a company or department.  "Members[0]" must be a
            # person and/or department (if common is not a department).
            org = self.parse_company_or_dept(common, optional=False)
            self.parse_residences(common, org)
            dept = None
            if not isinstance(org, Department):
                dept = self.parse_dept(members[0], org, optional=True,
                                       with_aka=True)
            per = self.parse_person(members[0], optional=bool(dept),
                                    principal=members[0].delim == '+',
                                    with_aka=not dept)
            if dept:
                self.parse_residences(members[0], dept)
            elif per:
                self.parse_residences(members[0], per)
            # Now that all the named nodes are registered, we can parse contact
            # details (which might suspend in find()).
            self.parse_org_con(common, org)
            self.parse_org_extra(common, org)
            if dept:
                self.parse_org_con(members[0], dept)
            if per:
                self.parse_works_at(members[0], per, dept or org)
                self.parse_person_con(members[0], per, dept)
            else:
                assert dept
                self.parse_org_extra(members[0], dept)
        else:
            # If more than one person, if "common" is not a company or
            # department then it must be a family.  If it is a company, then
            # each member part must define either a person and/or department.
            # If it is a department, then each member must define a person.  If
            # a family, then each member part must define a person.
            org = self.parse_company_or_dept(common, optional=True)
            if org:
                self.parse_residences(common, org)
            else:
                aka = map(multilang.optparse, common.mgetvalue('aka', []))
                fam = Family(aka=aka)
                self.parse_residences(common, fam)
            for member in members:
                member.dept = None
                if org and not isinstance(org, Department):
                    member.dept = self.parse_dept(member, org, optional=True,
                                                  with_aka=True)
                member.person = self.parse_person(member,
                                                  optional=bool(member.dept),
                                                  principal=member.delim != '-',
                                                  with_aka=not member.dept)
                if not org:
                    assert member.person
                    assert not member.dept
                    Belongs_to(member.person, fam,
                               is_head=member.delim != '-',
                               sequence=member.sequence,
                               timestamp=member.updated or common.updated)
                self.parse_residences(member, member.dept or member.person)
            # We register a Family object only after all members have been
            # linked with Belongs_to, because the result of Family.matches(),
            # which is invoked through find(), depends on the members, and if
            # we registered it earlier, then it could potentially match where
            # it shouldn't.
            if not org:
                self.model.register(fam)
            # Now that all the named nodes are registered, we can parse contact
            # details (which might suspend in find()).
            if org:
                self.parse_org_con(common, org)
                self.parse_org_extra(common, org)
            else:
                self.parse_family_con(common, fam)
            for member in members:
                if member.dept:
                    self.parse_org_con(member, member.dept)
                if org:
                    if member.person:
                        self.parse_works_at(member, member.person,
                                            member.dept or org)
                    else:
                        assert member.dept
                        self.parse_org_extra(member, member.dept)
                else:
                    self.parse_contacts_work(member, member.person)
                self.parse_person_con(member, member.person, member.dept)
        # Now find lines that were not parsed, and complain about them.
        missed = set()
        for part in chain([common], members):
            missed |= set(part.all_locs()) - part.memo
        for loc in sorted(missed):
            raise InputError('spurious line', line=loc)

    def prepare(self, part, defaults, default_updated=None):
        r'''Parse 'in' and 'upd' fields in the given part and all sub-parts,
        and assign the results to the 'updated' and 'place' attributes of all
        those parts.
        '''
        part.defaults = defaults
        part.updated = self.parse_update(part) or default_updated
        part.place = None
        found_in = False
        if 'in' in part:
            for value, sub in part.mget('in'):
                place = self.world.parse_place(value)
                if sub:
                    sub.defaults = defaults
                    sub.place = place
                    sub.updated = self.parse_update(sub) or part.updated
                elif found_in:
                    raise InputError('duplicate "in"', line=value)
                else:
                    part.place = place
                    found_in = True

    def parse_company_or_dept(self, part, optional=False):
        r'''Parse a company and/or any department thereof.
        '''
        company = None
        if 'co' in part:
            name = multilang.optparse(part.getvalue('co'))
            aka = map(multilang.optparse, part.mgetvalue('aka', []))
            # The preferred name is the one that appears first in the input.
            prefer = sorted([name] + aka, key=lambda s: s.loc())[0]
            company = self.model.register(Company(name=name, aka=aka,
                                                  prefer=prefer))
            company.place = part.place
        dept = self.parse_dept(part, company, optional=company or optional,
                               with_aka=not company)
        org = dept or company
        if not org and not optional:
            raise InputError('missing company or department', line=part)
        return org

    def parse_dept(self, part, company=None, optional=False, with_aka=False):
        r'''Parse a department and connect it to its parent organisation.
        '''
        if optional and 'de' not in part and 'de-' not in part:
            return None
        if 'de' in part:
            name = multilang.optparse(part.getvalue('de'))
            is_head = True
        else:
            name = multilang.optparse(part.getvalue('de-'))
            is_head = False
        aka = []
        if with_aka:
            aka = map(multilang.optparse, part.mgetvalue('aka', []))
        prefer = sorted([name] + aka, key=lambda s: s.loc())[0]
        dept = self.model.register(Department(name=name, aka=aka,
                                              prefer=prefer))
        dept.place = part.place
        if not company:
            company = self.find(Company, part.getvalue('of'))
        try:
            Has_department(company, dept, is_head=is_head)
        except ValueError, e:
            raise InputError(e, line=name)
        return dept

    def parse_org_con(self, part, org):
        r'''Parse contact details that may be associated with an organisation
        (company or department), skipping those that could pertain to a person,
        just in case this part also defines a person.  If it doesn't, then the
        details we skip now will be parsed later in parse_org_extra().
        '''
        # First, parse details that can provide place context when parsing
        # telephone numbers.
        self.parse_homes(part, org)
        self.parse_locations(part, org)
        self.parse_con(part, org, 'po', PostalAddress, Has_postal_address)
        # Now parse the various contact details - phone/fax numbers, email
        # addresses, web pages, etc.  We DON'T parse mobile phone numbers here,
        # because if this part is shared with a person, then the mobile number,
        # if present, gets parsed when parsing the person, and associated with
        # the resultant Person object.  The mobile number, if it pertains to
        # the organisation, gets parsed later in parse_org_extra().
        self.parse_con(part, org, 'ph', Telephone, Has_fixed)
        self.parse_con(part, org, 'fax', Telephone, Has_fax)
        self.parse_con(part, org, 'em', Email, Has_email)
        self.parse_con(part, org, 'www', URI, Has_web_page)
        # Now parse 'data' and keywords, which take advantage of the place
        # context provided by residence and phone numbers already parsed.
        self.parse_con(part, org, 'com', Comment, Has_comment)
        self.parse_data(part, org)
        self.parse_assoc(part, org, 'with', NamedNode, With, self.parse_assoc_contacts)
        self.parse_assoc(part, org, 'ex', NamedNode, Ex, self.parse_assoc_contacts)
        self.parse_keywords(part, org)
        # Parse any 'in' sub-parts.
        for sub in (s for v, s in part.mget('in', []) if s):
            self.parse_homes(sub, org)
            self.parse_locations(sub, org)
            self.parse_con(sub, org, 'po', PostalAddress, Has_postal_address)
            self.parse_con(sub, org, 'ph', Telephone, Has_fixed_home)
            self.parse_con(sub, org, 'fax', Telephone, Has_fax_home)
            self.parse_data(sub, org)
        return org

    def parse_org_extra(self, part, org):
        r'''Parse remaining contact details that were omitted in parse_org(),
        which could have pertained to a person, but a person was not defined so
        they pertain to the organisation itself.
        '''
        self.parse_con(part, org, 'mob', Telephone, Has_mobile)
        for sub in (s for v, s in part.mget('in', []) if s):
            self.parse_con(sub, org, 'mob', Telephone, Has_mobile_home)

    def parse_family_con(self, part, fam):
        r'''Parse a family's contact details.
        '''
        self.parse_homes(part, fam)
        self.parse_con(part, fam, 'phh', Telephone, Has_fixed_home)
        self.parse_con(part, fam, 'faxh', Telephone, Has_fax_home)
        self.parse_con(part, fam, 'ph', Telephone, Has_fixed)
        self.parse_con(part, fam, 'fax', Telephone, Has_fax)
        # Parse contact details that don't go with the residence.
        self.parse_con(part, fam, 'po', PostalAddress, Has_postal_address)
        self.parse_con(part, fam, 'mob', Telephone, Has_mobile_home)
        self.parse_con(part, fam, 'em', Email, Has_email_home)
        self.parse_con(part, fam, 'www', URI, Has_web_page)
        self.parse_con(part, fam, 'com', Comment, Has_comment)
        self.parse_data(part, fam)
        self.parse_assoc(part, fam, 'with', NamedNode, With, self.parse_assoc_contacts)
        self.parse_assoc(part, fam, 'ex', NamedNode, Ex, self.parse_assoc_contacts)
        self.parse_keywords(part, fam)
        # Parse any 'in' sub-parts.
        for sub in (s for v, s in part.mget('in', []) if s):
            self.parse_homes(sub, fam)
            self.parse_con(sub, fam, 'po', PostalAddress, Has_postal_address)
            self.parse_con(sub, fam, 'mob', Telephone, Has_mobile_home)
            self.parse_con(sub, fam, 'ph', Telephone, Has_fixed_home)
            self.parse_con(sub, fam, 'fax', Telephone, Has_fax_home)
            self.parse_data(sub, fam)
        return fam

    def parse_person(self, part, optional=False, with_aka=False,
                                 principal=True):
        r'''Parse a person's name and other details into a Person node.
        '''
        pn = Person.initargs(part)
        if not pn:
            if optional:
                return None
            raise InputError('missing person', line=part)
        aka = None
        if with_aka:
            aka = map(multilang.optparse, part.mgetvalue('aka', []))
        per = self.model.register(Person.from_initargs(pn, aka=aka),
                                  principal=principal)
        # Birthday.
        if 'bd' in part:
            birthday, year = Birthday.parse(part.getvalue('bd'))
            birthday = self.model.register(birthday)
            Born_on(per, birthday, year=year)
        return per

    def parse_person_con(self, part, per, org=None):
        r'''Parse a person's contact details and attach them to a given Person
        node.
        @param org: if not None, then 'part' also defines an Organisation, so
            skip those contact details which pertain to the organisation (so we
            don't parse them twice)
        '''
        # First, parse details that provide place context when parsing
        # telephone numbers.  If this part is also used to declare an
        # organisation, then the 'po' lines pertain to the organisation so we
        # don't parse them here.
        if not org:
            self.parse_homes(part, per)
            self.parse_con(part, per, 'po', PostalAddress, Has_postal_address)
        # Now parse the various contact details - phone/fax/mobile numbers,
        # email addresses, web pages, etc.  If this part is also used to
        # declare an organisation, then the unadorned 'ph', 'fax', etc. lines
        # pertain to the organisation, so instead we parse 'phh', 'faxh', etc.
        self.parse_con(part, per, 'mob', Telephone, Has_mobile)
        self.parse_con(part, per, 'phh', Telephone, Has_fixed_home)
        self.parse_con(part, per, 'faxh', Telephone, Has_fax_home)
        self.parse_con(part, per, 'emh', Email, Has_email_home)
        self.parse_con(part, per, 'wwwh', URI, Has_web_page)
        if not org:
            self.parse_con(part, per, 'ph', Telephone, Has_fixed)
            self.parse_con(part, per, 'fax', Telephone, Has_fax)
            self.parse_con(part, per, 'em', Email, Has_email)
            self.parse_con(part, per, 'www', URI, Has_web_page)
        # Now parse 'data', 'key', and associations, which take advantage of
        # the place context provided by residence and phone numbers already
        # parsed.
        if not org:
            self.parse_con(part, per, 'com', Comment, Has_comment)
            self.parse_data(part, per)
            self.parse_keywords(part, per)
            # Parse any 'work', 'work-', 'with', and 'ex' sub-parts.  The
            # 'work-' variant does not make the person a head of the
            # organisation they work for.
            self.parse_assoc(part, per, 'work', (Organisation, Residence),
                             Works_at, self.parse_assoc_contacts_work,
                             is_head=True)
            self.parse_assoc(part, per, 'work-', (Organisation, Residence),
                             Works_at, self.parse_assoc_contacts_work,
                             is_head=False)
            self.parse_assoc(part, per, 'with', NamedNode, With,
                             self.parse_assoc_contacts)
            self.parse_assoc(part, per, 'ex', NamedNode, Ex,
                             self.parse_assoc_contacts)
        # Parse any 'in' sub-parts.
        for sub in (s for v, s in part.mget('in', []) if s):
            self.parse_con(sub, per, 'mob', Telephone, Has_mobile)
            self.parse_con(sub, per, 'phh', Telephone, Has_fixed_home)
            self.parse_con(sub, per, 'faxh', Telephone, Has_fax_home)
            if not org:
                self.parse_homes(sub, per)
                self.parse_con(sub, per, 'po', PostalAddress, Has_postal_address)
                self.parse_con(sub, per, 'ph', Telephone, Has_fixed_home)
                self.parse_con(sub, per, 'fax', Telephone, Has_fax_home)
                self.parse_data(sub, per)

    def parse_works_at(self, part, who, org):
        r'''Create a Works_at association between a person and organisation,
        and parse comment, keyword, and work contact details that pertain to
        the association link.  This method is used when the works-at
        relationship is implicit (ie, not explicitly defined with a 'work'
        line), so the link does not have its own sub-part to contain contact
        and other details.  Whether or not the person is a head of the
        organisation is derived from the part's delimiter, in make_assoc().
        '''
        wat = self.make_assoc(part, who, org, Works_at)
        self.parse_con(part, wat, 'comw', Comment, Has_comment)
        if 'keyw' in part:
            for text in part.mgetvalue('keyw'):
                for keyword in self.split_keywords(text):
                    self.add_keyword(wat, keyword, part)
        self.parse_contacts_work(part, wat)
        return wat

    def parse_contacts_work(self, part, who):
        r'''Parse work-only contact details.
        '''
        self.parse_con(part, who, 'pow', PostalAddress, Has_postal_address)
        self.parse_con(part, who, 'mobw', Telephone, Has_mobile_work)
        self.parse_con(part, who, 'phw', Telephone, Has_fixed_work)
        self.parse_con(part, who, 'faxw', Telephone, Has_fax_work)
        self.parse_con(part, who, 'emw', Email, Has_email_work)

    def parse_assoc(self, part, who, key, ntype, ltype, parse_sub=None,
                          is_head=None):
        r'''Parse an association line, look up the referred node, and link it
        to a given node with an Association link or subclass thereof.  Parse
        any contact details, keywords, data, and comments that pertain to the
        association.
        '''
        if key in part:
            for name, sub in part.mget(key):
                try:
                    oth = self.find(ntype, name)
                except LookupError, e:
                    raise InputError(e, char=name)
                if sub:
                    sub.updated = self.parse_update(sub) or part.updated
                    sub.place = part.place
                    sub.defaults = copy.copy(part.defaults)
                    sub.defaults.keywords = []
                ass = self.make_assoc(sub, who, oth, ltype,
                                      timestamp=(sub or part).updated,
                                      is_head=is_head)
                if sub:
                    if parse_sub:
                        parse_sub(sub, ass)
                    self.parse_keywords(sub, ass)
                    self.parse_data(sub, ass)
                    self.parse_con(sub, ass, 'com', Comment, Has_comment)

    def make_assoc(self, part, who, oth, ltype, timestamp=None, is_head=None):
        r'''Create an Associate_with link (or subtype) between two nodes,
        with suitable constructor data.
        '''
        assert issubclass(ltype, Association)
        # Here we introspect the keyword args accepted by ltype's constructor
        # and adapt accordingly.
        kw = {'timestamp': timestamp}
        if is_head is not None:
            kw['is_head'] = is_head
        if part:
            import inspect
            kwa = dict.fromkeys(inspect.getargspec(ltype.__init__)[0])
            if ('is_head' in kwa and hasattr(part, 'delim') and
                'is_head' not in kw):
                kw['is_head'] = part.delim != '-'
            if 'sequence' in kwa and hasattr(part, 'sequence'):
                kw['sequence'] = part.sequence
            if 'position' in kwa and 'pos' in part:
                kw['position'] = multilang.optparse(part.getvalue('pos'))
        return ltype(who, oth, **kw)

    def parse_assoc_contacts(self, part, ass):
        r'''Callback to pass to parse_assoc(), which parses contact details
        for a generic association.
        '''
        self.parse_con(part, ass, 'mob', Telephone, Has_mobile)
        self.parse_con(part, ass, 'ph', Telephone, Has_fixed)
        self.parse_con(part, ass, 'fax', Telephone, Has_fax)
        self.parse_con(part, ass, 'em', Email, Has_email)

    def parse_assoc_contacts_work(self, part, ass):
        r'''Callback to pass to parse_assoc(), which parses contact details
        for a person-organisation Works_at association.
        '''
        self.parse_con(part, ass, 'po', PostalAddress, Has_postal_address)
        self.parse_con(part, ass, 'pow', PostalAddress, Has_postal_address)
        self.parse_con(part, ass, 'mobw', Telephone, Has_mobile_work)
        self.parse_con(part, ass, 'phw', Telephone, Has_fixed_work)
        self.parse_con(part, ass, 'faxw', Telephone, Has_fax_work)
        self.parse_con(part, ass, 'emw', Email, Has_email_work)
        self.parse_con(part, ass, 'mob', Telephone, Has_mobile_work)
        self.parse_con(part, ass, 'ph', Telephone, Has_fixed_work)
        self.parse_con(part, ass, 'fax', Telephone, Has_fax_work)
        self.parse_con(part, ass, 'em', Email, Has_email_work)
        # Parse 'data' and keywords, which take advantage of the place context
        # provided by residence and phone numbers already parsed.
        self.parse_con(part, ass, 'com', Comment, Has_comment)
        self.parse_data(part, ass)
        self.parse_assoc(part, ass, 'with', NamedNode, With)
        self.parse_assoc(part, ass, 'ex', NamedNode, Ex)
        self.parse_keywords(part, ass)

    def parse_con(self, part, who, key, ntype, ltype):
        r'''Parse a contact line and attach it to a given node.
        '''
        if key in part:
            for text in part.mgetvalue(key):
                obj, comment = ntype.parse(text,
                                           place=part.place,
                                           world=self.world,
                                           default_place=who.only_place() or
                                                         part.defaults.place)
                kw = {}
                if comment:
                    kw['comment'] = comment
                if part.updated:
                    kw['timestamp'] = part.updated
                ltype(who, obj, **kw)

    def parse_residences(self, part, who=None):
        r'''Parse 'ad' lines which define one or more residences (optionally
        with contact details), and descend into 'in' sections doing the same.
        If given a reference to a Person, Family, or Organisation in 'who' then
        link it (Resides_at) to each defined residence.
        '''
        for value, sub in part.mget('ad', []):
            res = self.parse_ad(part, value, sub)
            if who:
                Resides_at(who, res, timestamp=(sub or part).updated)
        for insub in (s for v, s in part.mget('in', []) if s):
            for value, sub in insub.mget('ad', []):
                res = self.parse_ad(part, value, sub)
                if who:
                    Resides_at(who, res, timestamp=(sub or part).updated)

    def parse_ad(self, part, value, sub=None):
        res, comment = Residence.parse(value,
                               world=  self.world,
                               place=  part.place,
                               default_place=part.defaults.place)
        assert comment is None
        res = self.model.register(res)
        if sub:
            # Parse contact details for this residence - phone/fax
            # numbers.
            sub.place = res.only_place()
            sub.updated = self.parse_update(sub) or part.updated
            sub.defaults = part.defaults
            self.parse_con(sub, res, 'ph', Telephone, Has_fixed)
            self.parse_con(sub, res, 'fax', Telephone, Has_fax)
            self.parse_con(sub, res, 'com', Comment, Has_comment)
        return res

    def parse_homes(self, part, who):
        r'''Parse 'home' lines for a person, family or organisation, which
        define one or more residences (optionally with contact details) for
        that person/organisation.
        '''
        for value, sub in part.mget('home', []):
            try:
                res = self.find(Residence, value)
            except LookupError, e:
                raise InputError(e, char=value)
            if sub:
                sub.place = res.only_place()
                sub.updated = self.parse_update(sub) or part.updated
                sub.defaults = part.defaults
            r = Resides_at(who, res, timestamp=(sub or part).updated)
            if sub:
                self.parse_con(sub, r, 'ph', Telephone, Has_fixed)
                self.parse_con(sub, r, 'fax', Telephone, Has_fax)
                self.parse_con(sub, r, 'com', Comment, Has_comment)

    def parse_locations(self, part, who):
        r'''Parse 'loc' lines for an organisation, which define the host
        residences (optionally with contact details) for that organisation.
        '''
        for value, sub in part.mget('loc', []):
            try:
                host = self.find(Organisation, value)
            except LookupError, e:
                raise InputError(e, char=value)
            if sub:
                sub.place = host.only_place()
                sub.updated = self.parse_update(sub) or part.updated
                sub.defaults = part.defaults
            r = Located_at(who, host, timestamp=(sub or part).updated)
            if sub:
                self.parse_con(sub, r, 'ph', Telephone, Has_fixed)
                self.parse_con(sub, r, 'fax', Telephone, Has_fax)
                self.parse_con(sub, r, 'com', Comment, Has_comment)

    def parse_keywords(self, part, node):
        r'''Parse 'key' lines in a given part, dereferencing and creating
        Keyword nodes for each keyword parsed, and attaching the given node
        (person, organisation, Works_at, etc.) to each such Keyword node.
        '''
        omit = set()
        if 'key-' in part:
            for text in part.mgetvalue('key-'):
                for keyword in self.split_keywords(text):
                    omit.add(keyword)
        for keyword in part.defaults.keywords:
            if keyword not in omit:
                if not node.link(outgoing & is_link(Keyed_with) &
                                to_node(keyword)):
                    Keyed_with(node, keyword, timestamp=part.updated)
        if 'key' in part:
            for text in part.mgetvalue('key'):
                for keyword in self.split_keywords(text):
                    if keyword not in omit:
                        self.add_keyword(node, keyword, part)

    def add_keyword(self, node, keyword, part=None):
        r'''Link the given Keyword to the given Node, if not already linked.
        Take the timestamp and any other context from the part which gave rise
        to the link.  Return the Link which was found or created.
        '''
        link = node.link(outgoing & is_link(Keyed_with) & to_node(keyword))
        if not link:
            link = Keyed_with(node, keyword,
                              timestamp= part.updated if part else None)
        return link

    def split_keywords(self, text):
        r'''Parse a string contining zero or more keywords and iterate over the
        resultant Keyword objects.
        '''
        for word in text.split():
            keyword, rem = Keyword.parse(word)
            assert rem is None
            yield self.model.register(keyword)

    def parse_update(self, part):
        r'''Parse the 'upd' line in a part, and return a corresponding
        datatime.date object.
        '''
        if 'upd' not in part:
            return None
        try:
            return Datetime.parse(part.getvalue('upd')).as_date()
        except ValueError, e:
            raise InputError(e, char=part.getvalue('upd'))

    def parse_data(self, part, who):
        r'''Parse a 'data' line and create a Data object using the data factory
        that corresponds to the parsed id string.
        '''
        if 'data' in part:
            for text in part.mgetvalue('data'):
                id, value = self.split_data(text)
                if value is None:
                    raise InputError('missing "="', char=text)
                dat = self.dfactory.get(id, self.dfactory_default)\
                                       (part, who, id, value)
                if dat.key() in self.model.data_keys:
                    raise InputError('duplicate data %r for %s (%s)' %
                                     (id, who, context), char=text)
                self.model.data_keys[dat.key()] = dat

    def split_data(self, text):
        r'''Partially parse a 'data' or '%data' line into an id string and
        value.
        '''
        spl = text.split('=', 1)
        id = spl[0].rstrip()
        value = spl[1].lstrip() if len(spl) == 2 else None
        return id, value

class In_model(Link):

    r'''All nodes that are registered in a Model are linked to the model's top
    node by an 'In_model' link, which then enables the selection of registered
    nodes using the standard Node.nodes(), Node.find_nodes() methods, etc.
    '''

    def __init__(self, node, model, principal=True):
        assert isinstance(model, Model)
        super(In_model, self).__init__(node, model)
        self.node = node
        self.model = model
        self.principal = principal

    def only_place(self):
        return self.node.only_place()

@link_predicate
def is_principal(link):
    r'''A Model.nodes() and Model.links() predicate that selects only links
    that are principal links in the model.
    '''
    return isinstance(link, In_model) and link.principal
