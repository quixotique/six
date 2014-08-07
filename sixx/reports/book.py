# vim: sw=4 sts=4 et fileencoding=utf8 nomod

r'''Booklet report.
'''

import time
from collections import defaultdict
from itertools import chain

from sixx.input import InputError
from sixx.text import sortstr, text_sort_key
from sixx.uniq import uniq
from sixx.multilang import multilang
from sixx.sort import *
from sixx.node import *
from sixx.node import node_predicate
from sixx.links import *
from sixx.person import *
from sixx.family import *
from sixx.org import *
from sixx.comment import *
from sixx.address import *
from sixx.telephone import *
from sixx.email import *
from sixx.struct import struct

def report_book_getopt(parser):
    parser.set_defaults(pagesize='filofax', sections='none')
    parser.add_option('-p', '--pagesize',
                      action='store', dest='pagesize',
                      choices=sorted(page_sizes),
                      help='use PAGESIZE as logical page size')
    parser.add_option('-s', '--sections',
                      action='store', dest='sections',
                      choices=sorted(sections),
                      help='use SECTIONS as alphabetic section grouping')

def report_book(options, model, predicate, local):
    if not options.output_path:
        raise InputError('missing --output option')
    # If no predicate given, then select all people, organisations, and
    # families.
    if predicate is None:
        predicate = node_predicate(lambda node: True)
    # Populate the top level of the report with all the nodes that satisfy the
    # predicate.
    itemiser = Itemiser()
    itemiser.update(model.nodes(is_other(instance_p(NamedNode) & predicate)))
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
    toplevel = sorted(chain(list(itemiser.items()),
                            itemiser.alias_items(iter(refs.items()))))
    refs.update(list(zip(itemiser, itemiser)))
    # Remove unnecessary references.
    cull_references(toplevel)
    # Format the report.
    booklet = Booklet(predicate=predicate, refs=refs, local=local,
                      page_size=page_sizes[options.pagesize],
                      sections=sections[options.sections])
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

paper_size = (210 * mm, 297 * mm) # landscape A4
paper_margins = (7.5 * mm, 7.5 * mm)

page_sizes = {
    'filofax':      struct(size=        (9.4 * cm, 17.1 * cm),
                           margin_left= 1 * cm),
    'agenda-juana': struct(size=       (7.6 * cm, 13.6 * cm),
                           margin_left= 7 * mm),
}

sections = {
    'none':         None,
    'single':       ('A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J',
                     'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T',
                     'U', 'V', 'W', 'X', 'Y', 'Z'),
    'single-wxyz':  ('A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J',
                     'K', 'L', 'M', 'NO', 'PQ', 'R', 'S', 'T',
                     'UV', 'WXYZ'),
    'pair':         ('AB', 'CD', 'EF', 'GH', 'IJ', 'KL', 'MN', 'OP',
                     'QR', 'ST', 'UV', 'WX', 'YZ'),
    'triple':       ('ABC', 'DEF', 'GHI', 'JKL', 'MNO', 'PQR', 'STU',
                     'VWX', 'YZ'),
}

def rotated(xy):
    return xy[1], xy[0]

styles = getSampleStyleSheet()

name_style = ParagraphStyle(name='Name',
                            fontSize=10, leading=12)

aka_style = ParagraphStyle(name='Aka',
                            fontSize=8, leading=10)

ref_style = ParagraphStyle(name='Reference',
                            parent=aka_style)

toplevel_ref_style = ParagraphStyle(name='TopReference',
                            parent=ref_style,
                            leftIndent=24, firstLineIndent=-24)

name_comment_style = ParagraphStyle(name='NameComment',
                            parent=aka_style,
                            fontName='Times-Italic')

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

continue_style=ParagraphStyle(name='Continue',
                            fontName='Times-Italic',
                            fontSize=8, leading=9)


qual_home = multilang(en='home', es='casa')
qual_work = multilang(en='work', es='trab')
NBSP = '\u00a0'
EN_DASH = '\u2013'
EM_DASH = '\u2014'
RIGHT_ARROW = '\u2192'
BLACK_DIAMOND = '\u25c6'
HEAVY_VERTICAL_BAR = '\u275a'
EMAIL_BULLET = BLACK_DIAMOND_MINUS_WHITE_X = '\u2756'
TELEPHONE_BULLET = BLACK_TELEPHONE = '\u260e'

class Booklet(object):

    r'''A booklet object is used to construct a booklet of entries that is
    designed to be cut to size and bound in a filofax.
    '''

    gutter = 0

    def __init__(self, predicate, refs, local, page_size, sections):
        self.predicate = predicate
        self.refs = refs
        self.local = local
        self.page_size = page_size
        self.sections = sections
        self.section = 0
        best_paper_size = best_paper_margins = None
        best_n = 0
        best_np = None
        for psize, pmarg in [(paper_size, paper_margins),
                             (rotated(paper_size), rotated(paper_margins))]:
            np = [None, None]
            for i in 0, 1:
                np[i] = int((psize[i] - pmarg[i] * 2 + self.gutter) /
                                (self.page_size.size[i] + self.gutter))
            n = np[0] * np[1]
            if n > best_n:
                best_paper_size, best_paper_margins = psize, pmarg
                best_n = n
                best_np = np
        assert best_n >= 1
        assert best_paper_size
        frames = []
        for iy in range(best_np[1]):
            for ix in range(best_np[0]):
                frames.append(CutFrame(
                    x1= best_paper_margins[0] +
                            ix * (self.page_size.size[0] + self.gutter),
                    y1= best_paper_margins[1] +
                            iy * (self.page_size.size[1] + self.gutter),
                    width=  self.page_size.size[0],
                    height= self.page_size.size[1],
                    leftPadding=   3 * mm + self.page_size.margin_left,
                    rightPadding=  3 * mm,
                    topPadding=    3 * mm,
                    bottomPadding= 3 * mm,
                    showBoundary=  True))
        self.page_width = (self.page_size.size[0] - 6 * mm
                                                  - self.page_size.margin_left)
        self.page = PageTemplate(frames=frames)
        self.doc = BookletDoc(None,
                    initialSection=self.sections[self.section] if self.sections
                                   else 'A-Z',
                    headerLeft=time.strftime(r'%-d %b %Y'),
                    headerRight=str(multilang(en='Page', es='Página')) +
                                ' <seq id="page" />',
                    pagesize=best_paper_size,
                    pageTemplates=[self.page],
                    leftMargin=0, rightMargin=0,
                    topMargin=0, bottomMargin=0,
                )
        self.flowables = []
        self._keeptogether_stack = []

    def write_pdf_to(self, path):
        r'''Generate the PDF for the booklet, writing it to a file with the
        given path name.
        '''
        self.doc.build(self.flowables, filename=path)

    def add_entry(self, item):
        letter = text_sort_key(item.key)[:1].upper() or 'Z'
        if self.sections:
            section = self.section
            while letter not in self.sections[section]:
                section += 1
                self.flowables.append(ActionFlowable(('newSection',
                                                      self.sections[section])))
                self.flowables.append(FrameBreak())
                self.section = section
        self.entry = []
        self.indent = 0
        self._empty_flag = True
        self.start_keep_together()
        self.entry.append(ActionFlowable(('entryTitle',
            Paragraph(escape_xml(item.key + '...'), continue_style))))
        if item is not item.single:
            self.add_names([item.key], refname=item.single.key, bold=False,
                           refstyle=toplevel_ref_style)
        else:
            self.add_names([item.key] + list(item.node.names()))
            if isinstance(item.node, Person):
                self.add_person(item.node)
            elif isinstance(item.node, Family):
                self.add_family(item.node)
            elif isinstance(item.node, Company):
                self.add_organisation(item.node)
        last_flowable = self.entry.pop()
        self.entry.append(KeepTogether([
                last_flowable,
                Rule(lineWidth=.5, spaceBefore=2, spaceAfter=1)],
            maxHeight= 4 * cm))
        self.entry.append(ActionFlowable(('entryTitle', None)))
        self.end_keep_together()
        self.flowables.extend(self.entry)

    def start_keep_together(self):
        r'''Start a KeepTogether sequence of flowables, which will be
        terminated by at the matching call to self.end_keep_together().
        '''
        self._keeptogether_stack.append(self.entry)
        self.entry = []

    def end_keep_together(self):
        r'''End a KeepTogether sequence of flowables which was started with its
        matching call to self.start_keep_together().
        '''
        keep = self.entry
        self.entry = self._keeptogether_stack.pop()
        if keep:
            self.entry.append(KeepTogether(keep, maxHeight= 4 * cm))

    def test_is_empty(self, func):
        r'''Return true if invoking the given callable would produce any
        important content, such as comments, birthday, contacts or addresses.
        '''
        entry, indent, eflag = self.entry, self.indent, self._empty_flag
        self.entry = []
        self._empty_flag = True
        func()
        ret = self._empty_flag
        self.entry, self.indent, self._empty_flag = entry, indent, eflag
        return ret

    def if_not_empty(self, func):
        r'''Append content to the current entry by calling func(), but if func
        tests as empty, then do not append anything.
        '''
        entry, indent, eflag = self.entry, self.indent, self._empty_flag
        self.entry = []
        self._empty_flag = True
        func()
        if not self._empty_flag:
            self.entry = entry + self.entry
            self._empty_flag = eflag
            return True
        self.entry, self.indent, self._empty_flag = entry, indent, eflag
        return False

    def _is_not_empty(self):
        r'''Called by any method whenever it outputs important information.
        Used internally to implement self.test_is_empty().
        '''
        self._empty_flag = False

    def _para(self, text, style, bullet='', proud=False,
              returnIndent=0, firstIndent=0, join_to_prev=False):
        r'''Append a paragraph to the current entry.  If the 'join_to_prev'
        argument is True then make the paragraph a continuation of the
        immediately preceding paragraph.
        '''
        lefti = style.leftIndent + 12 * self.indent + returnIndent
        firsti = style.firstLineIndent + firstIndent - returnIndent
        if bullet:
            bw = stringWidth(bullet, style.fontName, style.fontSize)
            firsti -= bw
            if not proud:
                lefti += bw
        paraclass = Paragraph
        if join_to_prev:
            # To accomplish a continuation paragraph, we use a variant of
            # Paragraph that reports its wrapped height as one line less than
            # it actually is.  This causes the reportlab document flow layout
            # to position it one line higher than it would actually be
            # otherwise, which makes its first line coincide vertically with
            # the last line of the prior paragraph.  So then, we make the
            # continuation paragraph have a first line indent that clears the
            # last line of the prior paragraph, plus a bit of space, and voila!
            # (But there's a wrinkle... see below.)
            prev = self.entry[-1]
            assert isinstance(prev, Paragraph)
            prev.wrap(availWidth=self.page_width, availHeight=1000*cm)
            w = prev.getActualLineWidths0()[-1]
            paraclass = ShortWrapParagraph
            firsti = w + style.fontSize / 2 - lefti
        istyle = ParagraphStyle(
                        name=           '%s-%d' % (style.name, self.indent),
                        parent=         style,
                        leftIndent=     lefti,
                        firstLineIndent=firsti)
        para = paraclass(bullet + text, istyle)
        if join_to_prev:
            # The reportlab paragraph wrapping logic always places the first
            # word on the first line, so when continuing the prior paragraph,
            # if there isn't enough space left on the prior paragraph's last
            # line, it can cause the first line of the continuing paragraph to
            # spill out of the available width.  In this case, we don't
            # continue the last line of the prior paragraph, we just start a
            # new paragraph under it.
            para.wrap(availWidth=self.page_width, availHeight=1000*cm)
            if para.getActualLineWidths0()[0] > self.page_width:
                istyle = ParagraphStyle(
                        name=           '%s-%d' % (style.name, self.indent),
                        parent=         style,
                        leftIndent=     lefti,
                        firstLineIndent=0)
                para = Paragraph(bullet + text, istyle)
        self.entry.append(para)
        return para

    def add_names(self, names, refname=None, bullet='', bold=True,
                  prefix='', suffix='', comments=(),
                  style=name_style, akastyle=aka_style, refstyle=ref_style,
                  comstyle=name_comment_style):
        names = uniq(names)
        first = next(names)
        if bold:
            startbold, endbold = '<b>', '</b>'
        else:
            startbold, endbold = '', ''
        if bullet:
            bullet = bullet + ' '
        bulletWidth = stringWidth(bullet, style.fontName, style.fontSize)
        if hasattr(first, 'sortsplit'):
            pre, sort, post = first.sortsplit()
            name = ''.join([escape_xml(pre),
                             startbold, escape_xml(sort), endbold,
                             escape_xml(post)])
        else:
            name = startbold + escape_xml(str(first)) + endbold
        first = str(first)
        para = [prefix, name, suffix]
        self._para(''.join(para), style, bullet=bullet)
        # Join AKA names onto the end of the name.
        para = []
        for aka in map(str, names):
            if aka != first:
                para += [' =', NBSP, escape_xml(aka)]
        if para:
            self._para(''.join(para), akastyle, returnIndent=bulletWidth,
                       join_to_prev=True)
        # Join reference arrow and text onto end of name.
        if refname:
            para = [' ', RIGHT_ARROW, NBSP, escape_xml(refname)]
            self._para(''.join(para), refstyle, returnIndent=bulletWidth,
                       join_to_prev=True)
        # Join comments onto end of name.
        para = []
        for c in comments:
            para += [' ', EN_DASH, NBSP, escape_xml(str(c))]
        if para:
            self._para(''.join(para), comstyle, returnIndent=bulletWidth,
                       join_to_prev=True)

    def add_person(self, per, link=None, show_family=True,
                                               show_work=True):
        self.add_comments(per)
        if per.birthday():
            self._is_not_empty()
            self._para(str(multilang(en='Birthday', es='Fecha nac.')) +
                           ': ' + str(per.birthday()),
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
                    self.add_names([next(link.family.sort_keys())],
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
                    position = escape_xml(str(link.position)) + ', '
                # If the organisation/residence where this person works has no
                # top level entry or has a top level reference to this person,
                # then list the organisation/residence here.  Otherwise, just
                # list a reference to its top level entry.
                top = self.refs.get(link.org, per)
                if top is per:
                    if isinstance(link.org, Residence):
                        self.indent += 1
                        self.add_address(link, link.org,
                                prefix='<i>' + str(qual_work).capitalize() +
                                       ':</i> ')
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
                    self.add_names([next(link.org.sort_keys())],
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
                self.start_keep_together()
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
                    self.add_names([next(link.person.sort_keys())],
                                   bullet=RIGHT_ARROW,
                                   comments=self.all_comments(link))
                    self.indent += 2
                    self.add_contacts(link, context=At_home)
                    self.indent -= 2
                else:
                    self.add_names([next(link.person.sort_keys())],
                                   bullet=EM_DASH,
                                   comments=self.all_comments(link))
                    self.indent += 2
                    self.add_contacts(link, context=At_home)
                    self.add_names([next(top.sort_keys())],
                                   bullet=RIGHT_ARROW, bold=False)
                    self.indent -= 2
                self.end_keep_together()
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
                    self.start_keep_together()
                    self.add_names([next(parent.company.sort_keys())],
                                   bullet=RIGHT_ARROW, bold=False,
                                   comments=self.all_comments(parent))
                    parent = None
                    self.end_keep_together()
        self.add_addresses(org)
        self.add_contacts(org, link)
        if parent:
            self.start_keep_together()
            self.add_names([next(parent.company.sort_keys())],
                           bullet=EM_DASH, bold=True,
                           comments=self.all_comments(parent))
            self.add_organisation(parent.company, parent,
                                  show_departments=False,
                                  show_workers=show_workers)
            self.end_keep_together()
        self.indent -= 1
        if show_workers:
            self.add_works_at(org)
        if show_departments:
            for link in sorted(org.links(outgoing & is_link(Has_department))):
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
                    self.start_keep_together()
                    self.add_names(link.dept.names(),
                                   bullet=EM_DASH, bold=True)
                    self.indent += 1
                    self.add_comments(link)
                    self.add_organisation(link.dept, link,
                                          show_workers=show_workers)
                    self.indent -= 1
                    self.end_keep_together()

    def add_works_at(self, org):
        for link in sorted(org.links(incoming & is_link(Works_at))):
            self.start_keep_together()
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
                position = ', ' + escape_xml(str(link.position))
            if top is com or (top is None and (link.is_head or
                                               self.predicate(link))):
                self._is_not_empty()
                # Special case: if the person has no top level entry but
                # belongs to a family that does, then list a reference to that
                # family.
                for linkf in link.person.links(outgoing & is_link(Belongs_to)):
                    if linkf.family in self.refs:
                        self.add_names([next(link.person.sort_keys())],
                                       suffix=position,
                                       refname=next(linkf.family.sort_keys()),
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
                name = next(link.person.sort_keys())
                if top is link.person:
                    self.add_names([name], bullet=RIGHT_ARROW, suffix=position,
                                   comments=self.all_comments(link))
                    self.indent += 2
                    self.add_contacts(link, context=At_work)
                    self.indent -= 2
                else:
                    self.add_names([name], bullet=EM_DASH,
                                   refname=next(top.sort_keys()),
                                   bold=True, suffix=position,
                                   comments=self.all_comments(link))
                    self.indent += 2
                    self.add_contacts(link, context=At_work)
                    self.indent -= 2
            self.end_keep_together()

    def all_comments(self, *nodes):
        for node in nodes:
            for com in node.nodes(outgoing & is_link(Has_comment)):
                yield com

    def add_comments(self, *nodes):
        for com in self.all_comments(*nodes):
            self._is_not_empty()
            self._para(escape_xml(str(com)), comment_style)

    def add_contacts(self, *nodes, **kwargs):
        context = kwargs.pop('context', None)
        if kwargs:
            raise TypeError(
                "%r is ann invalid keyword argument for this function" %
                    next(iter(kwargs.keys())))
        contacts = []
        for node in filter(bool, nodes):
            for typ in (Has_postal_address,
                        Has_mobile, Has_fixed, Has_fax,
                        Has_email):
                for link in node.links(outgoing & is_link(typ)):
                    self._is_not_empty()
                    label = ''
                    if isinstance(link, Has_postal_address):
                        self.add_address(link, link.postal)
                    elif isinstance(link, Has_email):
                        bullet = EMAIL_BULLET
                        cnode = link.email
                        contact = escape_xml(str(cnode).replace(' ', NBSP))
                        if isinstance(link, At_work):
                            if context != At_work:
                                label = str(qual_work).capitalize()
                        elif isinstance(link, At_home):
                            if context != At_home:
                                label = str(qual_home).capitalize()
                        if label:
                            label = '<i>' + label + '</i>'
                    else:
                        bullet = TELEPHONE_BULLET
                        cnode = link.tel
                        contact = ('<b>' +
                            escape_xml(str(link.tel.relative(self.local))) +
                            '</b>')
                        if isinstance(link, Has_fixed):
                            if isinstance(link, At_work):
                                label = str(qual_work).capitalize()
                            elif isinstance(link, At_home):
                                label = str(qual_home).capitalize()
                            else:
                                label = str(multilang(en='Tel', es='Tlf'))
                        else:
                            if isinstance(link, Has_mobile):
                                label = str(multilang(en='Mob', es='Móv'))
                            else:
                                assert isinstance(link, Has_fax)
                                label = 'Fax'
                            if isinstance(link, At_work):
                                label += ' ' + str(qual_work)
                            elif isinstance(link, At_home):
                                label += ' ' + str(qual_home)
                    comments = []
                    for n in cnode, link:
                        comment = getattr(n, 'comment', None)
                        if comment:
                            comments.append(comment)
                    if comments:
                        comments = (NBSP + '<i>' +
                            '; '.join(escape_xml(str(c)) for c in comments) +
                            '</i>')
                    else:
                        comments = ''
                    if label:
                        label += ': '
                    label = bullet + ' ' + label
                    contacts.append((label + contact).replace(' ', NBSP) +
                                    comments)
        self._para(' '.join(contacts), contacts_style)

    def add_addresses(self, who):
        # TODO: Located_at
        for link in who.links(outgoing & is_link(Resides_at)):
            self.add_address(link, link.residence)

    def add_address(self, link, addr, prefix=''):
        self._is_not_empty()
        self._para(prefix + escape_xml(addr.as_string(with_country=False)), address_style)
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
        self.__entryTitle = None

    def handle_newSection(self, section):
        self.__section = section

    def handle_entryTitle(self, title):
        self.__entryTitle = title

    def handle_frameBegin(self, resume=0):
        BaseDocTemplate.handle_frameBegin(self, resume=resume)
        self.frame.add(Paragraph(self.__headerLeft, header_left_style),
                       self.canv)
        self.frame.add(Paragraph(self.__headerRight, header_right_style),
                       self.canv)
        self.frame.add(Paragraph(' '.join(list(self.__section)), header_style),
                       self.canv)
        self.frame.add(Rule(lineWidth=.5, spaceBefore=2, spaceAfter=1),
                       self.canv)
        if self.__entryTitle:
            self.frame.add(self.__entryTitle, self.canv)

class CutFrame(Frame):

    def drawBoundary(self, canv):
        r'''Draw the frame boundary as cut marks.
        '''
        from reportlab.lib.colors import black, grey
        canv.saveState()
        canv.setStrokeColor(grey)
        canv.setLineWidth(.1)
        for x in self._x1, self._x2:
            for y in self._y1, self._y2:
                canv.saveState()
                canv.translate(x, y)
                canv.lines([(-10, 0, 10, 0), (0, -10, 0, 10)])
                canv.restoreState()
        canv.restoreState()

class ShortWrapParagraph(Paragraph):
    def wrap(self, availWidth, availHeight):
        w, h = Paragraph.wrap(self, availWidth, availHeight)
        assert h >= self.style.leading
        return w, h - self.style.leading

class Rule(Flowable):

    """A horizontal line.  It appears to have zero height, so that it doesn't
    get separated from its preceding flowable by a frame break."""

    _fixedWidth = False
    _fixedHeight = True

    def __init__(self, width=None, lineWidth=1, spaceBefore=0, spaceAfter=0):
        self.width = self._origWidth = width
        self.height = lineWidth
        self.lineWidth = lineWidth
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
        self.canv.setLineWidth(self.lineWidth)
        self.canv.line(0, 0, self.width, 0)
        self.canv.restoreState()

# Fix bugs in KeepTogether -- it merges adjacent space when calculating the
# height, which it shouldn't, and NullActionFlowable.apply() is missing the
# 'doc' arg, so it raises a TypeError in BaseDocTemplate.build().

import reportlab.platypus.flowables as _pf
import reportlab.platypus.doctemplate as _dt
from reportlab.rl_config import _FUZZ

class KeepTogether(_pf.KeepTogether):

    def wrap(self, aW, aH):
        dims = []
        W, H = _listWrapOn(self._content, aW, self.canv, mergeSpace=0,
                           dims=dims)
        self._H = self.wrapHeight = H
        self._H0 = dims and dims[0][1] or 0
        self._wrapInfo = aW, aH
        # Force a split, so that KeepTogether.draw() is never called (which we
        # don't implement).
        return W, 0xfffffff

    def split(self, aW, aH):
        if getattr(self, '_wrapInfo', None) != (aW, aH):
            self.wrap(aW, aH)
        S = self._content[:]
        C0 = self._H > aH
        C2 = self._maxHeight and aH > self._maxHeight
        C1 = self._H0 > aH
        if (C0 and not C2) or C1:
            A = _dt.FrameBreak
        else:
            # Prevent the logic in BaseDocTemplate.handle_flowable() from
            # raising a LayoutException.  Instead, it will insert our contents
            # at the top of the flowable list and iterate.
            A = NullActionFlowable
        S.insert(0, A())
        return S

def _listWrapOn(flowables, availWidth, canv, mergeSpace=True, dims=None):
    '''return max width, required height for a list of flowables'''
    W = 0
    H = 0
    pS = 0
    atTop = True
    for f in flowables:
        if hasattr(f, 'frameAction'):
            continue
        w, h = f.wrapOn(canv, availWidth, 0xfffffff)
        if h == 0xfffffff and hasattr(f, 'wrapHeight'):
            h = f.wrapHeight
        if dims is not None:
            dims.append((w, h))
        if w <= _FUZZ or h <= _FUZZ:
            continue
        W = max(W, w)
        H += h
        if not atTop:
            h = f.getSpaceBefore()
            if mergeSpace:
                h = max(h - pS, 0)
            H += h
        else:
            atTop = False
        pS = f.getSpaceAfter()
        H += pS
    return W, H - pS

class NullActionFlowable(_dt.NullActionFlowable):
    def apply(self, doc):
        pass
