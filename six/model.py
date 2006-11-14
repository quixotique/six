# vim: sw=4 sts=4 et fileencoding=latin1 nomod

r'''Data model.
'''

import stackless
import copy
from itertools import chain
from six.struct import struct
import six.parse as parse
from six.multilang import multilang
from six.world import World
from six.input import InputError
from six.node import *
from six.node import link_predicate
from six.links import *
from six.person import *
from six.family import *
from six.org import *
from six.address import *
from six.telephone import *
from six.email import *
from six.keyword import *
from six.date import *
from six.data import *
from six.comment import *

__all__ = ['Model', 'In_model', 'is_principal']

class Model(Node):

    r'''The data model consists of a world model (countries and areas) plus a
    graph (network) of data nodes joined by directional links.  Some types of
    nodes are indexed by the model so they can be found by textual search.
    Other nodes are intended to be found from one or more starting nodes by
    selectively traversing the graph.
    '''

    def __init__(self):
        super(Model, self).__init__()
        self.world = World()
        self.last_country = None
        self.defaults = struct(place=None, keywords=[])
        self.registered = {}
        self.data_keys = {}
        self._suspended = set()
        self._no_suspend = False
        self.dfactory = {}
        self.dfactory_default = Data_factory_context()
        self.last_dfactory = None

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
        r'''Find a single registered node that matches the given text.  If none
        is found, but parsing is not yet complete, then suspend the calling
        tasklet, and try again when woken.  If the `_no_suspend` attribute is
        true, it means that tasklets are being shut down, so instead of
        suspending, we raise LookupError.
        '''
        while True:
            found = None
            for rtyp, objs in self.registered.iteritems():
                if issubclass(rtyp, typ):
                    for obj in objs:
                        if obj.matches(text):
                            if not found:
                                found = obj
                            else:
                                if type(typ) is type:
                                    what = typ.__name__
                                else:
                                    what = '/'.join((t.__name__ for t in typ))
                                raise LookupError('ambiguous %s "%s"' %
                                                  (what, text))
            if found:
                return found
            if self._no_suspend:
                if type(typ) is type:
                    what = typ.__name__
                else:
                    what = '/'.join((t.__name__ for t in typ))
                raise LookupError('no such %s "%s"' % (what, text))
            ch = stackless.channel()
            self._suspended.add(ch)
            ch.receive()
            assert ch not in self._suspended
            del ch

    def parse_block(self, block):
        r'''Parse a block of lines and add the data to this data model.
        The block is either a "control" block (lines starting with '%') or
        a data block.  Each is handled separately.
        
        Control blocks are parsed immediately, and modify the 'world' and
        'defaults' attributes of the model.  These attributes are used when
        parsing data blocks.

        Data blocks are parsed each in its own tasklet.  If, during parsing, a
        reference to a node from another data block cannot be resolved (see the
        Model.find() method) then the tasklet is suspended until later blocks
        have been parsed.  This neatly resolves forward references.  The
        tasklet is passed a copy of the 'defaults' attribute so that if more
        control blocks are parsed while it is suspended, that will not affect
        it.
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
            task = stackless.tasklet(self._parse_data_block)
            task.setup(block, copy.copy(self.defaults))
            task.run()

    def finish_parsing(self):
        r'''Perform post-parsing cleanup.  After this, the parse_block() method
        should not be invoked.  All suspended tasklets are awoken, to give them
        a chance to resolve their node references.  If none of them succeed,
        then it means we must have a circular reference, or that the remaining
        references are just incorrect, so we proceed to awaken the tasklets
        with the '_no_suspend' attribute set, which will cause the first one
        that wakes to raise LookupError.
        '''
        while self._suspended:
            retry = self._suspended
            self._suspended = set()
            hung = len(retry)
            while retry:
                retry.pop().send(None)
            if len(self._suspended) == hung:
                self._no_suspend = True

    def finalise(self):
        r'''Shut down all remaining, suspended tasklets.  This should be done
        before calling sys.exit(), otherwise things could get ugly.
        '''
        while self._suspended:
            self._suspended.pop().send_exception(TaskletExit)

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
        self.last_country = self.world.parse_country(text)
        return self.last_country

    def parse_area(self, text):
        r'''Parse a '%area' declaration control line, and add the parsed area
        to the model's 'world' World() object.
        '''
        if self.last_country is None:
            raise InputError('no preceding country definition', line=text)
        return self.world.parse_area(text, self.last_country)

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
                raise InputError('missing "=" part', line=parts[''][0])
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
            # "common" could be a company, or person, or both, or if
            # neither then it must define a residence.  Never a family.
            org = self.parse_org(common, optional=True)
            per = self.parse_person(common, optional=True,
                                    principal=False if org else True)
            if org:
                self.parse_org_con(common, org)
                if per:
                    self.parse_works_at(common, per, org)
                else:
                    self.parse_org_extra(common, org)
            elif per:
                self.parse_contacts_work(common, per)
            else:
                res = self.parse_residences(common)
                if res:
                    self.parse_con(common, res, 'ph', Telephone, Has_fixed)
                    self.parse_con(common, res, 'fax', Telephone, Has_fax)
                    self.parse_con(common, res, 'com', Comment, Has_comment)
            # Parse a person's contact details after he or she has been
            # associated with the company, because the "Works_at" link may help
            # determine the person's place.  Or may not.
            if per:
                self.parse_person_con(common, per, org)
        elif len(members) == 1:
            # "Common" must be a company.  "Members[0]" must be a
            # person and/or department.
            org = self.parse_org(common, optional=False)
            self.parse_org_con(common, org)
            self.parse_org_extra(common, org)
            dept = self.parse_dept(members[0], optional=True)
            if dept:
                Has_department(org, dept)
                self.parse_org_con(members[0], dept)
            per = self.parse_person(members[0], optional=bool(dept),
                                    principal=members[0].delim == '+')
            if per:
                self.parse_works_at(members[0], per, dept or org)
                self.parse_person_con(members[0], per, dept)
            else:
                assert dept
                self.parse_org_extra(members[0], dept)
        else:
            # If more than one person, if "common" is not a company then it
            # must be a family.  If it is a company, then each member parts may
            # define a person and/or department.  If a family, then each member
            # part may only define a person.
            org = self.parse_org(common, optional=True)
            if org:
                self.parse_org_con(common, org)
                self.parse_org_extra(common, org)
            else:
                fam = self.parse_family(common)
            for member in members:
                dept = None
                if org:
                    dept = self.parse_dept(member, optional=True)
                    if dept:
                        Has_department(org, dept)
                        self.parse_org_con(member, dept)
                per = self.parse_person(member, optional=bool(dept),
                                        principal=member.delim != '-')
                if org:
                    if per:
                        self.parse_works_at(member, per, dept or org)
                    else:
                        assert dept
                        self.parse_org_extra(member, dept)
                else:
                    assert per
                    assert not dept
                    Belongs_to(per, fam,
                               is_head=member.delim != '-',
                               sequence=member.sequence,
                               timestamp=member.updated or common.updated)
                    self.parse_contacts_work(member, per)
                self.parse_person_con(member, per, dept)

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

    def parse_org(self, part, optional=False):
        r'''Parse an organisation (company) and any department thereof.
        '''
        if optional and 'co' not in part:
            return None
        name = part.getvalue('co')
        aka = part.mgetvalue('aka', [])
        prefer = sorted([name] + aka, key=lambda s: s.loc())[0]
        org = self.register(Company(name=name, aka=aka, prefer=prefer))
        dept = self.parse_dept(part, org=org, optional=True)
        if dept:
            Has_department(org, dept)
            org = dept
        return org

    def parse_dept(self, part, org=None, optional=False):
        r'''Parse a department.
        '''
        if optional and 'de' not in part:
            return None
        name = part.getvalue('de')
        aka = part.mgetvalue('aka', []) if not org else []
        prefer = sorted([name] + aka, key=lambda s: s.loc())[0]
        return self.register(Department(name=name, aka=aka, prefer=prefer))

    def parse_org_con(self, part, org):
        r'''Parse contact details that may be associated with an organisation
        (company or department), skipping those that could pertain to a person,
        just in case this part also defines a person.  If it doesn't, then the
        details we skip now will be parsed later in parse_org_extra().
        '''
        # First, parse residences that can provide place context when parsing
        # telephone numbers.
        self.parse_residences(part, org)
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
        self.parse_assoc(part, org, 'with', NamedNode, Associated_with,
                         self.parse_assoc_contacts)
        self.parse_assoc(part, org, 'ex', NamedNode, Ex,
                         self.parse_assoc_contacts)
        self.parse_keywords(part, org)
        # Parse any 'in' sub-parts.
        for sub in (s for v, s in part.mget('in', []) if s):
            res = self.parse_residences(sub, org)
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

    def parse_family(self, part):
        r'''Parse a family and its associated contact details.
        '''
        fam = self.register(Family())
        res = self.parse_residences(part, fam)
        self.parse_con(part, res or fam, 'phh', Telephone, Has_fixed_home)
        self.parse_con(part, res or fam, 'faxh', Telephone, Has_fax_home)
        self.parse_con(part, res or fam, 'ph', Telephone, Has_fixed)
        self.parse_con(part, res or fam, 'fax', Telephone, Has_fax)
        # Parse contact details that don't go with the residence.
        self.parse_con(part, fam, 'po', PostalAddress, Has_postal_address)
        self.parse_con(part, fam, 'mob', Telephone, Has_mobile_home)
        self.parse_con(part, fam, 'em', Email, Has_email_home)
        self.parse_con(part, fam, 'www', URI, Has_web_page)
        self.parse_con(part, fam, 'com', Comment, Has_comment)
        self.parse_data(part, fam)
        self.parse_assoc(part, fam, 'with', NamedNode, Associated_with,
                         self.parse_assoc_contacts)
        self.parse_assoc(part, fam, 'ex', NamedNode, Ex,
                         self.parse_assoc_contacts)
        self.parse_keywords(part, fam)
        # Parse any 'in' sub-parts.
        for sub in (s for v, s in part.mget('in', []) if s):
            res = self.parse_residences(sub, fam)
            if res:
                self.parse_con(part, res, 'ph', Telephone, Has_fixed)
                self.parse_con(part, res, 'fax', Telephone, Has_fax)
            self.parse_con(sub, fam, 'po', PostalAddress, Has_postal_address)
            self.parse_con(sub, fam, 'mob', Telephone, Has_mobile_home)
            self.parse_con(sub, fam, 'ph', Telephone, Has_fixed_home)
            self.parse_con(sub, fam, 'fax', Telephone, Has_fax_home)
            self.parse_data(sub, fam)
        return fam

    def parse_person(self, part, optional=False, principal=True):
        r'''Parse a person's name and other details into a Person node.
        '''
        pn = Person.initargs(part)
        if not pn:
            if optional:
                return None
            raise InputError('missing person', line=part)
        per = self.register(Person.from_initargs(pn), principal=principal)
        # Birthday.
        if 'bd' in part:
            birthday, year = Birthday.parse(part.getvalue('bd'))
            birthday = self.register(birthday)
            Born_on(per, birthday, year=year)
        return per

    def parse_person_con(self, part, per, org=None):
        r'''Parse a person's contact details and attach them to a given Person
        node.
        @param org: if not None, then 'part' also defines an Organisation, so
            skip those contact details which pertain to the organisation (so we
            don't parse them twice)
        '''
        # First, parse residences that can provide place context when parsing
        # telephone numbers.  If this part is also used to declare an
        # organisation, then the 'ad' and 'po' lines pertain to the
        # organisation so we don't parse them here.
        res = None
        if not org:
            res = self.parse_residences(part, per)
            self.parse_con(part, per, 'po', PostalAddress, Has_postal_address)
        # Now parse the various contact details - phone/fax/mobile numbers,
        # email addresses, web pages, etc.  If this part is also used to
        # declare an organisation, then the unadorned 'ph', 'fax', etc. lines
        # pertain to the organisation, so instead we parse 'phh', 'faxh', etc.
        self.parse_con(part, per, 'mob', Telephone, Has_mobile)
        self.parse_con(part, res or per, 'phh', Telephone, Has_fixed_home)
        self.parse_con(part, res or per, 'faxh', Telephone, Has_fax_home)
        self.parse_con(part, per, 'emh', Email, Has_email_home)
        self.parse_con(part, per, 'wwwh', URI, Has_web_page)
        if not org:
            self.parse_con(part, res or per, 'ph', Telephone, Has_fixed)
            self.parse_con(part, res or per, 'fax', Telephone, Has_fax)
            self.parse_con(part, per, 'em', Email, Has_email)
            self.parse_con(part, per, 'www', URI, Has_web_page)
        # Now parse 'data', 'key', and associations, which take advantage of
        # the place context provided by residence and phone numbers already
        # parsed.
        if not org:
            self.parse_con(part, per, 'com', Comment, Has_comment)
            self.parse_data(part, per)
            self.parse_keywords(part, per)
            # Parse any 'work', 'with', and 'ex' sub-parts.
            self.parse_assoc(part, per, 'work', (Organisation, Residence),
                             Works_at, self.parse_assoc_contacts_work)
            self.parse_assoc(part, per, 'with', NamedNode, Associated_with,
                             self.parse_assoc_contacts)
            self.parse_assoc(part, per, 'ex', NamedNode, Ex,
                             self.parse_assoc_contacts)
        # Parse any 'in' sub-parts.
        for sub in (s for v, s in part.mget('in', []) if s):
            self.parse_con(sub, per, 'mob', Telephone, Has_mobile)
            self.parse_con(sub, res or per, 'phh', Telephone, Has_fixed_home)
            self.parse_con(sub, res or per, 'faxh', Telephone, Has_fax_home)
            if not org:
                res = self.parse_residences(sub, per)
                self.parse_con(sub, per, 'po', PostalAddress, Has_postal_address)
                self.parse_con(sub, res or per, 'ph', Telephone, Has_fixed_home)
                self.parse_con(sub, res or per, 'fax', Telephone, Has_fax_home)
                self.parse_data(sub, per)

    def parse_works_at(self, part, who, org):
        r'''Create a Works_at association between a person and organisation,
        and parse work contact details that pertain to the association link.
        This method is used when the works-at relationship is implicit (ie, not
        explicitly defined with a 'work' line), so the link does not have its
        own sub-part to contain contact and other details.
        '''
        wat = self.make_assoc(part, who, org, Works_at)
        self.parse_contacts_work(part, wat)
        return wat

    def parse_contacts_work(self, part, who):
        r'''Parse work-only contact details.
        '''
        self.parse_con(part, who, 'mobw', Telephone, Has_mobile_work)
        self.parse_con(part, who, 'phw', Telephone, Has_fixed_work)
        self.parse_con(part, who, 'faxw', Telephone, Has_fax_work)
        self.parse_con(part, who, 'emw', Email, Has_email_work)

    def parse_assoc(self, part, who, key, ntype, ltype, parse_sub=None):
        r'''Parse an association line, look up the referred node, and link it
        to a given node with an Associated_with or subclass thereof.  Parse any
        contact details, data, and comments that pertain to the association.
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
                    sub.defaults = part.defaults
                ass = self.make_assoc(sub, who, oth, ltype,
                                      timestamp=(sub or part).updated)
                if sub:
                    if parse_sub:
                        parse_sub(sub, ass)
                    self.parse_data(sub, ass)
                    self.parse_con(sub, ass, 'com', Comment, Has_comment)

    def make_assoc(self, part, who, oth, ltype, timestamp=None):
        r'''Create an Associate_with link (or subtype) between two nodes,
        with suitable constructor data.
        '''
        assert issubclass(ltype, Associated_with)
        # Here we should introspect the keyword args accepted by
        # ltype() and adapt accordingly.  One day.
        kw = {'timestamp': timestamp}
        if part:
            import inspect
            kwa = dict.fromkeys(inspect.getargspec(ltype.__init__)[0])
            if 'sequence' in kwa and hasattr(part, 'sequence'):
                kw['sequence'] = part.sequence
            if 'position' in kwa and 'pos' in part:
                kw['position'] = part.getvalue('pos')
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
        self.parse_con(part, ass, 'mobw', Telephone, Has_mobile_work)
        self.parse_con(part, ass, 'phw', Telephone, Has_fixed_work)
        self.parse_con(part, ass, 'faxw', Telephone, Has_fax_work)
        self.parse_con(part, ass, 'emw', Email, Has_email_work)
        self.parse_con(part, ass, 'mob', Telephone, Has_mobile_work)
        self.parse_con(part, ass, 'ph', Telephone, Has_fixed_work)
        self.parse_con(part, ass, 'fax', Telephone, Has_fax_work)
        self.parse_con(part, ass, 'em', Email, Has_email_work)

    def parse_con(self, part, who, key, ntype, ltype):
        r'''Parse a contact line and attach it to a given node.
        '''
        if key in part:
            for text in part.mgetvalue(key):
                obj, comment = ntype.parse(text,
                               place=part.place,
                               world=self.world,
                               default_place=who.place() or part.defaults.place)
                kw = {}
                if comment:
                    kw['comment'] = comment
                if part.updated:
                    kw['timestamp'] = part.updated
                ltype(who, obj, **kw)

    def parse_residences(self, part, who=None):
        r'''Parse 'ad' and 'home' lines for a person, family or organisation,
        which define to one or more residences and contact details for that
        person/organisation.
        '''
        residences = set()
        for value, sub in part.mget('ad', []):
            res, comment = Residence.parse(value,
                                   world=  self.world,
                                   place=  part.place,
                                   default_place=part.defaults.place)
            assert comment is None
            res = self.register(res)
            residences.add(res)
            if sub:
                # Parse contact details for this residence - phone/fax
                # numbers.
                sub.place = res.place()
                sub.updated = self.parse_update(sub) or part.updated
                sub.defaults = part.defaults
                self.parse_con(sub, res, 'ph', Telephone, Has_fixed)
                self.parse_con(sub, res, 'fax', Telephone, Has_fax)
                self.parse_con(sub, res, 'com', Comment, Has_comment)
            if who:
                Resides_at(who, res, timestamp=(sub or part).updated)
        if who:
            for value, sub in part.mget('home', []):
                try:
                    res = self.find(Residence, value)
                except LookupError, e:
                    raise InputError(e, char=value)
                if sub:
                    sub.place = res.place()
                    sub.updated = self.parse_update(sub) or part.updated
                    sub.defaults = part.defaults
                r = Resides_at(who, res, timestamp=(sub or part).updated)
                if sub:
                    self.parse_con(sub, r, 'ph', Telephone, Has_fixed)
                    self.parse_con(sub, r, 'fax', Telephone, Has_fax)
                    self.parse_con(sub, r, 'com', Comment, Has_comment)
        return iter(residences).next() if len(residences) == 1 else None

    def parse_keywords(self, part, who):
        r'''Parse 'key' lines in a given part, dereferencing and creating
        Keyword nodes for each keyword parsed, and attaching the given node
        (person, organisation) to each such Keyword node.
        '''
        omit = set()
        if 'key-' in part:
            for text in part.mgetvalue('key-'):
                for keyword in self.split_keywords(text):
                    omit.add(keyword)
        for keyword in self.defaults.keywords:
            if keyword not in omit:
                Keyed_with(who, keyword, timestamp=part.updated)
        if 'key' in part:
            for text in part.mgetvalue('key'):
                for keyword in self.split_keywords(text):
                    if keyword not in omit:
                        Keyed_with(who, keyword, timestamp=part.updated)

    def split_keywords(self, text):
        r'''Parse a string contining zero or more keywords and iterate over the
        resultant Keyword objects.
        '''
        for word in text.split():
            keyword, rem = Keyword.parse(word)
            assert rem is None
            yield self.register(keyword)

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
                if dat.key() in self.data_keys:
                    raise InputError('duplicate data %r for %s (%s)' %
                                     (id, who, context), char=text)
                self.data_keys[dat.key()] = dat

    def split_data(self, text):
        r'''Partially parse a 'data' or '%data' line into an id string and
        value.
        '''
        spl = text.split('=', 1)
        id = spl[0].rstrip()
        try:
            id = id.encode('ascii')
        except UnicodeEncodeError:
            raise InputError('data id %r contains non-ASCII character'
                             % unicode(id), char=id)
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

    def place(self):
        return self.node.place()

@link_predicate
def is_principal(node, link):
    r'''A Model.nodes() and Model.links() predicate that selects only links
    that are principal links in the model.
    '''
    return isinstance(link, In_model) and link.principal
