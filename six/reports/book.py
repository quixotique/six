# vim: sw=4 sts=4 et fileencoding=latin1 nomod

r'''Booklet report.
'''

import time
from collections import defaultdict
from itertools import chain

from six.input import InputError
from six.text import sortstr, text_sort_key
from six.uniq import uniq
from six.multilang import multilang
from six.sort import *
from six.node import *
from six.links import *
from six.person import *
from six.family import *
from six.org import *
from six.comment import *
from six.address import *
from six.telephone import *
from six.email import *

def report_book(options, model, predicate, local, encoding):
    if not options.output_path:
        raise InputError('missing --output option')
    # If no predicate given, then select all people, organisations, and
    # families.
    if predicate is None:
        predicate = (instance_p(Person) |
                     instance_p(Company) |
                     instance_p(Family))
    # Populate the top level of the report with all the nodes that satisfy the
    # predicate.
    itemiser = Itemiser()
    itemiser.update(model.nodes(is_other(predicate)))
    # Top level references.  A dictionary that maps top level node to the node
    # in whose entry it appears.
    refs = dict()
    # Add top level nodes that are implied by the predicate:
    # - A selected department imples its parent company and all intermediate
    #   departments.  Departments are always listed within the entry of their
    #   parent company, so they are never listed as top level entries.  Any
    #   Departments at the top level are there because they were selected by
    #   the predicate, so these are converted into references to their
    #   company's entry.
    for node in list(itemiser):
        if isinstance(node, Department):
            dept = node
            com = dept.company()
            itemiser.discard(dept)
            itemiser.add(com)
            assert dept not in refs
            refs[dept] = com
    # Add top level nodes that are implied by the predicate:
    # - A selected person implies the family(ies) they belong to.  If a person
    #   belongs to only one family, then that person's top level entry becomes
    #   a reference to their family.
    for node in list(itemiser):
        if isinstance(node, Person):
            person = node
            # Omit top-level entries for people who belong to a single family
            # or who work for a single organisation, if the family/org has its
            # own top-level entry.  Instead, their details will get listed
            # within that entry.  Any top level entries for heads of families
            # get turned into aliases for the family.
            belongs_to = list(person.links(outgoing & is_link(Belongs_to)))
            if len(belongs_to) == 1 and belongs_to[0].family in itemiser:
                itemiser.discard(person)
                if belongs_to[0].is_head and person in refs:
                    refs[person] = belongs_to[0].family
    # Form the sorted index of all the top-level entries in the report, and
    # the 'refs' dictionary.
    toplevel = sorted(chain(itemiser.items(),
                            itemiser.alias_items(refs.iteritems())))
    refs.update(zip(itemiser, itemiser))
    # Remove unnecessary references.
    cull_references(toplevel)
    # Format the report.
    booklet = Booklet(predicate=predicate, refs=refs, local=local)
    for item in toplevel:
        if item.node is not None:
            booklet.add_entry(item)
    booklet.write_pdf_to(options.output_path)

from xml.sax.saxutils import escape as escape_xml
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                Flowable, Spacer, FrameBreak,
                                ActionFlowable)
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.units import cm, mm
from reportlab.pdfbase.pdfmetrics import stringWidth

page_size = (297 * mm, 210 * mm) # landscape A4
styles = getSampleStyleSheet()

name_style = ParagraphStyle(name='Name',
                            spaceAfter=2,
                            fontSize=10, leading=10)

toplevel_ref_style = ParagraphStyle(name='TopReference',
                            parent=name_style,
                            leftIndent=24, firstLineIndent=-24)

ref_style = ParagraphStyle(name='Reference',
                            parent=name_style,
                            fontSize=9, leading=10)

comment_style=ParagraphStyle(name='Comment',
                            fontName='Times-Italic',
                            fontSize=9, leading=10)

birthday_style=ParagraphStyle(name='Birthday',
                            fontName='Times-Italic',
                            fontSize=9, leading=10)

contacts_style=ParagraphStyle(name='Contacts',
                            fontName='Times-Roman',
                            fontSize=9, leading=10)

address_style=ParagraphStyle(name='Address',
                            fontName='Times-Roman',
                            fontSize=9, leading=10)

header_style=ParagraphStyle(name='Header',
                            fontName='Times-Bold',
                            alignment=TA_CENTER)

header_left_style=ParagraphStyle(name='HeaderLeft',
                            fontName='Times-Italic',
                            fontSize=8,
                            alignment=TA_LEFT,
                            leading=0)

header_right_style=ParagraphStyle(name='HeaderRight',
                            fontName='Times-Italic',
                            fontSize=8,
                            alignment=TA_RIGHT,
                            leading=0)

sections = ('AB', 'CD', 'EF', 'GH', 'IJ', 'KL', 'MN',
            'OP', 'QR', 'ST', 'UV', 'WX', 'YZ')

qual_home = multilang(en='home', es='casa')
qual_work = multilang(en='work', es='trab')
NBSP = u'\u00a0'
EN_DASH = u'\u2013'
EM_DASH = u'\u2014'
RIGHT_ARROW = u'\u2192'
BLACK_BOX = u'\u25c6'

class Booklet(object):

    r'''A booklet object is used to construct a booklet of entries that is
    designed to be cut to size and bound in a filofax.
    '''

    def __init__(self, predicate, refs, local):
        self.predicate = predicate
        self.refs = refs
        self.local = local
        self.section = 0
        self.page = PageTemplate(
                frames=[CutFrame(x1=x1, y1=1.8*cm, width=9.4*cm, height=17.1*cm,
                                 leftPadding=14*mm, rightPadding=2*mm,
                                 topPadding=3*mm, bottomPadding=3*mm,
                                 showBoundary=True)
                        for x1 in 8*mm, 10.2*cm, 19.6*cm])
        self.doc = BookletDoc(None,
                    initialSection=sections[self.section],
                    headerLeft=time.strftime(r'%-d %b %Y'),
                    headerRight=unicode(multilang(en='Page', es=u'Página')) +
                                u' <seq id="page" />',
                    pagesize=page_size,
                    pageTemplates=[self.page],
                    leftMargin=0, rightMargin=0,
                    topMargin=0, bottomMargin=0,
                )
        self.flowables = []
        self._stack = []

    def write_pdf_to(self, path):
        r'''Generate the PDF for the booklet, writing it to a file with the
        given path name.
        '''
        self.doc.build(self.flowables, filename=path)

    def set_section(self, section):
        self.flowables.append(ActionFlowable(('newSection', sections[section])))
        self.section = section

    def add_entry(self, item):
        letter = text_sort_key(item.key)[:1].upper() or 'Z'
        section = self.section
        while letter not in sections[section]:
            section += 1
        if section != self.section:
            self.set_section(section)
            self.flowables.append(FrameBreak())
        self.entry = []
        self.indent = 0
        self._empty_flag = True
        if item is not item.single:
            self.add_names([item.key], refname=item.single.key, bold=False)
            rulegap = 4
        else:
            self.add_names([item.key] + list(item.node.names()))
            if isinstance(item.node, Person):
                self.add_person(item.node)
            elif isinstance(item.node, Family):
                self.add_family(item.node)
            elif isinstance(item.node, Company):
                self.add_organisation(item.node)
            else:
                assert False, repr(item.node)
            rulegap = 2
        self.entry.append(Rule(height=.5, spaceBefore=rulegap, spaceAfter=1))
        self.flowables.append(KeepTogether(self.entry))

    def test_is_empty(self, func):
        r'''Return true if invoking the given callable would produce any
        important content, such as comments, birthday, contacts or addresses.
        '''
        self._stack.append((self.entry, self.indent, self._empty_flag))
        self.entry = []
        self._empty_flag = True
        func()
        ret = self._empty_flag
        self.entry, self.indent, self._empty_flag = self._stack.pop()
        return ret

    def if_not_empty(self, func):
        r'''Append content to the current entry by calling func(), but if func
        tests as empty, then do not append anything.
        '''
        self._stack.append((self.entry, self.indent, self._empty_flag))
        self.entry = []
        self._empty_flag = True
        func()
        if not self._empty_flag:
            top = self._stack.pop()
            self.entry = top[0] + self.entry
            self._empty_flag = top[2]
            return True
        self.entry, self.indent, self._empty_flag = self._stack.pop()
        return False

    def _is_not_empty(self):
        r'''Called by any method whenever it outputs important information.
        Used internally to implement self.test_is_empty().
        '''
        self._empty_flag = False

    def _para(self, text, style, bullet='', proud=False, returnIndent=0):
        r'''Append a paragraph to the current entry.
        '''
        lefti = style.leftIndent + 12 * self.indent + returnIndent
        firsti = style.firstLineIndent - returnIndent
        if bullet:
            bw = stringWidth(bullet, style.fontName, style.fontSize)
            firsti -= bw
            if not proud:
                lefti += bw
        istyle = ParagraphStyle(
                        name=           '%s-%d' % (style.name, self.indent),
                        parent=         style,
                        leftIndent=     lefti,
                        firstLineIndent=firsti)
        self.entry.append(Paragraph(bullet + text, istyle))

    def add_names(self, names, refname=None, bullet='', bold=True,
                  prefix='', suffix='', comments=()):
        names = uniq(names)
        first = names.next()
        if bold:
            startbold, endbold = u'<b>', u'</b>'
        else:
            startbold, endbold = u'', u''
        if hasattr(first, 'sortsplit'):
            pre, sort, post = first.sortsplit()
            name = u''.join([escape_xml(pre),
                             startbold, escape_xml(sort), endbold,
                             escape_xml(post)])
        else:
            name = startbold + escape_xml(unicode(first)) + endbold
        first = unicode(first)
        para = [prefix, name, suffix]
        for aka in map(unicode, names):
            if aka != first:
                para += [u' <font size="%d">=' % (name_style.fontSize - 2),
                         NBSP, escape_xml(aka), u'</font>']
        if refname:
            para += [(u' <font size="%d">' % (toplevel_ref_style.leading - 2)),
                     RIGHT_ARROW, u' ', escape_xml(refname), u'</font>']
        if bullet:
            bullet = bullet + ' '
        if comments:
            para += [u' <font size="%d"><i>' % (name_style.fontSize - 2),
                     ' '.join(EN_DASH + NBSP + escape_xml(unicode(c))
                              for c in comments),
                     u'</i></font>']
        self._para(u''.join(para), name_style, bullet=bullet)

    def add_person(self, per, link=None, show_family=True,
                                               show_work=True):
        self.add_comments(per)
        if per.birthday():
            self._is_not_empty()
            self._para(unicode(multilang(en='Birthday', es='Fecha nac.')) +
                           ': ' + unicode(per.birthday()),
                       birthday_style)
        self.indent += 1
        self.add_addresses(per)
        self.add_contacts(per, link)
        self.indent -= 1
        if show_family:
            for link in per.links(outgoing & is_link(Belongs_to)):
                # If this person's family has no top level entry, or has a top
                # level reference to this person, then list the family here.
                # Otherwise, just list a reference to the family.
                top = self.refs.get(link.family, per)
                if top is per:
                    self.add_names(link.family.names(), bullet=EM_DASH)
                    self.indent += 1
                    self.add_comments(link)
                    self.add_family(link.family, link, show_members=False)
                    self.indent -= 1
                else:
                    self.add_names([link.family.sort_keys().next()],
                                   bullet=RIGHT_ARROW, bold=False,
                                   comments=self.all_comments(link))
                    self.indent += 2
                    self.add_contacts(link, context=At_home)
                    self.indent -= 2
        if show_work:
            for link in per.links(outgoing & is_link(Works_at)):
                position = ''
                if link.position:
                    self._is_not_empty()
                    position = escape_xml(unicode(link.position)) + ', '
                # If the organisation/residence where this person works has no
                # top level entry or has a top level reference to this person,
                # then list the organisation/residence here.  Otherwise, just
                # list a reference to its top level entry.
                top = self.refs.get(link.org, per)
                if top is per:
                    if isinstance(link.org, Residence):
                        self.indent += 1
                        self.add_address(link, link.org,
                                prefix=u'<i>' + unicode(qual_work).capitalize() +
                                       u':</i> ')
                        self.indent -= 1
                    else:
                        self.add_names(link.org.names(), bullet=EM_DASH,
                                       prefix=position)
                        self.indent += 1
                        self.add_comments(link)
                        self.add_organisation(link.org, link, show_parents=True,
                                              show_workers=False)
                        self.indent -= 1
                else:
                    self.add_names([link.org.sort_keys().next()],
                                   bullet=RIGHT_ARROW, bold=False,
                                   prefix=position,
                                   comments=self.all_comments(link))
                    self.indent += 2
                    self.add_contacts(link, context=At_work)
                    self.indent -= 2

    def add_family(self, fam, link=None, show_members=True):
        self.add_comments(fam)
        self.indent += 1
        self.add_addresses(fam)
        self.add_contacts(fam, link)
        self.indent -= 1
        if show_members:
            omitted = []
            for link in sorted(fam.links(incoming & is_link(Belongs_to)),
                               key=lambda l: (not l.is_head,
                                              l.sequence or 0,
                                              l.person.sortkey())):
                # If this member has no top level entry, or has a top level
                # reference to this family, then list the member here.
                # Otherwise, just list a reference to the entry where the
                # person is listed.
                top = self.refs.get(link.person, fam)
                if top is fam:
                    def add_member():
                        anames = list(link.person.names(with_aka=False))
                        names = []
                        if link.is_head:
                            hn = link.person.family_head_name()
                            names = [n for n in names
                                     if hn != n and not hn.startswith(n + ' ')]
                        if names:
                            self._is_not_empty()
                        else:
                            names = anames
                        self.add_names(names, bullet=EM_DASH)
                        self.indent += 1
                        self.add_comments(link)
                        self.add_person(link.person, link, show_family=False)
                        self.indent -= 1
                    if not self.if_not_empty(add_member):
                        omitted.append(link)
                elif top is link.person:
                    self.add_names([link.person.sort_keys().next()],
                                   bullet=RIGHT_ARROW,
                                   comments=self.all_comments(link))
                    self.indent += 2
                    self.add_contacts(link, context=At_home)
                    self.indent -= 2
                else:
                    self.add_names([link.person.sort_keys().next()],
                                   bullet=EM_DASH,
                                   comments=self.all_comments(link))
                    self.indent += 2
                    self.add_contacts(link, context=At_home)
                    self.add_names([top.sort_keys().next()],
                                   bullet=RIGHT_ARROW, bold=False)
                    self.indent -= 2
            # Omitted family members who are not heads will not be mentioned
            # anywhere unless we list them here.
            plus = [link.person for link in omitted if not link.is_head]
            if plus:
                self._is_not_empty()
                self.indent += 1
                self._para((' +' + NBSP).join(per.complete_name()
                                              for per in plus),
                           name_style, bullet='+ ', proud=True)
                self.indent -= 1

    def add_organisation(self, org, link=None, show_workers=True,
                         show_parents=False, show_departments=True):
        self.add_comments(org)
        self.indent += 1
        parent = None
        if show_parents:
            if isinstance(org, Department):
                # If the parent organisation has a top level entry, then refer
                # to it.  Otherwise, we list it below.
                parent = org.link(incoming & is_link(Has_department))
                assert parent is not None
                if parent.company in self.refs:
                    self.add_names([parent.company.sort_keys().next()],
                                   bullet=RIGHT_ARROW, bold=False,
                                   comments=self.all_comments(parent))
                    parent = None
        self.add_addresses(org)
        self.add_contacts(org, link)
        if parent:
            self.add_names([parent.company.sort_keys().next()],
                           bullet=EM_DASH, bold=True,
                           comments=self.all_comments(parent))
            self.add_organisation(parent.company, parent,
                                  show_departments=False,
                                  show_workers=show_workers)
        self.indent -= 1
        if show_workers:
            self.add_works_at(org)
        if show_departments:
            for link in org.links(outgoing & is_link(Has_department)):
                # Departments' top level entries are always references to their
                # parent company's top level entry.  So we list departments
                # here in full -- no references.  Only departments with top
                # level entries, or are head departments, or whose link
                # satisfies the predicate get listed.
                top = self.refs.get(link.dept)
                if top is not None:
                    com = org if isinstance(org, Company) else org.company()
                    assert top is com, '%r is in %r, should be in %r' % (
                                                            link.dept, top, com)
                if top or link.is_head or self.predicate(link):
                    self._is_not_empty()
                    self.add_names(link.dept.names(),
                                   bullet=EM_DASH, bold=True)
                    self.indent += 1
                    self.add_comments(link)
                    self.add_organisation(link.dept, link,
                                          show_workers=show_workers)
                    self.indent -= 1

    def add_works_at(self, org):
        for link in sorted(org.links(incoming & is_link(Works_at))):
            # If the person has a top level reference to the company entry in
            # which this organisation appears, or has no top level entry but is
            # a principal of the company, then list the person here.
            # Otherwise, list a reference to the entry where the person is
            # listed.
            com = org if isinstance(org, Company) else org.company()
            top = self.refs.get(link.person)
            position = ''
            if link.position:
                self._is_not_empty()
                position = ', ' + escape_xml(unicode(link.position))
            if top is com or (top is None and (link.is_head or
                                               self.predicate(link))):
                self._is_not_empty()
                # Special case: if the person has no top level entry but
                # belongs to a family that does, then list a reference to that
                # family.
                for linkf in link.person.links(outgoing & is_link(Belongs_to)):
                    if linkf.family in self.refs:
                        self.add_names([link.person.sort_keys().next()],
                                       suffix=position,
                                       refname=linkf.family.sort_keys().next(),
                                       bullet=RIGHT_ARROW,
                                       comments=self.all_comments(link))
                        self.indent += 2
                        self.add_contacts(link, context=At_work)
                        self.indent -= 2
                        break
                else:
                    self.add_names(link.person.names(), suffix=position,
                                   bullet=EM_DASH,
                                   comments=self.all_comments(link))
                    self.indent += 1
                    self.add_person(link.person, link, show_work=False)
                    self.indent -= 1
            elif top is not None:
                name = link.person.sort_keys().next()
                if top is link.person:
                    self.add_names([name], bullet=RIGHT_ARROW, suffix=position,
                                   comments=self.all_comments(link))
                    self.indent += 2
                    self.add_contacts(link, context=At_work)
                    self.indent -= 2
                else:
                    self.add_names([name], bullet=EM_DASH,
                                   refname=top.sort_keys().next(),
                                   bold=True, suffix=position,
                                   comments=self.all_comments(link))
                    self.indent += 2
                    self.add_contacts(link, context=At_work)
                    self.indent -= 2

    def all_comments(self, *nodes):
        for node in nodes:
            for com in node.nodes(outgoing & is_link(Has_comment)):
                yield com

    def add_comments(self, *nodes):
        for com in self.all_comments(*nodes):
            self._is_not_empty()
            self._para(unicode(com), comment_style)

    def add_contacts(self, *nodes, **kwargs):
        context = kwargs.pop('context', None)
        if kwargs:
            raise TypeError(
                "%r is ann invalid keyword argument for this function" %
                    kwargs.iterkeys().next())
        contacts = []
        for node in filter(bool, nodes):
            for typ in Has_mobile, Has_fixed, Has_fax, Has_email:
                for link in node.links(outgoing & is_link(typ)):
                    self._is_not_empty()
                    label = ''
                    if isinstance(link, Has_email):
                        cnode = link.email
                        contact = escape_xml(str(cnode).replace(u' ', NBSP))
                        if isinstance(link, At_work):
                            if context != At_work:
                                label = unicode(qual_work).capitalize()
                        elif isinstance(link, At_home):
                            if context != At_home:
                                label = unicode(qual_home).capitalize()
                        if label:
                            label = '<i>' + label + '</i>'
                    else:
                        cnode = link.tel
                        contact = (u'<b>' +
                            escape_xml(unicode(link.tel.relative(self.local))) +
                            u'</b>')
                        if isinstance(link, Has_fixed):
                            if isinstance(link, At_work):
                                label = unicode(qual_work).capitalize()
                            elif isinstance(link, At_home):
                                label = unicode(qual_home).capitalize()
                            else:
                                label = unicode(multilang(en='Tel', es=u'Tlf'))
                        else:
                            if isinstance(link, Has_mobile):
                                label = unicode(multilang(en='Mob', es=u'Móv'))
                            else:
                                assert isinstance(link, Has_fax)
                                label = u'Fax'
                            if isinstance(link, At_work):
                                label += ' ' + unicode(qual_work)
                            elif isinstance(link, At_home):
                                label += ' ' + unicode(qual_home)
                    comments = []
                    for n in cnode, link:
                        comment = getattr(n, 'comment', None)
                        if comment:
                            comments.append(comment)
                    if comments:
                        comments = (NBSP + u'<i>' +
                            u'; '.join(escape_xml(unicode(c)) for c in comments) +
                            u'</i>')
                    else:
                        comments = ''
                    if label:
                        label += u': '
                    label = BLACK_BOX + u' ' + label
                    contacts.append((label + contact).replace(u' ', NBSP) +
                                    comments)
        self._para(u' '.join(contacts), contacts_style)

    def add_addresses(self, who):
        for typ in Resides_at, Has_postal_address:
            for link in who.links(outgoing & is_link(typ)):
                self.add_address(link, link.node2)

    def add_address(self, link, addr, prefix=''):
        self._is_not_empty()
        self._para(prefix + addr.as_unicode(with_country=False),
                   address_style)
        self.indent += 1
        self.add_comments(link, addr)
        self.add_contacts(link, addr)
        self.indent -= 1

class BookletDoc(BaseDocTemplate):

    def __init__(self, filename, initialSection=None,
                 headerLeft='', headerRight='', **kw):
        BaseDocTemplate.__init__(self, filename, **kw)
        self.__section = initialSection
        self.__headerLeft = headerLeft
        self.__headerRight = headerRight

    def handle_newSection(self, section):
        self.__section = section

    def handle_frameBegin(self, resume=0):
        BaseDocTemplate.handle_frameBegin(self, resume=resume)
        self.frame.add(Paragraph(self.__headerLeft, header_left_style),
                       self.canv)
        self.frame.add(Paragraph(self.__headerRight, header_right_style),
                       self.canv)
        self.frame.add(Paragraph(' '.join(list(self.__section)), header_style),
                       self.canv)
        self.frame.add(Rule(height=.5, spaceBefore=2, spaceAfter=1), self.canv)

class CutFrame(Frame):

    def drawBoundary(self, canv):
        r'''Draw the frame boundary as cut marks.
        '''
        from reportlab.lib.colors import black
        canv.saveState()
        canv.setStrokeColor(black)
        canv.setLineWidth(.1)
        for x in self._x1, self._x2:
            for y in self._y1, self._y2:
                canv.saveState()
                canv.translate(x, y)
                canv.lines([(-10, 0, 10, 0), (0, -10, 0, 10)])
                canv.restoreState()
        canv.restoreState()

class Rule(Flowable):

    """A horizontal line."""

    _fixedWidth = False
    _fixedHeight = True

    def __init__(self, width=None, height=1, spaceBefore=0, spaceAfter=0):
        self.width = self._origWidth = width
        self.height = height
        self.spaceBefore = spaceBefore
        self.spaceAfter = spaceAfter

    def __repr__(self):
        return "%s(%s, %s)" % (self.__class__.__name__, self.width, self.height)

    def wrap(self, availWidth, availHeight):
        if self._origWidth is None:
            self.width = availWidth
        return self.width, self.height

    def draw(self):
        from reportlab.lib.colors import black
        self.canv.saveState()
        self.canv.setStrokeColor(black)
        self.canv.setLineWidth(self.height)
        y = -self.height / 2
        self.canv.line(0, y, self.width, y)
        self.canv.restoreState()

# Fix a bug in KeepTogether -- it merges adjacent space when calculating the
# height, which it shouldn't.
import reportlab.platypus.flowables as _pf
class KeepTogether(_pf.KeepTogether):
    def wrap(self, aW, aH):
        dims = []
        W,H = _pf._listWrapOn(self._content,aW,self.canv,mergeSpace=0,dims=dims)
        self._H = H
        self._H0 = dims and dims[0][1] or 0
        self._wrapInfo = aW,aH
        return W, 0xffffff  # force a split
